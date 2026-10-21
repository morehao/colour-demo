"""面板 18：色觉障碍模拟（`POST /api/v1/cvd`）。

Machado 2009 给的是**随严重度连续变化**的 3×3 矩阵，作用在**线性 RGB** 上，
不是 hex 编码值——直接乘编码值是最常见的错（原型里专门记过这条）。

结论部分给两个可判定的指标：
- 原色 vs 模拟的平均 ΔE（这支颜色变了多少）；
- 模拟后相邻两色的最小 ΔE（调色板还剩多少可区分性）。
"""

from __future__ import annotations

import numpy as np

import colour

from ..config import MAX_COLOURS
from ..core.diagnostics import WarningCollector, number, numbers
from ..core.errors import value_error
from ..core.parsing import parse_colours, rgb_to_hex

DEFICIENCIES = {
    "Protanomaly": "红色弱 / 红色盲（L 锥体响应衰减）",
    "Deuteranomaly": "绿色弱 / 绿色盲（M 锥体响应衰减）",
    "Tritanomaly": "蓝色弱 / 蓝色盲（S 锥体响应衰减）",
}
DEFAULT_SEVERITIES = (0.0, 0.25, 0.5, 0.75, 1.0)
# 相邻两色的 ΔE 低于这个值，在图上基本分不开（CIE 2000，经验阈值）
INDISTINGUISHABLE_DELTA_E = 3.0


def _matrix(deficiency: str, severity: float) -> np.ndarray:
    return np.asarray(colour.blindness.matrix_cvd_Machado2009(deficiency, severity), dtype=float)


def _simulate(rgb: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """线性光里乘矩阵，再编码回来；越界要裁到 0–1 才算“屏幕能显示”。"""

    linear = np.asarray(colour.models.eotf_inverse_sRGB(rgb), dtype=float)
    return np.clip(np.asarray(colour.models.eotf_sRGB(matrix @ linear), dtype=float), 0, 1)


def cvd_data(
    colours: list[str],
    deficiency: str = "Deuteranomaly",
    severity: float = 1.0,
    severities: list[float] | None = None,
) -> dict:
    if deficiency not in DEFICIENCIES:
        raise value_error(f"未知类型 {deficiency!r}，可选：{list(DEFICIENCIES)}")
    if not (0.0 <= severity <= 1.0):
        raise value_error("severity 需在 0–1")
    if len(colours) > MAX_COLOURS:
        raise value_error(f"colors 最多 {MAX_COLOURS} 个，当前 {len(colours)} 个")

    levels = list(severities or DEFAULT_SEVERITIES)
    if any(not (0.0 <= level <= 1.0) for level in levels):
        raise value_error("severities 每一项都需在 0–1")

    rgb_list = parse_colours(colours)

    with WarningCollector(limit=6) as log:
        matrix = _matrix(deficiency, severity)
        simulated = [_simulate(rgb, matrix) for rgb in rgb_list]

        original_labs = [
            np.asarray(colour.XYZ_to_Lab(colour.sRGB_to_XYZ(rgb)), dtype=float) for rgb in rgb_list
        ]
        simulated_labs = [
            np.asarray(colour.XYZ_to_Lab(colour.sRGB_to_XYZ(rgb)), dtype=float) for rgb in simulated
        ]

        rows = []
        for spec, rgb, sim, lab_original, lab_simulated in zip(
            colours, rgb_list, simulated, original_labs, simulated_labs
        ):
            rows.append(
                {
                    "input": spec,
                    "hex": rgb_to_hex(rgb),
                    "simulated_hex": rgb_to_hex(sim),
                    "simulated_rgb": numbers(sim, 5),
                    "delta_e": number(
                        colour.delta_E(lab_original, lab_simulated, method="CIE 2000"), 3
                    ),
                }
            )

        deltas = [
            float(colour.delta_E(lab_original, lab_simulated, method="CIE 2000"))
            for lab_original, lab_simulated in zip(original_labs, simulated_labs)
        ]
        adjacent = [
            float(colour.delta_E(simulated_labs[index], simulated_labs[index + 1], method="CIE 2000"))
            for index in range(len(simulated_labs) - 1)
        ]
        collisions = [
            {
                "a": rows[index]["simulated_hex"],
                "b": rows[index + 1]["simulated_hex"],
                "delta_e": round(value, 3),
            }
            for index, value in enumerate(adjacent)
            if np.isfinite(value) and value < INDISTINGUISHABLE_DELTA_E
        ]

        matrix_rows = [
            {"severity": round(level, 2), "matrix": [numbers(row, 5) for row in _matrix(deficiency, level)]}
            for level in levels
        ]

        log.add(
            "note",
            "矩阵必须作用在**线性** RGB 上；编码值（hex）直接相乘会得到系统性偏色。"
            "该模型是严重度插值的近似，不等同于临床诊断。",
        )

    return {
        "deficiency": deficiency,
        "label": DEFICIENCIES[deficiency],
        "types": DEFICIENCIES,
        "severity": severity,
        "severities": [round(level, 2) for level in levels],
        "matrix": [numbers(row, 5) for row in matrix],
        "rows": rows,
        "metrics": {
            "mean_delta_e": round(float(np.mean(deltas)), 3) if deltas else None,
            "max_delta_e": round(float(np.max(deltas)), 3) if deltas else None,
            "min_adjacent_delta_e": round(float(np.min(adjacent)), 3) if adjacent else None,
            "indistinguishable_threshold": INDISTINGUISHABLE_DELTA_E,
            "collisions": collisions,
        },
        "matrix_by_severity": matrix_rows,
        "warnings": log.payload,
    }
