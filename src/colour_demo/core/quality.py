"""面板 12：色彩质量（`POST /api/v1/quality`）。

四套口径同时给：CIE 显色指数 Ra（1995 / 2024 两版）、NIST CQS、ANSI/IES TM-30（Rf/Rg）、
以及以参考光源为基准的光谱相似度 SSI。它们**不是同一个量的不同精度**，结论会互相打架，
所以响应里逐项并列、不合并成单一分数。
"""

from __future__ import annotations

import colour

from ..core.diagnostics import WarningCollector, number
from ..core.errors import value_error

DEFAULT_ILLUMINANTS = ("D65", "FL2", "A", "FL11")
REFERENCE_ILLUMINANT = "D65"
MAX_ILLUMINANTS = 12

CRI_METHODS = ("CIE 1995", "CIE 2024")
CQS_METHODS = ("NIST CQS 7.4", "NIST CQS 9.0")
FIDELITY_METHODS = ("CIE 2017", "ANSI/IES TM-30-18")


def _illuminant(name: str):
    try:
        return colour.SDS_ILLUMINANTS[name]
    except Exception as error:
        sample = sorted(colour.SDS_ILLUMINANTS.keys())[:8]
        raise value_error(f"未知光源 {name!r}（示例：{sample}）") from error


def quality_data(
    illuminants: list[str] | None = None,
    reference: str = REFERENCE_ILLUMINANT,
    include_special: bool = True,
) -> dict:
    names = list(illuminants or DEFAULT_ILLUMINANTS)
    if len(names) > MAX_ILLUMINANTS:
        raise value_error(f"光源最多 {MAX_ILLUMINANTS} 个，当前 {len(names)} 个")

    reference_sd = _illuminant(reference)

    rows = []
    special_rows = []
    with WarningCollector(limit=12) as log:
        for name in names:
            sd = _illuminant(name)
            row = {"illuminant": name}
            special = {}

            try:
                cri = colour.quality.colour_rendering_index(sd, additional_data=True, method="CIE 1995")
                row["Ra"] = number(cri.Q_a, 2)
                special = {f"R{index}": number(value, 2) for index, value in dict(cri.Q_as).items()}
            except Exception as error:
                row["Ra"] = None
                log.add("unavailable", f"{name} 的 CRI(CIE 1995) 计算失败：{type(error).__name__}")

            try:
                cri_2024 = colour.quality.colour_rendering_index(sd, additional_data=True, method="CIE 2024")
                row["Ra_2024"] = number(cri_2024.Q_a, 2)
            except Exception as error:
                row["Ra_2024"] = None
                log.add("unavailable", f"{name} 的 CRI(CIE 2024) 计算失败：{type(error).__name__}")

            try:
                cqs = colour.quality.colour_quality_scale(sd, additional_data=True, method="NIST CQS 9.0")
                row["Qa"] = number(cqs.Q_a, 2)
                row["Qf"] = number(cqs.Q_f, 2)
                row["Qp"] = number(cqs.Q_p, 2)
                row["Qg"] = number(cqs.Q_g, 2)
                row["Qd"] = number(cqs.Q_d, 2)
            except Exception as error:
                row.update({"Qa": None, "Qf": None, "Qp": None, "Qg": None, "Qd": None})
                log.add("unavailable", f"{name} 的 CQS 计算失败：{type(error).__name__}")

            try:
                tm30 = colour.quality.colour_fidelity_index(
                    sd, additional_data=True, method="ANSI/IES TM-30-18"
                )
                row["Rf"] = number(tm30.R_f, 2)
                row["Rg"] = number(tm30.R_g, 2)
            except Exception as error:
                row.update({"Rf": None, "Rg": None})
                log.add("unavailable", f"{name} 的 TM-30 计算失败：{type(error).__name__}")

            try:
                row["Rf_CIE2017"] = number(
                    colour.quality.colour_fidelity_index(sd, method="CIE 2017"), 2
                )
            except Exception as error:
                row["Rf_CIE2017"] = None
                log.add("unavailable", f"{name} 的 CIE 2017 保真度计算失败：{type(error).__name__}")

            try:
                row["ssi"] = number(colour.quality.spectral_similarity_index(sd, reference_sd), 4)
            except Exception as error:
                row["ssi"] = None
                log.add("unavailable", f"{name} 的 SSI 计算失败：{type(error).__name__}")

            rows.append(row)
            if include_special and special:
                special_rows.append({"illuminant": name, **special})

        log.add(
            "note",
            "Ra 只用 8 个中等饱和色样（R1–R8）、且基于 CIE 1995 的老色样，对窄带 LED 会高估；"
            "Rf（TM-30）用 99 个色样 + 色域形状 Rg，两者不一致时以 Rf 更可信。",
        )

    return {
        "reference": reference,
        "methods": {"cri": list(CRI_METHODS), "cqs": list(CQS_METHODS), "fidelity": list(FIDELITY_METHODS)},
        "rows": rows,
        "special_indices": special_rows,
        "warnings": log.payload,
    }
