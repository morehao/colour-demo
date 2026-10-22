"""面板 11：色温与黑体轨迹（`POST /api/v1/temperature`）。

0.4.7 的四张方法表口径不同，混用会直接抛错（原型里就踩了）：

- `xy_to_CCT` 只认 `XY_TO_CCT_METHODS`（4 个），`CCT_to_xy` 只认 `CCT_TO_XY_METHODS`；
- `uv_to_CCT` / `CCT_to_uv` 只认 `UV_TO_CCT_METHODS` / `CCT_TO_UV_METHODS`；
- Ohno 2013 / Robertson 1968 的**反解**返回 `(CCT, D_uv)` 二元组而不是标量，
  它们的**正解**也只接受 `CCT_D_uv` 二元组输入。

所以这里按“xy 派”“uv 派”分开返回，谁都不能冒充谁。
"""

from __future__ import annotations

import warnings

import numpy as np

import colour

from ..core.diagnostics import WarningCollector, number, numbers
from ..core.errors import value_error
from ..core.parsing import parse_colours, rgb_to_hex

# 只保留规范写法（colour 里还有 kang2002 / mccamy1992 这类历史小写别名）
XY_TO_CCT_METHODS = tuple(name for name in colour.temperature.XY_TO_CCT_METHODS if name[0].isupper())
UV_TO_CCT_METHODS = tuple(name for name in colour.temperature.UV_TO_CCT_METHODS if name[0].isupper())
CCT_TO_XY_METHODS = tuple(name for name in colour.temperature.CCT_TO_XY_METHODS if name[0].isupper())
CCT_TO_UV_METHODS = tuple(name for name in colour.temperature.CCT_TO_UV_METHODS if name[0].isupper())

# 反向表求 xy 时用一个“一定可用”的方法构造样本点（D65 附近）
_REFERENCE_METHOD = "CIE Illuminant D Series"
# 普朗克轨迹只由黑体给出，与“日光轨迹”不是同一条
_LOCUS_METHOD = "Planck 1900"

CCT_RANGE = (800.0, 100000.0)


def _cct_scalar(value) -> float | None:
    return number(value, 4)


def _cct_and_duv(value) -> tuple[float | None, float | None]:
    array = np.asarray(value, dtype=float).ravel()
    cct = number(array[0], 4) if array.size else None
    duv = number(array[1], 6) if array.size > 1 else None
    return cct, duv


def _uv_pair(value) -> np.ndarray:
    """CCT_to_uv 的返回形状不统一：Ohno/Robertson 给 (2,)，Krystek/Planck 给 (2, 2)。

    两种形状下**第一组**才是本次输入的 u′v′（第二组是 duv 分支或占位），统一取前两个数。
    """

    return np.asarray(value, dtype=float).reshape(-1, 2)[0]


def _validate(method: str, table: tuple[str, ...], kind: str) -> str:
    if method not in table:
        raise value_error(f"{kind} 不支持方法 {method!r}，可选：{list(table)}")
    return method


def _sample_points(colours: list[str] | None, cct: float) -> list[dict]:
    """没有给颜色时，用给定色温在黑体/日光轨迹上的点做样本，保证表格不空。"""

    samples = []
    if colours:
        for spec, rgb in zip(colours, parse_colours(colours)):
            xyz = np.asarray(colour.sRGB_to_XYZ(rgb), dtype=float)
            xy = np.asarray(colour.XYZ_to_xy(xyz), dtype=float)
            samples.append(
                {
                    "input": spec,
                    "hex": rgb_to_hex(rgb),
                    "xy": numbers(xy, 6),
                    "uv": numbers(colour.models.xy_to_UCS_uv(xy), 6),
                }
            )
        return samples

    xy = np.asarray(colour.temperature.CCT_to_xy(cct, method=_REFERENCE_METHOD), dtype=float)
    samples.append(
        {
            "input": None,
            "hex": None,
            "xy": numbers(xy, 6),
            "uv": numbers(colour.models.xy_to_UCS_uv(xy), 6),
        }
    )
    return samples


