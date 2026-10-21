"""面板 14：色适应（`POST /api/v1/adapt`）。

7 个方法的通用入口 `chromatic_adaptation(XYZ, XYZ_w, XYZ_wr, method=...)` **不是全都能直接调**：
CIE 1994 / CMCCAT2000 / Fairchild 1990 / Li 2025 需要额外的观察条件参数，
不传就 TypeError（原型里这四行显示“不可用”，就是这个原因）。这里按方法补齐默认参数，
让 7 个方法全部出数，并把用到的参数回传，方便复核。
"""

from __future__ import annotations

import numpy as np

import colour

from ..config import CAM16_L_A, MAX_COLOURS
from ..core.diagnostics import WarningCollector, number, numbers
from ..core.errors import value_error
from ..core.parsing import parse_colours, rgb_to_hex

DEFAULT_SOURCE = "A"
DEFAULT_TARGET = "D65"
OBSERVER = "CIE 1931 2 Degree Standard Observer"
METHODS = tuple(name for name in colour.CHROMATIC_ADAPTATION_METHODS if name[0].isupper())

# 通用入口缺省参数：不补就会 TypeError。
# 注意 `Domain100` 标注入参要按 **0–1** 传（colour 内部再乘 100）：Y_o=0.2 就是 20%，
# 传 20 会触发 `"Y_o" luminance factor must be in [18, 100] domain` 的假告警。
METHOD_KWARGS = {
    "CIE 1994": {"Y_o": 0.2, "E_o1": 1000.0, "E_o2": 1000.0},
    "CMCCAT2000": {"L_A1": CAM16_L_A, "L_A2": CAM16_L_A},
    "Fairchild 1990": {"Y_n": 1.0},
    "Li 2025": {"L_A": CAM16_L_A, "F_surround": 1.0},
}

# 13 个标准 CAT 矩阵（属性名 → 展示名）
CAT_ATTRIBUTES = (
    ("CAT_BRADFORD", "Bradford"),
    ("CAT_VON_KRIES", "Von Kries"),
    ("CAT_XYZ_SCALING", "XYZ Scaling"),
    ("CAT_CAT02", "CAT02"),
    ("CAT_CAT16", "CAT16"),
    ("CAT_CAT16_INVERSE", "CAT16 Inverse"),
    ("CAT_CMCCAT97", "CMCCAT97"),
    ("CAT_CMCCAT2000", "CMCCAT2000"),
    ("CAT_SHARP", "Sharp"),
    ("CAT_FAIRCHILD", "Fairchild"),
    ("CAT_BIANCO2010", "Bianco 2010"),
    ("CAT_PC_BIANCO2010", "PC Bianco 2010"),
    ("CAT_CAT02_BRILL2008", "CAT02 Brill 2008"),
)


def _white_xy(name: str) -> np.ndarray:
    """白点：先查 CCS 表（A/D50/D65/FL2…），再退回用 SPD 现算。"""

    ccs = colour.CCS_ILLUMINANTS[OBSERVER]
    if name in ccs:
        return np.asarray(ccs[name], dtype=float)
    try:
        # sd_to_XYZ 给 0–100，但 XYZ_to_xy 与刻度无关
        return np.asarray(colour.XYZ_to_xy(colour.sd_to_XYZ(colour.SDS_ILLUMINANTS[name])), dtype=float)
    except Exception as error:
        raise value_error(f"未知白点 {name!r}（示例：{sorted(ccs)[:8]}）") from error


def _cat_matrices() -> list[dict]:
    rows = []
    for attribute, label in CAT_ATTRIBUTES:
        matrix = getattr(colour.adaptation, attribute, None)
        if matrix is None:
            continue
        rows.append(
            {"name": label, "attribute": attribute, "matrix": [numbers(row, 6) for row in np.asarray(matrix, dtype=float)]}
        )
    return rows


