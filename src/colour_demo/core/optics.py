"""面板 24：光学现象与响应动力学（`POST /api/v1/optics`）。

colour 不只会算颜色，还会算光：薄膜干涉、瑞利散射、Snell 折射；
`biochemistry` 则给光感受器响应的动力学模型。

两个口径：

- `thin_film_tmm` 返回 (反射, 透射) 两个数组，形状是 (波长 × 偏振/层组合)，
  取第 0 列才是非偏振单层膜的结果；
- `reaction_rate_MichaelisMenten(method="Abebe 2017")` **多一个偏置因子 `b_m`**，
  不传会 TypeError——原型里这条曲线因此从未画出来。
"""

from __future__ import annotations

import numpy as np

import colour

from ..core.diagnostics import WarningCollector, number
from ..core.errors import value_error

FILM_INDICES = (1.0, 1.38, 1.0)  # 空气 / 膜 / 空气
DEFAULT_THICKNESSES = (200.0, 350.0, 500.0)
RAYLEIGH_PAIRS = ((400.0, 700.0), (450.0, 650.0), (450.0, 550.0))
KINETIC_VMAX = 1.0
KINETIC_KM = 0.8
ABEBE_B_M = 0.813


def _thin_film(thickness: float, wavelengths: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    reflected, transmitted = colour.phenomena.thin_film_tmm(list(FILM_INDICES), float(thickness), wavelengths)
    reflected = np.asarray(reflected, dtype=float).reshape(len(wavelengths), -1)[:, 0]
    transmitted = np.asarray(transmitted, dtype=float).reshape(len(wavelengths), -1)[:, 0]
    return reflected, transmitted


def optics_data(
    thicknesses: list[float] | None = None,
    start: float = 400.0,
    end: float = 700.0,
    step: float = 5.0,
    substrate_points: int = 40,
) -> dict:
    layers = list(thicknesses or DEFAULT_THICKNESSES)
    if not layers or any(not (10.0 <= value <= 5000.0) for value in layers):
        raise value_error("thicknesses 每项需在 10–5000 nm")
    if not (360.0 <= start < end <= 830.0):
        raise value_error("范围需在 360–830 nm 且 start < end")
    if not (8 <= substrate_points <= 120):
        raise value_error("substrate_points 需在 8–120")

    wavelengths = np.arange(start, end + step / 2, step)

    with WarningCollector() as log:
        # ---- 薄膜：反射率随膜厚周期性起伏 ----
        film_rows = []
        film_curves = []
        for thickness in layers:
            try:
                reflected, transmitted = _thin_film(thickness, wavelengths)
            except Exception as error:
                log.add("unavailable", f"薄膜 {thickness:g} nm 计算失败：{type(error).__name__}")
                continue
            film_curves.append(
                {
                    "name": f"{thickness:g} nm",
                    "wavelengths": [round(float(w), 1) for w in wavelengths],
                    "values": [round(float(v), 5) for v in reflected],
                }
            )
            at550 = float(reflected[int(np.argmin(np.abs(wavelengths - 550.0)))])
            film_rows.append(
                {
                    "thickness_nm": thickness,
                    "reflectance_550": number(at550, 5),
                    "reflectance_max": number(reflected.max(), 5),
                    "reflectance_mean": number(reflected.mean(), 5),
                    "transmittance_mean": number(transmitted.mean(), 5),
                    # R + T ≈ 1 是无损介质的健全性检查
                    "rt_sum_mean": number(reflected.mean() + transmitted.mean(), 5),
                }
            )

        # ---- 瑞利散射：是否真的 1/λ⁴ ----
        scattering = colour.phenomena.sd_rayleigh_scattering(colour.SpectralShape(360, 780, 5))
        rayleigh_rows = []
        for short, long in RAYLEIGH_PAIRS:
            measured = float(np.asarray(scattering[short], dtype=float) / np.asarray(scattering[long], dtype=float))
            theory = (long / short) ** 4
            rayleigh_rows.append(
                {
                    "pair_nm": f"{short:.0f} / {long:.0f}",
                    "measured_ratio": number(measured, 4),
                    "theory_ratio": number(theory, 4),
                    "deviation_pct": number((measured / theory - 1) * 100, 2),
                }
            )

        # ---- Michaelis–Menten：经典式 vs Abebe 2017 ----
        substrate = np.linspace(0.05, 20.0, substrate_points)
        try:
            classic = [
                float(np.asarray(colour.biochemistry.reaction_rate_MichaelisMenten(s, KINETIC_VMAX, KINETIC_KM)).ravel()[0])
                for s in substrate
            ]
            revised = [
                float(
                    np.asarray(
                        colour.biochemistry.reaction_rate_MichaelisMenten(
                            s, KINETIC_VMAX, KINETIC_KM, method="Abebe 2017", b_m=ABEBE_B_M
                        )
                    ).ravel()[0]
                )
                for s in substrate
            ]
        except Exception as error:
            raise value_error(f"Michaelis–Menten 计算失败：{error}") from error

        kinetics_rows = []
        for s in (0.5, 2.0, 5.0, 20.0):
            base = float(np.asarray(colour.biochemistry.reaction_rate_MichaelisMenten(s, KINETIC_VMAX, KINETIC_KM)).ravel()[0])
            abebe = float(
                np.asarray(
                    colour.biochemistry.reaction_rate_MichaelisMenten(
                        s, KINETIC_VMAX, KINETIC_KM, method="Abebe 2017", b_m=ABEBE_B_M
                    )
                ).ravel()[0]
            )
            kinetics_rows.append({"substrate": s, "michaelis": number(base, 4), "abebe": number(abebe, 4), "delta": number(abebe - base, 4)})

        log.add(
            "note",
            "薄膜反射率整体很小（<9%），因为只有两个界面的菲涅尔反射在相互干涉；"
            "瑞利散射实测比纯 1/λ⁴ 高 2–5%，实现里含折射率色散与大气层厚度修正。"
            f"Abebe 2017 的 b_m={ABEBE_B_M} 把上渐近线抬到 V_max/b_m≈{KINETIC_VMAX / ABEBE_B_M:.2f}，"
            "所以 S=20 时速率超过 1.0 并不矛盾。",
        )

    return {
        "film": {
            "indices": list(FILM_INDICES),
            "wavelengths": [round(float(w), 1) for w in wavelengths],
            "curves": film_curves,
            "rows": film_rows,
        },
        "rayleigh": {
            "rows": rayleigh_rows,
            "curve": {
                "wavelengths": [round(float(w), 1) for w in scattering.wavelengths],
                "values": [round(float(v), 5) for v in np.asarray(scattering.values)],
            },
            "reference": "sd_rayleigh_scattering(360–780 nm, 5 nm)",
        },
        "kinetics": {
            "params": {"V_max": KINETIC_VMAX, "K_m": KINETIC_KM, "b_m": ABEBE_B_M},
            "substrate": [round(float(s), 3) for s in substrate],
            "michaelis": [round(value, 5) for value in classic],
            "abebe": [round(value, 5) for value in revised],
            "rows": kinetics_rows,
        },
        "warnings": log.payload,
    }
