"""面板 16：视觉模型与感知现象（`POST /api/v1/phenomena-vision`）。

两件事放在一个面板，因为它们是同一类问题：**同一块光，人看到的不等于仪器测到的**。

- Helmholtz–Kohlrausch 效应：饱和度更高的颜色显得更亮（VCC / VAC 两种修正）；
- Barten 1999 对比敏感度函数：判断“这个 ΔE 到底看不看得见”的阈值曲线。

口径提醒（0.4.7）：`colour.phenomena` 是**物理光学**（薄膜干涉、瑞利散射、Snell），
感知现象在 `colour.appearance` 里；两者别搞反。
"""

from __future__ import annotations

import numpy as np

import colour

from ..core.diagnostics import WarningCollector, number, numbers
from ..core.errors import value_error
from ..core.parsing import parse_colours, rgb_to_hex

OBSERVER = "CIE 1931 2 Degree Standard Observer"
D65_XY = np.asarray(colour.CCS_ILLUMINANTS[OBSERVER]["D65"], dtype=float)
HK_METHODS = ("VCC", "VAC")
DEFAULT_LUMINANCES = (10.0, 100.0, 1000.0)


def phenomena_data(
    colours: list[str] | None = None,
    luminances: list[float] | None = None,
    chroma_max: float = 120.0,
    points: int = 40,
) -> dict:
    if not (1.0 <= chroma_max <= 200.0):
        raise value_error("chroma_max 需在 1–200")
    if not (8 <= points <= 120):
        raise value_error("points 需在 8–120")

    specs = list(colours or ["#3B82F6"])
    levels = list(luminances or DEFAULT_LUMINANCES)
    if any(not (0.001 <= level <= 100000) for level in levels):
        raise value_error("luminances 每一项需在 0.001–100000 cd·m⁻²")

    with WarningCollector() as log:
        # ---- H-K 效应：第一支颜色，围绕 D65 白点 ----
        sample = specs[0]
        rgb = parse_colours([sample])[0]
        xyz = np.asarray(colour.sRGB_to_XYZ(rgb), dtype=float)
        uv = np.asarray(colour.models.xy_to_UCS_uv(colour.XYZ_to_xy(xyz)), dtype=float)
        uv_c = np.asarray(colour.models.xy_to_UCS_uv(D65_XY), dtype=float)

        chromas = np.linspace(0.0, chroma_max, points)
        curves = {}
        for method in HK_METHODS:
            values = []
            for chroma in chromas:
                try:
                    factor = float(
                        np.asarray(
                            colour.appearance.HelmholtzKohlrausch_effect_object_Nayatani1997(
                                uv, uv_c, float(chroma), method=method
                            ),
                            dtype=float,
                        ).ravel()[0]
                    )
                except Exception as error:
                    factor = float("nan")
                    log.add("unavailable", f"H-K({method}) 在 C={chroma:g} 失败：{type(error).__name__}")
                values.append(number(factor, 6))
            curves[method] = values

        sampling = [0.0, 20.0, 50.0, 80.0]
        hk_table = [
            {
                "chroma": chroma,
                "vcc": number(
                    colour.appearance.HelmholtzKohlrausch_effect_object_Nayatani1997(
                        uv, uv_c, chroma, method="VCC"
                    ),
                    6,
                ),
                "vac": number(
                    colour.appearance.HelmholtzKohlrausch_effect_object_Nayatani1997(
                        uv, uv_c, chroma, method="VAC"
                    ),
                    6,
                ),
            }
            for chroma in sampling
        ]

        # ---- Barten 1999 CSF ----
        # 关键口径：`Y_0` 是**视角（度）**，不是亮度；亮度要经“瞳孔直径 → 视网膜照度 E”
        # 换算后传进 `E`（0.4.7 文档里的示例就是这么串的）。把亮度直接塞给 `Y_0`
        # 会得到一条几乎全零的曲线（原型阶段踩过）。
        frequencies = np.linspace(0.5, 60.0, points)
        angular_size = 60.0
        csf = {}
        retinal = {}
        for level in levels:
            try:
                pupil = float(np.asarray(colour.contrast.pupil_diameter_Barten1999(float(level), angular_size)).ravel()[0])
                illuminance = float(
                    np.asarray(colour.contrast.retinal_illuminance_Barten1999(float(level), pupil, True)).ravel()[0]
                )
            except Exception as error:
                pupil = illuminance = float("nan")
                log.add("unavailable", f"瞳孔/视网膜照度在 {level:g} cd·m⁻² 失败：{type(error).__name__}")
            retinal[f"{level:g}"] = {"pupil_diameter_mm": number(pupil, 4), "retinal_illuminance_td": number(illuminance, 4)}

            values = []
            for frequency in frequencies:
                try:
                    value = float(
                        np.asarray(
                            colour.contrast.contrast_sensitivity_function_Barten1999(
                                float(frequency), E=illuminance, X_0=angular_size, Y_0=angular_size
                            ),
                            dtype=float,
                        ).ravel()[0]
                    )
                except Exception as error:
                    value = float("nan")
                    log.add("unavailable", f"CSF 在 {level:g} cd·m⁻² 失败：{type(error).__name__}")
                values.append(number(value, 4))
            csf[f"{level:g}"] = values

        derived = [
            {
                "luminance": level,
                "pupil_diameter_mm": retinal[f"{level:g}"]["pupil_diameter_mm"],
                "retinal_illuminance_td": retinal[f"{level:g}"]["retinal_illuminance_td"],
                # 峰值频率随亮度上移，正是“亮度适应”的直接体现
                "peak_frequency_cpd": _peak_frequency(frequencies, csf[f"{level:g}"]),
            }
            for level in levels
        ]

        log.add(
            "note",
            "H-K 修正系数是 Nayatani 1997 的经验模型，给出的是“亮度增益因子”而非绝对亮度；"
            "CSF 里 `Y_0` 是视角（度），亮度经瞳孔直径换成视网膜照度 `E` 才进公式，"
            "把 cd·m⁻² 直接当 `Y_0` 传会得到一条几乎全零的假曲线。",
        )

    return {
        "observer": OBSERVER,
        "sample": {"input": sample, "hex": rgb_to_hex(rgb), "uv": numbers(uv, 6), "uv_white": numbers(uv_c, 6)},
        "hk": {
            "methods": list(HK_METHODS),
            "chromas": [round(float(value), 3) for value in chromas],
            "curves": curves,
            "table": hk_table,
            "source": "appearance.HelmholtzKohlrausch_effect_object_Nayatani1997",
        },
        "csf": {
            "source": "contrast.contrast_sensitivity_function_Barten1999",
            "frequencies": [round(float(value), 3) for value in frequencies],
            "curves": csf,
            "derived": derived,
        },
        "warnings": log.payload,
    }


def _peak_frequency(frequencies, values) -> float | None:
    """CSF 曲线的峰值频率：视觉系统最敏感的空间频率（约 2–5 cycles/degree）。"""

    pairs = [(float(f), float(v)) for f, v in zip(frequencies, values) if v is not None]
    if not pairs:
        return None
    return round(max(pairs, key=lambda pair: pair[1])[0], 3)