def temperature_data(
    colours: list[str] | None = None,
    cct: float = 6500.0,
    duv: float = 0.0,
    locus_points: int = 12,
) -> dict:
    low, high = CCT_RANGE
    if not (low <= cct <= high):
        raise value_error(f"cct 需在 {low:g}–{high:g} K，当前 {cct:g}")
    if not (-0.05 <= duv <= 0.05):
        raise value_error("duv 需在 -0.05–0.05")
    if not (3 <= locus_points <= 64):
        raise value_error("locus_points 需在 3–64")

    samples = _sample_points(colours, cct)

    with WarningCollector() as log:
        # 1) xy → CCT（4 个反解方法）
        xy_to_cct_rows = []
        for sample in samples:
            xy = np.asarray(sample["xy"], dtype=float)
            results = {}
            for method in XY_TO_CCT_METHODS:
                try:
                    results[method] = _cct_scalar(colour.temperature.xy_to_CCT(xy, method=method))
                except Exception as error:  # colour 抛的异常种类很杂，按“该方法不可用”上报
                    results[method] = None
                    log.add("unavailable", f"xy_to_CCT {method} 失败：{type(error).__name__}")
            xy_to_cct_rows.append({"sample": sample["hex"] or f"{cct:g} K", "results": results})

        # 2) uv → CCT（含 D_uv，Ohno/Robertson 返回二元组）
        uv_to_cct_rows = []
        for sample in samples:
            uv = np.asarray(sample["uv"], dtype=float)
            results = {}
            for method in UV_TO_CCT_METHODS:
                try:
                    value, duv_out = _cct_and_duv(colour.temperature.uv_to_CCT(uv, method=method))
                    results[method] = {"cct": value, "duv": duv_out}
                except Exception as error:
                    results[method] = None
                    log.add("unavailable", f"uv_to_CCT {method} 失败：{type(error).__name__}")
            uv_to_cct_rows.append({"sample": sample["hex"] or f"{cct:g} K", "results": results})

        # 3) CCT → xy / uv（正解）
        cct_to_xy_rows = []
        for method in CCT_TO_XY_METHODS:
            try:
                xy = numbers(colour.temperature.CCT_to_xy(cct, method=method), 6)
            except Exception as error:
                xy = None
                log.add("unavailable", f"CCT_to_xy {method} 失败：{type(error).__name__}")
            cct_to_xy_rows.append({"method": method, "xy": xy})

        cct_to_uv_rows = []
        for method in CCT_TO_UV_METHODS:
            try:
                uv = _uv_pair(colour.temperature.CCT_to_uv(np.array([[cct, duv]]), method=method))
                cct_to_uv_rows.append(
                    {
                        "method": method,
                        "uv": numbers(uv, 6),
                        "xy": numbers(colour.models.UCS_uv_to_xy(uv), 6),
                    }
                )
            except Exception as error:
                cct_to_uv_rows.append({"method": method, "uv": None, "xy": None})
                log.add("unavailable", f"CCT_to_uv {method} 失败：{type(error).__name__}")

        # 4) mired（色温的倒数坐标，摄影滤色片用它）
        mired = number(colour.temperature.CCT_to_mired(cct), 4)
        mired_back = (
            number(colour.temperature.mired_to_CCT(mired), 4) if mired is not None else None
        )

        # 5) 普朗克轨迹采样（黑体，不是日光轨迹）
        # Planck 1900 在轨迹两端会触发 `divide by zero` 的 RuntimeWarning（库内数值问题，
        # 曲线本身仍然正常），这里只压这一条，避免把库噪声当成口径告警回给前端。
        locus = []
        for value in np.geomspace(max(cct * 0.25, low), min(cct * 2.5, high), locus_points):
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", message=".*divide by zero.*", category=RuntimeWarning)
                uv = _uv_pair(
                    colour.temperature.CCT_to_uv(np.array([float(value), 0.0]), method=_LOCUS_METHOD)
                )
            locus.append(
                {
                    "cct": round(float(value), 1),
                    "uv": numbers(uv, 6),
                    "xy": numbers(colour.models.UCS_uv_to_xy(uv), 6),
                }
            )

        log.add(
            "note",
            "xy 派与 uv 派的方法表互不通用；McCamy 1992 是经验拟合、非双射，"
            "给定 CCT 反推的 xy 不保证落在轨迹上。",
        )

    return {
        "input": {"cct": cct, "duv": duv, "mired": mired, "locus_method": _LOCUS_METHOD},
        "samples": samples,
        "methods": {
            "xy_to_cct": list(XY_TO_CCT_METHODS),
            "uv_to_cct": list(UV_TO_CCT_METHODS),
            "cct_to_xy": list(CCT_TO_XY_METHODS),
            "cct_to_uv": list(CCT_TO_UV_METHODS),
        },
        "xy_to_cct": xy_to_cct_rows,
        "uv_to_cct": uv_to_cct_rows,
        "cct_to_xy": cct_to_xy_rows,
        "cct_to_uv": cct_to_uv_rows,
        "mired": {"cct": cct, "mired": mired, "round_trip_cct": mired_back},
        "planckian_locus": locus,
        "warnings": log.payload,
    }
