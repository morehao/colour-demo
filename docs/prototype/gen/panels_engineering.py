"""面板 19–25：光谱重建、色彩校正、记号解析、信号与插值、几何拟合、光学与动力学、图表画廊。"""

from __future__ import annotations

import gc
import warnings

import numpy as np

import colour

import matplotlib.pyplot as plt  # noqa: E402

from colour.algebra import (  # noqa: E402
    CubicSplineInterpolator,
    LinearInterpolator,
    PchipInterpolator,
    SpragueInterpolator,
    table_interpolation_tetrahedral,
    table_interpolation_trilinear,
)

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
    strip,
    strips,
    swatches,
    table,
    vec,
)

D65 = colour.CCS_ILLUMINANTS["CIE 1931 2 Degree Standard Observer"]["D65"]
XYZ_W = colour.xy_to_XYZ(D65)
D65_SD = colour.SDS_ILLUMINANTS["D65"]
PALETTE = ["#264653", "#2A9D8F", "#E9C46A", "#F4A261", "#E76F51"]
CURVE_CSS = ["#264653", "#3B82F6", "#2A9D8F", "#E76F51", "#8E44AD"]
DEMO = "#3B82F6"


# --------------------------------------------------------------------------- #
# 19 光谱重建
# --------------------------------------------------------------------------- #
def panel_recovery() -> dict:
    encoded = hex_to_rgb(DEMO)
    # Smits 1999 / Mallett 2019 的入参是**线性** RGB（见 colour 文档示例：
    # XYZ_to_sRGB(XYZ, apply_cctf_encoding=False)），传编码值会把结果算偏。
    linear = colour.cctf_decoding(encoded)
    xyz = colour.sRGB_to_XYZ(encoded)
    methods = {}
    for label, call in [
        ("Smits 1999", lambda: colour.recovery.RGB_to_sd_Smits1999(linear)),
        ("Mallett 2019", lambda: colour.recovery.RGB_to_sd_Mallett2019(linear)),
        ("Jakob 2019", lambda: colour.recovery.XYZ_to_sd(xyz, method="Jakob 2019")),
        ("Meng 2015", lambda: colour.recovery.XYZ_to_sd(xyz, method="Meng 2015")),
    ]:
        try:
            methods[label] = call()
        except Exception:
            continue

    rows = []
    curves = []
    for label, sd in methods.items():
        # 重建结果按**反射率**处理：在 D65 下积分回 XYZ，才是可比的 sRGB。
        # 直接 sd_to_XYZ(sd) 会得到 0–100 的自发光标度，XYZ_to_sRGB 会把它裁成白色。
        samples = sd.copy()
        # Smits 1999 采样非等间隔（380–720），ASTM E308 只接受 1/5/10/20 nm，先重采样
        if samples.shape.interval not in (1, 5, 10, 20):
            samples = samples.interpolate(
                colour.SpectralShape(samples.shape.start, samples.shape.end, 5),
                interpolator=colour.SpragueInterpolator,
            )
        xyz_back = colour.sd_to_XYZ(samples, illuminant=D65_SD) / 100
        reconstructed = np.clip(colour.XYZ_to_sRGB(xyz_back), 0, 1)
        hex_back = rgb_to_hex(reconstructed).upper()
        rows.append(
            [
                label,
                hex_back,
                f"{delta_e(hex_back, DEMO):.2f}",
                f"{len(sd.values)}",
            ]
        )
        curves.append(
            series(
                label,
                sd.wavelengths,
                sd.values,
                color=CURVE_CSS[len(curves) % len(CURVE_CSS)],
            )
        )

    return panel(
        "recovery",
        "工程与数据",
        "19",
        "光谱重建",
        "一支 RGB 背后是无穷多条光谱——这是同色异谱的根源。光谱重建就是「猜一条最合理的光谱」：Smits 用平滑基函数，Mallett 用 sRGB 优化基，Jakob 用 LUT。",
        [
            chart(
                curves,
                xlabel="波长 / nm",
                ylabel="反射率",
                title="四种方法的重建光谱",
                caption=f"同一支 {DEMO} 的重建反射率曲线：形状各不相同，但在 D65 下积分回三刺激值后应当一致——这正是同色异谱。曲线由后端计算，前端 SVG 绘制。",
                height=250,
                zero=True,
            ),
            table(["方法", "重建后的 sRGB", "与原色 ΔE", "波长采样点数"], rows, title="重建精度", mono=[1, 2, 3]),
            note(
                "重建曲线 → 三刺激值的口径：把 SD 当作反射率，在 CIE 1931 2° 观察者 + D65 光源下积分，"
                "再除以 100 转到 0–1 量纲后转 sRGB。Mallett 2019 / Jakob 2019 / Meng 2015 由基函数/优化构造，"
                "ΔE 精确为 0.00；Smits 1999 用平滑分段基函数，蓝端超出其覆盖范围，因此留有约 1 个 ΔE 的残差——这是方法本身的局限，不是实现误差。",
                tone="info",
                title="口径与误差来源",
            ),
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
    # 真值（D65 下的理想 sRGB）与「在 A 光源下拍到的偏色版本」
    ideal = np.clip(colour.XYZ_to_sRGB(reference), 0, 1)
    captured = np.clip(
        colour.XYZ_to_sRGB(colour.chromatic_adaptation(reference, xyzw_d65, xyzw_a, method="Von Kries")),
        0,
        1,
    )

    def deltas(data) -> tuple[float, float]:
        values = [delta_e(rgb_to_hex(data[i]), rgb_to_hex(ideal[i])) for i in range(len(data))]
        return float(np.mean(values)), float(np.max(values))

    before_mean, before_max = deltas(captured)
    rows = [["校正前（A 光源下拍摄）", f"{before_mean:.2f}", f"{before_max:.2f}"]]
    corrected: dict[str, np.ndarray] = {}
    # Finlayson 2015 默认 degree=1，与 Cheung 2004 的 3 项展开等价、结果完全相同；
    # 用 3 阶展开才能体现该方法「靠更高次项降残差」的差异。
    correction_specs = [
        ("Cheung 2004", {"method": "Cheung 2004"}),
        ("Finlayson 2015 · 3 阶", {"method": "Finlayson 2015", "degree": 3}),
        ("Vandermonde", {"method": "Vandermonde"}),
    ]
    for label, spec in correction_specs:
        # colour_correction(RGB, M_T, M_R)：M_T=实测、M_R=参考真值；两边都传 reference 会退化成恒等变换
        data = np.clip(colour.characterisation.colour_correction(captured, captured, ideal, **spec), 0, 1)
        corrected[label] = data
        mean, peak = deltas(data)
        rows.append([f"校正后（{label}）", f"{mean:.2f}", f"{peak:.2f}"])

    methods = []
    for label, spec in correction_specs:
        try:
            matrix_correction = np.asarray(colour.characterisation.matrix_colour_correction(captured, ideal, **spec))
            methods.append(
                [label, f"{matrix_correction.shape[0]}×{matrix_correction.shape[1]}", "RGB → XYZ 的线性映射"]
            )
        except Exception as error:
            methods.append([label, f"不可用（{type(error).__name__}）", "—"])

    cheung = corrected["Cheung 2004"]
    cheung_mean, cheung_max = deltas(cheung)
    best_label = min(corrected, key=lambda k: deltas(corrected[k])[0])
    best_mean = deltas(corrected[best_label])[0]
    return panel(
        "characterisation",
        "工程与数据",
        "20",
        "色彩校正与 ACES",
        "「相机拍出来偏色」的本质是一次线性变换。用 24 色卡在已知光源下拍一张，解出一个校正矩阵，就能把整批图像拉回正确颜色——这就是 Cheung 2004 与 Finlayson 2015 在做的事。",
        [
            strips(
                [
                    strip(
                        "校正前",
                        "模拟在 A 光源（2856 K）下拍摄，色卡整体偏黄",
                        [rgb_to_hex(captured[i]) for i in range(12)],
                        [("平均 ΔE", f"{before_mean:.2f}"), ("最大 ΔE", f"{before_max:.2f}")],
                    ),
                    strip(
                        "校正后",
                        "Cheung 2004 多项式校正，拉回 D65 真值",
                        [rgb_to_hex(cheung[i]) for i in range(12)],
                        [("平均 ΔE", f"{cheung_mean:.2f}"), ("最大 ΔE", f"{cheung_max:.2f}")],
                    ),
                ],
                title="24 色卡前 12 色：校正前后",
                caption="色块为真实计算结果（sRGB），非示意色；ΔE 以 ΔE*ab 计，基准是色卡在 D65 下的真实值。",
            ),
            table(["阶段", "平均 ΔE", "最大 ΔE"], rows, title="校正效果（ColorChecker 24）", mono=[1, 2], widths=["190px", "110px", "110px"]),
            table(["矩阵方法", "输出维度", "说明"], methods, title="三种多项式展开", mono=[0, 1], widths=["160px", "110px", "220px"]),
            note(
                f"口径：把「在 A 光源下拍摄」建模为 D65 参考色经 Von Kries 色适应到 A 再转 sRGB，"
                f"平均 ΔE 从 {before_mean:.2f} 降到 {cheung_mean:.2f}（Cheung 2004）；"
                f"本组参数下最优是 {best_label}，平均 ΔE {best_mean:.2f}。"
                "多项式校正只能把偏色拉回、无法归零：残差来自色卡的非线性响应与色适应模型的差异，这是方法本身的局限。"
                "另外 Finlayson 2015 默认 degree=1 与 Cheung 2004 的 3 项展开数学等价，会给出完全相同的数字，故这里取 3 阶以便区分。",
                tone="info",
                title="口径与误差来源",
            ),
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
                    ("色名集合", f"{len(colour.notation.CSS_COLOR_3)} 个关键字（含 {len(colour.notation.CSS_COLOR_3_BASIC)} 基础色、{len(colour.notation.CSS_COLOR_3_EXTENDED)} 扩展色）", "CSS Color 3"),
                    ("Munsell 色卡", f"{len(colour.notation.MUNSELL_COLOURS_ALL)} 个色样（REAL {len(colour.notation.MUNSELL_COLOURS_REAL)} / 1929 {len(colour.notation.MUNSELL_COLOURS_1929)}）", "MUNSELL_COLOURS_ALL"),
                ],
                title="解析结果",
            ),
            swatches(
                [
                    # CSS_COLOR_3_BASIC 存的是十六进制字符串，这里走一遍 keyword_to_RGB_CSSColor3 实算再转回 HEX
                    (
                        rgb_to_hex(colour.notation.keyword_to_RGB_CSSColor3(name)).upper(),
                        name,
                        f"表内 {hex_value.upper()}",
                    )
                    for name, hex_value in colour.notation.CSS_COLOR_3_BASIC.items()
                ],
                title="CSS Color 3 的 16 个基础色名（keyword_to_RGB_CSSColor3 实算）",
                cols=8,
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
    # FL11 有汞灯的尖锐谱线（435.8/546.1/611.6 nm），最适合暴露插值差异；
    # 换用 D65 会失效：D65 的 5 nm 表在 10 nm 节点之间本身就是线性的，线性插值必然「零误差」。
    truth = colour.SDS_ILLUMINANTS["FL11"].copy().align(colour.SpectralShape(400, 700, 5))
    coarse = colour.SpectralDistribution({w: truth[w] for w in truth.wavelengths[::4]})  # 每 4 点取样 = 20 nm
    specs = [
        ("Linear", LinearInterpolator, "#264653"),
        ("Sprague", SpragueInterpolator, "#3B82F6"),
        ("PCHIP", PchipInterpolator, "#E76F51"),
        ("Cubic Spline", CubicSplineInterpolator, "#E9C46A"),
    ]
    curves = [
        series("真实 FL11（5 nm）", truth.wavelengths, truth.values, color="#8B9099", dashed=True),
        series("20 nm 原始采样", coarse.wavelengths, coarse.values, color="#C2410C", mode="scatter"),
    ]
    interp_rows = []
    residual_curves = []
    for name, cls, css in specs:
        fine = coarse.copy().interpolate(colour.SpectralShape(400, 700, 5), interpolator=cls)
        values = np.asarray(fine.values)
        target = np.asarray(truth.values)
        error = np.abs(values - target)
        curves.append(series(name, fine.wavelengths, values, color=css))
        residual_curves.append(series(name, fine.wavelengths, values - target, color=css))
        interp_rows.append(
            [name, f"{error.max():.2f}", f"{error.mean():.2f}", f"{int((values < 0).sum())}"]
        )

    # 3D LUT：恒等表（linear_table）上两种插值必然完全相同，必须用非线性的合成表才能看出差异
    grid = np.linspace(0, 1, 9)
    matrix = np.array([[0.82, 0.18, 0.04], [0.12, 0.86, 0.09], [0.06, 0.14, 0.90]])
    table_lut = np.empty((9, 9, 9, 3))
    for i, a in enumerate(grid):
        for j, b in enumerate(grid):
            for k, c in enumerate(grid):
                table_lut[i, j, k] = np.clip(matrix @ np.array([a, b, c]), 0, 1) ** 2.2
    probe = np.array([0.31, 0.47, 0.82])
    probes = np.random.default_rng(7).random((200, 3))
    trilinear = np.array([table_interpolation_trilinear(p, table_lut) for p in probes])
    tetrahedral = np.array([table_interpolation_tetrahedral(p, table_lut) for p in probes])
    gap = np.abs(trilinear - tetrahedral).max(axis=1) * 255
    lut_rows = [
        [
            "Trilinear",
            vec(table_interpolation_trilinear(probe, table_lut), 4),
            f"{gap.max():.2f}（本行 vs 下行，200 随机点最大）",
        ],
        [
            "Tetrahedral",
            vec(table_interpolation_tetrahedral(probe, table_lut), 4),
            f"平均差 {gap.mean():.2f} /255",
        ],
    ]

    return panel(
        "signals",
        "数据与算法",
        "22",
        "连续信号与插值器",
        "光谱数据是离散采样，但物理量是连续的。插值方法决定「采样点之间」长什么样——Sprague 是为等间隔光谱设计的五次插值，PCHIP 保单调，线性插值会切断峰。",
        [
            chart(
                curves,
                xlabel="波长 / nm",
                ylabel="相对功率",
                title="FL11 光谱：20 nm 采样 → 5 nm 重建",
                caption="灰色虚线是真实 FL11（5 nm），橙点为丢掉的 20 nm 采样点，四条曲线是各插值器的重建结果。汞灯谱线被 20 nm 采样漏掉后，任何插值都补不回来——这是采样定理的问题，不是插值器的问题。",
                height=270,
            ),
            chart(
                residual_curves,
                xlabel="波长 / nm",
                ylabel="误差（相对功率）",
                title="重建误差（各方法 − 真实 FL11）",
                caption="残差最负处正是 435.8 / 546.1 / 611.6 nm 三条汞灯谱线——20 nm 采样把峰整个漏掉，任何插值都补不回来。注意区分两个量：这里是「重建值 − 真值」；表格里的负值点数是「重建值本身 < 0」，即过冲到物理上不可能的负功率。",
                height=230,
                zero=True,
            ),
            table(
                ["插值方法", "最大绝对误差", "平均绝对误差", "负值点数"],
                interp_rows,
                title="重建误差（基准：真实 FL11 5 nm 采样）",
                mono=[1, 2, 3],
                widths=["160px", "130px", "130px", "110px"],
                note="负值点数 = 重建后小于 0 的采样点数。Sprague 与 Cubic Spline 在尖峰两侧会过冲（Gibbs 现象），给出物理上不可能的负功率；PCHIP 保单调、Linear 不会越界，但都把峰削平了。",
            ),
            table(
                ["LUT 插值", "结果 @ (0.31, 0.47, 0.82)", "与另一方法差异"],
                lut_rows,
                title="3D LUT 的两种插值（9³ 合成表：通道混合 + gamma 2.2）",
                mono=[0, 1],
                widths=["130px", "200px", "auto"],
                note="两种插值只在表本身非线性且跨通道时才有差异；对恒等表（LUT3D.linear_table）二者结果完全一致。",
            ),
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
    row = data[10]  # 列序：u, v, a, b, theta_a, a_sd, b_sd, theta_sd
    cx, cy, a_raw, b_raw, theta_raw = row[0], row[1], row[2], row[3], row[4]
    angles = np.linspace(0, 2 * np.pi, 60)
    rotation = np.radians(theta_raw)
    ex = cx + (a_raw / 1000) * np.cos(angles) * np.cos(rotation) - (b_raw / 1000) * np.sin(angles) * np.sin(rotation)
    ey = cy + (a_raw / 1000) * np.cos(angles) * np.sin(rotation) + (b_raw / 1000) * np.sin(angles) * np.cos(rotation)
    points = np.column_stack([ex, ey])

    # ellipse_fitting 内部走广义特征值分解，返回 dtype 是 complex128（虚部恒为 0），必须取 .real，
    # 否则会抛 numpy ComplexWarning。
    coefficients = np.asarray(colour.geometry.ellipse_fitting(points)).real
    x0, y0, fit_a, fit_b, fit_theta = np.asarray(
        colour.geometry.ellipse_coefficients_canonical_form(coefficients)
    ).real

    fit_rotation = np.radians(float(fit_theta))
    fx = x0 + fit_a * np.cos(angles) * np.cos(fit_rotation) - fit_b * np.sin(angles) * np.sin(fit_rotation)
    fy = y0 + fit_a * np.cos(angles) * np.sin(fit_rotation) + fit_b * np.sin(angles) * np.cos(fit_rotation)

    zoom_curves = [
        series("原始可辨椭圆", ex, ey, color="#E76F51"),
        series("拟合结果（Halir 1998）", fx, fy, color="#2A9D8F", dashed=True),
        series("60 个采样点", points[:, 0], points[:, 1], color="#8B9099", mode="scatter"),
    ]

    # 拟合把「采样点 → 二次曲线 → 标准形」倒推回原始参数
    compare = [
        ["中心 (x₀, y₀)", f"({cx:.4f}, {cy:.4f})", f"({x0:.4f}, {y0:.4f})", "完全一致"],
        ["半轴 1", f"{a_raw / 1000:.6f}", f"{fit_b:.6f}", "轴序互换"],
        ["半轴 2", f"{b_raw / 1000:.6f}", f"{fit_a:.6f}", "轴序互换"],
        ["旋转角 θ", f"{theta_raw:.2f}°", f"{float(fit_theta):.2f}°", f"差 {theta_raw - float(fit_theta):.2f}°（约 90°，表示约定差异）"],
    ]

    residuals = []
    for i, point in enumerate(points[:3]):
        x, y = point
        value = (
            coefficients[0] * x * x
            + coefficients[1] * x * y
            + coefficients[2] * y * y
            + coefficients[3] * x
            + coefficients[4] * y
            + coefficients[5]
        )
        residuals.append([f"点 {i + 1}", f"{x:.5f}", f"{y:.5f}", f"{value:+.2e}"])

    primitives = []
    for label, call in [
        (
            "primitive_grid(width_segments=4, height_segments=4)",
            lambda: colour.geometry.primitive_grid(width_segments=4, height_segments=4)[0],
        ),
        (
            "primitive_cube(width_segments=2, height_segments=2, depth_segments=2)",
            lambda: colour.geometry.primitive_cube(width_segments=2, height_segments=2, depth_segments=2)[0],
        ),
        (
            "primitive_vertices_sphere(radius=0.5, segments=16)",
            lambda: colour.geometry.primitive_vertices_sphere(radius=0.5, segments=16),
        ),
    ]:
        try:
            primitives.append([label, str(np.asarray(call()).shape), "顶点数组形状"])
        except Exception as error:
            primitives.append([label, f"不可用（{type(error).__name__}）", "—"])

    cross = colour.geometry.intersect_line_segments(np.array([[0, 0], [1, 1]]), np.array([[0, 1], [1, 0]]))
    parallel = colour.geometry.intersect_line_segments(np.array([[0, 0], [1, 1]]), np.array([[0, 1], [1, 2]]))
    segment_rows = [
        [
            "交叉 (0,0)-(1,1) vs (0,1)-(1,0)",
            f"交点 ({cross.xy[0][0][0]:.3f}, {cross.xy[0][0][1]:.3f})",
            f"intersect={bool(cross.intersect[0][0])}",
        ],
        [
            "平行 (0,0)-(1,1) vs (0,1)-(1,2)",
            "无交点（坐标 nan）",
            f"parallel={bool(parallel.parallel[0][0])}、intersect={bool(parallel.intersect[0][0])}",
        ],
    ]

    all_rows = [
        [f"{i + 1}", f"{r[0]:.4f}", f"{r[1]:.4f}", f"{r[2]:.2f}", f"{r[3]:.2f}", f"{r[4]:.1f}"]
        for i, r in enumerate(data)
    ]

    return panel(
        "geometry",
        "数据与算法",
        "23",
        "几何与椭圆拟合",
        "MacAdam 1942 的椭圆告诉你「人眼在各方向上有多不敏感」；把它拟合成二次曲线，就能反过来量化局部均匀性。geometry 子模块负责这类拟合、图元与线段求交。",
        [
            chart(
                zoom_curves,
                xlabel="CIE x",
                ylabel="CIE y",
                title=f"第 11 组 MacAdam 椭圆：采样点 → 拟合椭圆（中心 {cx:.3f}, {cy:.3f}）",
                caption="坐标跨度只有 0.002×0.004，所以看上去接近一个圆——这正是 MacAdam 椭圆的特点。拟合曲线与原曲线在此分辨率下完全重合。",
                height=280,
            ),
            table(
                ["参数", "原始数据", "拟合恢复", "说明"],
                compare,
                title="拟合是否还原了原始参数",
                mono=[1, 2],
                widths=["110px", "140px", "140px", "auto"],
                note="拟合不是「造出一个新椭圆」，而是从 60 个点反推原来那组参数：中心精度到小数点后 4 位，半轴完全对上（顺序互换），θ 相差 90° 属于标准形表示法的约定差异。",
            ),
            table(
                ["采样点", "x", "y", "二次型残差"],
                residuals,
                title="二次型残差（隐式方程代入，应接近 0）",
                mono=[1, 2, 3],
                widths=["80px", "120px", "120px", "130px"],
            ),
            table(
                ["调用", "输出", "说明"],
                primitives,
                title="图元生成（geometry 子模块）",
                mono=[0],
                widths=["auto", "140px", "110px"],
                note="primitive_* 返回 (vertices, indexes, faces) 三元组，这里取第 0 个元素的形状；colour.geometry 没有 primitive_sphere，球面用 primitive_vertices_sphere。",
            ),
            table(
                ["线段", "结果", "标志位"],
                segment_rows,
                title="线段求交（intersect_line_segments）",
                mono=[1, 2],
                widths=["auto", "170px", "auto"],
            ),
            table(
                ["#", "u", "v", "a ×10⁻³", "b ×10⁻³", "θ°"],
                all_rows,
                title="全部 25 组 MacAdam 1942 椭圆（原始数据）",
                mono=[1, 2, 3, 4, 5],
                note="u/v 是色度图中心坐标，a/b 是长短半轴（×10⁻³），θ 是长轴方向角。面板 25 会把它们整体画到 CIE 1931 色度图上。",
            ),
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
    film_curves = []
    film_rows = []
    for thickness, css in [(200, "#264653"), (350, "#3B82F6"), (500, "#E76F51")]:
        reflected, transmitted = colour.phenomena.thin_film_tmm(
            np.array([1.0, 1.38, 1.0]), float(thickness), wavelengths
        )
        values = np.asarray(reflected).reshape(len(wavelengths), -1)[:, 0]
        transmitted_values = np.asarray(transmitted).reshape(len(wavelengths), -1)[:, 0]
        film_curves.append(series(f"{thickness} nm", wavelengths, values, color=css))
        at550 = float(values[int(np.argmin(np.abs(wavelengths - 550)))])
        film_rows.append(
            [
                f"{thickness} nm",
                f"{at550:.4f}",
                f"{float(values.max()):.4f}",
                f"{float(np.mean(values)):.4f}",
                f"{float(transmitted_values.mean()):.4f}",
            ]
        )

    scattering = colour.phenomena.sd_rayleigh_scattering(colour.SpectralShape(360, 780, 5))
    rayleigh_curve = [
        series("Rayleigh 散射强度", scattering.wavelengths, scattering.values, color="#3B82F6")
    ]
    rayleigh_rows = []
    for short, long in [(400.0, 700.0), (450.0, 650.0), (450.0, 550.0)]:
        measured = float(scattering[short] / scattering[long])
        theory = (long / short) ** 4
        rayleigh_rows.append(
            [
                f"{short:.0f} / {long:.0f} nm",
                f"{measured:.3f}",
                f"{theory:.3f}",
                f"{(measured / theory - 1) * 100:+.1f}%",
            ]
        )

    substrate = np.linspace(0.05, 20, 60)
    kinetics_curves = [
        series(
            "Michaelis 1913",
            substrate,
            [float(colour.biochemistry.reaction_rate_MichaelisMenten(s, 1.0, 0.8)) for s in substrate],
            color="#264653",
        ),
        # Abebe 2017 多一个偏置因子 b_m，不传会抛 TypeError（原实现把它吞掉了，导致这条曲线从未画出）
        series(
            "Abebe 2017（b_m=0.813）",
            substrate,
            [
                float(colour.biochemistry.reaction_rate_MichaelisMenten(s, 1.0, 0.8, method="Abebe 2017", b_m=0.813))
                for s in substrate
            ],
            color="#E76F51",
        ),
    ]
    kinetics_rows = []
    for s in [0.5, 2.0, 5.0, 20.0]:
        classic = float(colour.biochemistry.reaction_rate_MichaelisMenten(s, 1.0, 0.8))
        revised = float(
            colour.biochemistry.reaction_rate_MichaelisMenten(s, 1.0, 0.8, method="Abebe 2017", b_m=0.813)
        )
        kinetics_rows.append([f"{s:g}", f"{classic:.4f}", f"{revised:.4f}", f"{revised - classic:+.4f}"])

    return panel(
        "optics",
        "数据与算法",
        "24",
        "光学现象与响应动力学",
        "colour 不只会算颜色，还会算光：薄膜干涉为什么让肥皂泡变彩虹、天空为什么是蓝的（瑞利散射）、光在两种介质间怎么拐弯（Snell）。biochemistry 则提供光感受器响应的动力学模型。",
        [
            chart(
                film_curves,
                xlabel="波长 / nm",
                ylabel="反射率 R",
                title="单层薄膜（n=1.38，空气/膜/空气）的反射光谱",
                caption="传输矩阵法（thin_film_tmm）算出的真实反射率：膜厚改变光程差，反射率随波长周期性起伏——这就是肥皂泡与油膜的彩虹。注意反射率整体很小（<9%），因为只有 2.5% 的单面菲涅尔反射在相互干涉。",
                height=260,
                zero=True,
            ),
            chart(
                rayleigh_curve,
                xlabel="波长 / nm",
                ylabel="散射强度（相对）",
                title="瑞利散射：短波被散射得更强",
                caption="蓝光（450 nm）的散射强度约为红光的 4 倍以上——天空是蓝的、夕阳是红的，都来自这条曲线。",
                height=230,
                zero=True,
            ),
            table(
                ["波长比", "实测强度比", "(λ₂/λ₁)⁴ 理论值", "偏差"],
                rayleigh_rows,
                title="瑞利散射是否真的遵循 1/λ⁴",
                mono=[1, 2, 3],
                widths=["130px", "130px", "160px", "110px"],
                note="实测比理论值系统性偏高 2–5%：colour 的实现里还含折射率色散与大气层厚度修正，并非教科书上的纯 1/λ⁴ 项。这不影响「短波散射更强」的结论，但定量时不能直接套 1/λ⁴。",
            ),
            chart(
                kinetics_curves,
                xlabel="底物浓度 S",
                ylabel="反应速率 v",
                title="Michaelis–Menten 动力学：经典式 vs Abebe 2017 修正",
                caption="V_max=1.0、K_m=0.8 相同，只改公式：Abebe 2017 在分母乘了偏置因子 b_m，于是上渐近线从 V_max 变成 V_max/b_m = 1.23，半饱和点也从 K_m 挪到 K_m/b_m。",
                height=240,
                zero=True,
            ),
            table(
                ["S", "Michaelis 1913", "Abebe 2017（b_m=0.813）", "差值"],
                kinetics_rows,
                title="两种动力学模型在同参数下的差异",
                mono=[0, 1, 2, 3],
                widths=["80px", "150px", "190px", "110px"],
                note="经典式 v = V_max·S/(K_m+S)：S=K_m=0.8 时正好是 V_max 的一半，上渐近线是 V_max。Abebe 2017 的 v = V_max·S/(b_m·S+K_m)：b_m=0.813<1，分母被压小，速率整体抬高且上渐近线升到 V_max/b_m≈1.23——所以 S=20 时速率超过 1.0 并不矛盾，那是公式定义的另一条渐近线。",
            ),
            table(
                ["膜厚", "R @ 550 nm", "R 最大", "R 平均", "T 平均"],
                film_rows,
                title="薄膜数值（对应上方第一张图）",
                mono=[0, 1, 2, 3, 4],
                widths=["100px", "130px", "110px", "110px", "110px"],
                note="R + T ≈ 1（无损介质），可作为传输矩阵实现的健全性检查。",
            ),
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
    # plotting 子模块是全库唯一必须 matplotlib 的地方（D7 例外）：
    # 这些函数自带图例、色度背景与坐标轴样式，改写成数据块等于重做一套渲染器。
    # 但它是本机最容易触发 jetsam 的面板：每张图编码完必须立刻 close + collect，
    # 否则 4 张图同时驻留会把进程推到系统内存回收边缘（实测 exit 137）。
    spec = [
        (
            "可见光谱色带",
            lambda ax: colour.plotting.plot_visible_spectrum(axes=ax, show=False),
            "plot_visible_spectrum：把 380–780 nm 渲染成连续色带，是「波长 → 颜色」最直观的一次演示。",
            "3.2",
            "1.6",
        ),
        (
            "黑体辐射",
            lambda ax: colour.plotting.plot_blackbody_spectral_radiance(5000, axes=ax, show=False),
            "plot_blackbody_spectral_radiance：5000 K 黑体的光谱辐亮度，峰值随温度按维恩位移定律移动。",
            "3.2",
            "2.0",
        ),
        (
            "MacAdam 椭圆",
            lambda ax: colour.plotting.plot_ellipses_MacAdam1942_in_chromaticity_diagram_CIE1931(axes=ax, show=False),
            "plot_ellipses_MacAdam1942_in_chromaticity_diagram_CIE1931：把 25 组感知等距椭圆画到 CIE 1931 色度图上（数据见面板 23）。",
            "3.2",
            "2.2",
        ),
    ]

    images = []
    for label, paint, caption, width, height in spec:
        fig, ax = new_axes((float(width), float(height)), dpi=110)
        try:
            xlim_before = ax.get_xlim()
            with warnings.catch_warnings():
                # colour 内部画 MacAdam 椭圆时会抛 numpy ComplexWarning（虚部恒 0），属库内噪声
                warnings.simplefilter("ignore", np.exceptions.ComplexWarning)
                result = paint(ax)
            # plot_blackbody_spectral_radiance 会把曲线画进传入的 axes，却不设置坐标范围
            # （xlim 仍停在 0–1，线画在视野外），且返回的是一个空白模板 figure —— 只能自己补 autoscale。
            if ax.get_xlim() == xlim_before and ax.get_lines():
                # 该函数不设坐标范围，且额外画了 474 个色块补丁（占满 0–1），
                # relim 会被补丁带偏，只能直接用曲线的数据范围定轴。
                xs = np.concatenate([np.asarray(line.get_xdata(), dtype=float) for line in ax.get_lines()])
                ys = np.concatenate([np.asarray(line.get_ydata(), dtype=float) for line in ax.get_lines()])
                ax.set_xlim(float(xs.min()), float(xs.max()))
                ax.set_ylim(0.0, float(ys.max()) * 1.05)
            if isinstance(result, tuple) and len(result) == 2 and isinstance(result[0], plt.Figure) and result[0] is not fig:
                plt.close(result[0])  # 丢弃函数内部新建的空白画布
            ax.set_title("")
            # 固定边距代替 bbox_inches="tight"：这些图的 artist 太多，tight bbox 会把进程撑爆
            fig.subplots_adjust(left=0.16, right=0.97, top=0.92, bottom=0.2)
            images.append(image(fig, caption=caption, maxw="560px", tight=False))
        finally:
            plt.close(fig)
            gc.collect()

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

    total = len([n for n in colour.plotting.__all__ if n.startswith("plot_")])
    exported = len(colour.plotting.__all__)
    return panel(
        "gallery",
        "数据与算法",
        "25",
        "图表画廊",
        f"`colour.plotting` 导出 {exported} 个名字，其中 {total} 个是 `plot_*` 绘图函数：从色度图到薄膜反射率，从 SPD 到色卡检测结果。它们既是演示的素材，也是「不用自己画图」的现成能力——代价是必须服务端渲染位图，所以全站只在这一页破例。",
        [
            *images,
            table(
                ["绘图分组", "数量", "函数举例"],
                groups,
                title=f"plotting 的 {total} 个 plot_* 函数按前缀分组（__all__ 共 {exported} 个导出名，其余为样式/工具函数）",
                mono=[1],
                widths=["150px", "70px", "auto"],
                note="其余面板一律走 chart 块（前端 SVG、数据驱动）；只有本页这些自带色度背景与图例的成品图用 matplotlib，且按内存预算限定 3 张。",
            ),
            kv(
                [
                    ("样式系统", "colour_style / override_style / artist / CONSTANTS_COLOUR_STYLE", "统一主题"),
                    ("3D 图", "plot_RGB_colourspace_section / plot_RGB_scatter（需 trimesh）", "可选依赖"),
                    ("导出", "savefig 前设置 Agg 后端；服务端固定 dpi 与画幅", "见方案 7.4"),
                    ("内存预算", "每张图编码后 plt.close(fig) + gc.collect()；本页限 3 张", "实测单张 130–150 MB"),
                ],
                title="能力",
            ),
        ],
        phase="M3",
        apis=["POST /api/v1/plot"],
        footer="对应 API：`POST /api/v1/plot`；依赖 `colour.plotting` 的 plot_* 函数，服务端 Agg 后端渲染位图。",
    )


