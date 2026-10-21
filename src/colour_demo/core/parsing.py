"""颜色解析：把用户输入的字符串统一成 sRGB 编码值（0–1）。

支持 `#RRGGBB`、`rgb(r, g, b)`、CSS Color 3 关键字、Munsell 记号。
解析失败一律抛 `ColourParseError`，由 API 层映射成 422 + `detail.type = value_error`
（方案 6.3：不合法输入不进入 colour）。
"""

from __future__ import annotations

import re

import numpy as np

import colour


class ColourParseError(ValueError):
    """无法解析的颜色字面量。"""


_HEX_RE = re.compile(r"^#?([0-9a-fA-F]{6})$")
_RGB_RE = re.compile(r"^rgb\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*\)$")
_MUNSELL_RE = re.compile(r"^\d+(\.\d+)?[A-Z]{1,2}\s+\d+(\.\d+)?\s*/\s*\d+(\.\d+)?$")


def parse_colour(spec: str) -> np.ndarray:
    """解析单个颜色，返回 sRGB 编码值（Domain1, 0–1）。"""

    text = str(spec).strip()
    if not text:
        raise ColourParseError("颜色字符串为空")

    match = _HEX_RE.match(text)
    if match:
        digits = match.group(1)
        return np.array([int(digits[i : i + 2], 16) / 255 for i in (0, 2, 4)], dtype=float)

    match = _RGB_RE.match(text)
    if match:
        channels = [int(value) for value in match.groups()]
        if any(channel > 255 for channel in channels):
            raise ColourParseError(f"rgb() 通道必须在 0–255：{text}")
        return np.array([channel / 255 for channel in channels], dtype=float)

    if _MUNSELL_RE.match(text.replace("  ", " ")):
        try:
            xyY = colour.notation.munsell_colour_to_xyY(text)
            return np.asarray(colour.XYZ_to_sRGB(colour.xyY_to_XYZ(xyY)), dtype=float)
        except Exception as error:  # colour 抛的异常种类很杂，统一收口
            raise ColourParseError(f"无法把 {text} 解析为 Munsell 颜色：{error}") from error

    try:
        return np.asarray(colour.notation.keyword_to_RGB_CSSColor3(text.lower()), dtype=float)
    except Exception as error:
        raise ColourParseError(
            f"无法解析颜色 {text!r}：支持 #RRGGBB、rgb(r,g,b)、CSS 关键字、Munsell 记号（如 5R 5/12）"
        ) from error


def parse_colours(specs: list[str]) -> list[np.ndarray]:
    """批量解析，错误信息里带上序号（方案 6.3 要求指出第几个色值）。"""

    parsed: list[np.ndarray] = []
    for index, spec in enumerate(specs, start=1):
        try:
            parsed.append(parse_colour(spec))
        except ColourParseError as error:
            raise ColourParseError(f"第 {index} 个颜色 {spec!r} 解析失败：{error}") from error
    return parsed


def rgb_to_hex(rgb) -> str:
    """sRGB（0–1）→ `#RRGGBB`。"""

    channels = [int(round(max(0.0, min(1.0, float(channel))) * 255)) for channel in np.asarray(rgb)[:3]]
    return "#" + "".join(f"{channel:02X}" for channel in channels)
