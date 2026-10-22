"""术语表：40 条，新手浮层与术语页的单一来源。

每条：
    term    展示用短名（原文优先）
    zh      中文名
    aliases 自动高亮用的别名（最长匹配；不要与别的条目重复）
    plain   一句话解释（≤80 字，浮层首行）
    note    可选补充（易混点）
    see     可选深链（#/ref/<panel-id>）
"""

from __future__ import annotations

GLOSSARY: dict[str, dict] = {
    "delta-e": {
        "term": "ΔE",
        "zh": "色差",
        "aliases": ["ΔE", "ΔE00", "Delta E", "色差"],
        "plain": "给两个颜色的差别打的分数，数字越大差得越多。",
        "note": "不同算法的分数不能直接比较。",
        "see": "#/ref/delta-e",
    },
    "srgb": {
        "term": "sRGB",
        "zh": "标准 RGB 色域",
        "aliases": ["sRGB"],
        "plain": "最常见的屏幕色域，网页和普通显示器默认就是它。",
        "see": "#/ref/rgb-spaces",
    },
    "display-p3": {
        "term": "Display P3",
        "zh": "广色域",
        "aliases": ["Display P3", "P3"],
        "plain": "苹果设备和部分新显示器用的更宽色域，比 sRGB 更鲜艳。",
        "see": "#/ref/rgb-spaces",
    },
    "bt2020": {
        "term": "BT.2020",
        "zh": "超高清色域",
        "aliases": ["BT.2020", "Rec. 2020"],
        "plain": "4K/8K 视频标准色域，比 P3 还宽，日常屏幕基本显示不全。",
        "see": "#/ref/rgb-spaces",
    },
    "gamut": {
        "term": "色域",
        "zh": "色域",
        "aliases": ["色域"],
        "plain": "一台设备或一种标准能显示的颜色范围。",
        "see": "#/ref/chromaticity",
    },
    "white-point": {
        "term": "白点",
        "zh": "白点",
        "aliases": ["白点"],
        "plain": "把什么颜色当作纯白，决定了整套颜色的基准。",
        "see": "#/ref/observers",
    },
    "d65": {
        "term": "D65",
        "zh": "日光白点",
        "aliases": ["D65"],
        "plain": "常用日光白点，约 6500K，屏幕校准的默认参考。",
        "see": "#/ref/temperature",
    },
    "cct": {
        "term": "色温",
        "zh": "色温",
        "aliases": ["色温", "CCT"],
        "plain": "用开尔文表示光的冷暖：2700K 偏黄，6500K 接近日光。",
        "see": "#/ref/temperature",
    },
    "planckian-locus": {
        "term": "黑体轨迹",
        "zh": "黑体轨迹",
        "aliases": ["黑体轨迹", "普朗克轨迹"],
        "plain": "理想黑体加热后颜色变化的曲线，色温就定义在它上面。",
    },
    "duv": {
        "term": "D_uv",
        "zh": "色温偏差",
        "aliases": ["D_uv", "Duv"],
        "plain": "颜色偏离黑体轨迹的程度，正值偏绿、负值偏品红。",
    },
    "cie-xyz": {
        "term": "CIE XYZ",
        "zh": "三刺激值",
        "aliases": ["CIE XYZ", "XYZ"],
        "plain": "色彩计算的通用中间语言，几乎所有换算都经过它。",
        "see": "#/ref/convert",
    },
    "cie-lab": {
        "term": "CIE Lab",
        "zh": "感知均匀空间",
        "aliases": ["CIE Lab", "Lab"],
        "plain": "按人眼感知排列的颜色坐标，L 是明度，a/b 是两个色相方向。",
        "see": "#/ref/convert",
    },
    "oklab": {
        "term": "Oklab",
        "zh": "感知均匀空间（新）",
        "aliases": ["Oklab", "OKLab"],
        "plain": "更新的感知均匀空间，做渐变时过渡更顺。",
        "see": "#/ref/gradient",
    },
    "hue": {
        "term": "色相",
        "zh": "色相",
        "aliases": ["色相"],
        "plain": "颜色的种类，比如红、黄、蓝。",
    },
    "lightness": {
        "term": "明度",
        "zh": "明度",
        "aliases": ["明度"],
        "plain": "颜色有多亮，和有多鲜艳是两件事。",
    },
    "chroma": {
        "term": "彩度",
        "zh": "彩度",
        "aliases": ["彩度", "饱和度"],
        "plain": "颜色有多鲜艳，越低越接近灰。",
    },
    "colour-adaptation": {
        "term": "色适应",
        "zh": "色适应",
        "aliases": ["色适应", "色彩适应"],
        "plain": "眼睛会自动校准光源，所以白纸在白炽灯下仍像白的。",
        "see": "#/ref/adaptation",
    },
    "cri": {
        "term": "显色指数",
        "zh": "显色指数",
        "aliases": ["CRI", "显色指数", "Ra"],
        "plain": "灯光还原物体真实颜色的能力，Ra 越高越好，但有局限。",
        "see": "#/ref/quality",
    },
    "tm30": {
        "term": "TM-30",
        "zh": "显色评价",
        "aliases": ["TM-30"],
        "plain": "更新的显色评价，Rf 看还原度、Rg 看鲜艳度。",
        "see": "#/ref/quality",
    },
    "metamerism": {
        "term": "同色异谱",
        "zh": "同色异谱",
        "aliases": ["同色异谱"],
        "plain": "两个颜色在一种光下一样、换一种光就不一样。",
        "see": "#/ref/recovery",
    },
    "spd": {
        "term": "光谱",
        "zh": "光谱功率分布",
        "aliases": ["SPD", "光谱功率分布"],
        "plain": "一束光里每个波长的强度分布。",
        "see": "#/ref/observers",
    },
    "reflectance": {
        "term": "反射率",
        "zh": "反射率",
        "aliases": ["反射率"],
        "plain": "物体在每个波长上反射了多少光。",
        "see": "#/ref/recovery",
    },
    "transfer-function": {
        "term": "传递函数",
        "zh": "传递函数",
        "aliases": ["传递函数", "OETF", "EOTF"],
        "plain": "文件里的数字和实际亮度之间的换算曲线。",
        "see": "#/ref/transfer",
    },
    "lut": {
        "term": "3D LUT",
        "zh": "颜色查找表",
        "aliases": ["3D LUT", "LUT"],
        "plain": "一张输入颜色到输出颜色的查找表，调色常用。",
        "see": "#/ref/image-lut",
    },
    "munsell": {
        "term": "Munsell",
        "zh": "孟塞尔体系",
        "aliases": ["Munsell", "孟塞尔"],
        "plain": "用色相 明度/彩度描述颜色的经典体系，如 5R 5/12。",
        "see": "#/ref/notation",
    },
    "cvd": {
        "term": "色觉障碍",
        "zh": "色觉障碍",
        "aliases": ["色觉障碍", "色盲", "色弱"],
        "plain": "分辨某些颜色困难，最常见的是红绿型。",
        "see": "#/ref/cvd",
    },
    "jnd": {
        "term": "最小可觉差",
        "zh": "最小可觉差",
        "aliases": ["JND", "最小可觉差"],
        "plain": "人眼刚好能察觉的最小差别，ΔE 约等于 1。",
    },
    "csf": {
        "term": "对比敏感度",
        "zh": "对比敏感度",
        "aliases": ["CSF", "对比敏感度"],
        "plain": "不同粗细的图案，人眼能看出多小的对比。",
        "see": "#/ref/phenomena-vision",
    },
    "hk-effect": {
        "term": "H-K 效应",
        "zh": "H-K 效应",
        "aliases": ["H-K 效应"],
        "plain": "鲜艳的颜色会显得更亮。",
        "see": "#/ref/phenomena-vision",
    },
    "macadam": {
        "term": "MacAdam 椭圆",
        "zh": "麦克亚当椭圆",
        "aliases": ["MacAdam 椭圆", "麦克亚当椭圆"],
        "plain": "图上感觉一样的范围，椭圆越大说明这个方向越不敏感。",
        "see": "#/ref/geometry",
    },
    "dominant-wavelength": {
        "term": "主波长",
        "zh": "主波长",
        "aliases": ["主波长"],
        "plain": "这个颜色最接近光谱上的哪个单色光。",
        "see": "#/ref/chroma",
    },
    "purity": {
        "term": "纯度",
        "zh": "纯度",
        "aliases": ["纯度", "激发纯度"],
        "plain": "颜色离白/灰有多远，越高越接近单色光。",
        "see": "#/ref/chroma",
    },
    "chromaticity-diagram": {
        "term": "色度图",
        "zh": "色度图",
        "aliases": ["色度图"],
        "plain": "把所有颜色按色相和纯度铺在一张平面图上的图。",
        "see": "#/ref/chromaticity",
    },
    "palette": {
        "term": "调色板",
        "zh": "调色板",
        "aliases": ["调色板"],
        "plain": "一组搭配使用的颜色。",
        "see": "#/ref/cvd",
    },
    "wcag-contrast": {
        "term": "对比度",
        "zh": "无障碍对比度",
        "aliases": ["WCAG 对比度", "无障碍对比度"],
        "plain": "文字和背景的亮度差，网页无障碍有明确门槛。",
    },
    "linear-light": {
        "term": "线性光",
        "zh": "线性光",
        "aliases": ["线性光"],
        "plain": "去掉显示器的亮度曲线后，可以直接相加的光。",
        "see": "#/ref/transfer",
    },
    "gamma": {
        "term": "伽马",
        "zh": "伽马",
        "aliases": ["伽马", "gamma"],
        "plain": "显示器把数字变成亮度的非线性曲线。",
    },
    "gamut-mapping": {
        "term": "色域映射",
        "zh": "色域映射",
        "aliases": ["色域映射"],
        "plain": "把超出设备范围的颜色压缩进可显示范围。",
        "see": "#/ref/gamut-volume",
    },
    "hue-angle": {
        "term": "色相角",
        "zh": "色相角",
        "aliases": ["色相角"],
        "plain": "在 Lab/LCh 里用角度表示色相，0° 附近偏红。",
    },
    "observer": {
        "term": "标准观察者",
        "zh": "标准观察者",
        "aliases": ["标准观察者", "2° 观察者"],
        "plain": "用平均人眼数据定义的人眼模型，常用 2° 和 10°。",
        "see": "#/ref/observers",
    },
}

assert len(GLOSSARY) == 40, f"术语表应为 40 条，当前 {len(GLOSSARY)}"
