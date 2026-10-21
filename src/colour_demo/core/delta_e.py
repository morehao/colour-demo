"""面板 05：ΔE 全家桶（`POST /api/v1/delta-e`）。

输出与方案 6.2 的契约一致：`method` + 对称矩阵 `matrix` + `pairs`（最近/最远一对）+ `warnings`。
"""

from __future__ import annotations

import itertools
import warnings

import numpy as np

import colour

from ..config import DEFAULT_METHOD
from ..core.errors import value_error
from ..core.parsing import parse_colours, rgb_to_hex

# 只保留大写开头的方法名（colour 里同名小写别名是历史兼容）。
# colour 首次展开别名表会发一条 ColourUsageWarning（别名 key collide），属库内噪声：
# 这里只过滤这一条明确的消息，不影响其它告警。
warnings.filterwarnings("ignore", message=r".*key\(s\) collide.*", category=colour.utilities.ColourUsageWarning)
METHODS = [m for m in colour.difference.DELTA_E_METHODS if m[0].isupper()]


def _validate_method(method: str) -> str:
    if method not in colour.difference.DELTA_E_METHODS:
        raise value_error(f"ΔE 方法 {method!r} 不存在，可选：{METHODS}")
    return method


def delta_e_matrix(colours: list[str], method: str = DEFAULT_METHOD) -> dict:
    _validate_method(method)
    if len(colours) < 2:
        raise value_error("至少需要 2 个颜色才能算 ΔE 矩阵")

    rgb_list = parse_colours(colours)
    labs = [
        np.asarray(colour.XYZ_to_Lab(colour.sRGB_to_XYZ(rgb)), dtype=float) for rgb in rgb_list
    ]

    size = len(labs)
    matrix = np.zeros((size, size), dtype=float)
    warnings: list[dict] = []
    for i, j in itertools.combinations(range(size), 2):
        try:
            value = float(np.asarray(colour.delta_E(labs[i], labs[j], method=method)).ravel()[0])
        except Exception as error:
            raise value_error(f"{method} 无法计算第 {i + 1}/{j + 1} 对：{error}") from error
        matrix[i, j] = matrix[j, i] = value

    hexes = [rgb_to_hex(rgb) for rgb in rgb_list]
    pairs = _extremes(matrix, hexes)
    if np.any(~np.isfinite(matrix)):
        warnings.append({"type": "undefined", "message": "矩阵含非有限值，请检查输入是否超出该方法定义域"})

    return {
        "method": method,
        "colors": hexes,
        "lab": [[round(float(channel), 4) for channel in lab] for lab in labs],
        "matrix": [[round(float(value), 4) for value in row] for row in matrix],
        "pairs": pairs,
        "warnings": warnings,
    }


def _extremes(matrix: np.ndarray, hexes: list[str]) -> dict:
    size = matrix.shape[0]
    closest = None
    farthest = None
    for i, j in itertools.combinations(range(size), 2):
        value = float(matrix[i, j])
        entry = {"a": hexes[i], "b": hexes[j], "value": round(value, 4)}
        if closest is None or value < closest["value"]:
            closest = entry
        if farthest is None or value > farthest["value"]:
            farthest = entry
    return {"closest": closest, "farthest": farthest}


def stress_index(deltas, delta_v) -> dict:
    """面板 05 的压力指数（Garcia 2007），供后续面板复用。"""

    try:
        value = float(np.asarray(colour.index_stress(deltas, delta_v), dtype=float).ravel()[0])
    except Exception as error:
        raise value_error(f"压力指数计算失败：{error}") from error
    return {"index_stress": round(value, 4)}
