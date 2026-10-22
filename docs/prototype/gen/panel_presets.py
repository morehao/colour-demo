"""参考面板的参数示例（纯数据）。

state 只放相对 LIVE 适配器默认值的覆盖项；前端合并默认值后调用现有 API。
没有输入参数的面板（characterisation / invoke / api）保持 0 个预设。
"""

PANEL_PRESETS = {
    "convert": [
        ("oklab", "看 Oklab", {"target": "Oklab"}),
        ("cam16", "看 CAM16", {"target": "CAM16 UCS"}),
        ("hcl", "看 HCL", {"target": "HCL"}),
    ],
    "chroma": [
        ("d50", "换 D50", {"illuminant": "D50"}),
        ("a", "换 A", {"illuminant": "A"}),
        ("fl2", "换 FL2", {"illuminant": "FL2"}),
    ],
    "observers": [
        ("d50", "日光 D50", {"illuminant": "D50"}),
        ("a", "白炽灯 A", {"illuminant": "A"}),
        ("fl11", "荧光灯 FL11", {"illuminant": "FL11"}),
    ],
    "photometry": [
        ("neutral", "黑白灰", {"colors": "#FFFFFF, #808080, #000000"}),
        ("brand", "品牌蓝黄", {"colors": "#3B82F6, #E9C46A"}),
        ("traffic", "红绿黄", {"colors": "#FF0000, #00FF00, #FFFF00"}),
    ],
    "delta-e": [
        ("de1976", "CIE 1976", {"method": "CIE 1976"}),
        ("de1994", "CIE 1994", {"method": "CIE 1994"}),
        ("cam16", "CAM16-UCS", {"method": "CAM16-UCS"}),
    ],
    "gradient": [
        ("lab", "Lab 过渡", {"space": "CIE Lab"}),
        ("srgb", "sRGB 过渡", {"space": "sRGB"}),
        ("luv", "Luv 过渡", {"space": "CIE Luv"}),
    ],
    "rgb-spaces": [
        ("ten", "前 10 个", {"limit": "10"}),
        ("twenty", "前 20 个", {"limit": "20"}),
        ("all", "全部 96 个", {"limit": "96"}),
    ],
    "transfer": [
        ("s17", "17 点采样", {"samples": "17"}),
        ("s33", "33 点采样", {"samples": "33"}),
        ("s65", "65 点采样", {"samples": "65"}),
    ],
    "chromaticity": [
        ("srgb", "只看 sRGB", {"gamuts": "sRGB"}),
        ("p3", "sRGB + P3", {"gamuts": "sRGB,Display P3"}),
        ("ucs", "1960 UCS", {"diagram": "CIE 1960 UCS"}),
    ],
    "gamut-volume": [
        ("s5k", "5000 采样", {"samples": "5000"}),
        ("s20k", "20000 采样", {"samples": "20000"}),
        ("s50k", "50000 采样", {"samples": "50000"}),
    ],
    "temperature": [
        ("warm", "2700 K 暖光", {"cct": "2700"}),
        ("neutral", "4000 K 中性", {"cct": "4000"}),
        ("cool", "9000 K 冷光", {"cct": "9000"}),
    ],
    "quality": [
        ("fl2", "荧光灯 FL2", {"illuminants": "FL2"}),
        ("a", "白炽灯 A", {"illuminants": "A"}),
        ("mixed", "一组混光", {"illuminants": "D65, D50, A, FL2, FL11"}),
    ],
    "image-lut": [
        ("s9", "9³ LUT", {"size": "9"}),
        ("s17", "17³ LUT", {"size": "17"}),
        ("s33", "33³ LUT", {"size": "33"}),
    ],
    "adaptation": [
        ("d65-a", "D65 → A", {"source": "D65", "target": "A"}),
        ("d50-d65", "D50 → D65", {"source": "D50", "target": "D65"}),
        ("fl2-d50", "FL2 → D50", {"source": "FL2", "target": "D50"}),
    ],
    "appearance": [
        ("dark", "暗环境", {"L_A": "4.07", "surround": "Dark"}),
        ("office", "办公室", {"L_A": "100", "surround": "Average"}),
        ("bright", "明亮环境", {"L_A": "318.31", "surround": "Dim"}),
    ],
    "phenomena-vision": [
        ("low", "低亮度", {"luminances": "1, 10, 100"}),
        ("mid", "中等亮度", {"luminances": "10, 100, 1000"}),
        ("high", "高亮度", {"luminances": "100, 1000, 5000"}),
    ],
    "corresponding": [
        ("e1", "实验 1", {"experiment": "1"}),
        ("e6", "实验 6", {"experiment": "6"}),
        ("e11", "实验 11", {"experiment": "11"}),
    ],
    "cvd": [
        ("protan", "红色弱", {"deficiency": "Protanomaly"}),
        ("deutan", "绿色弱", {"deficiency": "Deuteranomaly"}),
        ("tritan", "蓝色弱", {"deficiency": "Tritanomaly"}),
    ],
    "recovery": [
        ("blue", "品牌蓝", {"colors": "#3B82F6"}),
        ("gray", "中性灰", {"colors": "#808080"}),
        ("gold", "暖黄", {"colors": "#E9C46A"}),
    ],
    "notation": [
        ("tomato", "番茄红", {"keyword": "tomato"}),
        ("steelblue", "钢蓝", {"keyword": "steelblue"}),
        ("gold", "金色", {"keyword": "gold"}),
    ],
    "signals": [
        ("fl11-10", "FL11 / 10 nm", {"illuminant": "FL11", "coarse_step": "10"}),
        ("fl2-20", "FL2 / 20 nm", {"illuminant": "FL2", "coarse_step": "20"}),
        ("a-40", "A / 40 nm", {"illuminant": "A", "coarse_step": "40"}),
    ],
    "geometry": [
        ("e6", "椭圆 6", {"ellipse_index": "6"}),
        ("e11", "椭圆 11", {"ellipse_index": "11"}),
        ("e25", "椭圆 25", {"ellipse_index": "25"}),
    ],
    "optics": [
        ("thin", "薄膜 100–400 nm", {"thicknesses": "100, 250, 400"}),
        ("mid", "薄膜 200–500 nm", {"thicknesses": "200, 350, 500"}),
        ("thick", "薄膜 300–600 nm", {"thicknesses": "300, 450, 600"}),
    ],
    "gallery": [
        ("spectrum", "可见光谱", {"plots": "visible-spectrum"}),
        ("blackbody", "黑体轨迹", {"plots": "blackbody"}),
        ("macadam", "MacAdam 椭圆", {"plots": "macadam-ellipses"}),
    ],
    "catalog": [
        ("panels", "只看面板", {"status": "面板"}),
        ("datasets", "只看数据集", {"status": "数据集"}),
        ("all", "全部条目", {"status": "全部"}),
    ],
}


def apply_panel_presets(panels: list[dict]) -> None:
    for panel in panels:
        presets = PANEL_PRESETS.get(panel["id"])
        if not presets:
            continue
        panel["presets"] = [
            {"id": preset_id, "label": label, "state": dict(state)}
            for preset_id, label, state in presets
        ]
