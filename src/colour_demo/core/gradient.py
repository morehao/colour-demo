"""面板 06：均匀空间与渐变（`POST /api/v1/gradient`）。

在指定空间里做 N 步线性插值，再用 ΔE 量化「步长是否均匀」——这正是面板 06 的论点。

实现要点：整批采样一次性转回 XYZ（`colour.convert` 支持 N×3 数组），
避免逐步调用把 101 步场景拖到 20 ms 以上。
"""

from __future__ import annotations

import numpy as np

import colour

from ..config import MAX_STEPS
from ..core.errors import value_error
from ..core.parsing import parse_colour, rgb_to_hex

DEFAULT_SPACE = "CIE Lab"
DEFAULT_METHOD = "CIE 2000"


def gradient_data(
    start_colour: str,
    end_colour: str,
    space: str = DEFAULT_SPACE,
    steps: int = 11,
    method: str = DEFAULT_METHOD,
) -> dict:
    if steps < 2:
        raise value_error("steps 至少为 2")
    if steps > MAX_STEPS:
        raise value_error(f"steps 最多 {MAX_STEPS} 步，当前 {steps}")

    start_rgb = parse_colour(start_colour)
    end_rgb = parse_colour(end_colour)
    start_xyz = np.asarray(colour.sRGB_to_XYZ(start_rgb), dtype=float)
    end_xyz = np.asarray(colour.sRGB_to_XYZ(end_rgb), dtype=float)

    try:
        # 与 /convert 同口径：空间内用人类可读刻度（Lab 0–100），转回时再还原
        start_in_space = np.asarray(
            colour.convert(start_xyz, "CIE XYZ", space, to_reference_scale=True), dtype=float
        )
        end_in_space = np.asarray(
            colour.convert(end_xyz, "CIE XYZ", space, to_reference_scale=True), dtype=float
        )
    except Exception as error:
        raise value_error(f"无法在空间 {space!r} 中插值：{error}") from error

    samples = np.linspace(start_in_space, end_in_space, steps)  # (steps, 3)
    try:
        xyz_all = np.asarray(
            colour.convert(samples, space, "CIE XYZ", from_reference_scale=True), dtype=float
        )
    except Exception as error:
        raise value_error(f"插值结果无法转回 XYZ：{error}") from error

    rgb_all = np.clip(np.asarray(colour.XYZ_to_sRGB(xyz_all), dtype=float), 0, 1)
    labs = np.asarray(colour.XYZ_to_Lab(xyz_all), dtype=float)

    rows = [
        {
            "step": index,
            "hex": rgb_to_hex(rgb_all[index]),
            "coordinates": [round(float(channel), 6) for channel in samples[index]],
        }
        for index in range(steps)
    ]

    # 一次性算相邻步的 ΔE（colour.delta_E 支持数组广播）
    deltas_array = np.asarray(colour.delta_E(labs[:-1], labs[1:], method=method), dtype=float).ravel()
    deltas = [round(float(value), 4) for value in deltas_array]

    finite = [value for value in deltas if np.isfinite(value)]
    mean = float(np.mean(finite)) if finite else float("nan")
    spread = float(np.max(finite) - np.min(finite)) if finite else float("nan")

    return {
        "space": space,
        "method": method,
        "steps": steps,
        "rows": rows,
        "deltas": deltas,
        "uniformity": {
            # 步长最大/最小之比：1.0 = 完全均匀；越大说明该空间越不均匀
            "ratio": round(float(max(finite) / min(finite)), 4) if finite and min(finite) > 0 else None,
            "mean": round(mean, 4) if np.isfinite(mean) else None,
            "spread": round(spread, 4) if np.isfinite(spread) else None,
        },
        "warnings": [],
    }
