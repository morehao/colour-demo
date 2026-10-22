"""面板 21：记号与解析（`POST /api/v1/notation`）。

「5R 5/12」「tomato」「#3B82F6」是同一件事的三种写法。解析层把它们统一成坐标，
是任何色彩工具的第一道工序。

两个必须说清的口径：

- **反向不唯一**：`xyY_to_munsell_colour` 会把坐标映射到最接近的色卡孔位，同一坐标可能对应多个记号，
  结果只能当建议值；
- `munsell_value(Y)` 收 **Domain100 的 Y**（0–100），传 0–1 会得到接近 0 的假明度值。
"""

from __future__ import annotations

import re

import numpy as np

import colour

from ..core.diagnostics import WarningCollector, number, numbers
from ..core.errors import value_error
from ..core.parsing import parse_colour, rgb_to_hex

OBSERVER = "CIE 1931 2 Degree Standard Observer"
# 只留规范写法（表里还有 astm2008 这类历史小写别名）
VALUE_METHODS = tuple(name for name in colour.notation.MUNSELL_VALUE_METHODS if name[0].isupper())
DEFAULT_MUNSELL = "5R 5/12"
_MUNSELL_KEY = re.compile(r"(\d+(?:\.\d+)?)\s*([A-Z]{1,2})\s+(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)", re.IGNORECASE)


def _munsell_key(text: str) -> tuple | None:
    """把记号归一成 (色相数, 色相字母, 明度, 彩度) 便于比较。"""

    match = _MUNSELL_KEY.search(str(text or ""))
    if not match:
        return None
    hue, letters, value, chroma = match.groups()
    return (float(hue), letters.upper(), float(value), float(chroma))
DEFAULT_KEYWORD = "tomato"
DEFAULT_HEX = "#3B82F6"
CSS_BASIC_LIMIT = 16


def notation_data(
    munsell: str = DEFAULT_MUNSELL,
    keyword: str = DEFAULT_KEYWORD,
    hex_value: str = DEFAULT_HEX,
    value_y: float = 5.0,
) -> dict:
    if not (0.0 <= value_y <= 100.0):
        raise value_error("value_y 是 Domain100 的 Y（0–100）")

    with WarningCollector() as log:
        # 1) Munsell 记号 ↔ xyY
        try:
            xyY = np.asarray(colour.notation.munsell_colour_to_xyY(munsell), dtype=float)
            back = colour.notation.xyY_to_munsell_colour(xyY)
            munsell_row = {
                "input": munsell,
                "xyY": numbers(xyY, 5),
                "back": str(back),
                # 记号是「色相 明度/彩度」，回程会把 5R 5/12 写成 5.0R 5.0/12.0，
                # 所以按数值比较，别按字符串比较
                "roundtrip_matches": _munsell_key(str(back)) == _munsell_key(munsell),
                "rgb": numbers(np.clip(colour.XYZ_to_sRGB(colour.xyY_to_XYZ(xyY)), 0, 1), 5),
                "hex": rgb_to_hex(np.clip(colour.XYZ_to_sRGB(colour.xyY_to_XYZ(xyY)), 0, 1)),
            }
        except Exception as error:
            raise value_error(f"无法解析 Munsell 记号 {munsell!r}：{error}") from error

        # 2) CSS 关键字 / HEX
        try:
            keyword_rgb = np.asarray(colour.notation.keyword_to_RGB_CSSColor3(keyword.lower()), dtype=float)
        except Exception as error:
            raise value_error(f"CSS 关键字 {keyword!r} 不在 CSS Color 3 里：{error}") from error
        hex_rgb = parse_colour(hex_value)

        # 3) 七种 Munsell 明度换算（Y 用 Domain100）
        rows = []
        for method in VALUE_METHODS:
            try:
                value = number(colour.notation.munsell_value(value_y, method=method), 4)
            except Exception as error:
                value = None
                log.add("unavailable", f"munsell_value({method}) 失败：{type(error).__name__}")
            rows.append({"method": method, "value": value})

        # 4) CSS Color 3 基础色（实算一遍再给 HEX，别信表里写的字符串）
        swatches = []
        for name in list(colour.notation.CSS_COLOR_3_BASIC)[:CSS_BASIC_LIMIT]:
            try:
                rgb = np.asarray(colour.notation.keyword_to_RGB_CSSColor3(name), dtype=float)
                swatches.append({"name": name, "hex": rgb_to_hex(rgb)})
            except Exception:
                continue

        log.add(
            "note",
            "xyY → Munsell 是病态逆：同一坐标可能落在多个色卡孔位之间，返回的是“最接近的记号”，"
            "工程上按建议值处理；munsell_value 的 Y 走 0–100 域。",
        )

    return {
        "munsell": munsell_row,
        "keyword": {"input": keyword, "rgb": numbers(keyword_rgb, 5), "hex": rgb_to_hex(keyword_rgb)},
        "hex": {"input": hex_value, "rgb": numbers(hex_rgb, 5), "canonical": rgb_to_hex(hex_rgb)},
        "value_y": value_y,
        "value_methods": rows,
        "css_basic": swatches,
        "counts": {
            "css_color_3": len(colour.notation.CSS_COLOR_3),
            "css_basic": len(colour.notation.CSS_COLOR_3_BASIC),
            "css_extended": len(colour.notation.CSS_COLOR_3_EXTENDED),
            "munsell_all": len(colour.notation.MUNSELL_COLOURS_ALL),
            "munsell_real": len(colour.notation.MUNSELL_COLOURS_REAL),
            "munsell_1929": len(colour.notation.MUNSELL_COLOURS_1929),
        },
        "warnings": log.payload,
    }
