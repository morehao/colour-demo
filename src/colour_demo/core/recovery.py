"""面板 19：光谱重建（`POST /api/v1/recovery`）。

一支 RGB 背后是无穷多条光谱——这就是同色异谱。重建就是“猜一条最合理的光谱”。

三个口径必须照做（原型阶段全部踩过）：

1. **Smits 1999 / Mallett 2019 收线性 RGB**，不是编码值：传 `#3B82F6` 的 0–255/255 直接进会算偏，
   要先用 `cctf_decoding` 线性化；
2. **Jakob 2019 / Meng 2015 / Otsu 2018 收 XYZ**（0–1，D65）；
3. 重建结果是**反射率**，要按反射率口径积分回三刺激值：
   `sd_to_XYZ(sd, illuminant=D65) / 100`，再转 sRGB。直接 `XYZ_to_sRGB(sd_to_XYZ(sd))` 会拿到
   0–100 的自发光标度，被裁成纯白。

另外 Smits 1999 的采样是 380–720 nm 非等间隔（37.8 nm），ASTM E308 只接受 1/5/10/20 nm，
所以回算前要重采样到等间隔，否则 `sd_to_XYZ` 内部会报警或给出偏差。
"""

from __future__ import annotations

import numpy as np

import colour

from ..config import MAX_COLOURS
from ..core.diagnostics import WarningCollector, number
from ..core.errors import value_error
from ..core.parsing import parse_colours, rgb_to_hex

DEFAULT_COLOUR = "#3B82F6"
# XYZ 派（收 0–1 XYZ）与 RGB 派（收线性 RGB）分开列，避免“传错域不报错、只静默偏差”
METHODS = {
    "Smits 1999": {"domain": "线性 RGB", "kind": "rgb"},
    "Mallett 2019": {"domain": "线性 RGB", "kind": "rgb"},
    "Jakob 2019": {"domain": "XYZ（0–1）", "kind": "xyz"},
    "Meng 2015": {"domain": "XYZ（0–1）", "kind": "xyz"},
    "Otsu 2018": {"domain": "XYZ（0–1）", "kind": "xyz"},
}
DEFAULT_METHODS = ("Smits 1999", "Mallett 2019", "Jakob 2019", "Meng 2015")

OBSERVER = "CIE 1931 2 Degree Standard Observer"
D65_SD = colour.SDS_ILLUMINANTS["D65"]
RESAMPLE_STEP = 5.0


def _reconstruct(method: str, linear_rgb: np.ndarray, xyz: np.ndarray):
    if METHODS[method]["kind"] == "rgb":
        if method == "Smits 1999":
            return colour.recovery.RGB_to_sd_Smits1999(linear_rgb)
        return colour.recovery.RGB_to_sd_Mallett2019(linear_rgb)
    return colour.recovery.XYZ_to_sd(xyz, method=method)


def _reflectance_to_hex(sd, step: float) -> tuple[str, np.ndarray]:
    """按**反射率**口径把它积分回三刺激值，再转 sRGB（这条链是面板 19 的核心口径）。"""

    samples = sd.copy()
    if round(float(samples.shape.interval), 3) not in (1.0, 5.0, 10.0, 20.0):
        samples = samples.interpolate(
            colour.SpectralShape(samples.shape.start, samples.shape.end, step),
            interpolator=colour.SpragueInterpolator,
        )
    xyz_back = np.asarray(colour.sd_to_XYZ(samples, illuminant=D65_SD), dtype=float) / 100
    rgb_back = np.clip(np.asarray(colour.XYZ_to_sRGB(xyz_back), dtype=float), 0, 1)
    return rgb_to_hex(rgb_back), rgb_back


def recovery_data(
    colours: list[str] | None = None,
    methods: list[str] | None = None,
    step: float = RESAMPLE_STEP,
) -> dict:
    specs = list(colours or [DEFAULT_COLOUR])
    if len(specs) > MAX_COLOURS:
        raise value_error(f"colors 最多 {MAX_COLOURS} 个，当前 {len(specs)} 个")
    names = list(methods or DEFAULT_METHODS)
    unknown = [name for name in names if name not in METHODS]
    if unknown:
        raise value_error(f"未知重建方法 {unknown}，可选：{list(METHODS)}")
    if step not in (1.0, 2.0, 5.0, 10.0, 20.0):
        raise value_error("step 只支持 1 / 2 / 5 / 10 / 20 nm（ASTM E308 的等间隔网格）")

    with WarningCollector() as log:
        rows = []
        curves = []
        for spec, rgb in zip(specs, parse_colours(specs)):
            # 线性化 = 码值 → 线性光，是 `eotf_sRGB`；`eotf_inverse_sRGB` 是反方向（线性 → 码值），
            # 写成后者会把 0.231 编成 0.518，重建结果整体偏亮（面板 19 实测 ΔE 26 就是这么来的）。
            linear = np.asarray(colour.models.eotf_sRGB(rgb), dtype=float)
            xyz = np.asarray(colour.sRGB_to_XYZ(rgb), dtype=float)
            lab_original = np.asarray(colour.XYZ_to_Lab(xyz), dtype=float)

            for method in names:
                try:
                    sd = _reconstruct(method, linear, xyz)
                    hex_back, rgb_back = _reflectance_to_hex(sd, step)
                    delta = number(
                        colour.delta_E(
                            lab_original,
                            np.asarray(colour.XYZ_to_Lab(colour.sRGB_to_XYZ(rgb_back)), dtype=float),
                            method="CIE 2000",
                        ),
                        3,
                    )
                except Exception as error:
                    rows.append({"method": method, "domain": METHODS[method]["domain"], "hex": None, "delta_e": None})
                    log.add("unavailable", f"{spec} 的 {method} 重建失败：{type(error).__name__}")
                    continue

                rows.append(
                    {
                        "input": spec,
                        "method": method,
                        "domain": METHODS[method]["domain"],
                        "hex": hex_back.upper(),
                        "delta_e": delta,
                        "samples": int(len(sd.values)),
                        "range_nm": [round(float(sd.shape.start), 1), round(float(sd.shape.end), 1)],
                    }
                )
                curves.append(
                    {
                        "name": method,
                        "wavelengths": [round(float(w), 1) for w in sd.wavelengths],
                        "values": [round(float(v), 5) for v in np.asarray(sd.values)],
                    }
                )

        log.add(
            "note",
            "重建不唯一：给 RGB 加“平滑、非负、基函数限定”等约束才收敛，所以不同方法给不同曲线是正常现象，"
            "只要在 D65 下积分回三刺激值后一致，就是同一支颜色（同色异谱）。"
            "Smits 1999 用平滑分段基函数，蓝端超出覆盖范围，残差约 1 个 ΔE 是方法局限，不是实现误差。",
        )

    return {
        "methods": {name: METHODS[name] for name in names},
        "step": step,
        "observer": OBSERVER,
        "illuminant": "D65",
        "rows": rows,
        "curves": curves,
        "warnings": log.payload,
    }
