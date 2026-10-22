"""面板 08：传递函数与视频信号（`POST /api/v1/transfer`）。

一块光要进文件，先过“传递函数”（OETF/EOTF/对数编码）；进了文件要进 YCbCr，再过一遍矩阵。
这两步都是**可逆**的，所以面板的论点是“往返误差有多小、曲线长什么样”。

编码目录不硬编码函数名，而是从 colour 的公开表里现取，避免版本漂移时静默错位：

- `colour.OETFS`：12 个广播/显示 OETF，逆函数按 `oetf_inverse_<后缀>` 约定找；
  找不到的（0.4.7 里 `oetf_SMPTE240M` 就没有逆函数）如实标成“无逆变换”，不假装能往返；
- `colour.LOG_ENCODINGS` / `colour.LOG_DECODINGS`：32 组对数编码，正逆成对；
- sRGB 走显示编码 `eotf_inverse_sRGB` / `eotf_sRGB`（它的命名不在 OETF 里，单独列）。

注意口径：这些曲线作用在**归一化编码值**上，不是绝对亮度；PQ/HLG 的“绝对”含义要靠
BT.2100 的参考白与峰值亮度换算，面板只比较曲线形状与可逆性。
"""

from __future__ import annotations

import contextlib
import io
import warnings

import numpy as np

import colour

from ..config import MAX_COLOURS
from ..core.diagnostics import WarningCollector, number, numbers
from ..core.errors import value_error
from ..core.parsing import parse_colours, rgb_to_hex

GROUP_OETF = "广播 / 显示 OETF"
GROUP_LOG = "对数编码（Log）"
GROUP_SRGB = "sRGB 显示编码"

MAX_ENCODINGS = 12
DEFAULT_ENCODINGS = (
    "sRGB",
    "ITU-R BT.709",
    "ITU-R BT.2100 PQ",
    "ITU-R BT.2100 HLG",
    "S-Log3",
    "ARRI LogC3",
    "ACEScct",
)
LUMA_PRESETS = tuple(colour.WEIGHTS_YCBCR)
DEFAULT_LUMA = "ITU-R BT.709"


def _inverse_oetf(encoder) -> object | None:
    """按 `oetf_BT709` → `oetf_inverse_BT709` 的约定找逆函数；没有就返回 None。"""

    name = getattr(encoder, "__name__", "")
    if not name.startswith("oetf_"):
        return None
    return getattr(colour.models, "oetf_inverse_" + name[len("oetf_") :], None)


def _catalogue() -> dict[str, dict]:
    entries: dict[str, dict] = {
        "sRGB": {
            "group": GROUP_SRGB,
            "encode": colour.models.eotf_inverse_sRGB,
            "decode": colour.models.eotf_sRGB,
        }
    }
    for name, encoder in colour.OETFS.items():
        entries[name] = {"group": GROUP_OETF, "encode": encoder, "decode": _inverse_oetf(encoder)}
    for name, encoder in colour.LOG_ENCODINGS.items():
        entries[name] = {"group": GROUP_LOG, "encode": encoder, "decode": colour.LOG_DECODINGS.get(name)}
    return entries


CATALOGUE = _catalogue()
ENCODING_NAMES = tuple(sorted(CATALOGUE))


def _curve(entry: dict, samples: int) -> dict:
    """编码曲线：线性光 → 编码值。个别编码在 0 附近无定义，逐点兜住。"""

    # 对数编码在 0 处是 -inf，采样从 1e-4 起；否则曲线端点会是 nan/None 且刷一堆 RuntimeWarning
    inputs = np.linspace(1e-4, 1.0, samples)
    encoded = []
    for value in inputs:
        with warnings.catch_warnings():
            # 个别对数编码在极小输入上会告警（log(0) 的极限），不影响曲线主体
            warnings.filterwarnings("ignore", category=RuntimeWarning)
            try:
                encoded.append(number(entry["encode"](float(value)), 5))
            except Exception:
                encoded.append(None)

    roundtrip = None
    if entry["decode"] is not None:
        errors = []
        for value in np.linspace(0.02, 0.98, 25):
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=RuntimeWarning)
                try:
                    errors.append(abs(float(entry["decode"](float(entry["encode"](float(value))))) - float(value)))
                except Exception:
                    continue
        if errors:
            roundtrip = number(max(errors), 10)

    return {
        "linear": [round(float(value), 5) for value in inputs],
        "encoded": encoded,
        "roundtrip_error": roundtrip,
        "invertible": entry["decode"] is not None,
    }


def _itu_table(describe, code_points, limit: int = 6) -> list[dict]:
    """把 ITU-T H.273 的代码点翻译成人话。

    `describe_video_signal_*` 会**直接 print** 一张 ASCII 表再返回同一段文本，
    服务里不能让它往 stdout 上刷屏，所以整段调用重定向掉。
    """

    rows = []
    for code in code_points:
        if len(rows) >= limit:
            break
        buffer = io.StringIO()
        try:
            with contextlib.redirect_stdout(buffer):
                text = str(describe(code))
        except Exception:
            continue
        # 返回文本里先有一行表头（`Matrix Coefficients: 1`），后面才是内容；
        # 所以要取**最后**一条匹配，不能取第一条。
        summary = ""
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith(("Function", "Matrix Coefficients")):
                value = stripped.split(":", 1)[-1].strip()
                if "<function " in value:  # 只要函数名，不要内存地址
                    value = value.split("<function ")[1].split(" at ")[0]
                summary = value
        # reserved / unspecified 两类代码点没有信息量，跳过
        if not summary or summary.startswith("_") or summary.lower() in {"reserved", "unspecified"}:
            continue
        rows.append({"code": int(code), "summary": summary})
    return rows


