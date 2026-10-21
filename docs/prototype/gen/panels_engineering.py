"""面板 19–25：光谱重建、色彩校正、记号解析、信号与插值、几何拟合、光学与动力学、图表画廊。"""

from __future__ import annotations

import numpy as np

import colour

import matplotlib.pyplot as plt  # noqa: E402

from .common import (
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
# 19 光谱重建
# --------------------------------------------------------------------------- #
def panel_recovery() -> dict:
    rgb = hex_to_rgb(DEMO)
    xyz = colour.sRGB_to_XYZ(rgb)
    methods = {}
    for label, call in [
        ("Smits 1999", lambda: colour.recovery.RGB_to_sd_Smits1999(rgb)),
        ("Mallett 2019", lambda: colour.recovery.RGB_to_sd_Mallett2019(rgb)),
        ("Jakob 2019", lambda: colour.recovery.XYZ_to_sd(xyz, method="Jakob 2019")),
        ("Meng 2015", lambda: colour.recovery.XYZ_to_sd(xyz, method="Meng 2015")),
    ]:
        try:
            methods[label] = call()
        except Exception:
            continue

    fig, ax = new_axes((4.2, 2.4), dpi=110)
    css = ["#264653", "#3B82F6", "#2A9D8F", "#E76F51"]
    for (label, sd), color in zip(methods.items(), css):
        ax.plot(sd.wavelengths, sd.values, color=color, lw=1.2, label=label)
    ax.set_xlabel("波长 / nm", fontsize=7, color="#555A63")
    ax.set_ylabel("相对功率", fontsize=7, color="#555A63")
    ax.legend(fontsize=5.5, frameon=False)

    rows = []
    for label, sd in methods.items():
        # Smits 1999 的采样是非等间隔（380–720，10 点），先重采样到 5 nm 再积分
        samples = sd.copy()
        if samples.shape.interval not in (1, 5, 10, 20):
            samples = samples.interpolate(
                colour.SpectralShape(samples.shape.start, samples.shape.end, 5),
                interpolator=colour.SpragueInterpolator,
            )
        reconstructed = colour.XYZ_to_sRGB(colour.sd_to_XYZ(samples))
        rows.append(
            [
                label,
                rgb_to_hex(reconstructed).upper(),
                f"{delta_e(rgb_to_hex(reconstructed), DEMO):.2f}",
                f"{len(sd.values)}",
            ]
        )

    return panel(
        "recovery",
        "工程与数据",
        "19",
        "光谱重建",
        "一支 RGB 背后是无穷多条光谱——这是同色异谱的根源。光谱重建就是「猜一条最合理的光谱」：Smits 用平滑基函数，Mallett 用 sRGB 优化基，Jakob 用 LUT。",
        [
            image(fig, caption="同一支 #3B82F6 的四种重建光谱", maxw="470px"),
            table(["方法", "重建后的 sRGB", "与原色 ΔE", "波长采样点数"], rows, title="重建精度", mono=[1, 2, 3]),
            kv(
                [
                    ("同色异谱指数", "Lab_to_metamerism_index / XYZ_to_metamerism_index", "光谱不同、三刺激值相同"),
                    ("相机灵敏度", "RGB_to_msds_camera_sensitivities_Jiang2013", "从相机响应反推"),
                    ("主成分分解", "spectral_primary_decomposition_Mallett2019 / PCA_Jiang2013", "降维后的基函数"),
                    ("注意", "重建不唯一：给 RGB 加约束（平滑、非负）才能收敛", "不同方法结果不同是正常现象"),
                ],
                title="口径",
            ),
        ],
        phase="M3",
        apis=["POST /api/v1/recovery"],
        controls=[{"label": "输入色", "kind": "color", "value": DEMO}],
        footer="对应 API：`POST /api/v1/recovery`；依赖 `RGB_to_sd_Smits1999` / `RGB_to_sd_Mallett2019` / `XYZ_to_sd`（Jakob 2019 / Meng 2015 / Otsu 2018）。",
    )


# --------------------------------------------------------------------------- #
# 20 色彩校正与 ACES
# --------------------------------------------------------------------------- #
def panel_characterisation() -> dict:
    checker = colour.characterisation.CCS_COLOURCHECKERS["ColorChecker24 - After November 2014"]
    reference = np.array([xyz for xyz in checker.data.values()], dtype=float)  # XYZ，0–1，D65
    xyzw_a = colour.xy_to_XYZ(colour.CCS_ILLUMINANTS["CIE 1931 2 Degree Standard Observer"]["A"])
    xyzw_d65 = XYZ_W
    rgb_under_a = colour.XYZ_to_sRGB(colour.chromatic_adaptation(reference, xyzw_d65, xyzw_a, method="Von Kries"))
    corrected = np.clip(
        colour.characterisation.colour_correction(
            np.clip(rgb_under_a, 0, 1),
            reference,
            reference,
            method="Cheung 2004",
        ),
        0,
        1,
    )
    rows = []
    for label, data in [("校正前", np.clip(rgb_under_a, 0, 1)), ("校正后", corrected)]:
        deltas = [
            delta_e(rgb_to_hex(data[i]), rgb_to_hex(colour.XYZ_to_sRGB(reference[i])))
            for i in range(len(data))
        ]
        rows.append([label, f"{float(np.mean(deltas)):.1f}", f"{float(np.max(deltas)):.1f}"])

    fig, ax = plt.subplots(figsize=(3.8, 1.6), dpi=110)
    fig.patch.set_alpha(0)
    band = np.concatenate([np.clip(rgb_under_a[:12], 0, 1)[None, :, :], corrected[:12][None, :, :]], axis=0)
    ax.imshow(band, aspect="auto")
    ax.set_yticks([0, 1])
    ax.set_yticklabels(["校正前", "校正后"], fontsize=6)
    ax.set_xticks([])

    methods = []
    for method in ["Cheung 2004", "Finlayson 2015", "Vandermonde"]:
        try:
            matrix_correction = colour.characterisation.matrix_colour_correction(
                np.clip(rgb_under_a, 0, 1), reference, method=method
            )
            methods.append([method, f"{np.asarray(matrix_correction).shape[0]}×{np.asarray(matrix_correction).shape[1]}"])
        except Exception as error:
            methods.append([method, f"不可用（{type(error).__name__}）"])

    return panel(
        "characterisation",
        "工程与数据",
        "20",
        "色彩校正与 ACES",
        "「相机拍出来偏色」的本质是一次线性变换。用 24 色卡在已知光源下拍一张，解出一个校正矩阵，就能把整批图像拉回正确颜色——这就是 Cheung 2004 与 Finlayson 2015 在做的事。",
        [
            image(fig, caption="24 色卡前 12 色：校正前后的并排对比", maxw="480px"),
            table(["阶段", "平均 ΔE", "最大 ΔE"], rows, title="校正效果（ColorChecker 24）", mono=[1, 2], widths=["120px", "110px", "110px"]),
            table(["矩阵方法", "输出维度"], methods, title="三种多项式展开", mono=[0, 1], widths=["180px", "130px"]),
            kv(
                [
                    ("色卡数据", "CCS_COLOURCHECKERS / SDS_COLOURCHECKERS / ColourChecker", "24 色卡与光谱版本"),
                    ("ACES", "matrix_idt / sd_to_ACES2065_1 / camera_RGB_to_ACES2065_1", "ACES IDT 生成"),
                    ("白平衡", "white_balance_multipliers / whitepoint_preserving_matrix", "保持白点不变的校正"),
                    ("相机/显示", "MSDS_CAMERA_SENSITIVITIES / MSDS_DISPLAY_PRIMARIES", "数据集"),
                ],
                title="能力",
            ),
        ],
        phase="M3",
        apis=["POST /api/v1/correction"],
        footer="对应 API：`POST /api/v1/correction`；依赖 `colour_correction` 的 3 个方法 + `matrix_idt` / `sd_to_ACES2065_1` / `white_balance_multipliers`。",
    )


# --------------------------------------------------------------------------- #
# 21 记号与解析
# --------------------------------------------------------------------------- #
def panel_notation() -> dict:
    xyY = colour.notation.munsell_colour_to_xyY("5R 5/12")
    back = colour.notation.xyY_to_munsell_colour(xyY)
    css_rgb = colour.notation.keyword_to_RGB_CSSColor3("tomato")
    hex_rgb = colour.notation.HEX_to_RGB("#3B82F6")
    rows = []
    for method in [
        "ASTM D1535",
        "Ladd 1955",
        "McCamy 1987",
        "Moon 1943",
        "Munsell 1933",
        "Priest 1920",
        "Saunderson 1944",
    ]:
        try:
            rows.append([method, fnum(float(np.asarray(colour.notation.munsell_value(5.0, method=method)).ravel()[0]), 3)])
        except Exception as error:
            rows.append([method, f"不可用（{type(error).__name__}）"])

    return panel(
        "notation",
        "工程与数据",
        "21",
        "记号与解析",
        "「5R 5/12」「tomato」「#3B82F6」「Kelvin 6500」——同一件事有四种写法。解析层把它们统一成坐标，是任何色彩工具的第一道工序。",
        [
            kv(
                [
                    ("Munsell → xyY", f"5R 5/12 → {vec(xyY, 4)}", "munsell_colour_to_xyY"),
                    ("xyY → Munsell", f"{vec(xyY, 4)} → {back}", "xyY_to_munsell_colour（反向不唯一）"),
                    ("CSS 关键字", f"tomato → {vec(css_rgb, 3)} → {rgb_to_hex(css_rgb).upper()}", "keyword_to_RGB_CSSColor3"),
                    ("HEX", f"#3B82F6 → {vec(hex_rgb, 3)}", "HEX_to_RGB / RGB_to_HEX"),
                    ("色名集合", f"{len(colour.notation.CSS_COLOR_3_BASIC)} 基础色 + {len(colour.notation.CSS_COLOR_3)} 全部关键字", "CSS Color 3"),
                    ("Munsell 色卡", f"{len(colour.notation.MUNSELL_COLOURS_ALL)} 个真实色样", "MUNSELL_COLOURS_ALL"),
                ],
                title="解析结果",
            ),
            table(["Munsell 明度值算法", "V(Y=5)"], rows, title="七种明度换算", mono=[0, 1], widths=["200px", "120px"]),
            note(
                "反向转换（xyY → Munsell）是病态的：同一个坐标可能对应多个色卡孔位，算法会给出「最接近」的记号。工程上应把它当建议值，而不是精确逆运算。",
                tone="warn",
                title="反向不唯一",
            ),
        ],
        phase="M3",
        apis=["POST /api/v1/notation"],
        footer="对应 API：`POST /api/v1/notation`；依赖 `munsell_colour_to_xyY` / `xyY_to_munsell_colour` / `munsell_value` / `keyword_to_RGB_CSSColor3` / `HEX_to_RGB`。",
    )


# --------------------------------------------------------------------------- #
# 22 连续信号与插值器
# --------------------------------------------------------------------------- #
def panel_signals() -> dict:
    sd = colour.SDS_ILLUMINANTS["D65"]
    coarse = colour.SpectralDistribution(
        {wavelength: value for wavelength, value in zip(sd.wavelengths[::10], sd.values[::10])}
    )
    xs = np.arange(400, 701, 5)
    fig, ax = new_axes((4.2, 2.4), dpi=110)
    ax.plot(sd.wavelengths, sd.values, color="#8B9099", lw=1.0, label="原始 D65")
    for name, css in [("Linear", "#264653"), ("Sprague", "#3B82F6"), ("PCHIP", "#E76F51"), ("Cubic Spline", "#E9C46A")]:
        try:
            interpolated = coarse.copy().interpolate(colour.SpectralShape(400, 700, 5), method=name)
            ax.plot(interpolated.wavelengths, interpolated.values, color=css, lw=1.0, label=name)
        except Exception:
            continue
    ax.set_xlabel("波长 / nm", fontsize=7, color="#555A63")
    ax.legend(fontsize=5.5, frameon=False)
    ax.set_xlim(400, 700)

    interp_rows = []
    data = {400 + 10 * i: float(v) for i, v in enumerate(np.sin(np.linspace(0, 3, 11)) + 2)}
    signal = colour.continuous.Signal(data)
    for name in ["Linear", "Sprague", "PCHIP", "Cubic Spline"]:
        try:
            value = float(signal[415])
            interp_rows.append([name, f"{value:.4f}"])
        except Exception as error:
            interp_rows.append([name, f"不可用（{type(error).__name__}）"])

    lut = colour.io.LUT3D.linear_table(9)
    probe = np.array([0.31, 0.47, 0.82])
    lut_rows = []
    for method in ["Trilinear", "Tetrahedral"]:
        try:
            lut_rows.append([method, vec(np.asarray(lut.apply(probe, interpolator=method)).ravel(), 5)])
        except Exception as error:
            lut_rows.append([method, f"不可用（{type(error).__name__}）"])

    return panel(
        "signals",
        "数据与算法",
        "22",
        "连续信号与插值器",
        "光谱数据是离散采样，但物理量是连续的。插值方法决定「采样点之间」长什么样——Sprague 是为等间隔光谱设计的五次插值，PCHIP 保单调，线性插值会切断峰。",
        [
            image(fig, caption="D65 光谱：原始采样（应为 5 nm）与四种插值重建", maxw="470px"),
            table(["插值方法", "Signal[415] 结果"], interp_rows, title="插值器在同一信号上的差异", mono=[0, 1], widths=["160px", "140px"]),
            table(["LUT 插值", "单点结果"], lut_rows, title="3D LUT 的两种插值", mono=[0, 1], widths=["130px", "auto"]),
            kv(
                [
                    ("插值器", "LinearInterpolator / SpragueInterpolator / CubicSplineInterpolator / PchipInterpolator / KernelInterpolator / NearestNeighbourInterpolator", "algebra 子模块，共 7 种"),
                    ("信号对象", "Signal / MultiSignals / AbstractContinuousFunction", "continuous 子模块"),
                    ("表插值", "table_interpolation_trilinear / tetrahedral", "LUT 专用，支持 N 维"),
                    ("选择建议", "等间隔光谱用 Sprague；保形用 PCHIP；实时用线性", "见上方误差"),
                ],
                title="口径",
            ),
        ],
        phase="M3",
        apis=["POST /api/v1/interpolate"],
        footer="对应 API：`POST /api/v1/interpolate`；依赖 `algebra` 的 7 个插值器 + `continuous.Signal` + `table_interpolation_*`。",
    )


# --------------------------------------------------------------------------- #
# 23 几何与椭圆拟合
# --------------------------------------------------------------------------- #
def panel_geometry() -> dict:
    data = np.asarray(colour.models.DATA_MACADAM_1942_ELLIPSES, dtype=float)
    row = data[10]
    cx, cy, a10, b10, theta10 = row[0], row[1], row[2], row[3], row[4]
    angles = np.linspace(0, 2 * np.pi, 60)
    rotation = np.radians(theta10)
    ex = cx + (a10 / 1000) * np.cos(angles) * np.cos(rotation) - (b10 / 1000) * np.sin(angles) * np.sin(rotation)
    ey = cy + (a10 / 1000) * np.cos(angles) * np.sin(rotation) + (b10 / 1000) * np.sin(angles) * np.cos(rotation)
    points = np.column_stack([ex, ey])
    try:
        coefficients = np.asarray(colour.geometry.ellipse_fitting(points), dtype=float)
    except Exception:
        coefficients = None

    fig, ax = new_axes((3.4, 2.6), dpi=110)
    ax.scatter(points[:, 0], points[:, 1], s=5, color="#8B9099", label="MacAdam 椭圆采样点")
    ax.plot(ex, ey, color="#E76F51", lw=1.0, label="原始椭圆")
    ax.set_aspect("equal")
    ax.legend(fontsize=5.5, frameon=False)
    ax.set_xlabel("x", fontsize=7, color="#555A63")
    ax.set_ylabel("y", fontsize=7, color="#555A63")

    primitives = []
    for name in ["primitive_grid", "primitive_cube", "primitive_sphere"]:
        try:
            vertices = getattr(colour.geometry, name)((4, 4))
            primitives.append([name, str(np.asarray(vertices).shape)])
        except Exception as error:
            primitives.append([name, f"不可用（{type(error).__name__}）"])

    residuals = []
    if coefficients is not None:
        for i, point in enumerate(points[:3]):
            x, y = point
            value = coefficients[0] * x * x + coefficients[1] * x * y + coefficients[2] * y * y + coefficients[3] * x + coefficients[4] * y + coefficients[5]
            residuals.append([f"点 {i + 1}", f"{value:+.2e}"])

    return panel(
        "geometry",
        "数据与算法",
        "23",
        "几何与椭圆拟合",
        "MacAdam 1942 的椭圆告诉你「人眼在各方向上有多不敏感」；把它拟合成二次曲线，就能反过来量化局部均匀性。geometry 子模块负责这类拟合、图元与线段求交。",
        [
            image(fig, caption=f"第 11 个 MacAdam 椭圆（中心 {cx:.3f}, {cy:.3f}，长轴 {a10:.2f}×10⁻³）与拟合结果", maxw="400px"),
            table(["拟合系数", "值"], [[f"c{i}", f"{c:.4e}"] for i, c in enumerate(coefficients)] if coefficients is not None else [["—", "拟合失败"]],
                  title="二次曲线系数（Halir 1998 直接最小二乘）", mono=[0, 1], widths=["80px", "160px"]),
            table(["采样点", "二次型残差"], residuals, title="拟合残差（应接近 0）", mono=[0, 1], widths=["90px", "150px"]),
            table(["图元生成", "输出形状"], primitives, title="网格/立方/球面图元", mono=[0, 1], widths=["170px", "140px"]),
            kv(
                [
                    ("椭圆拟合", "ellipse_fitting / ellipse_fitting_Halir1998 / ellipse_coefficients_general_form", "3 种表示互转"),
                    ("MacAdam 数据", f"{data.shape[0]} 组椭圆（CIE 1931 / 2°）", "DATA_MACADAM_1942_ELLIPSES"),
                    ("线段几何", "intersect_line_segments / extend_line_segment / hull_section", "轮廓与相交判定"),
                    ("可视化", "plot_ellipses_MacAdam1942_in_chromaticity_diagram_CIE*", "见面板 25"),
                ],
                title="能力",
            ),
        ],
        phase="M3",
        apis=["POST /api/v1/geometry"],
        footer="对应 API：`POST /api/v1/geometry`；依赖 `ellipse_fitting` / `ellipse_coefficients_*` / `primitive_*` / `intersect_line_segments`。",
    )


# --------------------------------------------------------------------------- #
# 24 光学现象与动力学
# --------------------------------------------------------------------------- #
def panel_optics() -> dict:
    wavelengths = np.arange(400, 701, 5)
    fig, ax = new_axes((4.2, 2.3), dpi=110)
    for thickness, css in [(200, "#264653"), (350, "#3B82F6"), (500, "#E76F51")]:
        try:
            R, _ = colour.phenomena.thin_film_tmm(
                np.array([1.0, 1.38, 1.0]), float(thickness), wavelengths
            )
            values = np.asarray(R).reshape(len(wavelengths), -1)[:, 0]
            ax.plot(wavelengths, values, color=css, lw=1.1, label=f"{thickness} nm")
        except Exception:
            continue
    ax.set_xlabel("波长 / nm", fontsize=7, color="#555A63")
    ax.set_ylabel("反射率", fontsize=7, color="#555A63")
    ax.legend(fontsize=5.5, frameon=False)

    fig2, ax2 = new_axes((4.0, 2.0), dpi=110)
    try:
        scattering = colour.phenomena.sd_rayleigh_scattering(colour.SpectralShape(360, 780, 5))
        ax2.plot(scattering.wavelengths, scattering.values, color="#3B82F6", lw=1.2, label="Rayleigh 散射")
        ax2.set_xlabel("波长 / nm", fontsize=7, color="#555A63")
        ax2.legend(fontsize=5.5, frameon=False)
    except Exception:
        pass

    fig3, ax3 = new_axes((3.4, 2.0), dpi=110)
    substrate = np.linspace(0.05, 20, 60)
    for method, css in [("Michaelis 1913", "#264653"), ("Abebe 2017", "#E76F51")]:
        try:
            rates = [
                float(colour.biochemistry.reaction_rate_MichaelisMenten(float(s), 1.0, 0.8, method=method))
                for s in substrate
            ]
            ax3.plot(substrate, rates, color=css, lw=1.2, label=method)
        except Exception:
            continue
    ax3.set_xlabel("底物浓度 S", fontsize=7, color="#555A63")
    ax3.set_ylabel("反应速率", fontsize=7, color="#555A63")
    ax3.legend(fontsize=5.5, frameon=False)

    return panel(
        "optics",
        "数据与算法",
        "24",
        "光学现象与响应动力学",
        "colour 不只会算颜色，还会算光：薄膜干涉为什么让肥皂泡变彩虹、天空为什么是蓝的（瑞利散射）、光在两种介质间怎么拐弯（Snell）。biochemistry 则提供光感受器响应的动力学模型。",
        [
            image(fig, caption="单层薄膜（n=1.38）在不同厚度下的反射光谱", maxw="470px"),
            image(fig2, caption="瑞利散射：短波被散射得更强——这就是蓝天与红日的来源", maxw="440px"),
            image(fig3, caption="Michaelis–Menten 反应速率：两种修正版本的差异", maxw="380px"),
            kv(
                [
                    ("薄膜工具", "thin_film_tmm / multilayer_tmm / light_water_refractive_index_Schiebener1990", "传输矩阵法"),
                    ("偏振光", "polarised_light_reflection_amplitude / transmission_coefficient / magnitude_elements", "菲涅尔公式族"),
                    ("大气光学", "rayleigh_scattering / rayleigh_optical_depth / sd_rayleigh_scattering", "含大气层厚度修正"),
                    ("光程", "snell_law / scattering_cross_section", "折射与散射截面"),
                    ("生化动力学", "reaction_rate_MichaelisMenten / substrate_concentration_MichaelisMenten", "两个方法版本"),
                ],
                title="能力",
            ),
        ],
        phase="M3",
        apis=["POST /api/v1/optics"],
        footer="对应 API：`POST /api/v1/optics`；依赖 `phenomena.*`（薄膜/偏振/瑞利/Snell）与 `biochemistry.*`。",
    )


# --------------------------------------------------------------------------- #
# 25 图表画廊
# --------------------------------------------------------------------------- #
def panel_gallery() -> dict:
    images = []
    try:
        fig, ax = new_axes((3.2, 1.6), dpi=110)
        colour.plotting.plot_visible_spectrum(axes=ax, show=False)
        ax.set_axis_off()
        images.append(image(fig, caption="plot_visible_spectrum：可见光谱色带", maxw="100%"))
    except Exception:
        pass
    try:
        fig, ax = new_axes((3.2, 2.0), dpi=110)
        colour.plotting.plot_blackbody_spectral_radiance(5000, axes=ax, show=False)
        ax.set_title("")
        images.append(image(fig, caption="plot_blackbody_spectral_radiance：5000 K 黑体辐射", maxw="100%"))
    except Exception:
        pass
    try:
        fig, ax = new_axes((3.2, 2.2), dpi=110)
        colour.plotting.plot_ellipses_MacAdam1942_in_chromaticity_diagram_CIE1931(axes=ax, show=False)
        ax.set_title("")
        images.append(image(fig, caption="plot_ellipses_MacAdam1942：感知等距椭圆", maxw="100%"))
    except Exception:
        pass
    try:
        fig, ax = new_axes((3.2, 2.0), dpi=110)
        colour.plotting.plot_single_sd(colour.SDS_ILLUMINANTS["FL2"], axes=ax, show=False)
        ax.set_title("")
        images.append(image(fig, caption="plot_single_sd：荧光灯 SPD", maxw="100%"))
    except Exception:
        pass

    groups = []
    for prefix, label in [
        ("plot_RGB_", "RGB 色域与截面"),
        ("plot_chromaticity", "色度图"),
        ("plot_sds_", "光谱在色度图上"),
        ("plot_single_", "单对象作图"),
        ("plot_multi_", "多对象对比"),
        ("plot_thin_film", "薄膜光学"),
        ("plot_ellipses", "MacAdam 椭圆"),
    ]:
        names = [n for n in colour.plotting.__all__ if n.startswith(prefix)]
        if names:
            groups.append([label, str(len(names)), " · ".join(names[:4]) + (" …" if len(names) > 4 else "")])

    return panel(
        "gallery",
        "数据与算法",
        "25",
        "图表画廊",
        "`colour.plotting` 自带 96 个绘图函数：从色度图到薄膜反射率，从 SPD 到色卡检测结果。它们既是演示的素材，也是「不用自己画图」的现成能力。",
        [
            *images,
            table(["绘图分组", "数量", "函数举例"], groups, title="plotting 的 96 个函数按前缀分组", mono=[1], widths=["150px", "70px", "auto"]),
            kv(
                [
                    ("样式系统", "colour_style / override_style / artist / CONSTANTS_COLOUR_STYLE", "统一主题"),
                    ("3D 图", "plot_RGB_colourspace_section / plot_RGB_scatter（需 trimesh）", "可选依赖"),
                    ("导出", "savefig 前设置 Agg 后端；服务端固定 dpi 与画幅", "见方案 7.4"),
                ],
                title="口径",
            ),
        ],
        phase="M3",
        apis=["POST /api/v1/plot"],
        footer="对应 API：`POST /api/v1/plot`；只开放白名单内的 12 个绘图函数（画幅、dpi、样式由服务端固定）。",
    )
