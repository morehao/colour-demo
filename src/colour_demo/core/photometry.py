"""面板 04：光度、明度与白度黄度（`POST /api/v1/photometry`）。

域约定（方案 7.2）：colour 的 lightness/luminance/whiteness/yellowness 收 **Domain100**，
所以这里严格把 XYZ 与 Y 乘 100 再传，绝不混用 0–1。
"""

from __future__ import annotations

import numpy as np

import colour

from ..core.errors import value_error
from ..core.parsing import parse_colour, parse_colours, rgb_to_hex

LIGHTNESS_METHODS = [m for m in colour.colorimetry.LIGHTNESS_METHODS if m[0].isupper()]
WHITENESS_METHODS = [m for m in colour.colorimetry.WHITENESS_METHODS if m[0].isupper()]
YELLOWNESS_METHODS = [m for m in colour.colorimetry.YELLOWNESS_METHODS if m[0].isupper()]


def photometry_data(colours: list[str], white: str = "#FFFFFF") -> dict:
    rgb_list = parse_colours(colours)
    xyzw = np.asarray(colour.sRGB_to_XYZ(parse_colour(white)), dtype=float) * 100

    rows = []
    for spec, rgb in zip(colours, rgb_list):
        xyz100 = np.asarray(colour.sRGB_to_XYZ(rgb), dtype=float) * 100
        y100 = float(xyz100[1])

        lightness = {}
        for method in LIGHTNESS_METHODS:
            try:
                lightness[method] = round(float(np.asarray(colour.colorimetry.lightness(y100, method=method)).ravel()[0]), 4)
            except Exception as error:
                lightness[method] = f"不可用（{type(error).__name__}）"

        luminance = {}
        for method in ["Newhall 1943", "ASTM D1535", "CIE 1976", "Fairchild 2010", "Fairchild 2011", "Abebe 2017"]:
            try:
                luminance[method] = round(float(np.asarray(colour.colorimetry.luminance(y100, method=method)).ravel()[0]), 4)
            except Exception as error:
                luminance[method] = f"不可用（{type(error).__name__}）"

        whiteness = {}
        for method in WHITENESS_METHODS:
            try:
                value = np.asarray(colour.colorimetry.whiteness(xyz100, xyzw, method=method)).ravel()[0]
                whiteness[method] = round(float(value), 4)
            except Exception as error:
                whiteness[method] = f"不可用（{type(error).__name__}）"

        yellowness = {}
        for method in YELLOWNESS_METHODS:
            try:
                value = np.asarray(colour.colorimetry.yellowness(xyz100, method=method)).ravel()[0]
                yellowness[method] = round(float(value), 4)
            except Exception as error:
                yellowness[method] = f"不可用（{type(error).__name__}）"

        rows.append(
            {
                "input": spec,
                "hex": rgb_to_hex(rgb),
                "Y": round(y100, 4),
                "lightness": lightness,
                "luminance": luminance,
                "whiteness": whiteness,
                "yellowness": yellowness,
            }
        )

    return {
        "domain": "XYZ/Y 乘 100（Domain100）",
        "white": white,
        "rows": rows,
        "warnings": [],
    }


def validate_method(kind: str, method: str) -> str:
    table = {
        "lightness": LIGHTNESS_METHODS,
        "whiteness": WHITENESS_METHODS,
        "yellowness": YELLOWNESS_METHODS,
    }
    if kind not in table:
        raise value_error(f"未知类别 {kind!r}")
    if method not in table[kind]:
        raise value_error(f"{kind} 不支持方法 {method!r}，可选：{table[kind]}")
    return method
