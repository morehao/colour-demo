"""面板 13：图像与 3D LUT（`POST /api/v1/lut`）。

这里只算数据、不返回位图：LUT 的作用是把“编码值 → 编码值”的映射查表化，
把同一批颜色过两个插值器（三线性 / 四面体）并给出差异，比一张缩略图更能说明问题。

两个坑：
1. `LUT3D.apply(..., interpolator=...)` 在 0.4.7 要的是**可调用对象**
   （`colour.algebra.table_interpolation_*`），传 `"Trilinear"` 字符串会 TypeError；
2. LUT 作用在**编码值**（0–1 的 sRGB 编码）上，增益就直接乘在编码值上，
   不是在线性光里乘——需要线性时先用 `eotf_inverse_sRGB`。
"""

from __future__ import annotations

import numpy as np

import colour

from ..config import MAX_COLOURS
from ..core.diagnostics import WarningCollector, number, numbers
from ..core.errors import value_error
from ..core.parsing import parse_colours, rgb_to_hex

INTERPOLATORS = {
    "Trilinear": colour.algebra.table_interpolation_trilinear,
    "Tetrahedral": colour.algebra.table_interpolation_tetrahedral,
}
DEFAULT_INTERPOLATORS = ("Trilinear", "Tetrahedral")
DEFAULT_GAINS = (0.9, 1.0, 1.1)
MAX_LUT_SIZE = 33
MIN_LUT_SIZE = 2


def _gains(values: list[float] | None) -> np.ndarray:
    gains = np.asarray(list(values or DEFAULT_GAINS), dtype=float)
    if gains.shape != (3,):
        raise value_error(f"gains 需要 3 个通道增益，当前 {gains.shape[0]} 个")
    if np.any(gains <= 0.05) or np.any(gains > 10):
        raise value_error("gains 每个通道需在 0.05–10")
    return gains


def _build_lut(size: int, gains: np.ndarray) -> colour.io.LUT3D:
    lut = colour.io.LUT3D(size=size)
    # 逐通道增益等于把线性表抬高成幂函数，是“最容易看出差别”的最小变换
    lut.table = np.asarray(colour.io.LUT3D.linear_table(size), dtype=float) ** gains
    return lut


def lut_data(
    colours: list[str] | None = None,
    size: int = 17,
    gains: list[float] | None = None,
    interpolators: list[str] | None = None,
    ramp_steps: int = 9,
) -> dict:
    if not (MIN_LUT_SIZE <= size <= MAX_LUT_SIZE):
        raise value_error(f"LUT 尺寸需在 {MIN_LUT_SIZE}–{MAX_LUT_SIZE}，当前 {size}")
    if not (2 <= ramp_steps <= 33):
        raise value_error("ramp_steps 需在 2–33")

    names = list(interpolators or DEFAULT_INTERPOLATORS)
    unknown = [name for name in names if name not in INTERPOLATORS]
    if unknown:
        raise value_error(f"未知插值器 {unknown}，可选：{list(INTERPOLATORS)}")

    specs = list(colours or ["#3B82F6", "#264653", "#E9C46A"])
    if len(specs) > MAX_COLOURS:
        raise value_error(f"colors 最多 {MAX_COLOURS} 个，当前 {len(specs)} 个")

    channel_gains = _gains(gains)
    lut = _build_lut(size, channel_gains)

    with WarningCollector() as log:
        rows = []
        for spec, rgb in zip(specs, parse_colours(specs)):
            outputs = {}
            values = []
            for name in names:
                try:
                    applied = np.clip(
                        np.asarray(lut.apply(rgb, interpolator=INTERPOLATORS[name]), dtype=float), 0, 1
                    )
                    outputs[name] = {"rgb": numbers(applied, 5), "hex": rgb_to_hex(applied)}
                    values.append(applied)
                except Exception as error:
                    outputs[name] = None
                    log.add("unavailable", f"{name} 插值失败：{type(error).__name__}")
            spread = (
                number(np.max(np.abs(values[0] - values[1])), 6) if len(values) >= 2 else None
            )
            rows.append(
                {
                    "input": spec,
                    "hex": rgb_to_hex(rgb),
                    "rgb": numbers(rgb, 5),
                    "outputs": outputs,
                    "interpolator_spread": spread,
                }
            )

        # 灰阶带：一眼看出幂律增益把中灰推向哪边
        ramp = []
        grey = np.linspace(0, 1, ramp_steps)
        for value in grey:
            rgb = np.array([value, value, value])
            applied = np.clip(
                np.asarray(lut.apply(rgb, interpolator=INTERPOLATORS[names[0]]), dtype=float), 0, 1
            )
            ramp.append({"input": rgb_to_hex(rgb), "output": rgb_to_hex(applied)})

        log.add(
            "note",
            f"LUT 表是 {size}³ = {size ** 3} 个格点，内存 O(n³)；"
            "四面体插值通常更贴合非线性变换，代价是常数因子更大。",
        )

    return {
        "size": size,
        "table_points": size**3,
        "gains": numbers(channel_gains, 4),
        "interpolators": names,
        "domain": "编码值（sRGB 0–1），不是线性光",
        "rows": rows,
        "ramp": ramp,
        "warnings": log.payload,
    }
