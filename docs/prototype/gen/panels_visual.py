"""面板 09–18：色度图、色域体、色温、色彩质量、图像/LUT、色适应、外观模型、感知现象、对应色、CVD。"""

from __future__ import annotations

import warnings

import numpy as np
from matplotlib.collections import PolyCollection

import colour

import matplotlib.pyplot as plt  # noqa: E402

from .common import (
    chart,
    delta_e,
    fnum,
    hex_to_rgb,
    image,
    kv,
    matrix,
    new_axes,
    note,
    panel,
    rgb_to_hex,
    series,
    stats,
    swatches,
    table,
    vec,
)

D65 = colour.CCS_ILLUMINANTS["CIE 1931 2 Degree Standard Observer"]["D65"]
XYZ_W = colour.xy_to_XYZ(D65)
PALETTE = ["#264653", "#2A9D8F", "#E9C46A", "#F4A261", "#E76F51"]
DEMO = "#3B82F6"


# --------------------------------------------------------------------------- #
# 09 色度图
# --------------------------------------------------------------------------- #
GAMUTS = ["sRGB", "Display P3", "ITU-R BT.2020"]


def gamut_area(name: str) -> float:
    p = np.asarray(colour.RGB_COLOURSPACES[name].primaries, dtype=float)
    (x1, y1), (x2, y2), (x3, y3) = p
    return abs((x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2)) / 2)


def panel_chromaticity() -> dict:
    fig, ax = new_axes((3.9, 3.5), dpi=110)
    colour.plotting.plot_chromaticity_diagram_CIE1931(axes=ax, show=False)
    ax.set_title("")
    ax.set_axis_off()
    for text in ax.texts:
        text.set_clip_on(False)
    for name, css, dash in [("sRGB", "#111111", "-"), ("Display P3", "#3B82F6", "--"), ("ITU-R BT.2020", "#E76F51", "--")]:
        p = np.asarray(colour.RGB_COLOURSPACES[name].primaries, dtype=float)
        closed = np.vstack([p, p[0]])
        ax.plot(closed[:, 0], closed[:, 1], color=css, lw=1.0, ls=dash, alpha=0.85, zorder=8)
    for index, hex_value in enumerate(PALETTE, start=1):
        xy = colour.XYZ_to_xy(colour.sRGB_to_XYZ(hex_to_rgb(hex_value)))
        ax.scatter([xy[0]], [xy[1]], s=52, c=[hex_value], edgecolors="#1C1C1E", linewidths=0.7, zorder=20)
        ax.annotate(str(index), (xy[0], xy[1]), xytext=(5.5, 3), textcoords="offset points",
                    fontsize=6, color="#1C1C1E", zorder=21)

    rows = [[g, f"{gamut_area(g):.4f}", f"{gamut_area(g) / gamut_area('sRGB'):.2f}×"] for g in GAMUTS]
    return panel(
        "chromaticity",
        "色域与光源",
        "09",
        "色度图与色域",
        "三种色度图（CIE 1931 xy、1960 uv、1976 u′v′）描述的是同一件事，只是「均匀程度」不同。把样本点与色域三角形放上去，就能一眼看出「这支颜色超出 sRGB 多少」。",
        [
            image(fig, caption="CIE 1931 色度图 + 三个色域三角形 + 5 个样本点", maxw="480px"),
            table(["色域", "面积（xy 平面）", "相对 sRGB"], rows, title="三角形面积", mono=[1, 2], widths=["160px", "130px", "90px"]),
            kv(
                [
                    ("三种色度图", "plot_chromaticity_diagram_CIE1931 / CIE1960UCS / CIE1976UCS", "同一套 CMFS，不同投影"),
                    ("MacAdam 椭圆", "plot_ellipses_MacAdam1942_in_chromaticity_diagram_*", "感知等距圈，见面板 22/25"),
                    (
                        "样本点",
                        " · ".join(
                            f"{p['i']}: {p['x']:.3f},{p['y']:.3f}"
                            for p in [
                                {
                                    "i": i + 1,
                                    "x": float(colour.XYZ_to_xy(colour.sRGB_to_XYZ(hex_to_rgb(h)))[0]),
                                    "y": float(colour.XYZ_to_xy(colour.sRGB_to_XYZ(hex_to_rgb(h)))[1]),
                                }
                                for i, h in enumerate(PALETTE)
                            ]
                        ),
                        "xy 坐标",
                    ),
                ],
                title="口径",
            ),
        ],
        phase="M2",
        apis=["GET /api/v1/chromaticity.svg"],
        controls=[
            {"label": "色度图", "kind": "select", "value": "CIE 1931", "options": ["CIE 1931", "CIE 1960 UCS", "CIE 1976 UCS"]},
            {"label": "叠加色域", "kind": "select", "value": "sRGB / P3 / BT.2020", "options": ["sRGB / P3 / BT.2020", "仅 sRGB"]},
        ],
        footer="对应 API：`GET /api/v1/chromaticity.svg`；依赖 `plot_chromaticity_diagram_CIE*` / `RGB_COLOURSPACES[*].primaries`。",
    )