def transfer_data(
    colours: list[str] | None = None,
    encodings: list[str] | None = None,
    samples: int = 33,
    luma: str = DEFAULT_LUMA,
    bits: int = 8,
    limited_range: bool = True,
) -> dict:
    if not (5 <= samples <= 101):
        raise value_error("samples 需在 5–101")
    if bits not in (8, 10, 12, 16):
        raise value_error(f"bits 只支持 8 / 10 / 12 / 16，当前 {bits}")
    if luma not in LUMA_PRESETS:
        raise value_error(f"未知亮度权重 {luma!r}，可选：{list(LUMA_PRESETS)}")

    names = list(encodings or DEFAULT_ENCODINGS)
    if len(names) > MAX_ENCODINGS:
        raise value_error(f"编码最多 {MAX_ENCODINGS} 个，当前 {len(names)} 个")
    unknown = [name for name in names if name not in CATALOGUE]
    if unknown:
        raise value_error(f"未知编码 {unknown}；可用（节选）：{list(ENCODING_NAMES[:10])}")

    specs = list(colours or ["#3B82F6"])
    if len(specs) > MAX_COLOURS:
        raise value_error(f"colors 最多 {MAX_COLOURS} 个，当前 {len(specs)} 个")

    weights = colour.WEIGHTS_YCBCR[luma]

    with WarningCollector() as log:
        curves = []
        for name in names:
            entry = CATALOGUE[name]
            row = {"name": name, "group": entry["group"], **_curve(entry, samples)}
            if entry["decode"] is None:
                log.add("note", f"{name} 在 colour 0.4.7 里没有对应的逆函数，往返误差不可计算")
            curves.append(row)

        # YCbCr：同一支颜色在“合法范围 / 满范围”下的编码值（这是视频链路的常见坑）
        ycbcr_rows = []
        for spec, rgb in zip(specs, parse_colours(specs)):
            row = {"input": spec, "hex": rgb_to_hex(rgb), "rgb": numbers(rgb, 5)}
            for label, legal in (("limited", True), ("full", False)):
                try:
                    encoded = np.asarray(
                        colour.models.RGB_to_YCbCr(
                            rgb,
                            K=weights,
                            in_bits=bits,
                            in_legal=True,
                            in_int=False,
                            out_bits=bits,
                            out_legal=legal,
                            out_int=False,
                        ),
                        dtype=float,
                    )
                    restored = np.asarray(
                        colour.models.YCbCr_to_RGB(
                            encoded,
                            K=weights,
                            in_bits=bits,
                            in_legal=legal,
                            in_int=False,
                            out_bits=bits,
                            out_legal=True,
                            out_int=False,
                        ),
                        dtype=float,
                    )
                    # 再走一次 out_int=True，让 colour 自己出整数码值（和播放器/示波器对表用）
                    codes = np.asarray(
                        colour.models.RGB_to_YCbCr(
                            rgb,
                            K=weights,
                            in_bits=bits,
                            in_legal=True,
                            in_int=False,
                            out_bits=bits,
                            out_legal=legal,
                            out_int=True,
                        ),
                        dtype=int,
                    )
                    row[label] = {
                        "ycbcr": numbers(encoded, 5),
                        "codes": [int(code) for code in codes.ravel()],
                        "roundtrip_error": number(np.max(np.abs(restored - np.asarray(rgb, dtype=float))), 8),
                    }
                except Exception as error:
                    row[label] = None
                    log.add("unavailable", f"{spec} 的 YCbCr（{label}）换算失败：{type(error).__name__}")
            ycbcr_rows.append(row)

        log.add(
            "note",
            "曲线横轴是归一化编码值（0–1 线性光），不是绝对亮度；"
            "PQ / HLG 的绝对含义依赖 BT.2100 的参考白与峰值亮度，本面板只比形状与可逆性。"
            f" YCbCr 用 {luma} 权重、{bits} bit、{'limited' if limited_range else 'full'} range。",
        )

    return {
        "catalogue": {
            "groups": {
                GROUP_SRGB: [name for name, entry in CATALOGUE.items() if entry["group"] == GROUP_SRGB],
                GROUP_OETF: sorted(name for name, entry in CATALOGUE.items() if entry["group"] == GROUP_OETF),
                GROUP_LOG: sorted(name for name, entry in CATALOGUE.items() if entry["group"] == GROUP_LOG),
            },
            "counts": {
                "eotfs": len(colour.EOTFS),
                "oetfs": len(colour.OETFS),
                "log_encodings": len(colour.LOG_ENCODINGS),
                "matrix_coefficients": len(colour.models.MATRIX_COEFFICIENTS_ITUTH273),
                "transfer_characteristics": len(colour.models.TRANSFER_CHARACTERISTICS_ITUTH273),
            },
        },
        "samples": samples,
        "curves": curves,
        "ycbcr": {"luma": luma, "bits": bits, "limited_range": limited_range, "rows": ycbcr_rows},
        "itu": {
            "matrix_coefficients": _itu_table(
                colour.models.describe_video_signal_matrix_coefficients,
                colour.models.MATRIX_COEFFICIENTS_ITUTH273.keys(),
            ),
            "transfer_characteristics": _itu_table(
                colour.models.describe_video_signal_transfer_characteristics,
                colour.models.TRANSFER_CHARACTERISTICS_ITUTH273.keys(),
            ),
        },
        "warnings": log.payload,
    }
