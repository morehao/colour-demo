"""6 个任务页的元数据（纯数据，不依赖 colour）。

字段约定：
- `tool`     复用的参考面板 id（决定 API 与控件能力）
- `outcome`  结论文案规则 id（见 verdicts.py）
- `fields`   控件声明；`presets[].state` 的 key 必须与 fields 的 key 完全一致
- `related`  延伸阅读的参考面板 id
- `jargon`   术语表 key

新增任务时同步：本文件 + manifest.TASK_IDS + 附录 B/任务页规格。
"""

from __future__ import annotations

TASKS: list[dict] = [
    {
        "id": "purity",
        "nav": "鲜艳度",
        "no": "T1",
        "title": "这个颜色，够鲜艳吗？",
        "intro": "选几个颜色，看看它们离灰有多远、最接近哪种单色光。",
        "est": "30 秒",
        "tool": "chroma",
        "outcome": "purity",
        "fields": [
            {
                "key": "colors",
                "kind": "colors",
                "label": "要看的颜色",
                "min": 1,
                "max": 5,
                "value": ["#3B82F6", "#9DB2C6", "#FF0000"],
            },
            {
                "key": "illuminant",
                "kind": "select",
                "label": "在什么光下看",
                "options": ["D65", "A", "FL2"],
                "value": "D65",
            },
        ],
        "steps": ["选颜色", "看鲜艳度", "想细看再展开"],
        "explain": [
            "纯度是颜色离白/灰有多远：0% 是灰白，100% 接近单色光。",
            "它不等于设计软件里的饱和度，换一种光，数字也会变。",
            "主波长告诉你它最接近光谱上的哪种单色光。",
        ],
        "related": ["chroma", "chromaticity"],
        "jargon": ["purity", "dominant-wavelength", "d65"],
        "presets": [
            {
                "id": "blues",
                "label": "三个蓝",
                "state": {"colors": ["#3B82F6", "#9DB2C6", "#1E3A8A"], "illuminant": "D65"},
            },
            {
                "id": "brands",
                "label": "一组品牌色",
                "state": {"colors": ["#264653", "#2A9D8F", "#E9C46A", "#E76F51"], "illuminant": "D65"},
            },
            {
                "id": "vivid",
                "label": "纯色与灰",
                "state": {"colors": ["#FF0000", "#CC8888"], "illuminant": "D65"},
            },
        ],
    },
    {
        "id": "delta-e",
        "nav": "色差",
        "no": "T2",
        "title": "这两个颜色，差得明显吗？",
        "intro": "选两个颜色，30 秒得到一个能直接用的判断。",
        "est": "30 秒",
        "tool": "delta-e",
        "outcome": "deltaE",
        "fields": [
            {
                "key": "colors",
                "kind": "colors",
                "label": "要比的颜色",
                "min": 2,
                "max": 12,
                "value": ["#3B82F6", "#E9C46A"],
            },
            {
                "key": "method",
                "kind": "method",
                "label": "配色差的算法",
                "options": ["CIE 2000"],
                "more": True,
                "value": "CIE 2000",
            },
        ],
        "steps": ["选两个颜色", "直接看结论", "想细看再展开"],
        "explain": [
            "两个颜色放在一起，人眼能分辨的最小差异叫最小可觉差。",
            "ΔE 小于 1 基本看不出；2–5 能看出来；大于 10 就是两个色系。",
            "默认用最常见的 CIE 2000；换算法数字会变，但方向通常一致。",
        ],
        "related": ["delta-e", "chromaticity"],
        "jargon": ["delta-e", "jnd"],
        "presets": [
            {
                "id": "near",
                "label": "几乎一样",
                "state": {"colors": ["#3B82F6", "#3D86F8"], "method": "CIE 2000"},
            },
            {
                "id": "slight",
                "label": "轻微偏色",
                "state": {"colors": ["#3B82F6", "#5B9CF0"], "method": "CIE 2000"},
            },
            {
                "id": "far",
                "label": "完全不同",
                "state": {"colors": ["#3B82F6", "#E9C46A"], "method": "CIE 2000"},
            },
        ],
    },
    {
        "id": "gradient",
        "nav": "渐变",
        "no": "T3",
        "title": "渐变为什么中间发灰？",
        "intro": "同一个起点和终点，换一种过渡方式，中间那段会完全不同。",
        "est": "1 分钟",
        "tool": "gradient",
        "outcome": "uniformity",
        "fields": [
            {"key": "from", "kind": "color", "label": "起点颜色", "value": "#264653"},
            {"key": "to", "kind": "color", "label": "终点颜色", "value": "#E9C46A"},
            {
                "key": "space",
                "kind": "select",
                "label": "过渡方式",
                "options": ["Oklab", "CIE Lab", "sRGB"],
                "value": "Oklab",
            },
            {"key": "steps", "kind": "number", "label": "分几步", "min": 2, "max": 101, "value": 11},
        ],
        "steps": ["选两端颜色", "三条色带并排比较", "看哪条最均匀"],
        "explain": [
            "在 sRGB 里直接过渡，中间会发灰；在 Oklab 里过渡更顺。",
            "衡量办法是看相邻两步的色差是否接近：越接近越均匀。",
            "色带中段最挤的地方，就是看起来发灰的地方。",
        ],
        "related": ["gradient", "chromaticity"],
        "jargon": ["oklab", "delta-e"],
        "presets": [
            {
                "id": "brand",
                "label": "蓝到黄",
                "state": {"from": "#264653", "to": "#E9C46A", "space": "Oklab", "steps": 11},
            },
            {
                "id": "red-green",
                "label": "红到绿",
                "state": {"from": "#E63946", "to": "#2A9D8F", "space": "Oklab", "steps": 11},
            },
            {
                "id": "black-white",
                "label": "黑到白",
                "state": {"from": "#000000", "to": "#FFFFFF", "space": "Oklab", "steps": 11},
            },
        ],
    },
    {
        "id": "cvd",
        "nav": "色弱",
        "no": "T4",
        "title": "色弱的人能分清这套配色吗？",
        "intro": "贴上你的配色，看看红绿色弱的人会把它看成什么样。",
        "est": "1 分钟",
        "tool": "cvd",
        "outcome": "cvd",
        "fields": [
            {
                "key": "colors",
                "kind": "colors",
                "label": "你的配色",
                "min": 2,
                "max": 12,
                "value": ["#264653", "#2A9D8F", "#E9C46A", "#E76F51"],
            },
            {
                "key": "deficiency",
                "kind": "select",
                "label": "先看哪一类",
                "options": ["Deuteranomaly", "Protanomaly", "Tritanomaly"],
                "option_labels": {
                    "Deuteranomaly": "绿色弱 / 绿色盲",
                    "Protanomaly": "红色弱 / 红色盲",
                    "Tritanomaly": "蓝色弱 / 蓝色盲",
                },
                "value": "Deuteranomaly",
            },
        ],
        "steps": ["贴配色", "切换三类色觉", "看哪几块糊在一起"],
        "explain": [
            "色觉障碍不是看不见颜色，而是某些相邻颜色会挤在一起。",
            "模拟后相邻两块色差低于 3，基本就是分不清。",
            "提高明暗差、换更深的蓝，通常比换红色有效。",
        ],
        "related": ["cvd", "chroma"],
        "jargon": ["cvd", "delta-e"],
        "presets": [
            {
                "id": "brands",
                "label": "品牌蓝橙",
                "state": {
                    "colors": ["#264653", "#2A9D8F", "#E9C46A", "#E76F51"],
                    "deficiency": "Deuteranomaly",
                },
            },
            {
                "id": "red-green",
                "label": "红绿对比",
                "state": {"colors": ["#D62828", "#2A9D8F", "#F77F00"], "deficiency": "Deuteranomaly"},
            },
            {
                "id": "rainbow",
                "label": "彩虹渐变",
                "state": {
                    "colors": ["#E63946", "#F4A261", "#E9C46A", "#2A9D8F", "#457B9D", "#5E548E"],
                    "deficiency": "Deuteranomaly",
                },
            },
        ],
    },
    {
        "id": "light",
        "nav": "换灯",
        "no": "T5",
        "title": "换一盏灯，颜色还一样吗？",
        "intro": "同一支颜色，在白炽灯下和日光下，看起来会差多少？",
        "est": "30 秒",
        "tool": "adaptation",
        "outcome": "shift",
        "fields": [
            {
                "key": "colors",
                "kind": "colors",
                "label": "待测颜色",
                "min": 1,
                "max": 3,
                "value": ["#3B82F6"],
            },
            {"key": "source", "kind": "select", "label": "现在在", "options": ["A", "D50", "D65", "D93", "FL2"], "value": "A"},
            {"key": "target", "kind": "select", "label": "换到", "options": ["D65", "D50", "D93", "A", "FL2"], "value": "D65"},
        ],
        "steps": ["选颜色", "选现在和换到的光", "看前后并排"],
        "explain": [
            "眼睛会自动适应光源，所以白纸在暖灯下仍然像白的。",
            "不同光源的白点不一样，同一个色号换算过去会偏。",
            "如果结果超出屏幕能显示的范围，页面会用近似色代替。",
        ],
        "related": ["adaptation", "temperature"],
        "jargon": ["colour-adaptation", "white-point", "d65"],
        "presets": [
            {
                "id": "bulb-blue",
                "label": "白炽灯下的蓝",
                "state": {"colors": ["#3B82F6"], "source": "A", "target": "D65"},
            },
            {
                "id": "daylight-orange",
                "label": "日光下的橙",
                "state": {"colors": ["#E9C46A"], "source": "D65", "target": "A"},
            },
            {
                "id": "fluorescent",
                "label": "荧光灯下的蓝",
                "state": {"colors": ["#3B82F6"], "source": "FL2", "target": "D65"},
            },
        ],
    },
    {
        "id": "notation",
        "nav": "色号",
        "no": "T6",
        "title": "这个色号，换成别的写法是多少？",
        "intro": "把色号、颜色名或 Munsell 记号粘进来，翻译成同一套坐标。",
        "est": "30 秒",
        "tool": "notation",
        "outcome": "translate",
        "fields": [
            {
                "key": "value",
                "kind": "notation",
                "label": "色号或颜色名",
                "hint": "支持 #3B82F6、tomato、5R 5/12",
                "value": "#3B82F6",
            }
        ],
        "steps": ["粘贴一个色号", "看同一颜色的多种写法", "复制需要的那行"],
        "explain": [
            "一个颜色可以写成 HEX、RGB、Lab、Munsell 等多种样子。",
            "它们描述的是同一个颜色，只是给不同场景用的。",
            "复制任意一行，就能贴到设计软件或代码里。",
        ],
        "related": ["notation", "convert"],
        "jargon": ["munsell", "cie-lab"],
        "presets": [
            {"id": "hex", "label": "#3B82F6", "state": {"value": "#3B82F6"}},
            {"id": "keyword", "label": "tomato", "state": {"value": "tomato"}},
            {"id": "munsell", "label": "5R 5/12", "state": {"value": "5R 5/12"}},
        ],
    },
]

assert len(TASKS) == 6, f"任务应为 6 个，当前 {len(TASKS)}"
assert len({task["id"] for task in TASKS}) == 6, "任务 id 不能重复"
