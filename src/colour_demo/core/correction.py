"""面板 20：色彩校正与 ACES（`POST /api/v1/correction`）。

「相机拍出来偏色」的本质是一次线性（或多项式）变换：拿 24 色卡在已知光源下拍一张，
把实测 RGB 映射回已知真值，解出校正矩阵，就能整批拉回。

口径（原型阶段踩过，照做）：

- `colour_correction(RGB, M_T, M_R)` 的 `M_T` 是**实测**、`M_R` 是**参考真值**；
  两边都传参考值会退化成恒等变换，看上去“删了矩阵也对”，其实是没做校正；
- Finlayson 2015 的默认 `degree=1` 与 Cheung 2004 的三项展开数学等价，数字一模一样；
  要体现它的差异必须 `degree=3`（靠更高次项降残差）；
- 「在 A 光源下拍摄」用 Von Kries 把 D65 参考色适应到 A 来模拟，不是真的重算光谱。
"""

from __future__ import annotations

import numpy as np

import colour

from ..core.diagnostics import WarningCollector, number
from ..core.errors import value_error
from ..core.parsing import rgb_to_hex

OBSERVER = "CIE 1931 2 Degree Standard Observer"
CHECKER = "ColorChecker24 - After November 2014"
D65_XY = np.asarray(colour.CCS_ILLUMINANTS[OBSERVER]["D65"], dtype=float)
A_XY = np.asarray(colour.CCS_ILLUMINANTS[OBSERVER]["A"], dtype=float)

# (标签, 传给 colour_correction 的参数)
CORRECTION_SPECS = (
    ("Cheung 2004", {"method": "Cheung 2004"}),
    ("Finlayson 2015 · 3 阶", {"method": "Finlayson 2015", "degree": 3}),
    ("Vandermonde", {"method": "Vandermonde"}),
)
METHODS = tuple(label for label, _ in CORRECTION_SPECS)
STRIP_PATCHES = 12


def _checker():
    try:
        return colour.characterisation.CCS_COLOURCHECKERS[CHECKER]
    except Exception as error:
        raise value_error(f"取不到色卡 {CHECKER!r}：{error}") from error


def _deltas(data: np.ndarray, ideal: np.ndarray) -> tuple[float, float]:
    """逐色块 ΔE（CIE 2000）；返回 (均值, 最大)。"""

    values = [
        float(colour.delta_E(colour.XYZ_to_Lab(colour.sRGB_to_XYZ(data[i])),
                             colour.XYZ_to_Lab(colour.sRGB_to_XYZ(ideal[i])), method="CIE 2000"))
        for i in range(len(data))
    ]
    return float(np.mean(values)), float(np.max(values))


def correction_data(methods: list[str] | None = None) -> dict:
    names = list(methods or METHODS)
    unknown = [name for name in names if name not in METHODS]
    if unknown:
        raise value_error(f"未知校正方法 {unknown}，可选：{list(METHODS)}")

    checker = _checker()
    reference = np.asarray([xyz for xyz in checker.data.values()], dtype=float)
    xyz_d65 = np.asarray(colour.xy_to_XYZ(D65_XY), dtype=float)
    xyz_a = np.asarray(colour.xy_to_XYZ(A_XY), dtype=float)

    ideal = np.clip(np.asarray(colour.XYZ_to_sRGB(reference), dtype=float), 0, 1)
    captured = np.clip(
        np.asarray(
            colour.XYZ_to_sRGB(
                colour.chromatic_adaptation(reference, xyz_d65, xyz_a, method="Von Kries")
            ),
            dtype=float,
        ),
        0,
        1,
    )

    before_mean, before_max = _deltas(captured, ideal)

    with WarningCollector() as log:
        stages = [
            {
                "stage": "校正前（A 光源下拍摄）",
                "mean_delta_e": round(before_mean, 3),
                "max_delta_e": round(before_max, 3),
                "swatches": [rgb_to_hex(captured[i]) for i in range(STRIP_PATCHES)],
            }
        ]
        matrices = []
        for label, spec in CORRECTION_SPECS:
            if label not in names:
                continue
            try:
                corrected = np.clip(
                    np.asarray(
                        colour.characterisation.colour_correction(captured, captured, ideal, **spec), dtype=float
                    ),
                    0,
                    1,
                )
                mean, peak = _deltas(corrected, ideal)
                stages.append(
                    {
                        "stage": f"校正后（{label}）",
                        "method": label,
                        "mean_delta_e": round(mean, 3),
                        "max_delta_e": round(peak, 3),
                        "swatches": [rgb_to_hex(corrected[i]) for i in range(STRIP_PATCHES)],
                    }
                )
                matrix = np.asarray(colour.characterisation.matrix_colour_correction(captured, ideal, **spec))
                matrices.append(
                    {
                        "method": label,
                        "shape": [int(matrix.shape[0]), int(matrix.shape[1])],
                        "kind": "多项式展开项数 × 通道数",
                    }
                )
            except Exception as error:
                log.add("unavailable", f"{label} 校正失败：{type(error).__name__}")
                stages.append({"stage": f"校正后（{label}）", "method": label, "mean_delta_e": None, "max_delta_e": None, "swatches": []})

        best = min((row for row in stages if row["mean_delta_e"] is not None), key=lambda row: row["mean_delta_e"])
        log.add(
            "note",
            "ΔE 用 CIE 2000；「拍摄」是把 D65 参考色经 Von Kries 适应到 A 再转 sRGB 的模拟，不是真实光谱重算。"
            "多项式校正只能把偏色拉回、无法归零：残差来自色卡的非线性响应与色适应模型的差异。",
        )

    return {
        "checker": CHECKER,
        "patches": len(reference),
        "capture_model": "D65 参考色 → Von Kries → A → sRGB",
        "delta_e_method": "CIE 2000",
        "stages": stages,
        "best": {"method": best.get("method"), "mean_delta_e": best["mean_delta_e"]},
        "matrices": matrices,
        "methods": list(METHODS),
        "warnings": log.payload,
    }
