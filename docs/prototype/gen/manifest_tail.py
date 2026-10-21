"""面板 19–25 的元数据（暂为占位：按阶段补充数据）。

这些面板的数值与图表需要 M3 阶段逐面板构建（每个面板单独进程、限制内存）。
现在只登记它们的标题、说明、端点、依赖与「待补的块」，让原型导航与方案保持一致，
同时明确区分「已出数据」与「待补数据」，不伪造任何结果。
"""

from __future__ import annotations

from .common import note, panel, table

PENDING = [
    {
        "id": "recovery",
        "no": "19",
        "title": "光谱重建",
        "lead": "一支 RGB 背后是无穷多条光谱——这是同色异谱的根源。光谱重建就是「猜一条最合理的光谱」：Smits 用平滑基函数，Mallett 用 sRGB 优化基，Jakob 用 LUT。",
        "apis": ["POST /api/v1/recovery"],
        "footer": "对应 API：`POST /api/v1/recovery`；依赖 `RGB_to_sd_Smits1999` / `RGB_to_sd_Mallett2019` / `XYZ_to_sd`（Jakob 2019 / Meng 2015 / Otsu 2018）。",
        "planned": [
            ["SPD 曲线图", "四种方法重建的光谱叠加（380–780 nm）"],
            ["重建精度表", "重建 → sRGB 的 ΔE、采样点数"],
            ["口径表", "同色异谱指数、相机灵敏度、主成分基函数"],
        ],
    },
    {
        "id": "characterisation",
        "no": "20",
        "title": "色彩校正与 ACES",
        "lead": "「相机拍出来偏色」的本质是一次线性变换。用 24 色卡在已知光源下拍一张，解出一个校正矩阵，就能把整批图像拉回正确颜色——这就是 Cheung 2004 与 Finlayson 2015 在做的事。",
        "apis": ["POST /api/v1/correction"],
        "footer": "对应 API：`POST /api/v1/correction`；依赖 `colour_correction` 的 3 个方法 + `matrix_idt` / `sd_to_ACES2065_1` / `white_balance_multipliers`。",
        "planned": [
            ["色卡对比", "24 色卡前 12 色：校正前后色块"],
            ["效果表", "校正前后平均/最大 ΔE"],
            ["矩阵方法表", "Cheung 2004 / Finlayson 2015 / Vandermonde 输出维度"],
        ],
    },
    {
        "id": "notation",
        "no": "21",
        "title": "记号与解析",
        "lead": "「5R 5/12」「tomato」「#3B82F6」——同一件事有四种写法。解析层把它们统一成坐标，是任何色彩工具的第一道工序。",
        "apis": ["POST /api/v1/notation"],
        "footer": "对应 API：`POST /api/v1/notation`；依赖 `munsell_colour_to_xyY` / `xyY_to_munsell_colour` / `munsell_value` / `keyword_to_RGB_CSSColor3` / `HEX_to_RGB`。",
        "planned": [
            ["解析结果表", "Munsell ↔ xyY、CSS 关键字、HEX 往返"],
            ["明度算法表", "Munsell value 的 7 种实现"],
            ["注意", "反向转换病态：同一坐标可能对应多个色卡孔位"],
        ],
    },
    {
        "id": "signals",
        "no": "22",
        "title": "连续信号与插值器",
        "lead": "光谱数据是离散采样，但物理量是连续的。插值方法决定「采样点之间」长什么样——Sprague 是为等间隔光谱设计的五次插值，PCHIP 保单调，线性插值会切断峰。",
        "apis": ["POST /api/v1/interpolate"],
        "footer": "对应 API：`POST /api/v1/interpolate`；依赖 `algebra` 的 7 个插值器 + `continuous.Signal` + `table_interpolation_*`。",
        "planned": [
            ["插值曲线图", "D65 原采样 vs Linear / Sprague / PCHIP / Cubic"],
            ["插值器表", "同一 Signal 采样点的数值差异"],
            ["LUT 表", "三线性 vs 四面体插值"],
        ],
    },
    {
        "id": "geometry",
        "no": "23",
        "title": "几何与椭圆拟合",
        "lead": "MacAdam 1942 的椭圆告诉你「人眼在各方向上有多不敏感」；把它拟合成二次曲线，就能反过来量化局部均匀性。geometry 子模块负责这类拟合、图元与线段求交。",
        "apis": ["POST /api/v1/geometry"],
        "footer": "对应 API：`POST /api/v1/geometry`；依赖 `ellipse_fitting` / `ellipse_coefficients_*` / `primitive_*` / `intersect_line_segments`。",
        "planned": [
            ["拟合图", "MacAdam 椭圆采样点 + 拟合曲线"],
            ["系数表", "二次曲线 6 个系数与残差"],
            ["图元表", "primitive_grid / cube / sphere 输出形状"],
        ],
    },
    {
        "id": "optics",
        "no": "24",
        "title": "光学现象与响应动力学",
        "lead": "colour 不只会算颜色，还会算光：薄膜干涉为什么让肥皂泡变彩虹、天空为什么是蓝的（瑞利散射）、光在两种介质间怎么拐弯（Snell）。biochemistry 提供光感受器响应的动力学模型。",
        "apis": ["POST /api/v1/optics"],
        "footer": "对应 API：`POST /api/v1/optics`；依赖 `phenomena.*`（薄膜/偏振/瑞利/Snell）与 `biochemistry.*`。",
        "planned": [
            ["薄膜反射率", "单层薄膜在 200/350/500 nm 厚度下的光谱"],
            ["瑞利散射", "短波散射更强 → 蓝天、红日"],
            ["动力学", "Michaelis–Menten 两个方法版本"],
        ],
    },
    {
        "id": "gallery",
        "no": "25",
        "title": "图表画廊",
        "lead": "`colour.plotting` 自带 96 个绘图函数：从色度图到薄膜反射率，从 SPD 到色卡检测结果。它们既是演示素材，也是「不用自己画图」的现成能力。",
        "apis": ["POST /api/v1/plot"],
        "footer": "对应 API：`POST /api/v1/plot`；只开放白名单内的 12 个绘图函数（画幅、dpi、样式由服务端固定）。",
        "planned": [
            ["分组表", "96 个函数按前缀分组与示例"],
            ["示例图", "visible spectrum / blackbody / MacAdam 椭圆（服务端渲染）"],
            ["口径", "样式系统、3D 图的可选依赖（trimesh）"],
        ],
    },
]


def stub_panels() -> list[dict]:
    """生成 19–25 的占位面板：只写元数据与「待补块」，不产生任何数值结论。"""
    panels = []
    for item in PENDING:
        blocks = [
            note(
                "本面板的数据与图表按阶段补充（M3）。上面的说明、端点与依赖已经定稿，"
                "补数据时只填块，不改结构；每个面板单独一个进程构建，峰值内存受控。",
                tone="warn",
                title="数据待补充",
            ),
            table(
                ["待补的块", "内容"],
                item["planned"],
                title="补齐清单",
                widths=["160px", "auto"],
            ),
        ]
        panels.append(
            panel(
                item["id"],
                "数据与算法",
                item["no"],
                item["title"],
                item["lead"],
                blocks,
                phase="M3",
                apis=item["apis"],
                footer=item["footer"],
            )
            | {"pending": True}
        )
    return panels
