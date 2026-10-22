"""面板 22：连续信号与插值器（`POST /api/v1/interpolate`）。

光谱是离散采样、物理量是连续的：插值方法决定“采样点之间”长什么样。

两个必须照做的口径：

- 演示光源选 **FL11** 而不是 D65：D65 的 5 nm 表在 10 nm 节点之间本身就是线性的，
  线性插值必然“零误差”，看不出差别；FL11 有汞灯尖线（435.8 / 546.1 / 611.6 nm）最能暴露问题；
- 3D LUT 的两种表插值要用**非线性、跨通道**的合成表：在恒等表（`LUT3D.linear_table`）上
  三线性与四面体**必然完全相同**，用它对比等于什么都没测。
"""

from __future__ import annotations

import numpy as np

import colour
from colour.algebra import (
    CubicSplineInterpolator,
    LinearInterpolator,
    PchipInterpolator,
    SpragueInterpolator,
    table_interpolation_tetrahedral,
    table_interpolation_trilinear,
)

from ..core.diagnostics import WarningCollector, number
from ..core.errors import value_error
from ..core.parsing import rgb_to_hex

INTERPOLATORS = {
    "Linear": LinearInterpolator,
    "Sprague": SpragueInterpolator,
    "PCHIP": PchipInterpolator,
    "Cubic Spline": CubicSplineInterpolator,
}
DEFAULT_INTERPOLATORS = ("Linear", "Sprague", "PCHIP", "Cubic Spline")
DEFAULT_ILLUMINANT = "FL11"
LUT_GRID = 9
LUT_MATRIX = np.array([[0.82, 0.18, 0.04], [0.12, 0.86, 0.09], [0.06, 0.14, 0.90]])
LUT_PROBES = 200
LUT_SEED = 7


def _signal_payload(sd) -> dict:
    return {
        "wavelengths": [round(float(w), 1) for w in sd.wavelengths],
        "values": [round(float(v), 5) for v in np.asarray(sd.values)],
    }


def _synthetic_lut() -> np.ndarray:
    """9³ 合成表：通道混合 + gamma 2.2（恒等表上看不出两种插值的差别）。"""

    grid = np.linspace(0, 1, LUT_GRID)
    table = np.empty((LUT_GRID, LUT_GRID, LUT_GRID, 3))
    for i, a in enumerate(grid):
        for j, b in enumerate(grid):
            for k, c in enumerate(grid):
                table[i, j, k] = np.clip(LUT_MATRIX @ np.array([a, b, c]), 0, 1) ** 2.2
    return table


def interpolate_data(
    illuminant: str = DEFAULT_ILLUMINANT,
    coarse_step: float = 20.0,
    target_step: float = 5.0,
    start: float = 400.0,
    end: float = 700.0,
    interpolators: list[str] | None = None,
) -> dict:
    if coarse_step <= target_step:
        raise value_error("coarse_step 必须大于 target_step（否则没有可插值的空隙）")
    if not (360.0 <= start < end <= 830.0):
        raise value_error("范围需在 360–830 nm 且 start < end")
    if (end - start) / coarse_step > 40:
        raise value_error("采样点过多，请加大 coarse_step 或缩小范围")

    names = list(interpolators or DEFAULT_INTERPOLATORS)
    unknown = [name for name in names if name not in INTERPOLATORS]
    if unknown:
        raise value_error(f"未知插值器 {unknown}，可选：{list(INTERPOLATORS)}")

    try:
        truth = colour.SDS_ILLUMINANTS[illuminant].copy().align(colour.SpectralShape(start, end, target_step))
    except Exception as error:
        raise value_error(f"未知光源 {illuminant!r}：{error}") from error

    # 每「coarse/target」个点取一个，得到粗采样
    stride = max(1, int(round(coarse_step / target_step)))
    coarse = colour.SpectralDistribution(
        {float(w): float(truth[w]) for w in truth.wavelengths[::stride]},
        name=f"{illuminant} @ {coarse_step:g} nm",
    )

    target_values = np.asarray(truth.values, dtype=float)
    rows = []
    curves = {"truth": _signal_payload(truth), "coarse": _signal_payload(coarse), "reconstructions": [], "residuals": []}

    with WarningCollector() as log:
        for name in names:
            try:
                fine = coarse.copy().interpolate(
                    colour.SpectralShape(start, end, target_step), interpolator=INTERPOLATORS[name]
                )
                values = np.asarray(fine.values, dtype=float)
                error = np.abs(values - target_values)
                rows.append(
                    {
                        "interpolator": name,
                        "max_abs_error": number(error.max(), 4),
                        "mean_abs_error": number(error.mean(), 4),
                        # 过冲会给出物理上不可能的负功率（Gibbs 现象）
                        "negative_points": int((values < 0).sum()),
                        "resolution": number(fine.shape.interval, 3),
                    }
                )
                curves["reconstructions"].append({"name": name, **_signal_payload(fine)})
                curves["residuals"].append(
                    {
                        "name": name,
                        "wavelengths": [round(float(w), 1) for w in fine.wavelengths],
                        "values": [round(float(v), 5) for v in values - target_values],
                    }
                )
            except Exception as error:
                rows.append({"interpolator": name, "max_abs_error": None, "mean_abs_error": None, "negative_points": None})
                log.add("unavailable", f"{name} 插值失败：{type(error).__name__}")

        # ---- 3D LUT 表插值：非线性合成表才有可比性 ----
        table = _synthetic_lut()
        probes = np.random.default_rng(LUT_SEED).random((LUT_PROBES, 3))
        trilinear = np.asarray([table_interpolation_trilinear(point, table) for point in probes], dtype=float)
        tetrahedral = np.asarray([table_interpolation_tetrahedral(point, table) for point in probes], dtype=float)
        gap = np.abs(trilinear - tetrahedral).max(axis=1) * 255
        probe = np.array([0.31, 0.47, 0.82])

        log.add(
            "note",
            "负值点数 = 重建后小于 0 的点：Sprague 与 Cubic Spline 在尖峰两侧会过冲（Gibbs），"
            "给出物理上不可能的负功率；PCHIP 保单调、Linear 不越界，但都会削平峰。"
            "LUT 部分用 9³ 合成表（通道混合 + gamma 2.2），恒等表上两种插值必然相同。",
        )

    return {
        "illuminant": illuminant,
        "shape": {"start": start, "end": end, "target_step": target_step, "coarse_step": coarse_step},
        "samples": {"truth": len(truth.values), "coarse": len(coarse.values)},
        "curves": curves,
        "rows": rows,
        "lut": {
            "grid": LUT_GRID,
            "table_kind": "通道混合 + gamma 2.2（非线性、跨通道）",
            "probes": LUT_PROBES,
            "seed": LUT_SEED,
            "probe": [round(float(v), 3) for v in probe],
            "trilinear": [round(float(v), 5) for v in table_interpolation_trilinear(probe, table)],
            "tetrahedral": [round(float(v), 5) for v in table_interpolation_tetrahedral(probe, table)],
            "max_gap_codes": number(gap.max(), 3),
            "mean_gap_codes": number(gap.mean(), 3),
        },
        "interpolators": list(INTERPOLATORS),
        "warnings": log.payload,
    }
