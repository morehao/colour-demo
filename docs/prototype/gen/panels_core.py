"""面板 00–08：概览、基础换算、色度学、光度函数、ΔE、均匀空间、RGB 空间图鉴、传递函数。"""

from __future__ import annotations

import json

import numpy as np

import colour

import matplotlib.pyplot as plt  # noqa: E402

from .common import (
    adjacent_delta_e,
    cards,
    chain,
    chart,
    delta_e,
    fnum,
    hex_to_rgb,
    image,
    json_block,
    kv,
    matrix,
    new_axes,
    note,
    panel,
    rgb_to_hex,
    series,
    stats,
    strip,
    strips,
    swatches,
    table,
    vec,
)

D65 = colour.CCS_ILLUMINANTS["CIE 1931 2 Degree Standard Observer"]["D65"]
XYZ_W = colour.xy_to_XYZ(D65)
CMFS = colour.MSDS_CMFS["CIE 1931 2 Degree Standard Observer"]
PALETTE = ["#264653", "#2A9D8F", "#E9C46A", "#F4A261", "#E76F51"]
DEMO = "#3B82F6"


# --------------------------------------------------------------------------- #
# 00 概览
# --------------------------------------------------------------------------- #
def panel_overview(catalog_summary: dict) -> dict:
    blocks = [
        chain(
            [
                ("sRGB", "#3B82F6", "输入：显示器编码值（带 γ 的 8 bit）"),
                ("线性 sRGB", "#2563EB", "去 γ：eotf_inverse_sRGB，光照可加"),
                ("CIE XYZ", "#1D4ED8", "物理量：颜色 + 观察条件"),
                ("Lab / Oklab / CAM16", "#4338CA", "感知空间：明度、色相对齐人眼"),
                ("ΔE / 色域 / CVD / 质量", "#6D28D9", "比较、判断、模拟与评估"),
            ]
        ),
        stats(
            [
                (catalog_summary["version"], "colour-science", "稳定 tag v0.4.7"),
                (str(catalog_summary["submodules"]), "子模块", "pkgutil 扫描"),
                (str(catalog_summary["top_level"]), "顶层聚合名称", "dir(colour) 去私有"),
                (str(catalog_summary["names"]), "子模块导出条目", "25 个子模块 __all__ 之和"),
                (str(catalog_summary["callables"]), "顶层可调用对象", "callable() 判定"),
                (str(catalog_summary["spaces"]), "RGB 色彩空间", "RGB_COLOURSPACES"),
                ("106", "换算图节点", "colour.convert()"),
            ],
            title="基线规模（v0.4.7 实测）",
        ),
        cards(
            [
                ("基础换算 · 01–04", "14 个坐标系、色度学属性、观察者与光源、光度与明度函数", "colorimetry / graph / models"),
                ("差异与均匀性 · 05–08", "14 种 ΔE、7 个感知空间与步长均匀度、96 个 RGB 空间、传递函数", "difference / models"),
                ("色域与光源 · 09–12", "三种色度图、色域体、色温、色彩质量", "plotting / volume / temperature / quality"),
                ("工程与数据 · 13", "图像与 3D LUT", "io"),
                ("外观与感知 · 14–18", "7 种色适应、12 个外观模型、H-K 与 CSF、对应色、CVD", "adaptation / appearance / corresponding / blindness"),
                ("数据与算法 · 19–25", "光谱重建、色彩校正、记号、插值器、几何、光学、图表画廊", "recovery / characterisation / notation / algebra / geometry / phenomena / plotting"),
                ("元能力 · 26–28", "全量能力目录、参数化调用、API 契约", "catalog / FastAPI"),
            ],
            title="全站地图",
        ),
        table(
            ["阶段", "范围", "出口标准"],
            [
                ["M1", "面板 00–08：换算、色度学、ΔE、均匀空间、色彩空间库、传递函数", "数值可复现，黄金值测试全绿"],
                ["M2", "面板 09–18：色域体、色温、质量、图像/LUT、校正、适应、外观、CVD", "所有子模块都有可用面板"],
                ["M3", "面板 19–25：光谱重建、记号、插值、几何、光学、图表", "长尾能力全部可达"],
                ["M4", "面板 26–28：能力目录、invoke、API 契约 + 部署", "覆盖率自检 100%，API 文档自动生成"],
            ],
            title="分期（原型与方案一次到位，实现分阶段）",
            note="分期只影响实现顺序，不影响设计：每个面板的端点、数据形状与 colour 依赖在本文档里已经定稿。",
        ),
    ]
    return panel(
        "overview",
        "起点",
        "00",
        "一条链路，看懂全部颜色能力",
        "颜色不是三个字节，而是「物理量 + 观察条件 + 感知模型」。这个演示把 colour-science 0.4.7 的 **25 个子模块、1284 条导出**全部纳入：高频场景做成面板，长尾能力通过能力目录与参数化调用可达。原型按阶段补充，当前已出 00–18 与 26–28 的数据。",
        blocks,
        phase="M0",
        apis=["GET /api/v1/meta", "GET /api/v1/catalog"],
    )