# --------------------------------------------------------------------------- #
# 10 色域体
# --------------------------------------------------------------------------- #
def panel_gamut_volume() -> dict:
    samples = 5000
    baseline = colour.volume.RGB_colourspace_volume_MonteCarlo(
        colour.RGB_COLOURSPACES["sRGB"], samples=samples, illuminant_Lab=np.array(D65)
    )
    rows = []
    for name in ["sRGB", "Display P3", "ITU-R BT.2020", "ACES2065-1"]:
        try:
            volume = (
                baseline
                if name == "sRGB"
                else colour.volume.RGB_colourspace_volume_MonteCarlo(
                    colour.RGB_COLOURSPACES[name], samples=samples, illuminant_Lab=np.array(D65)
                )
            )
            rows.append([name, f"{volume / 1000:.1f}×10³", f"{volume / baseline:.2f}×"])
        except Exception as error:
            rows.append([name, f"不可用（{type(error).__name__}）", "—"])

    fig = plt.figure(figsize=(3.2, 3.0), dpi=90)
    fig.patch.set_alpha(0)
    ax = fig.add_subplot(111, projection="3d")
    rng = np.random.default_rng(7)
    cube = rng.random((4000, 3))
    lab = colour.XYZ_to_Lab(colour.sRGB_to_XYZ(cube))
    ax.scatter(lab[:, 1], lab[:, 2], lab[:, 0], c=cube, s=1.4, linewidths=0, alpha=0.6)
    ax.set_xlabel("a*", fontsize=6, color="#555A63")
    ax.set_ylabel("b*", fontsize=6, color="#555A63")
    ax.set_zlabel("L*", fontsize=6, color="#555A63")
    ax.tick_params(labelsize=5, colors="#555A63", pad=-2)
    for pane in (ax.xaxis, ax.yaxis, ax.zaxis):
        pane.pane.set_alpha(0.0)
    ax.grid(False)

    return panel(
        "gamut-volume",
        "色域与光源",
        "10",
        "色域体与边界",
        "色域不是一张图，而是一个三维体：L*、a*、b* 围出的体积。体积越大能装的颜色越多——但「能装」和「装得准」是两件事，后者要看色域边界的形状。",
        [
            image(fig, caption="sRGB 在 CIELAB 空间中的体积采样（4000 点）", maxw="380px"),
            table(["色彩空间", "体积（MonteCarlo，Lab 单位）", "相对 sRGB"], rows, title="体积估算（5000 采样点）", mono=[1, 2], widths=["150px", "200px", "90px"]),
            kv(
                [
                    ("边界判定", "is_within_macadam_limits / is_within_pointer_gamut / is_within_visible_spectrum", "三套判据，用途不同"),
                    ("体积工具", "RGB_colourspace_volume_MonteCarlo / RGB_colourspace_volume_coverage_MonteCarlo", "采样法，分辨率可调"),
                    ("MacAdam 极限", "给定光源下最饱和的物体色边界", "由光源 SPD 决定"),
                    ("Pointer 色域", "真实物体表面色（皮肤、植物、涂料）的经验边界", "DATA_POINTER_GAMUT_VOLUME"),
                ],
                title="口径",
            ),
            note(
                "MonteCarlo 体积是抽样估算，值随采样数与随机种子波动；工程上用它做「色域大小」的相对比较，而不是绝对量。生产环境应固定随机种子并把采样数写进响应字段。",
                tone="warn",
                title="为什么体积不是精确值",
            ),
        ],
        phase="M2",
        apis=["POST /api/v1/volume"],
        footer="对应 API：`POST /api/v1/volume`；依赖 `RGB_colourspace_volume_MonteCarlo` / `RGB_colourspace_limits` / `is_within_*` / `solid_RoschMacAdam`。",
    )


# --------------------------------------------------------------------------- #
# 11 色温
# --------------------------------------------------------------------------- #
def panel_temperature() -> dict:
    fig, ax = new_axes((3.9, 3.0), dpi=110)
    colour.plotting.plot_planckian_locus_in_chromaticity_diagram_CIE1931(["A", "D65", "D50"], axes=ax, show=False)
    ax.set_title("")
    for text in ax.texts:
        text.set_clip_on(False)

    rows = []
    for method in ["Ohno 2013", "Robertson 1968", "McCamy 1992", "Krystek 1985", "Hernandez 1999", "Kang 2002", "CIE Illuminant D Series"]:
        try:
            value = colour.temperature.xy_to_CCT(D65, method=method)
            rows.append([method, f"{float(value):.0f} K"])
        except Exception as error:
            rows.append([method, f"不可用（{type(error).__name__}）"])

    forward = []
    for method in ["McCamy 1992", "Hernandez 1999", "Kang 2002", "CIE Illuminant D Series"]:
        try:
            xy = colour.temperature.CCT_to_xy(6500.0, method=method)
            forward.append([method, f"{float(xy[0]):.5f}, {float(xy[1]):.5f}"])
        except Exception as error:
            forward.append([method, f"不可用（{type(error).__name__}）"])

    return panel(
        "temperature",
        "色域与光源",
        "11",
        "色温与黑体轨迹",
        "「6500K 的光」其实是黑体轨迹上的一个点。正向（CCT → xy/uv）与反向（xy/uv → CCT）各有 4–7 种算法：暖端差异很小，一旦偏绿，不同算法的分歧就出来了。",
        [
            image(fig, caption="普朗克轨迹与 A / D50 / D65 的位置", maxw="470px"),
            table(["算法（xy → CCT）", "对 D65 的结果"], rows, title="七种反解算法", mono=[1], widths=["220px", "140px"]),
            table(["算法（CCT → xy）", "6500 K → xy"], forward, title="四种正向算法", mono=[1], widths=["200px", "160px"]),
            kv(
                [
                    ("mired", f"{float(colour.temperature.CCT_to_mired(6500)):.2f} mired（6500 K）", "色温的倒数坐标，摄影滤色片用它"),
                    ("正向方法表", ", ".join(list(colour.temperature.CCT_TO_XY_METHODS.keys())[:5]), "CCT_TO_XY_METHODS"),
                    ("反向方法表", ", ".join(list(colour.temperature.UV_TO_CCT_METHODS.keys())[:5]), "UV_TO_CCT_METHODS"),
                    ("日光轨迹", "daylight_locus_function / sd_CIE_illuminant_D_series", "D 系列光源由轨迹合成"),
                ],
                title="工具",
            ),
        ],
        phase="M2",
        apis=["POST /api/v1/temperature"],
        controls=[{"label": "色温", "kind": "select", "value": "6500 K", "options": ["2700 K", "4000 K", "5000 K", "6500 K", "9000 K"]}],
        footer="对应 API：`POST /api/v1/temperature`；依赖 `CCT_to_xy` / `xy_to_CCT` / `CCT_to_uv` / `uv_to_CCT` / `CCT_to_mired` 及全部方法实现。",
    )


