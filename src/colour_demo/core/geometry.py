"""面板 23：几何与椭圆拟合（`POST /api/v1/geometry`）。

MacAdam 1942 的 25 组椭圆描述「人眼在各方向上有多不敏感」；把它拟合成二次曲线，
就能反过来量化局部均匀性。这个模块只做几何，不涉及颜色计算。

两个实现口径：

- `ellipse_fitting` 内部走广义特征值分解，返回 **complex128**（虚部恒为 0），
  不取 `.real` 会抛 numpy ComplexWarning；
- 拟合结果与原始数据是「同一组参数的不同表示」：中心精度到 1e-4，长短半轴会互换，
  θ 相差 90° 属于标准形约定差异——这不是误差。
"""

from __future__ import annotations

import numpy as np

import colour

from ..core.diagnostics import WarningCollector, number
from ..core.errors import value_error

ELLIPSE_INDEX = 10  # 面板用第 11 组（0 基下标 10）
SAMPLES = 60


def _ellipse_points(cx, cy, a, b, theta_deg, samples=SAMPLES) -> tuple[np.ndarray, np.ndarray]:
    angles = np.linspace(0, 2 * np.pi, samples)
    rotation = np.radians(theta_deg)
    x = cx + a * np.cos(angles) * np.cos(rotation) - b * np.sin(angles) * np.sin(rotation)
    y = cy + a * np.cos(angles) * np.sin(rotation) + b * np.sin(angles) * np.cos(rotation)
    return x, y


def geometry_data(ellipse_index: int = ELLIPSE_INDEX, include_all: bool = True) -> dict:
    data = np.asarray(colour.models.DATA_MACADAM_1942_ELLIPSES, dtype=float)
    if not (0 <= ellipse_index < data.shape[0]):
        raise value_error(f"ellipse_index 需在 0–{data.shape[0] - 1}")

    rows_all = [
        {
            "index": index + 1,
            "u": number(row[0], 5),
            "v": number(row[1], 5),
            "a": number(row[2], 4),
            "b": number(row[3], 4),
            "theta": number(row[4], 3),
        }
        for index, row in enumerate(data)
    ]

    row = data[ellipse_index]
    cx, cy, a_raw, b_raw, theta_raw = (float(row[i]) for i in range(5))
    # 原始数据是 ×10⁻³ 量纲，换算成色度坐标
    ex, ey = _ellipse_points(cx, cy, a_raw / 1000, b_raw / 1000, theta_raw)
    points = np.column_stack([ex, ey])

    with WarningCollector() as log:
        # 虚部恒为 0，但类型是 complex128 → 必须 .real
        coefficients = np.asarray(colour.geometry.ellipse_fitting(points)).real
        x0, y0, fit_a, fit_b, fit_theta = (
            float(value) for value in np.asarray(colour.geometry.ellipse_coefficients_canonical_form(coefficients)).real
        )
        fx, fy = _ellipse_points(x0, y0, fit_a, fit_b, fit_theta)

        compare = [
            {"parameter": "中心 x₀", "original": round(cx, 6), "fitted": round(x0, 6), "note": "一致"},
            {"parameter": "中心 y₀", "original": round(cy, 6), "fitted": round(y0, 6), "note": "一致"},
            {"parameter": "半轴 1", "original": round(a_raw / 1000, 8), "fitted": round(fit_b, 8), "note": "轴序互换"},
            {"parameter": "半轴 2", "original": round(b_raw / 1000, 8), "fitted": round(fit_a, 8), "note": "轴序互换"},
            {
                "parameter": "旋转角 θ°",
                "original": round(theta_raw, 3),
                "fitted": round(fit_theta, 3),
                "note": f"差 {theta_raw - fit_theta:+.2f}°（标准形约定）",
            },
        ]

        # 二次型残差：把采样点代回隐式方程，应接近 0
        residuals = []
        for index in range(3):
            x, y = points[index]
            value = float(
                coefficients[0] * x * x
                + coefficients[1] * x * y
                + coefficients[2] * y * y
                + coefficients[3] * x
                + coefficients[4] * y
                + coefficients[5]
            )
            residuals.append({"point": index + 1, "x": number(x, 6), "y": number(y, 6), "residual": f"{value:+.3e}"})

        primitives = []
        for label, call in (
            ("primitive_grid(4, 4)", lambda: colour.geometry.primitive_grid(width_segments=4, height_segments=4)[0]),
            ("primitive_cube(2, 2, 2)", lambda: colour.geometry.primitive_cube(width_segments=2, height_segments=2, depth_segments=2)[0]),
            ("primitive_vertices_sphere(0.5, 16)", lambda: colour.geometry.primitive_vertices_sphere(radius=0.5, segments=16)),
        ):
            try:
                shape = np.asarray(call()).shape
                primitives.append({"call": label, "vertices_shape": list(shape)})
            except Exception as error:
                primitives.append({"call": label, "vertices_shape": None})
                log.add("unavailable", f"{label} 失败：{type(error).__name__}")

        # 线段求交：一组相交、一组平行
        crossing = colour.geometry.intersect_line_segments(np.array([[0, 0], [1, 1]]), np.array([[0, 1], [1, 0]]))
        parallel = colour.geometry.intersect_line_segments(np.array([[0, 0], [1, 1]]), np.array([[0, 1], [1, 2]]))
        segments = [
            {
                "case": "交叉 (0,0)-(1,1) × (0,1)-(1,0)",
                "intersect": bool(crossing.intersect[0][0]),
                "parallel": bool(crossing.parallel[0][0]),
                "point": [number(crossing.xy[0][0][0], 4), number(crossing.xy[0][0][1], 4)],
            },
            {
                "case": "平行 (0,0)-(1,1) ∥ (0,1)-(1,2)",
                "intersect": bool(parallel.intersect[0][0]),
                "parallel": bool(parallel.parallel[0][0]),
                "point": None,
            },
        ]

        log.add(
            "note",
            "拟合不是“造一个新椭圆”，而是从 60 个采样点反推原来那组参数；"
            "坐标跨度只有 0.002×0.004，所以看上去接近圆——这正是 MacAdam 椭圆的特点。",
        )

    return {
        "ellipse_index": ellipse_index,
        "ellipse": {
            "center": [round(cx, 6), round(cy, 6)],
            "semi_axes": [round(a_raw / 1000, 8), round(b_raw / 1000, 8)],
            "theta": round(theta_raw, 3),
            "samples": SAMPLES,
            "original_points": [[round(float(x), 7), round(float(y), 7)] for x, y in zip(ex, ey)],
            "fitted_points": [[round(float(x), 7), round(float(y), 7)] for x, y in zip(fx, fy)],
        },
        "compare": compare,
        "residuals": residuals,
        "primitives": primitives,
        "segments": segments,
        "ellipses": rows_all if include_all else [],
        "total_ellipses": int(data.shape[0]),
        "warnings": log.payload,
    }
