"""面板 26–28：能力目录、参数化调用、API 控制台（元能力，几乎不占内存）。"""

from __future__ import annotations

import json

import numpy as np

import colour

from .common import json_block, note, panel, stats, table

ENDPOINTS = [
    ("GET", "/api/v1/meta", "版本、色彩空间/观察者/方法枚举、限额", "M1"),
    ("POST", "/api/v1/convert", "单色多空间换算 + 派生指标", "M1"),
    ("POST", "/api/v1/chroma", "xy / uv / u′v′、主波长、纯度、补色波长", "M1"),
    ("POST", "/api/v1/spectral", "观察者 CMFS 与光源 SPD 曲线 + 积分结果", "M1"),
    ("POST", "/api/v1/photometry", "明度/亮度/白度/黄度函数族", "M1"),
    ("POST", "/api/v1/delta-e", "成对 ΔE 矩阵（14 种方法）", "M1"),
    ("POST", "/api/v1/gradient", "多空间插值与步长均匀度", "M1"),
    ("GET", "/api/v1/spaces", "96 个 RGB 色彩空间清单与色域面积", "M2"),
    ("POST", "/api/v1/transfer", "传递函数曲线与编解码往返误差", "M2"),
    ("GET", "/api/v1/chromaticity.svg", "三种色度图 + 色域 + 样本点", "M2"),
    ("POST", "/api/v1/volume", "色域体积与边界判定", "M2"),
    ("POST", "/api/v1/temperature", "CCT ↔ xy / uv 的正反向换算", "M2"),
    ("POST", "/api/v1/quality", "CRI / CQS / TM-30 / SSI", "M2"),
    ("POST", "/api/v1/lut", "图像 + 3D LUT 应用与插值对比", "M3"),
    ("POST", "/api/v1/adapt", "色适应（7 方法 + 13 个 CAT）", "M2"),
    ("POST", "/api/v1/appearance", "12 个外观模型的相关量", "M2"),
    ("POST", "/api/v1/phenomena-vision", "H-K 效应 + Barten 对比敏感度", "M2"),
    ("POST", "/api/v1/corresponding", "对应色预测与实验拟合", "M2"),
    ("POST", "/api/v1/cvd", "Machado 2009 色觉障碍模拟", "M2"),
    ("POST", "/api/v1/recovery", "RGB / XYZ → 光谱重建", "M3"),
    ("POST", "/api/v1/correction", "色卡校正矩阵与 ACES IDT", "M3"),
    ("POST", "/api/v1/notation", "Munsell / CSS / HEX 记号解析", "M3"),
    ("POST", "/api/v1/interpolate", "插值器与 LUT 表插值", "M3"),
    ("POST", "/api/v1/geometry", "椭圆拟合与图元生成", "M3"),
    ("POST", "/api/v1/optics", "薄膜/瑞利/Snell 与生化动力学", "M3"),
    ("POST", "/api/v1/plot", "白名单绘图函数（固定画幅）", "M3"),
    ("GET", "/api/v1/catalog", "全量能力目录与覆盖状态", "M4"),
    ("POST", "/api/v1/catalog/invoke", "白名单函数的参数化调用", "M4"),
    ("GET", "/healthz", "存活、库版本、matplotlib 状态", "M1"),
]


