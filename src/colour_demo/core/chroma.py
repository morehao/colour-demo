"""面板 02：色度学属性（`POST /api/v1/chroma`）。

xy / uv（CIE 1960）/ u′v′（CIE 1976）、主波长、激发纯度、色度纯度、补色波长。
"""

from __future__ import annotations

import numpy as np

import colour

from ..config import DEFAULT_ILLUMINANT, DEFAULT_OBSERVER
from ..core.errors import value_error
from ..core.parsing import parse_colours, rgb_to_hex


def _whitepoint(xy):
    return np.asarray(xy, dtype=float)


def chroma_data(colours: list[str], illuminant: str = DEFAULT_ILLUMINANT) -> dict:
    rgb_list = parse_colours(colours)
    try:
        xy_n = _whitepoint(colour.CCS_ILLUMINANTS[DEFAULT_OBSERVER][illuminant])
    except Exception as error:
        raise value_error(f"未知光源 {illuminant!r}：{error}") from error

    rows = []
    for spec, rgb in zip(colours, rgb_list):
        xyz = np.asarray(colour.sRGB_to_XYZ(rgb), dtype=float)
        xy = np.asarray(colour.XYZ_to_xy(xyz), dtype=float)
        uv_1960 = np.asarray(colour.models.xy_to_Luv_uv(xy), dtype=float)
        uv_1976 = np.asarray(colour.models.xy_to_UCS_uv(xy), dtype=float)

        # 主波长 / 补色波长：色度点落在白点附近时无解（返回 nan），如实上报
        dominant, _dominant_wl, _dominant_xy = colour.colorimetry.dominant_wavelength(xy, xy_n)
        complementary, _complementary_wl, _complementary_xy = colour.colorimetry.complementary_wavelength(
            xy, xy_n
        )
        rows.append(
            {
                "input": spec,
                "hex": rgb_to_hex(rgb),
                "xyz": [round(float(channel), 6) for channel in xyz],
                "xy": [round(float(channel), 6) for channel in xy],
                "uv": [round(float(channel), 6) for channel in uv_1960],
                "uv_prime": [round(float(channel), 6) for channel in uv_1976],
                "dominant_wavelength": _as_float(dominant),
                "complementary_wavelength": _as_float(complementary),
                "excitation_purity": _as_float(colour.colorimetry.excitation_purity(xy, xy_n)),
                "colorimetric_purity": _as_float(colour.colorimetry.colorimetric_purity(xy, xy_n)),
            }
        )

    return {
        "illuminant": illuminant,
        "observer": DEFAULT_OBSERVER,
        "whitepoint_xy": [round(float(channel), 6) for channel in xy_n],
        "rows": rows,
        "warnings": _warnings_for(rows),
    }


def _as_float(value) -> float | None:
    """nan / inf 一律转 None，避免 JSON 里出现非法字面量。"""

    try:
        number = float(np.asarray(value, dtype=float).ravel()[0])
    except Exception:
        return None
    return round(number, 4) if np.isfinite(number) else None


def _warnings_for(rows: list[dict]) -> list[dict]:
    warnings = []
    for row in rows:
        if row["dominant_wavelength"] is None:
            warnings.append(
                {
                    "type": "undefined",
                    "colour": row["input"],
                    "message": "该色度点无法定义主波长（接近白点或落在普尔金耶轨迹外侧），返回 null",
                }
            )
    return warnings