def adapt_data(
    colours: list[str],
    source: str = DEFAULT_SOURCE,
    target: str = DEFAULT_TARGET,
    methods: list[str] | None = None,
    include_matrices: bool = True,
) -> dict:
    if len(colours) > MAX_COLOURS:
        raise value_error(f"colors 最多 {MAX_COLOURS} 个，当前 {len(colours)} 个")

    names = list(methods or METHODS)
    unknown = [name for name in names if name not in METHODS]
    if unknown:
        raise value_error(f"未知色适应方法 {unknown}，可选：{list(METHODS)}")

    if source == target:
        raise value_error("source 与 target 不能是同一个白点")

    xyz_source = colour.xy_to_XYZ(_white_xy(source))
    xyz_target = colour.xy_to_XYZ(_white_xy(target))
    rgb_list = parse_colours(colours)

    with WarningCollector() as log:
        rows = []
        for spec, rgb in zip(colours, rgb_list):
            xyz = np.asarray(colour.sRGB_to_XYZ(rgb), dtype=float)
            lab = np.asarray(colour.XYZ_to_Lab(xyz), dtype=float)
            per_method = {}
            for method in names:
                try:
                    adapted = np.asarray(
                        colour.chromatic_adaptation(
                            xyz, xyz_source, xyz_target, method=method, **METHOD_KWARGS.get(method, {})
                        ),
                        dtype=float,
                    )
                    adapted_lab = np.asarray(colour.XYZ_to_Lab(adapted), dtype=float)
                    per_method[method] = {
                        "xyz": numbers(adapted, 6),
                        "xy": numbers(colour.XYZ_to_xy(adapted), 6),
                        "hex": rgb_to_hex(np.clip(colour.XYZ_to_sRGB(adapted), 0, 1)),
                        "delta_e": number(colour.delta_E(lab, adapted_lab, method="CIE 2000"), 3),
                    }
                except Exception as error:
                    per_method[method] = None
                    log.add("unavailable", f"色适应方法 {method} 失败：{type(error).__name__}")
            rows.append({"input": spec, "hex": rgb_to_hex(rgb), "xyz": numbers(xyz, 6), "results": per_method})

        # vK20 是唯一显式建模“不完全适应”的方法，签名也和通用入口完全不同：
        # (XYZ, XYZ_p 近端场, XYZ_n 背景, XYZ_r 参考白) —— 不是 (XYZ, 源白, 目标白)
        vk20 = {}
        for spec, rgb in zip(colours, rgb_list):
            xyz = np.asarray(colour.sRGB_to_XYZ(rgb), dtype=float)
            try:
                adapted = np.asarray(
                    colour.adaptation.chromatic_adaptation_vK20(
                        xyz, XYZ_p=xyz_source, XYZ_n=xyz_source, XYZ_r=xyz_target
                    ),
                    dtype=float,
                )
                vk20[spec] = {
                    "xy": numbers(colour.XYZ_to_xy(adapted), 6),
                    "hex": rgb_to_hex(np.clip(colour.XYZ_to_sRGB(adapted), 0, 1)),
                }
            except Exception as error:
                vk20[spec] = None
                log.add("unavailable", f"vK20 失败：{type(error).__name__}")

        log.add(
            "note",
            "通用入口只对 Von Kries / Zhai 2018 / vK20 免参数；CIE 1994 / CMCCAT2000 / "
            "Fairchild 1990 / Li 2025 必须补观察条件（本响应已在 method_kwargs 里回传）。"
            "vK20 走独立入口 chromatic_adaptation_vK20(XYZ, XYZ_p, XYZ_n, XYZ_r)，"
            "它建模的是不完全适应（degree of adaptation），与通用入口的 7 个方法不同源。",
        )

    return {
        "observer": OBSERVER,
        "source": {"name": source, "xy": numbers(_white_xy(source), 6)},
        "target": {"name": target, "xy": numbers(_white_xy(target), 6)},
        "methods": list(METHODS),
        "method_kwargs": {name: value for name, value in METHOD_KWARGS.items() if name in names},
        "rows": rows,
        "vK20": vk20,
        "cat_matrices": _cat_matrices() if include_matrices else [],
        "warnings": log.payload,
    }