# --------------------------------------------------------------------------- #
# 12 色彩质量
# --------------------------------------------------------------------------- #
def panel_quality() -> dict:
    illuminants = ["D65", "FL2", "A", "FL11"]
    rows = []
    for name in illuminants:
        sd = colour.SDS_ILLUMINANTS[name]
        ra = float(colour.quality.colour_rendering_index(sd))
        qa = float(colour.quality.colour_quality_scale(sd))
        cf = colour.quality.colour_fidelity_index(sd)
        rows.append([name, f"{ra:.1f}", f"{qa:.1f}", f"{float(cf):.1f}"])
    ref = colour.SDS_ILLUMINANTS["D65"]
    ssi = []
    for name in ["FL2", "A"]:
        try:
            ssi.append([name, f"{float(colour.quality.spectral_similarity_index(colour.SDS_ILLUMINANTS[name], ref)):.3f}"])
        except Exception as error:
            ssi.append([name, f"不可用（{type(error).__name__}）"])

    fig, ax = new_axes((3.9, 2.4), dpi=110)
    x = np.arange(1, 16)
    for name, css in [("D65", "#264653"), ("FL2", "#E76F51")]:
        values = []
        for i in x:
            try:
                values.append(float(colour.quality.colour_rendering_index(colour.SDS_ILLUMINANTS[name], additional_data=True).values[i - 1]))
            except Exception:
                values.append(np.nan)
        ax.bar(x + (0.2 if name == "FL2" else -0.2), values, width=0.38, color=css, label=name)
    ax.set_xticks(x)
    ax.set_xticklabels([f"R{i}" for i in x], fontsize=5)
    ax.set_ylabel("Ri", fontsize=7, color="#555A63")
    ax.legend(fontsize=6, frameon=False)

    return panel(
        "quality",
        "色域与光源",
        "12",
        "色彩质量（显色指数）",
        "同一个红苹果，在白炽灯下和荧光灯下看起来不一样——这就是显色性。CIE 的 Ra、CQS 的 Qa、TM-30 的 Rf/Rg、以及光谱相似度 SSI，是四套不同的度量口径。",
        [
            image(fig, caption="CRI 特殊显色指数 R1–R15：D65（参照）与 FL2（荧光）逐项对比", maxw="460px"),
            table(["光源", "CRI Ra", "CQS Qa", "TM-30 Rf"], rows, title="四种光源的显色指标", mono=[0, 1, 2, 3]),
            table(["光源（相对 D65）", "SSI"], ssi, title="光谱相似度", mono=[0, 1], widths=["160px", "120px"]),
            kv(
                [
                    ("测试色样", "SDS_TCS（14 个 CRI 色样）/ SDS_VS（TM-30 99 个色样）", "数据集内置"),
                    ("TM-30 图形", "plot_single_sd_colour_rendition_report", "Rf/Rg 与色域偏移矢量图"),
                    ("注意", "Ra 只覆盖 8 个中等饱和色样，对 LED 会高估", "TM-30 的 Rf 更严格"),
                ],
                title="口径",
            ),
        ],
        phase="M2",
        apis=["POST /api/v1/quality"],
        controls=[{"label": "光源", "kind": "select", "value": "FL2", "options": illuminants}],
        footer="对应 API：`POST /api/v1/quality`；依赖 `colour_rendering_index` / `colour_quality_scale` / `colour_fidelity_index` / `spectral_similarity_index`。",
    )