def panel_catalog(catalog: dict) -> dict:
    counts = catalog["counts"]
    blocks = [
        stats(
            [
                (str(catalog["total"]), "子模块导出条目", "25 个子模块 __all__ 之和"),
                (str(catalog.get("top_level_names", 0)), "顶层聚合名称", "dir(colour) 去私有"),
                (str(counts["面板"]), "面板覆盖", "有专门 UI 与端点"),
                (str(counts["数据集"]), "数据集 / 常量", "作为面板输入或参照"),
                (str(counts["内部"]), "内部基础设施", "被服务层复用，不单独暴露"),
                (f"{catalog['coverage']:.1f}%", "分类覆盖率", "构建脚本自检：不允许「未分类」"),
            ],
            title="映射结果",
        ),
        table(
            ["子模块", "公开项", "主归属面板"],
            [
                [
                    m["name"],
                    str(m["count"]),
                    f"{m['panel']} · {m['panel_title']}" if m["panel"] != "内部" else "内部复用",
                ]
                for m in catalog["modules"]
            ],
            title="25 个子模块的归属",
            mono=[0, 1],
            widths=["160px", "90px", "auto"],
        ),
        table(
            ["子模块", "名称", "类型", "归属", "状态"],
            [[r["module"], r["name"], r["kind"], r["target"], r["status"]] for r in catalog["rows"]],
            title=f"全部 {catalog['total']} 条子模块导出（可搜索 / 按状态过滤）",
            mono=[0, 1, 3],
            widths=["130px", "auto", "90px", "70px", "70px"],
            note="「归属」为面板编号；数据集与内部项不占面板。",
        ),
        note(
            "这张表就是「覆盖全部功能」的落地方式：面板负责高频场景（有交互、有图、有端点），"
            "数据集负责给面板供料，内部基础设施被服务层复用；长尾函数通过面板 27 的参数化调用可达，"
            "不为每个函数单独做页面。",
            tone="info",
            title="读法",
        ),
    ]
    return panel(
        "catalog",
        "元能力",
        "26",
        "能力目录",
        f"colour-science {catalog['version']} 的公开面是 25 个子模块、{catalog['total']} 条导出（顶层聚合后 {catalog.get('top_level_names', 0)} 个名称）。"
        "目录把每一个名称归到面板 / 数据集 / 内部三类，覆盖率由构建脚本自检。",
        blocks,
        phase="M4",
        apis=["GET /api/v1/catalog"],
        controls=[
            {"label": "搜索", "kind": "text", "value": "delta_E"},
            {"label": "状态", "kind": "select", "value": "全部", "options": ["全部", "面板", "数据集", "内部"]},
        ],
        footer="对应 API：`GET /api/v1/catalog`；目录由 `pkgutil` + `__all__` 扫描生成，随 colour 版本自动刷新。",
    )


def panel_invoke() -> dict:
    examples = []

    xy = colour.temperature.CCT_to_xy(6500.0, method="McCamy 1992")
    examples.append(
        (
            "CCT_to_xy",
            "色温 → 色度坐标（面板 11 未展开 McCamy 1992 这条通路）",
            {"function": "colour.temperature.CCT_to_xy", "args": [6500.0], "kwargs": {"method": "McCamy 1992"}},
            {"result": [round(float(v), 6) for v in np.asarray(xy).ravel()], "warnings": []},
        )
    )

    ra = colour.quality.colour_rendering_index(colour.SDS_ILLUMINANTS["FL2"])
    examples.append(
        (
            "colour_rendering_index",
            "对数据集直接求显色指数（面板 12 的表只是缓存结果）",
            {"function": "colour.quality.colour_rendering_index", "args": ["SDS_ILLUMINANTS['FL2']"], "kwargs": {}},
            {"result": round(float(ra), 4), "warnings": []},
        )
    )

    snell = colour.phenomena.snell_law(1.0, 1.5, 0.5236)
    examples.append(
        (
            "snell_law",
            "折射角：空气（n=1.0）→ 玻璃（n=1.5），入射 30°",
            {"function": "colour.phenomena.snell_law", "args": [1.0, 1.5, 0.5236], "kwargs": {}},
            {"result": round(float(snell), 6), "warnings": []},
        )
    )

    munsell = colour.notation.munsell_colour_to_xyY("5R 5/12")
    examples.append(
        (
            "munsell_colour_to_xyY",
            "Munsell 记号 → xyY（面板 21 的解析走同一条通路）",
            {"function": "colour.notation.munsell_colour_to_xyY", "args": ["5R 5/12"], "kwargs": {}},
            {"result": [round(float(v), 5) for v in np.asarray(munsell).ravel()], "warnings": []},
        )
    )

    blocks = [
        table(
            ["函数（白名单）", "参数 schema", "返回"],
            [
                ["colour.temperature.CCT_to_xy", "CCT: number[1000, 100000] · method: enum(5)", "xy: [number, number]"],
                ["colour.quality.colour_rendering_index", "sd: dataset-ref（只读内置）", "Ra: number"],
                ["colour.phenomena.snell_law", "n1,n2: number[1,4] · theta: number[0, π/2]", "theta: number"],
                ["colour.notation.munsell_colour_to_xyY", "munsell: string（正则校验）", "xyY: [number×3]"],
                ["colour.difference.delta_E", "Lab×2: number[3] · method: enum(14)", "ΔE: number"],
                ["colour.adaptation.chromatic_adaptation", "XYZ,XYZ_w,XYZ_wr: number[3] · method: enum(7)", "XYZ: [number×3]"],
            ],
            title="白名单与参数 schema（示例 6 条，M2 扩到 40+）",
            mono=[0, 1, 2],
            widths=["260px", "auto", "150px"],
        )
    ]
    for name, description, request, response in examples:
        blocks.append(
            json_block(
                "请求\n" + json.dumps(request, ensure_ascii=False, indent=2)
                + "\n\n200\n" + json.dumps(response, ensure_ascii=False, indent=2),
                title=f"{name} —— {description}",
            )
        )
    blocks.append(
        note(
            "调用只允许白名单函数：函数名 → 参数 schema → 一个示例。禁止字符串求值、禁止动态导入、"
            "禁止传文件路径；数据集只能按名字引用内置对象（只读）。不在白名单的函数返回 403。",
            tone="warn",
            title="安全边界",
        )
    )

    return panel(
        "invoke",
        "元能力",
        "27",
        "参数化调用",
        "长尾能力不需要单独页面：在能力目录里查到函数名与参数，就能通过一个统一端点调用。下面四条是构建时真实执行的结果。",
        blocks,
        phase="M4",
        apis=["POST /api/v1/catalog/invoke"],
        controls=[
            {
                "label": "函数",
                "kind": "select",
                "value": "colour.temperature.CCT_to_xy",
                "options": [e[0] for e in examples],
            }
        ],
        footer="对应 API：`POST /api/v1/catalog/invoke`；白名单与 schema 在 `core/registry.py`，随版本刷新并由 CI diff。",
    )