# --------------------------------------------------------------------------- #
# 01 颜色转换
# --------------------------------------------------------------------------- #
CONVERT_SPACES = [
    "CIE XYZ", "CIE xyY", "CIE Lab", "CIE Luv", "CIE LCHab", "CIE LCHuv", "CIE UCS", "CIE UVW",
    "Oklab", "OKLCH", "CAM16UCS", "CAM02UCS", "Jzazbz", "jzchab", "IPT", "IgPgTg",
    "ICtCp", "ICaCb", "DIN99", "Hunter Lab", "ProLab", "hdr-CIELab", "hdr-IPT", "HCL",
]


def panel_convert() -> dict:
    rgb = np.array(hex_to_rgb(DEMO))
    xyz = colour.sRGB_to_XYZ(rgb)
    cam16 = colour.XYZ_to_CAM16(
        xyz * 100, XYZ_w=XYZ_W * 100, L_A=64 / np.pi / 5, Y_b=20
    )
    oklch = colour.Oklab_to_Oklch(colour.XYZ_to_Oklab(xyz))
    hsd = colour.RGB_to_HSL(rgb)
    hsv = colour.RGB_to_HSV(rgb)
    linear = colour.models.eotf_inverse_sRGB(rgb)
    cam16ucs = colour.XYZ_to_CAM16UCS(
        xyz, XYZ_w=XYZ_W * 100, L_A=64 / np.pi / 5, Y_b=20
    )
    jzazbz = colour.XYZ_to_Jzazbz(xyz)
    ictcp = colour.XYZ_to_ICtCp(xyz)

    core_rows = [
        ("sRGB（0–255）", f"{rgb[0] * 255:.0f}, {rgb[1] * 255:.0f}, {rgb[2] * 255:.0f}", "整数通道，Web 常用"),
        ("sRGB（0–1）", vec(rgb, 4), "colour 的默认输入"),
        ("线性 sRGB", vec(linear, 4), "eotf_inverse_sRGB"),
        ("CIE XYZ（D65）", vec(xyz, 4), "Y 即相对亮度"),
        ("CIE xyY", vec(colour.XYZ_to_xyY(xyz), 4), "色度 + 亮度"),
        ("CIE Lab", vec(colour.XYZ_to_Lab(xyz), 2), "0–100 域"),
        ("CIE Luv", vec(colour.XYZ_to_Luv(xyz), 2), "加性混光更均匀"),
        ("Oklab", vec(colour.XYZ_to_Oklab(xyz), 4), "插值首选"),
        ("OKLCH", f"L {oklch[0]:.4f} · C {oklch[1]:.4f} · h {oklch[2]:.1f}°", "h 单位为度"),
        ("CAM16", f"J {cam16.J:.2f} · C {cam16.C:.2f} · h {cam16.h:.1f}° · M {cam16.M:.2f}", "含观察条件"),
        ("CAM16-UCS", vec(cam16ucs, 3), "J'a'b'"),
        ("Jzazbz", vec(jzazbz, 5), "HDR 感知空间"),
        ("ICtCp", vec(ictcp, 4), "BT.2100"),
        ("HSL / HSV", f"{hsd[0] * 360:.1f}° {hsd[1] * 100:.1f}% {hsd[2] * 100:.1f}% / V {hsv[2] * 100:.1f}%", "RGB_to_HSL / HSV"),
    ]

    graph_rows = []
    for space in CONVERT_SPACES:
        try:
            value = colour.convert(rgb, "sRGB", space)
            graph_rows.append([space, vec(value, 4)])
        except Exception as error:  # 记录而不是静默跳过
            graph_rows.append([space, f"不可达：{type(error).__name__}"])

    try:
        path = colour.graph.conversion_path("srgb", "jzazbz")
        path_text = " → ".join(fn.__name__ for fn in path)
    except Exception as error:
        path_text = f"不可达（{type(error).__name__}）"

    y = float(xyz[1])
    return panel(
        "convert",
        "基础换算",
        "01",
        "颜色转换与换算图",
        f"一支颜色在 14 个核心坐标系里的坐标，外加通过 `colour.convert()` 换算图可达的 {len(CONVERT_SPACES)} 个空间——106 个节点之间任意跳转，路径由 networkx 最短路径给出。",
        [
            swatches([(DEMO, "输入", "sRGB 8 bit")], cols=6),
            kv(core_rows, title="核心表示"),
            table(["空间（换算图节点）", "坐标"], graph_rows, title="任意空间换算", mono=[0, 1], widths=["190px", "auto"]),
            kv(
                [
                    ("换算路径 sRGB → Jzazbz", path_text, "colour.conversion_path()"),
                    ("白点", f"x {D65[0]:.4f} · y {D65[1]:.4f}", "D65 / CIE 1931 2°"),
                    ("相对亮度 Y", f"{y:.4f}", "WCAG 对比度 2.03:1（白）/ 10.35:1（黑）"),
                ],
                title="路径与白点",
            ),
            json_block(
                json.dumps(
                    {
                        "input": DEMO,
                        "space": "sRGB",
                        "values": {
                            "XYZ": [round(float(c), 6) for c in xyz],
                            "Lab": [round(float(c), 4) for c in colour.XYZ_to_Lab(xyz)],
                            "Oklab": [round(float(c), 6) for c in colour.XYZ_to_Oklab(xyz)],
                            "CAM16UCS": [round(float(c), 4) for c in cam16ucs],
                        },
                        "warnings": [],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                title="POST /api/v1/convert",
            ),
        ],
        phase="M1",
        apis=["POST /api/v1/convert", "GET /api/v1/meta"],
        controls=[
            {"label": "输入颜色", "kind": "color", "value": DEMO},
            {"label": "白点", "kind": "select", "value": "D65", "options": ["D65", "D50", "A"]},
            {"label": "标准观察者", "kind": "select", "value": "CIE 1931 2°", "options": ["CIE 1931 2°", "CIE 1964 10°"]},
        ],
        footer="对应 API：`POST /api/v1/convert`；换算图能力：`colour.convert()` / `conversion_path()` / `describe_conversion_path()`。",
    )


# --------------------------------------------------------------------------- #
# 02 色度学属性
# --------------------------------------------------------------------------- #
def panel_chroma() -> dict:
    rows = []
    for name, hex_value in [
        ("深青", "#264653"),
        ("蓝", DEMO),
        ("黄", "#E9C46A"),
        ("红", E76 := "#E76F51"),
    ]:
        xyz = colour.sRGB_to_XYZ(hex_to_rgb(hex_value))
        xy = colour.XYZ_to_xy(xyz)
        uv = colour.xy_to_UCS_uv(xy)
        uvp = colour.xy_to_Luv_uv(xy)
        dw, dw_xy, _ = colour.dominant_wavelength(xy, D65)
        rows.append(
            [
                name,
                hex_value.upper(),
                f"{xy[0]:.4f}, {xy[1]:.4f}",
                f"{uv[0]:.4f}, {uv[1]:.4f}",
                f"{uvp[0]:.4f}, {uvp[1]:.4f}",
                f"{float(np.squeeze(dw)):.1f} nm",
                f"{float(colour.excitation_purity(xy, D65)) * 100:.1f}%",
                f"{float(colour.colorimetric_purity(xy, D65)) * 100:.1f}%",
            ]
        )

    visible = CMFS.wavelengths[CMFS.wavelengths <= 780]
    locus_xy = colour.XYZ_to_xy(colour.wavelength_to_XYZ(visible, CMFS))
    fig, ax = new_axes((3.6, 3.0), dpi=100)
    ax.plot(locus_xy[:, 0], locus_xy[:, 1], color="#1C1C1E", lw=0.9)
    ax.plot([D65[0]], [D65[1]], "o", ms=4, color="#8E8E93")
    for index, hex_value in enumerate([h for _, h in [("", "#264653"), ("", DEMO), ("", "#E9C46A"), ("", "#E76F51")]]):
        xyz = colour.sRGB_to_XYZ(hex_to_rgb(hex_value))
        xy = colour.XYZ_to_xy(xyz)
        ax.plot([D65[0], xy[0]], [D65[1], xy[1]], color=hex_value, lw=0.8, ls="--", alpha=0.85)
        ax.plot([xy[0]], [xy[1]], "o", ms=5, color=hex_value, mec="#1C1C1E", mew=0.6)
    ax.set_xlim(0, 0.8)
    ax.set_ylim(0, 0.9)
    ax.set_xlabel("x", fontsize=7, color="#555A63")
    ax.set_ylabel("y", fontsize=7, color="#555A63")

    return panel(
        "chroma",
        "基础换算",
        "02",
        "色度学属性",
        "同一支颜色可以写成 xy、u′v′、Luv 的 uv；还能问出「它的主波长是多少、离白点多纯、补色是什么」——这些是 `colorimetry` 里最常被借用的判断。",
        [
            table(
                ["颜色", "hex", "xy", "uv (CIE 1960)", "u′v′ (CIE 1976)", "主波长", "激发纯度", "色度纯度"],
                rows,
                title="三组色度坐标 + 三个属性",
                mono=[1, 2, 3, 4, 5, 6, 7],
            ),
            image(fig, caption="白点 → 样本的连线延伸出去，与光谱轨迹的交点就是主波长", maxw="420px"),
            kv(
                [
                    ("白点", f"x {D65[0]:.4f} · y {D65[1]:.4f}", "D65，作为 dominant_wavelength 的参照"),
                    ("颜色匹配函数", f"{CMFS.shape.start}–{CMFS.shape.end} nm / 步长 {CMFS.shape.interval} nm", "MSDS_CMFS['CIE 1931 2 Degree Standard Observer']"),
                    ("补色波长", "对每个样本可算，见 /catalog/invoke", "complementary_wavelength(u, v, cmfs)"),
                    ("色度图陷阱", "色度图不含亮度；xy 相同、Y 不同的两个颜色看起来完全不同", "解释见面板 09"),
                ],
                title="口径",
            ),
        ],
        phase="M1",
        apis=["POST /api/v1/chroma"],
        controls=[{"label": "样本色", "kind": "color", "value": DEMO}],
        footer="对应 API：`POST /api/v1/chroma`；依赖 `dominant_wavelength` / `excitation_purity` / `colorimetric_purity` / `complementary_wavelength` / `xy_to_uv` / `xy_to_Luv_uv`。",
    )


# --------------------------------------------------------------------------- #
# 03 观察者与光源
# --------------------------------------------------------------------------- #
def panel_observers() -> dict:
    fig1, ax1 = new_axes((4.0, 2.4), dpi=100)
    for name, css in [("x", "#E76F51"), ("y", "#2A9D8F"), ("z", "#3B82F6")]:
        ax1.plot(CMFS.wavelengths, CMFS.values[:, "xyz".index(name)], color=css, lw=1.1, label=f"{name}̄")
    ax1.set_xlabel("波长 / nm", fontsize=7, color="#555A63")
    ax1.legend(fontsize=6, frameon=False, loc="upper right")

    d65 = colour.SDS_ILLUMINANTS["D65"]
    a = colour.SDS_ILLUMINANTS["A"]
    fl2 = colour.SDS_ILLUMINANTS["FL2"]
    fig2, ax2 = new_axes((4.0, 2.4), dpi=100)
    for sd, css, name in [(d65, "#3B82F6", "D65"), (a, "#E76F51", "A"), (fl2, "#2A9D8F", "FL2")]:
        ax2.plot(sd.wavelengths, sd.values, color=css, lw=1.1, label=name)
    ax2.set_xlabel("波长 / nm", fontsize=7, color="#555A63")
    ax2.legend(fontsize=6, frameon=False, loc="upper right")

    cmfs_names = list(colour.MSDS_CMFS.keys())
    illum_names = list(colour.SDS_ILLUMINANTS.keys())
    rows = []
    for name in cmfs_names[:8]:
        sd = colour.MSDS_CMFS[name]
        rows.append([name, f"{sd.shape.start:g}–{sd.shape.end:g} nm", f"{sd.shape.interval:g} nm"])

    return panel(
        "observers",
        "基础换算",
        "03",
        "观察者与光源",
        "一切换算的起点是「谁在看、在什么光下看」。标准观察者的颜色匹配函数与光源的相对光谱功率分布，决定了同一组 RGB 最终落在哪里。",
        [
            image(fig1, caption="CIE 1931 2° 标准观察者的 x̄ / ȳ / z̄", maxw="460px"),
            image(fig2, caption="三种典型光源的相对光谱功率分布：D65（日光）、A（白炽）、FL2（荧光）", maxw="460px"),
            stats(
                [
                    (str(len(cmfs_names)), "标准观察者数据集", "MSDS_CMFS"),
                    (str(len(illum_names)), "光源 SPD", "SDS_ILLUMINANTS"),
                    (str(len(colour.SDS_LIGHT_SOURCES)), "光源（含 LA/LED 等）", "SDS_LIGHT_SOURCES"),
                    ("5", "黑体/日光合成入口", "sd_blackbody / sd_CIE_illuminant_D_series"),
                ],
                title="数据集规模",
            ),
            table(["标准观察者", "波长范围", "步长"], rows, title="观察者抽样（前 8 个）", mono=[0, 1, 2]),
            kv(
                [
                    ("D65 色温", f"{float(colour.temperature.XYZ_to_CCT_Ohno2013(colour.sd_to_XYZ(d65))[0]):.0f} K", "由 SPD 反解"),
                    ("A 光源色温", f"{float(colour.temperature.XYZ_to_CCT_Ohno2013(colour.sd_to_XYZ(a))[0]):.0f} K", "2856 K 标准值"),
                    ("积分方法", "msds_to_XYZ / sd_to_XYZ（ASTM E308 也可）", "见 /catalog/invoke"),
                ],
                title="派生量",
            ),
        ],
        phase="M1",
        apis=["POST /api/v1/spectral"],
        controls=[
            {"label": "观察者", "kind": "select", "value": "CIE 1931 2°", "options": cmfs_names[:6]},
            {"label": "光源", "kind": "select", "value": "D65", "options": illum_names[:6]},
        ],
        footer="对应 API：`POST /api/v1/spectral`；依赖 `MSDS_CMFS` / `SDS_ILLUMINANTS` / `sd_blackbody` / `sd_CIE_illuminant_D_series` / `sd_to_XYZ`。",
    )


# --------------------------------------------------------------------------- #
# 04 光度、明度与白度黄度
# --------------------------------------------------------------------------- #
def panel_photometry() -> dict:
    Ys = np.linspace(0.5, 100, 60)
    fig, ax = new_axes((4.0, 2.4), dpi=100)
    css = ["#264653", "#2A9D8F", "#3B82F6", "#E9C46A", "#F4A261", "#E76F51"]
    for (name, css_color) in zip(
        ["CIE 1976", "Abebe 2017", "Glasser 1958", "Fairchild 2010", "Fairchild 2011", "Wyszecki 1963"], css
    ):
        try:
            values = [float(colour.lightness(float(y), method=name)) for y in Ys]
            ax.plot(Ys, values, color=css_color, lw=1.1, label=name)
        except Exception:
            continue
    ax.set_xlabel("Y（相对亮度，0–100）", fontsize=7, color="#555A63")
    ax.set_ylabel("明度 L*", fontsize=7, color="#555A63")
    ax.legend(fontsize=5.5, frameon=False, loc="lower right")

    fig2, ax2 = new_axes((4.0, 2.4), dpi=100)
    for (name, css_color) in zip(
        ["CIE 1976", "Abebe 2017", "Fairchild 2010", "Newhall 1943"], ["#264653", "#3B82F6", "#E9C46A", "#E76F51"]
    ):
        try:
            values = [float(colour.luminance(float(y), method=name)) for y in Ys]
            ax2.plot(Ys, values, color=css_color, lw=1.1, label=name)
        except Exception:
            continue
    ax2.set_xlabel("明度 L*", fontsize=7, color="#555A63")
    ax2.set_ylabel("亮度 Y", fontsize=7, color="#555A63")
    ax2.legend(fontsize=5.5, frameon=False, loc="lower right")

    paper = np.array([94.8, 100.0, 107.3])
    white = np.array([95.05, 100.0, 108.88])
    whiteness_rows = []
    for method in ["CIE 2004", "ASTM E313", "Berger 1959", "Ganz 1979", "Stensby 1968", "Taube 1960"]:
        try:
            value = colour.whiteness(paper, white, method=method)
            whiteness_rows.append([method, fnum(np.asarray(value).ravel()[0], 2)])
        except Exception as error:
            whiteness_rows.append([method, f"不可用（{type(error).__name__}）"])
    yellowness_rows = []
    for method in ["ASTM E313", "ASTM D1925", "ASTM E313 Alternative"]:
        try:
            value = colour.yellowness(paper, method=method)
            yellowness_rows.append([method, fnum(np.asarray(value).ravel()[0], 2)])
        except Exception as error:
            yellowness_rows.append([method, f"不可用（{type(error).__name__}）"])

    return panel(
        "photometry",
        "基础换算",
        "04",
        "光度、明度与白度黄度",
        "「这块白纸有多白」在色度学里不是一个数，而是一族公式：明度有 6 种定义，白度有 6 种，黄度有 3 种。选错公式，结论就会漂。",
        [
            image(fig, caption="明度函数：Y → L*（CIE 1976 是最常用的立方根，Fairchild 2011 更贴合 HDR 观感）", maxw="460px"),
            image(fig2, caption="亮度函数：L* → Y（明度的反函数族）", maxw="460px"),
            table(["白度公式", "白度值"], whiteness_rows, title="同一张纸的白度（CIE 2004 / ASTM E313 / …）", mono=[1], widths=["160px", "120px"]),
            table(["黄度公式", "黄度值"], yellowness_rows, title="同一张纸的黄度", mono=[1], widths=["200px", "120px"]),
            kv(
                [
                    ("样本", "XYZ = (94.80, 100.00, 107.30)", "近似 D65 下的漂白纸"),
                    ("参照白", "XYZ₀ = (95.05, 100.00, 108.88)", "D65 完全漫反射体"),
                    ("提醒", "白度/黄度是工程指标，不是感知量", "与 ΔE 不可换算"),
                ],
                title="口径",
            ),
        ],
        phase="M1",
        apis=["POST /api/v1/photometry"],
        footer="对应 API：`POST /api/v1/photometry`；依赖 `lightness` / `luminance` / `whiteness` / `yellowness` 及其 15 个具体实现。",
    )


# --------------------------------------------------------------------------- #
# 05 ΔE 全家桶
# --------------------------------------------------------------------------- #
DE_METHODS = [
    "CIE 2000", "CIE 1976", "CIE 1994", "CMC", "DIN99",
    "CAM16-UCS", "CAM16-LCD", "CAM16-SCD",
    "CAM02-UCS", "CAM02-LCD", "CAM02-SCD",
    "ITP", "HyAB", "HyCH",
]


def panel_delta_e() -> dict:
    labs = [colour.XYZ_to_Lab(colour.sRGB_to_XYZ(hex_to_rgb(h))) for h in PALETTE]
    values_2000 = [
        [float(colour.delta_E(labs[i], labs[j], method="CIE 2000")) for j in range(len(labs))]
        for i in range(len(labs))
    ]
    pair_rows = []
    for method in DE_METHODS:
        try:
            value = float(colour.delta_E(labs[0], labs[2], method=method))
            pair_rows.append([method, f"{value:.2f}"])
        except Exception as error:
            pair_rows.append([method, f"不可用（{type(error).__name__}）"])
    stress = None
    try:
        stress = float(colour.index_stress(np.array(values_2000)))
    except Exception:
        pass

    return panel(
        "delta-e",
        "差异与均匀性",
        "05",
        "ΔE 全家桶",
        "同一对颜色，14 个公式给出 14 个数字。ΔE 2000 是工业默认，CAM16-UCS 与 ITP 面向 HDR 与大色域，HyAB 适合大色差。选公式之前，先想清楚你要判定什么。",
        [
            swatches([(h, f"{i + 1}", "样本") for i, h in enumerate(PALETTE)], cols=8),
            matrix(PALETTE, values_2000, title="成对矩阵（CIE 2000）", caption="对称矩阵，对角线无意义；颜色越深表示差异越大"),
            table(["公式", "#264653 ↔ #E9C46A"], pair_rows, title="同一对颜色的 14 种 ΔE", mono=[0, 1], widths=["160px", "140px"]),
            kv(
                [
                    ("最接近的一对", f"#E9C46A ↔ #F4A261：ΔE {delta_e('#E9C46A', '#F4A261'):.2f}", "CIE 2000"),
                    ("最远的一对", f"#264653 ↔ #E9C46A：ΔE {delta_e('#264653', '#E9C46A'):.2f}", "CIE 2000"),
                    ("矩阵压力指数", f"{stress:.3f}" if stress is not None else "—", "index_stress()，衡量矩阵被压缩的程度"),
                    ("元度指数", "Lab_to_metamerism_index / XYZ_to_metamerism_index", "光谱层面的差异，见 /catalog/invoke"),
                    ("经验阈值", "ΔE<1 不可辨；1–2 需并排；2–5 一眼可辨；>10 完全不同色", "阈值必须与公式绑定"),
                ],
                title="读数与度量",
            ),
            note(
                "CIE 1976 的 ΔE 与 Lab 空间欧氏距离等价，对饱和色严重低估；CIE 2000 用明度/彩度/色相三条权重修正，但对大色差仍会被压缩。这就是 CAM16-UCS 与 HyAB 存在的理由。",
                tone="info",
                title="为什么公式会有差异",
            ),
        ],
        phase="M1",
        apis=["POST /api/v1/delta-e"],
        controls=[{"label": "ΔE 公式", "kind": "select", "value": "CIE 2000", "options": DE_METHODS}],
        footer="对应 API：`POST /api/v1/delta-e`；依赖 `colour.delta_E` 的 14 个方法 + `index_stress` + `delta_E` 元度扩展。",
    )


# --------------------------------------------------------------------------- #
# 06 均匀空间与渐变
# --------------------------------------------------------------------------- #
GRADIENT_SPACES = [
    ("sRGB", "sRGB"),
    ("Linear sRGB", "Linear sRGB"),
    ("CIE Lab", "CIE Lab"),
    ("Oklab", "Oklab"),
    ("CAM16-UCS", "CAM16UCS"),
    ("Jzazbz", "Jzazbz"),
    ("IPT", "IPT"),
]


def interpolate_via_graph(start: str, end: str, steps: int, space: str) -> list[str]:
    a = np.array(hex_to_rgb(start))
    b = np.array(hex_to_rgb(end))
    t = np.linspace(0, 1, steps)[:, None]
    if space == "sRGB":
        return [rgb_to_hex(row) for row in a * (1 - t) + b * t]
    if space == "Linear sRGB":
        la = colour.models.eotf_inverse_sRGB(a)
        lb = colour.models.eotf_inverse_sRGB(b)
        return [rgb_to_hex(colour.models.eotf_sRGB(row)) for row in la * (1 - t) + lb * t]
    ca = np.asarray(colour.convert(a, "sRGB", space), dtype=float)
    cb = np.asarray(colour.convert(b, "sRGB", space), dtype=float)
    mixed = ca * (1 - t) + cb * t
    return [rgb_to_hex(colour.convert(row, space, "sRGB")) for row in mixed]


def panel_gradient() -> dict:
    start, end = "#03045E", "#FEE440"
    items = []
    ranking = []
    for label, space in GRADIENT_SPACES:
        hexes = interpolate_via_graph(start, end, 11, space)
        deltas = adjacent_delta_e(hexes)
        stdev = float(np.std(deltas))
        ranking.append([space, f"{stdev:.2f}", f"{min(deltas):.2f} – {max(deltas):.2f}", f"{float(np.mean(deltas)):.2f}"])
        items.append(
            strip(
                space,
                "两两相邻步长的 ΔE 2000",
                hexes,
                [("σ", f"{stdev:.2f}"), ("区间", f"{min(deltas):.2f}–{max(deltas):.2f}")],
            )
        )
    ranking.sort(key=lambda row: float(row[1]))

    return panel(
        "gradient",
        "差异与均匀性",
        "06",
        "均匀空间与渐变插值",
        "把同一组端点丢进 7 个空间做线性插值：数学上都是「直线」，观感上差别很大。用相邻步长的 ΔE 标准差可以把它量化——σ 越小，过渡越均匀。",
        [
            strips(items, title=f"{start.upper()} → {end.upper()}，11 步", caption="σ 来自每段相邻色对的 ΔE 2000"),
            table(["空间", "σ（越小越均匀）", "ΔE 区间", "均值"], ranking, title="按均匀性排序", mono=[1, 2, 3]),
            note(
                "线性 sRGB 往往是最差的一个：它忽略了 γ 编码对人眼的压缩。Oklab 与 CAM16-UCS 把明度、彩度做了非线性压缩，因此步长最稳；Jzazbz 面向 HDR（绝对亮度 10000 cd/m²），在 SDR 区间与 Oklab 接近。",
                tone="info",
                title="为什么拉直了还不好看",
            ),
        ],
        phase="M1",
        apis=["POST /api/v1/gradient"],
        controls=[
            {"label": "起点", "kind": "color", "value": start},
            {"label": "终点", "kind": "color", "value": end},
            {"label": "步数", "kind": "select", "value": "11", "options": ["5", "9", "11", "21"]},
        ],
        footer="对应 API：`POST /api/v1/gradient`；任意空间插值走 `colour.convert()` 的换算图（106 节点），不依赖手写公式。",
    )


# --------------------------------------------------------------------------- #
# 07 RGB 色彩空间图鉴
# --------------------------------------------------------------------------- #
def gamut_area(colourspace) -> float:
    p = np.asarray(colourspace.primaries, dtype=float)
    (x1, y1), (x2, y2), (x3, y3) = p
    return abs((x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2)) / 2)


def panel_rgb_spaces() -> dict:
    rows = []
    for name, space in colour.RGB_COLOURSPACES.items():
        white = space.whitepoint
        rows.append(
            [
                name,
                f"{white[0]:.4f}, {white[1]:.4f}",
                f"{gamut_area(space) * 100:.1f}%",
                getattr(space.cctf_encoding, "__name__", "—"),
            ]
        )
    rows.sort(key=lambda row: -float(row[2].rstrip("%")))

    fig, ax = plt.subplots(figsize=(3.8, 3.2), dpi=100)
    fig.patch.set_alpha(0)
    colour.plotting.plot_RGB_colourspaces_in_chromaticity_diagram_CIE1931(
        ["sRGB", "Display P3", "ITU-R BT.2020", "ACES2065-1", "ProPhoto RGB", "Adobe RGB (1998)"],
        axes=ax,
        show=False,
    )
    ax.set_title("")
    for text in ax.texts:
        text.set_clip_on(False)

    return panel(
        "rgb-spaces",
        "差异与均匀性",
        "07",
        "RGB 色彩空间图鉴",
        "colour 内置 96 个 RGB 色彩空间：从 sRGB 到 ACES、从电影机的 S-Log3 到手机的 Display P3。每个空间 = 白点 + 三原色 + 传递函数，三件套齐了才能正确换算。",
        [
            image(fig, caption="六个代表色域在 CIE 1931 图上的位置（面积占比即 xy 平面三角形面积）", maxw="460px"),
            table(
                ["色彩空间", "白点 xy", "色域面积 / xy 平面", "编码函数（cctf_encoding）"],
                rows,
                title=f"全部 {len(rows)} 个 RGB 色彩空间（按面积排序）",
                mono=[0, 1, 2],
                widths=["150px", "120px", "130px", "auto"],
            ),
            stats(
                [
                    (str(len(colour.RGB_COLOURSPACES)), "RGB 色彩空间", "RGB_COLOURSPACES"),
                    (str(len(colour.models.LOG_ENCODINGS)), "对数编码", "log_encoding_*"),
                    (str(len(colour.models.EOTFS)), "EOTF", "eotf_*"),
                    (str(len(colour.models.OETFS)), "OETF", "oetf_*"),
                ],
                title="规模",
            ),
        ],
        phase="M2",
        apis=["GET /api/v1/spaces"],
        controls=[{"label": "叠加色域", "kind": "select", "value": "sRGB", "options": list(colour.RGB_COLOURSPACES)[:8]}],
        footer="对应 API：`GET /api/v1/spaces`；依赖 `RGB_COLOURSPACES`（96 个）、`RGB_Colourspace`、`normalised_primary_matrix`。",
    )


# --------------------------------------------------------------------------- #
# 08 传递函数与视频信号
# --------------------------------------------------------------------------- #
def panel_transfer() -> dict:
    x = np.linspace(0.001, 1.0, 200)
    curves = [
        ("sRGB（≈BT.709）", "oetf_BT709", "#264653"),
        ("SMPTE ST 2084 (PQ)", "oetf_BT2100_PQ", "#3B82F6"),
        ("HLG", "oetf_BT2100_HLG", "#2A9D8F"),
        ("S-Log3", "log_encoding_SLog3", "#E9C46A"),
        ("ARRI LogC3", "log_encoding_ARRILogC3", "#F4A261"),
        ("ACEScct", "log_encoding_ACEScct", "#E76F51"),
    ]
    fig, ax = new_axes((4.2, 2.4), dpi=100)
    for label, fn_name, css in curves:
        fn = getattr(colour.models, fn_name)
        try:
            ax.plot(x, [float(fn(float(v))) for v in x], color=css, lw=1.1, label=label)
        except Exception:
            continue
    ax.set_xlabel("线性光 / 0–1", fontsize=7, color="#555A63")
    ax.set_ylabel("编码值", fontsize=7, color="#555A63")
    ax.legend(fontsize=5.5, frameon=False, loc="lower right")

    roundtrip = []
    for label, enc, dec in [
        ("sRGB", "oetf_BT709", "oetf_inverse_BT709"),
        ("PQ", "oetf_BT2100_PQ", "oetf_inverse_BT2100_PQ"),
        ("HLG", "oetf_BT2100_HLG", "oetf_inverse_BT2100_HLG"),
        ("S-Log3", "log_encoding_SLog3", "log_decoding_SLog3"),
        ("ARRI LogC3", "log_encoding_ARRILogC3", "log_decoding_ARRILogC3"),
        ("ACEScct", "log_encoding_ACEScct", "log_decoding_ACEScct"),
    ]:
        try:
            f_enc = getattr(colour.models, enc)
            f_dec = getattr(colour.models, dec)
            error = max(abs(float(f_dec(f_enc(v))) - v) for v in np.linspace(0.02, 0.98, 25))
            roundtrip.append([label, f"{error:.2e}"])
        except Exception as e:
            roundtrip.append([label, f"不可用（{type(e).__name__}）"])

    rgb = hex_to_rgb(DEMO)
    ycbcr = colour.models.RGB_to_YCbCr(rgb)
    return panel(
        "transfer",
        "差异与均匀性",
        "08",
        "传递函数与视频信号",
        "编码/解码曲线决定了「同一束光」在文件里长什么样。colour 内置 30+ 组 EOTF/OETF 与 40+ 组对数编码，全部可逆——这里的往返误差就是它们的体检报告。",
        [
            image(fig, caption="六种常见传递函数的编码曲线（横轴线性光，纵轴编码值）", maxw="470px"),
            table(["编码", "往返最大误差"], roundtrip, title="编码 → 解码 往返精度", mono=[0, 1], widths=["160px", "140px"]),
            kv(
                [
                    ("YCbCr（BT.709，limited range）", vec(ycbcr, 4), "RGB_to_YCbCr"),
                    ("可用的矩阵系数", ", ".join(str(k) for k in list(colour.models.MATRIX_COEFFICIENTS_ITUTH273.keys())[:5]), "ITU-T H.273"),
                    ("可用的传递特性", ", ".join(str(k) for k in list(colour.models.TRANSFER_CHARACTERISTICS_ITUTH273.keys())[:4]), "ITU-T H.273"),
                    ("描述函数", "describe_video_signal_colour_primaries / matrix_coefficients / transfer_characteristics", "把 H.273 代码点翻译成人话"),
                ],
                title="视频信号",
            ),
        ],
        phase="M2",
        apis=["POST /api/v1/transfer"],
        controls=[{"label": "编码", "kind": "select", "value": "sRGB", "options": [c[0] for c in curves]}],
        footer="对应 API：`POST /api/v1/transfer`；依赖 `EOTFS` / `OETFS` / `LOG_ENCODINGS` / `RGB_to_YCbCr` / `describe_video_signal_*`。",
    )