# --------------------------------------------------------------------------- #
# 13 图像与 LUT
# --------------------------------------------------------------------------- #
def panel_image_lut() -> dict:
    # 生成一张测试图：色带 + 灰阶
    height, width = 60, 240
    image_rgb = np.zeros((height, width, 3))
    for x in range(width):
        image_rgb[:, x] = colour.HSV_to_RGB([x / width, 0.85, 0.95])
    for y in range(height // 3, height):
        image_rgb[y, :] = np.linspace(0, 1, width)[None, :, None]
    image_rgb = np.clip(image_rgb, 0, 1)

    lut = colour.io.LUT3D(size=17)
    lut.table = colour.io.LUT3D.linear_table(17) ** np.array([0.9, 1.0, 1.1])[:]
    filtered = lut.apply(image_rgb)

    fig, ax = plt.subplots(figsize=(3.6, 1.3), dpi=110)
    fig.patch.set_alpha(0)
    ax.imshow(image_rgb, aspect="auto")
    ax.axis("off")
    fig2, ax2 = plt.subplots(figsize=(3.6, 1.3), dpi=110)
    fig2.patch.set_alpha(0)
    ax2.imshow(np.clip(filtered, 0, 1), aspect="auto")
    ax2.axis("off")

    interp = []
    probe = np.array([0.23, 0.51, 0.96])
    for method in ["Trilinear", "Tetrahedral"]:
        try:
            value = lut.apply(probe, interpolator=method)
            interp.append([method, vec(value, 5)])
        except Exception as error:
            interp.append([method, f"不可用（{type(error).__name__}）"])

    return panel(
        "image-lut",
        "工程与数据",
        "13",
        "图像与 3D LUT",
        "把颜色算到像素上：一张测试图经过 17³ 的 3D LUT 变换，再交给三线性或四面体插值。这是影视调色与相机校色的基本操作，colour 里由 `colour.io` 承担。",
        [
            image(fig, caption="原图：HSV 色相带 + 灰阶（由 colour.HSV_to_RGB 生成）", maxw="520px"),
            image(fig2, caption="经 17³ LUT 变换后（通道增益 0.9 / 1.0 / 1.1）", maxw="520px"),
            table(["插值方法", "单点结果"], interp, title="两种插值方式", mono=[0, 1], widths=["130px", "auto"]),
            kv(
                [
                    ("LUT 尺寸", f"{lut.size}³ = {lut.size ** 3} 个格点", "LUT3D"),
                    ("读写格式", "Cinespace / Iridas Cube / Resolve Cube / Sony SPI1D / SPI3D", "read_LUT / write_LUT"),
                    ("图像 I/O", "read_image / write_image（ImageIO 与 OpenImageIO 后端）", "colour.io"),
                    ("光谱图像", "read_spectral_image_Fichet2021 / spectrum_attribute_to_sd_Fichet2021", "IESTM2714 元数据"),
                ],
                title="能力",
            ),
            note(
                "LUT 越大越准，但内存是 O(n³)：33³ 已是 3.6 万格点。四面体插值通常比三线性更贴合非线性变换，代价是常数因子更大。",
                tone="info",
                title="工程取舍",
            ),
        ],
        phase="M3",
        apis=["POST /api/v1/lut"],
        footer="对应 API：`POST /api/v1/lut`；依赖 `io.LUT3D` / `LUT3x1D` / `read_image` / `write_image` / `table_interpolation_trilinear|tetrahedral`。",
    )


# --------------------------------------------------------------------------- #
# 14 色适应
# --------------------------------------------------------------------------- #
def panel_adaptation() -> dict:
    xyz = colour.sRGB_to_XYZ(hex_to_rgb(DEMO))
    xyz_a = colour.xy_to_XYZ(colour.CCS_ILLUMINANTS["CIE 1931 2 Degree Standard Observer"]["A"])
    methods = list(colour.CHROMATIC_ADAPTATION_METHODS.keys())
    rows = []
    for method in methods:
        try:
            adapted = colour.chromatic_adaptation(xyz, xyz_a, XYZ_W, method=method)
            xy = colour.XYZ_to_xy(adapted)
            rows.append([method, f"{xy[0]:.4f}, {xy[1]:.4f}", rgb_to_hex(colour.XYZ_to_sRGB(adapted)).upper()])
        except Exception as error:
            rows.append([method, f"不可用（{type(error).__name__}）", "—"])

    cat_rows = []
    for name in ["Bradford", "CAT02", "CAT16", "Von Kries", "CMCCAT2000", "Sharp", "Fairchild"]:
        key = f"CAT_{name.upper().replace(' ', '_')}"
        matrix_cat = getattr(colour.adaptation, key, None)
        if matrix_cat is None:
            continue
        cat_rows.append([name, " · ".join(vec(row, 3) for row in np.asarray(matrix_cat))])

    return panel(
        "adaptation",
        "外观与感知",
        "14",
        "色适应",
        "同一支蓝在 A 光源下和白炽灯下，视网膜接收到的物理光不同，但你会认为它是同一支蓝——这叫色适应。不同 CAT 矩阵（Bradford / CAT02 / CAT16 / …）对这一过程的建模不同。",
        [
            table(["方法", "适应后 xy（A → D65）", "对应 sRGB"], rows, title="七种色适应方法对同一支颜色的处理", mono=[1, 2], widths=["170px", "170px", "120px"]),
            table(["CAT 矩阵", "3×3 系数"], cat_rows, title="七个标准 CAT 矩阵", mono=[0, 1], widths=["110px", "auto"]),
            kv(
                [
                    ("梯度/程度", "CAT_CAT16_INVERSE / conditions_degree_of_adaptation", "部分适应（degree of adaptation）"),
                    ("vK20", "chromatic_adaptation_vK20 / matrix_chromatic_adaptation_vk20", "2020 年的新方法，支持不完全适应"),
                    ("正向/反向", "chromatic_adaptation_forward_CMCCAT2000 / inverse_CMCCAT2000", "CMCCAT2000 是唯一带显式正向反向的实现"),
                ],
                title="进阶能力",
            ),
        ],
        phase="M2",
        apis=["POST /api/v1/adapt"],
        controls=[
            {"label": "源白点", "kind": "select", "value": "A", "options": ["A", "D50", "D65", "D93", "F2"]},
            {"label": "目标白点", "kind": "select", "value": "D65", "options": ["D50", "D65", "D93"]},
            {"label": "方法", "kind": "select", "value": "Bradford", "options": methods},
        ],
        footer="对应 API：`POST /api/v1/adapt`；依赖 `chromatic_adaptation` 的 7 个方法 + 13 个 CAT 矩阵 + `conditions_degree_of_adaptation`。",
    )


# --------------------------------------------------------------------------- #
# 15 外观模型
# --------------------------------------------------------------------------- #
def appearance_rows() -> list[list[str]]:
    xyz1 = colour.sRGB_to_XYZ(hex_to_rgb(DEMO))
    rows = []
    conditions = {
        "CAM16": "XYZ_w / L_A / Y_b（Domain100）",
        "CIECAM02": "同上",
        "CIECAM16": "同上",
        "Hellwig 2022": "同上",
        "ZCAM": "XYZ_w / L_A / Y_b（Domain1）",
        "Hunt": "XYZ_w / XYZ_b / L_A",
        "RLAB": "XYZ_n / Y_n（无适应度参数）",
        "LLAB": "XYZ_0 / Y_b / L",
        "Kim 2009": "XYZ_w / L_A(+媒体参数)",
        "Nayatani 95": "XYZ_n / Y_o / E_o / E_or",
        "ATD 95": "XYZ_0 / Y_0 / k₁ / k₂",
        "sCAM": "XYZ_w / L_A / Y_b",
    }
    calls = {
        "CAM16": lambda: colour.XYZ_to_CAM16(xyz1 * 100, XYZ_w=XYZ_W * 100, L_A=64 / np.pi / 5, Y_b=20),
        "CIECAM02": lambda: colour.XYZ_to_CIECAM02(xyz1 * 100, XYZ_w=XYZ_W * 100, L_A=64 / np.pi / 5, Y_b=20),
        "CIECAM16": lambda: colour.XYZ_to_CIECAM16(xyz1 * 100, XYZ_w=XYZ_W * 100, L_A=64 / np.pi / 5, Y_b=20),
        "Hellwig 2022": lambda: colour.XYZ_to_Hellwig2022(xyz1 * 100, XYZ_w=XYZ_W * 100, L_A=64 / np.pi / 5, Y_b=20),
        "ZCAM": lambda: colour.XYZ_to_ZCAM(xyz1, XYZ_w=XYZ_W, L_A=64 / np.pi / 5, Y_b=20),
        "Hunt": lambda: colour.XYZ_to_Hunt(xyz1 * 100, XYZ_w=XYZ_W * 100, XYZ_b=XYZ_W * 100 * 0.2, L_A=64 / np.pi / 5),
        "RLAB": lambda: colour.XYZ_to_RLAB(xyz1 * 100, XYZ_n=XYZ_W * 100, Y_n=20),
        "LLAB": lambda: colour.XYZ_to_LLAB(xyz1 * 100, XYZ_0=XYZ_W * 100, Y_b=20, L=318.31),
        "Kim 2009": lambda: colour.XYZ_to_Kim2009(xyz1 * 100, XYZ_w=XYZ_W * 100, L_A=64 / np.pi / 5),
        "Nayatani 95": lambda: colour.XYZ_to_Nayatani95(xyz1 * 100, XYZ_n=XYZ_W * 100, Y_o=20, E_o=5000, E_or=1000),
        "ATD 95": lambda: colour.XYZ_to_ATD95(xyz1 * 100, XYZ_0=XYZ_W * 100, Y_0=20, k_1=0.0, k_2=50),
        "sCAM": lambda: colour.XYZ_to_sCAM(xyz1 * 100, XYZ_w=XYZ_W * 100, L_A=64 / np.pi / 5, Y_b=20),
    }
    for model, call in calls.items():
        try:
            spec = call()
            rows.append(
                [
                    model,
                    fnum(getattr(spec, "J", float("nan")), 2),
                    fnum(getattr(spec, "C", float("nan")), 2),
                    fnum(getattr(spec, "h", float("nan")), 1),
                    fnum(getattr(spec, "M", float("nan")), 2),
                    conditions.get(model, "—"),
                ]
            )
        except Exception as error:
            rows.append([model, "—", "—", "—", "—", f"不可用：{type(error).__name__}"])
    return rows


def panel_appearance() -> dict:
    rows = appearance_rows()
    xyz1 = colour.sRGB_to_XYZ(hex_to_rgb(DEMO))
    rounded = colour.CAM16_to_XYZ(
        colour.XYZ_to_CAM16(xyz1 * 100, XYZ_w=XYZ_W * 100, L_A=64 / np.pi / 5, Y_b=20),
        XYZ_w=XYZ_W * 100,
        L_A=64 / np.pi / 5,
        Y_b=20,
    ) / 100
    error = float(np.max(np.abs(rounded - xyz1)))
    return panel(
        "appearance",
        "外观与感知",
        "15",
        "外观模型",
        "RGB 说的是「显示器发多少光」，外观模型说的是「你会觉得它多亮、多彩、什么色相」。colour 内置 12 个外观模型，每个模型的观察条件参数都不一样——这是最容易踩坑的地方。",
        [
            table(
                ["模型", "J（明度）", "C（彩度）", "h（色相）", "M（色度）", "需要的观察条件"],
                rows,
                title="12 个外观模型对同一支颜色的输出",
                mono=[1, 2, 3, 4],
                widths=["110px", "80px", "80px", "80px", "80px", "auto"],
            ),
            kv(
                [
                    ("往返验证", f"CAM16 → XYZ 最大误差 {error:.2e}（0–1 域）", "逆变换必须闭合"),
                    ("观察条件常量", "VIEWING_CONDITIONS_CAM16 / CIECAM02 / HUNT / ZCAM / …（共 11 组）", "只含环绕因子，不含白点"),
                    ("色彩空间化", "CAM16-UCS / CAM02-UCS / LCD / SCD 版本", "把 JCh 变成可算 ΔE 的直角坐标"),
                    ("注意", "ZCAM 用 0–1 域，其余多数用 0–100 域", "传错域不会报错，只会静默偏差"),
                ],
                title="口径与陷阱",
            ),
            note(
                "外观模型不是「更准的 Lab」，而是「显式建模观察者状态」：同一 XYZ，在不同 L_A、不同环绕下会得到不同的 J/C/h。要比较两个颜色，先固定观察条件。",
                tone="info",
                title="为什么不能跨条件比 J",
            ),
        ],
        phase="M2",
        apis=["POST /api/v1/appearance"],
        controls=[
            {"label": "模型", "kind": "select", "value": "CAM16", "options": list({r[0] for r in rows})},
            {"label": "L_A（cd·m⁻²）", "kind": "select", "value": "64/π/5 ≈ 4.07", "options": ["4.07", "20", "100", "318.31"]},
            {"label": "环绕", "kind": "select", "value": "Average", "options": ["Average", "Dim", "Dark"]},
        ],
        footer="对应 API：`POST /api/v1/appearance`；依赖 `XYZ_to_CAM16 / CIECAM02 / CIECAM16 / Hellwig2022 / Hunt / RLAB / LLAB / ZCAM / Kim2009 / Nayatani95 / ATD95 / sCAM` 及对应逆变换。",
    )


# --------------------------------------------------------------------------- #
# 16 感知现象
# --------------------------------------------------------------------------- #
def panel_phenomena_vision() -> dict:
    fig_csf, ax_csf = new_axes((4.0, 2.2), dpi=110)
    u = np.linspace(0.5, 60, 80)
    for luminance, css in [(10, "#264653"), (100, "#3B82F6"), (1000, "#E76F51")]:
        values = []
        for freq in u:
            try:
                values.append(float(colour.contrast.contrast_sensitivity_function_Barten1999(freq, sigma=0.3, Y_0=luminance)))
            except Exception:
                values.append(np.nan)
        ax_csf.plot(u, values, color=css, lw=1.2, label=f"Y₀={luminance} cd·m⁻²")
    ax_csf.set_xlabel("空间频率 / cycles per degree", fontsize=7, color="#555A63")
    ax_csf.set_ylabel("对比敏感度 S", fontsize=7, color="#555A63")
    ax_csf.legend(fontsize=5.5, frameon=False)

    rows_vcc, rows_vac = [], []
    for lightness in [30, 50, 70, 90]:
        for chroma in [0, 20, 50, 80]:
            uv_c = np.array(colour.xy_to_UCS_uv(colour.XYZ_to_xy(XYZ_W)))
            uv = np.array(colour.xy_to_UCS_uv(colour.XYZ_to_xy(colour.sRGB_to_XYZ(hex_to_rgb(DEMO)))))
            try:
                vcc = float(colour.appearance.HelmholtzKohlrausch_effect_object_Nayatani1997(uv, uv_c, float(chroma), method="VCC"))
                vac = float(colour.appearance.HelmholtzKohlrausch_effect_object_Nayatani1997(uv, uv_c, float(chroma), method="VAC"))
                rows_vcc.append([f"{lightness} / {chroma}", f"{vcc:.4f}"])
                rows_vac.append([f"{lightness} / {chroma}", f"{vac:.4f}"])
            except Exception:
                continue

    fig, ax = new_axes((4.0, 2.3), dpi=110)
    uv_c = np.array(colour.xy_to_UCS_uv(colour.XYZ_to_xy(XYZ_W)))
    uv = np.array(colour.xy_to_UCS_uv(colour.XYZ_to_xy(colour.sRGB_to_XYZ(hex_to_rgb(DEMO)))))
    chromas = np.linspace(0, 120, 40)
    for method, css in [("VCC", "#3B82F6"), ("VAC", "#E76F51")]:
        values = []
        for chroma in chromas:
            try:
                values.append(float(colour.appearance.HelmholtzKohlrausch_effect_object_Nayatani1997(uv, uv_c, float(chroma), method=method)))
            except Exception:
                values.append(np.nan)
        ax.plot(chromas, values, color=css, lw=1.2, label=f"{method}")
    ax.set_xlabel("彩度 C", fontsize=7, color="#555A63")
    ax.set_ylabel("H-K 效应因子", fontsize=7, color="#555A63")
    ax.legend(fontsize=6, frameon=False)

    return panel(
        "phenomena-vision",
        "外观与感知",
        "16",
        "视觉模型与感知现象",
        "人眼不是仪器：饱和度更高的颜色会显得更亮（Helmholtz–Kohlrausch 效应），而「能不能看出差别」取决于对比敏感度函数。一个模块管感知效应，一个模块管视觉极限。",
        [
            image(fig, caption="H-K 效应：固定明度、改变彩度时的亮度增益（VCC / VAC 两种修正）", maxw="470px"),
            image(fig_csf, caption="Barten 1999 对比敏感度函数：不同亮度下的可见阈值", maxw="470px"),
            kv(
                [
                    ("视觉模型", "contrast_sensitivity_function_Barten1999 / optical_MTF_Barten1999", "MTF 与 CSF 组合出阈值"),
                    ("派生量", "pupil_diameter_Barten1999 / retinal_illuminance_Barten1999 / sigma_Barten1999", "瞳孔、视网膜照度、光晕"),
                    ("用途", "判断「ΔE=1 的差异在 3 米外还能不能看见」", "把色差换算成可读性"),
                ],
                title="对比敏感度",
            ),
            table(["明度 / 彩度", "H-K 因子（VCC）"], rows_vcc[:8], title="采样点（VCC）", mono=[0, 1], widths=["140px", "120px"]),
            kv(
                [
                    ("相关函数", "HelmholtzKohlrausch_effect_object_Nayatani1997 / _luminous_", "同样输入，object 与 luminous 两种口径"),
                    ("系数工具", "coefficient_K_Br_Nayatani1997 / coefficient_q_Nayatani1997", "把效应折算成亮度"),
                    ("注意", "0.4.7 的 phenomena 子模块是物理光学（薄膜、瑞利散射、Snell），感知现象在 appearance 里", "见面板 24"),
                ],
                title="口径",
            ),
        ],
        phase="M2",
        apis=["POST /api/v1/phenomena-vision"],
        footer="对应 API：`POST /api/v1/phenomena-vision`；依赖 `appearance.HelmholtzKohlrausch_effect_*` 与两个系数函数。",
    )


# --------------------------------------------------------------------------- #
# 17 对应色
# --------------------------------------------------------------------------- #
def panel_corresponding() -> dict:
    rows = []
    for model in ["Von Kries", "CIE 1994", "CMCCAT2000", "Fairchild 1990", "Zhai 2018"]:
        try:
            prediction = colour.corresponding.corresponding_chromaticities_prediction(experiment=1, model=model)[0]
            error = float(np.linalg.norm(np.asarray(prediction.uv_p) - np.asarray(prediction.uv_t)))
            rows.append([model, f"{error:.4f}"])
        except Exception as error:
            rows.append([model, f"不可用（{type(error).__name__}）"])

    fig, ax = new_axes((3.6, 2.6), dpi=110)
    try:
        prediction = colour.corresponding.corresponding_chromaticities_prediction(experiment=1, model="CMCCAT2000")[0]
        ax.scatter([prediction.uv_t[0]], [prediction.uv_t[1]], s=40, color="#3B82F6", label="实测目标")
        ax.scatter([prediction.uv_p[0]], [prediction.uv_p[1]], s=40, color="#E76F51", marker="x", label="模型预测")
        ax.scatter([prediction.uv_m[0]], [prediction.uv_m[1]], s=26, color="#8B9099", marker="s", label="测试色")
        ax.plot([prediction.uv_t[0], prediction.uv_p[0]], [prediction.uv_t[1], prediction.uv_p[1]], color="#C9C9C2", lw=0.8, ls="--")
        ax.annotate("", xy=(prediction.uv_t[0], prediction.uv_t[1]), xytext=(prediction.uv_p[0], prediction.uv_p[1]),
                    arrowprops=dict(arrowstyle="->", color="#8B9099", lw=0.8))
        ax.legend(fontsize=5.5, frameon=False)
        ax.set_xlabel("u′", fontsize=7, color="#555A63")
        ax.set_ylabel("v′", fontsize=7, color="#555A63")
    except Exception:
        pass

    return panel(
        "corresponding",
        "外观与感知",
        "17",
        "对应色与记忆色",
        "给你一个在 A 灯下的橙子色，要你在 D65 下选一个「看起来一样」的颜色——这就是对应色。Breneman 的经典实验提供了 12 组数据，5 个模型分别去拟合它们。",
        [
            image(fig, caption="Breneman 实验 1：实测目标 vs CMCCAT2000 预测（箭头是预测偏差）", maxw="420px"),
            table(["模型", "预测偏差（uv 距离）"], rows, title="五个模型的拟合偏差", mono=[1], widths=["170px", "150px"]),
            kv(
                [
                    ("实验数据", "BRENEMAN_EXPERIMENTS / CorrespondingColourDataset", "12 组实验，含观察者与参考白"),
                    ("模型方法", ", ".join(list(colour.corresponding.CORRESPONDING_CHROMATICITIES_PREDICTION_MODELS.keys())), "5 个模型"),
                    ("可视化", "plot_corresponding_chromaticities_prediction", "见面板 25"),
                ],
                title="数据与工具",
            ),
        ],
        phase="M2",
        apis=["POST /api/v1/corresponding"],
        footer="对应 API：`POST /api/v1/corresponding`；依赖 `corresponding_chromaticities_prediction` 的 5 个模型与 Breneman 数据集。",
    )


# --------------------------------------------------------------------------- #
# 18 色觉障碍
# --------------------------------------------------------------------------- #
CVD_TYPES = [
    ("Protanomaly", "红色盲 / 红色弱", "L 锥体响应衰减"),
    ("Deuteranomaly", "绿色盲 / 绿色弱", "M 锥体响应衰减"),
    ("Tritanomaly", "蓝色盲 / 蓝色弱", "S 锥体响应衰减"),
]
CVD_PALETTE = PALETTE + ["#3B82F6", "#8E44AD", "#111827"]
SEVERITIES = [0.0, 0.25, 0.5, 0.75, 1.0]


def apply_cvd(hexes: list[str], matrix_cat: np.ndarray) -> list[str]:
    out = []
    for hex_value in hexes:
        linear = colour.models.eotf_inverse_sRGB(hex_to_rgb(hex_value))
        out.append(rgb_to_hex(colour.models.eotf_sRGB(matrix_cat @ linear)))
    return out


def panel_cvd() -> dict:
    blocks = []
    warnings_seen: list[str] = []
    swatch_items = [(h, h, "原始") for h in CVD_PALETTE]
    rows = []
    for name, label, note_text in CVD_TYPES:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            matrix_full = colour.blindness.matrix_cvd_Machado2009(name, 1.0)
        for item in caught:
            message = " ".join(str(item.message).split())
            if message not in warnings_seen:
                warnings_seen.append(message)
        simulated = apply_cvd(CVD_PALETTE, np.asarray(matrix_full))
        simulated_labs = [colour.XYZ_to_Lab(colour.sRGB_to_XYZ(hex_to_rgb(h))) for h in simulated]
        original_labs = [colour.XYZ_to_Lab(colour.sRGB_to_XYZ(hex_to_rgb(h))) for h in CVD_PALETTE]
        mean = float(np.mean([float(colour.delta_E(a, b, method="CIE 2000")) for a, b in zip(original_labs, simulated_labs)]))
        adjacent = [
            float(colour.delta_E(simulated_labs[i], simulated_labs[i + 1], method="CIE 2000"))
            for i in range(len(simulated_labs) - 1)
        ]
        rows.append([label, name, f"{mean:.1f}", f"{min(adjacent):.1f}"])
        blocks.append(swatches([(h, f"#{i + 1}", "模拟") for i, h in enumerate(simulated)], title=f"{label}（severity=100%）", cols=8))

    matrices = []
    for severity in SEVERITIES:
        m = colour.blindness.matrix_cvd_Machado2009("Deuteranomaly", severity)
        matrices.append([f"{severity:.2f}", " · ".join(vec(row, 3) for row in np.asarray(m))])

    return panel(
        "cvd",
        "外观与感知",
        "18",
        "色觉障碍模拟",
        "约 8% 的男性有某种色觉障碍。Machado 2009 用一个与严重程度相关的矩阵，在线性 RGB 上模拟三类锥体的响应衰减——这是判断调色板、图表、UI 是否可用的硬指标。",
        [
            swatches(swatch_items, title="原始调色板（8 色）", cols=8),
            *blocks,
            table(["类型", "name", "原色 vs 模拟平均 ΔE", "模拟后相邻最小 ΔE"], rows, title="三种类型在 100% 严重度下的结论", mono=[1, 2, 3]),
            table(["严重度", "Deuteranomaly 矩阵（逐行）"], matrices, title="严重度 → 矩阵（线性插值即可连续调）", mono=[0, 1], widths=["70px", "auto"]),
            note(
                (warnings_seen[0] if warnings_seen else "无告警") + " —— 该告警由 colour 自身发出，UI 原样展示，避免把近似模型当精确结论。",
                tone="warn",
                title="colour 告警",
            ),
        ],
        phase="M2",
        apis=["POST /api/v1/cvd"],
        controls=[
            {"label": "类型", "kind": "select", "value": CVD_TYPES[0][1], "options": [c[1] for c in CVD_TYPES]},
            {"label": "严重程度", "kind": "range", "value": "100"},
        ],
        footer="对应 API：`POST /api/v1/cvd`；依赖 `blindness.matrix_cvd_Machado2009` / `matrix_anomalous_trichromacy_Machado2009` / `msds_cmfs_anomalous_trichromacy_Machado2009`。",
    )
