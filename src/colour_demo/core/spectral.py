"""面板 03：观察者与光源（`POST /api/v1/spectral`）。

返回 SPD 采样点、标准观察者 CMFS 摘要，以及黑体合成光谱。
"""

from __future__ import annotations

import numpy as np

import colour

from ..config import DEFAULT_ILLUMINANT, MAX_SPECTRAL_SAMPLES, SPECTRAL_RANGE
from ..core.errors import value_error


def spectral_data(
    illuminant: str = DEFAULT_ILLUMINANT,
    start: float = 380.0,
    end: float = 780.0,
    interval: float = 5.0,
    blackbody_temperature: float | None = None,
) -> dict:
    low, high = SPECTRAL_RANGE
    if not (low <= start < end <= high):
        raise value_error(f"光谱范围必须在 {low:g}–{high:g} nm 且 start < end")
    if interval <= 0:
        raise value_error("interval 必须为正")
    samples = int(round((end - start) / interval)) + 1
    if samples > MAX_SPECTRAL_SAMPLES:
        raise value_error(f"采样点数 {samples} 超过上限 {MAX_SPECTRAL_SAMPLES}，请加大 interval")

    shape = colour.SpectralShape(start, end, interval)
    try:
        spd = colour.SDS_ILLUMINANTS[illuminant].copy().align(shape)
    except Exception as error:
        raise value_error(f"未知光源 {illuminant!r}：{error}") from error

    series = [
        {
            "name": illuminant,
            "wavelengths": [round(float(w), 3) for w in spd.wavelengths],
            "values": [round(float(v), 6) for v in spd.values],
            "peak": round(float(np.max(spd.values)), 4),
            "mean": round(float(np.mean(spd.values)), 4),
        }
    ]

    if blackbody_temperature is not None:
        if not (1000 <= blackbody_temperature <= 25000):
            raise value_error("blackbody_temperature 需在 1000–25000 K")
        blackbody = colour.sd_blackbody(blackbody_temperature, shape=shape)
        # 归一化到与 CIE 光源同量级（Y=100），否则曲线差几个数量级无法同图
        normalised = blackbody.copy()
        scale = 100.0 / max(float(np.max(blackbody.values)), 1e-12)
        normalised.values = np.asarray(blackbody.values) * scale
        series.append(
            {
                "name": f"黑体 {blackbody_temperature:g} K（归一化 ×{scale:.3g}）",
                "wavelengths": [round(float(w), 3) for w in normalised.wavelengths],
                "values": [round(float(v), 6) for v in normalised.values],
                "peak": round(float(np.max(normalised.values)), 4),
                "mean": round(float(np.mean(normalised.values)), 4),
            }
        )

    observer = colour.MSDS_CMFS["CIE 1931 2 Degree Standard Observer"]
    return {
        "shape": {"start": start, "end": end, "interval": interval, "samples": samples},
        "observers": sorted(colour.MSDS_CMFS.keys())[:12],
        "illuminants_total": len(colour.SDS_ILLUMINANTS),
        "observer_shape": {
            "start": float(observer.shape.start),
            "end": float(observer.shape.end),
            "interval": float(observer.shape.interval),
        },
        "series": series,
        "warnings": [],
    }