def panel_api() -> dict:
    blocks = [
        table(
            ["方法", "路径", "说明", "阶段"],
            [[m, p, d, s] for m, p, d, s in ENDPOINTS],
            title=f"{len(ENDPOINTS)} 个端点",
            mono=[0, 1],
            widths=["70px", "240px", "auto", "60px"],
        ),
        json_block(
            "POST /api/v1/delta-e\n"
            '{"colors": ["#264653", "#2A9D8F", "#E9C46A", "#F4A261", "#E76F51"], "method": "CIE 2000"}\n\n'
            "200\n"
            + json.dumps(
                {
                    "method": "CIE 2000",
                    "colors": ["#264653", "#2A9D8F", "#E9C46A", "#F4A261", "#E76F51"],
                    "matrix": [
                        [0.0, 33.53, 61.41, 57.7, 50.74],
                        [33.53, 0.0, 37.88, 44.52, 52.44],
                        [61.41, 37.88, 0.0, 16.1, 32.43],
                        [57.7, 44.52, 16.1, 0.0, 16.84],
                        [50.74, 52.44, 32.43, 16.84, 0.0],
                    ],
                    "pairs": {
                        "closest": {"a": "#E9C46A", "b": "#F4A261", "value": 16.1},
                        "farthest": {"a": "#264653", "b": "#E9C46A", "value": 61.41},
                    },
                    "warnings": [],
                },
                ensure_ascii=False,
                indent=2,
            ),
            title="一次真实请求（数值为 colour 0.4.7 输出）",
        ),
        table(
            ["场景", "状态码", "语义"],
            [
                ["颜色无法解析", "422", "detail[].type = value_error"],
                ["方法名不在枚举", "422", "枚举值由 /meta 提供"],
                ["超出颜色/步数上限", "422", "colors ≤ 12，steps ≤ 101"],
                ["请求体过大", "413", "中间件拦截"],
                ["invoke 非白名单", "403", "函数未登记"],
                ["计算超时", "504", "10 s 上限"],
                ["未预期异常", "500", "只返回 trace_id"],
            ],
            title="错误模型",
            mono=[1],
            widths=["180px", "80px", "auto"],
        ),
    ]
    return panel(
        "api",
        "元能力",
        "28",
        "API 控制台",
        "正式版所有能力都是 JSON API，前端只是它的第一个消费者。29 个端点覆盖全部面板，OpenAPI 由 pydantic 模型自动生成。",
        blocks,
        phase="M4",
        apis=["GET /openapi.json"],
        footer="契约细节见技术方案第 6 节；`/openapi.json` 由 FastAPI 自动产出，前端与能力目录共用。",
    )
