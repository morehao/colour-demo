/* adapters.js：M1/M2 面板的实时适配器（LIVE 定义 + 请求/回显映射） */

const splitList = (text) => String(text || "").split(/[,，\s]+/).filter(Boolean).slice(0, 12);
const series = (name, points, extra = {}) => ({ name, points, ...extra });

/* 每个面板的实时适配器：fields 决定控件，body/query 决定请求，blocks 决定回显 */
const LIVE = {};

LIVE.convert = {
  endpoint: "POST /api/v1/convert",
  hint: "改颜色或目标空间 → 服务端重算 14 个核心空间，并给出换算链路。",
  fields: [
    { key: "colors", label: "颜色（逗号分隔，≤12）", kind: "text", value: "#3B82F6, #E9C46A" },
    { key: "target", label: "换算链路目标", kind: "select", options: ["CIE Lab", "Oklab", "CAM16 UCS", "HCL", "Oklch"], value: "CIE Lab" },
  ],
  body: (s) => ({ colors: splitList(s.colors), target: s.target }),
  blocks: (p) => [
    B.table("实时结果：核心空间坐标", ["输入", ...p.spaces],
      p.rows.map((row) => [row.hex, ...p.spaces.map((space) => fixed(row.values[space], 4))]),
      { mono: [0], note: `XYZ 用 0–1 域，Lab/Luv 用 0–100 域（to_reference_scale=True）。` }),
    B.kv("换算链路", [
      ["路径", (p.conversion_path || []).join(" → ") || "—", `${p.conversion_hops || 0} 跳`],
      ["起点", p.source, "source"],
    ]),
  ],
};

LIVE.chroma = {
  endpoint: "POST /api/v1/chroma",
  hint: "主波长/纯度依赖光源白点，换光源看看数字怎么变。",
  fields: [
    { key: "colors", label: "颜色（逗号分隔）", kind: "text", value: "#264653, #2A9D8F, #E9C46A, #F4A261, #E76F51" },
    { key: "illuminant", label: "光源", kind: "select", options: ["D65", "D50", "A", "C", "FL2"], value: "D65" },
  ],
  body: (s) => ({ colors: splitList(s.colors), illuminant: s.illuminant }),
  blocks: (p) => [
    B.table("实时结果：色度学属性", ["颜色", "xy", "uv(1960)", "u′v′(1976)", "主波长 nm", "激发纯度", "色度纯度"],
      p.rows.map((row) => [row.hex, fixed(row.xy), fixed(row.uv), fixed(row.uv_prime), num(row.dominant_wavelength, 1), num(row.excitation_purity, 4), num(row.colorimetric_purity, 4)]),
      { mono: [0, 1, 2, 3], note: `白点 xy = ${fixed(p.whitepoint_xy)}（${p.illuminant} / ${p.observer}）` }),
  ],
};

LIVE["delta-e"] = {
  endpoint: "POST /api/v1/delta-e",
  hint: "换 ΔE 方法，同一组颜色的数值差可能很大——这就是「不可比」的来源。",
  fields: [
    { key: "colors", label: "颜色（逗号分隔，≥2）", kind: "text", value: "#264653, #2A9D8F, #E9C46A, #F4A261, #E76F51" },
    { key: "method", label: "方法", kind: "select", options: ["CIE 2000", "CIE 1976", "CIE 1994", "CMC", "CAM02-UCS", "CAM16-UCS"], value: "CIE 2000" },
  ],
  body: (s) => ({ colors: splitList(s.colors), method: s.method }),
  blocks: (p) => [
    B.matrix(`ΔE 矩阵（${p.method}）`, p.colors, p.matrix, "对角线不参与比较；单元格越深差异越大。"),
    B.kv("极值对", [
      ["最接近", `${p.pairs.closest.a} ↔ ${p.pairs.closest.b}`, `ΔE ${num(p.pairs.closest.value, 2)}`],
      ["最远", `${p.pairs.farthest.a} ↔ ${p.pairs.farthest.b}`, `ΔE ${num(p.pairs.farthest.value, 2)}`],
    ]),
  ],
};

LIVE.gradient = {
  endpoint: "POST /api/v1/gradient",
  hint: "在哪个空间插值，决定了步长是否均匀。",
  fields: [
    { key: "from", label: "起点", kind: "text", value: "#264653" },
    { key: "to", label: "终点", kind: "text", value: "#E9C46A" },
    { key: "space", label: "插值空间", kind: "select", options: ["CIE Lab", "Oklab", "CIE Luv", "sRGB", "CAM16 UCS"], value: "Oklab" },
    { key: "steps", label: "步数", kind: "text", value: "11" },
  ],
  body: (s) => ({ from: s.from, to: s.to, space: s.space, steps: Math.max(2, Math.min(101, parseInt(s.steps, 10) || 11)) }),
  blocks: (p) => [
    { type: "strips", title: `实时渐变（${p.space}，${p.steps} 步）`, items: [{ label: `${p.space}`, note: p.method, colors: p.rows.map((row) => row.hex), stats: [["比值", num(p.uniformity.ratio, 3)], ["均值 ΔE", num(p.uniformity.mean, 3)]] }] },
    B.chart("相邻步的 ΔE", [series("ΔE", p.deltas.map((value, index) => [index + 1, value]))], { xlabel: "步序", ylabel: "ΔE", zero: true }),
  ],
};

LIVE.transfer = {
  endpoint: "POST /api/v1/transfer",
  hint: "编码曲线 + 往返误差 + YCbCr 码值。",
  fields: [
    { key: "colors", label: "颜色（YCbCr 取样）", kind: "text", value: "#3B82F6" },
    { key: "samples", label: "曲线采样点", kind: "select", options: ["17", "33", "65"], value: "33" },
  ],
  body: (s) => ({ colors: splitList(s.colors), samples: parseInt(s.samples, 10) }),
  blocks: (p) => [
    B.chart("编码曲线（横轴线性光 0–1）",
      p.curves.slice(0, 6).map((row) => series(row.name, row.linear
        .map((x, i) => [x, row.encoded[i]])
        .filter(([, y]) => typeof y === "number" && isFinite(y)))),
      { xlabel: "线性光", ylabel: "编码值", height: 300 }),
    B.table("往返误差（encode → decode）", ["编码", "分组", "最大误差", "可逆"],
      p.curves.map((row) => [row.name, row.group, row.roundtrip_error === null ? "不可计算" : row.roundtrip_error.toExponential(1), row.invertible ? "是" : "否"]),
      { mono: [2] }),
    B.table("YCbCr 码值", ["颜色", "范围", "Y / Cb / Cr（浮点）", "码值", "往返误差"],
      p.ycbcr.rows.flatMap((row) => ["limited", "full"].filter((k) => row[k]).map((k) => [row.hex, k, fixed(row[k].ycbcr, 4), row[k].codes.join(" / "), row[k].roundtrip_error.toExponential(1)])),
      { mono: [0, 2, 3], note: `${p.ycbcr.luma} · ${p.ycbcr.bits} bit` }),
  ],
};

LIVE.chromaticity = {
  endpoint: "GET /api/v1/chromaticity.svg",
  hint: "换色度图/色域/样本点：图由服务端 matplotlib 现画，下面的面积表来自 /chromaticity。",
  fields: [
    { key: "diagram", label: "色度图", kind: "select", options: ["CIE 1931", "CIE 1960 UCS", "CIE 1976 UCS"], value: "CIE 1931" },
    { key: "gamuts", label: "叠加色域", kind: "select", options: ["sRGB,Display P3,ITU-R BT.2020", "sRGB", "sRGB,Display P3"], value: "sRGB,Display P3,ITU-R BT.2020" },
    { key: "colors", label: "样本点", kind: "text", value: "#264653, #2A9D8F, #E9C46A, #F4A261, #E76F51" },
  ],
  query: (s) => ({ diagram: s.diagram, gamuts: s.gamuts, colors: splitList(s.colors).join(",") }),
  svgUrl: (s) => `${API_BASE}/api/v1/chromaticity.svg?` + new URLSearchParams(LIVE.chromaticity.query(s)).toString(),
  dataEndpoint: "GET /api/v1/chromaticity",
  blocks: (p, state) => [
    B.image(LIVE.chromaticity.svgUrl(state), `${p.diagram} + ${p.gamuts.map((g) => g.name).join(" / ")} + ${p.samples.length} 个样本点`, "560px"),
    B.table("色域三角形面积（xy 平面）", ["色域", "面积", "相对 sRGB"],
      p.gamuts.map((g) => [g.name, num(g.area_xy, 5), num(g.relative_to_sRGB, 3) + "×"]), { mono: [1, 2] }),
    B.table("样本点与色域归属", ["颜色", "xy", "u′v′", ...p.gamuts.map((g) => g.name)],
      p.samples.map((row) => [row.hex, fixed(row.xy), fixed(row.uv_1976), ...p.gamuts.map((g) => (row.inside[g.name] ? "✔" : "✗"))]),
      { mono: [0, 1, 2], note: "✔/✗ = 该空间编码值是否都落在 0–1（矩阵 + cctf 判定）" }),
  ],
};

LIVE["gamut-volume"] = {
  endpoint: "POST /api/v1/volume",
  hint: "MonteCarlo 体积（固定种子，可复现）+ 三套边界判据。",
  fields: [
    { key: "samples", label: "采样数", kind: "select", options: ["5000", "20000", "50000"], value: "20000" },
    { key: "colors", label: "边界判定的样本色", kind: "text", value: "#264653, #2A9D8F, #E9C46A, #F4A261, #E76F51" },
  ],
  body: (s) => ({ spaces: ["sRGB", "Display P3", "ITU-R BT.2020", "ACES2065-1"], samples: parseInt(s.samples, 10), colors: splitList(s.colors) }),
  blocks: (p) => [
    B.table(`色域体积（${p.samples} 采样，seed=${p.seed}）`, ["色彩空间", "体积（Lab 单位）", "相对 sRGB", "Lab 范围"],
      p.rows.map((row) => [row.space, num(row.volume, 1), num(row.relative_to_reference, 3) + "×", row.lab_limits ? row.lab_limits.map((pair) => `[${num(pair[0], 0)}, ${num(pair[1], 0)}]`).join(" ") : "—"]),
      { mono: [1, 2] }),
    p.boundaries.length ? B.table("边界判据", ["颜色", "MacAdam(D65)", "Pointer", "可见光谱"],
      p.boundaries.map((row) => [row.hex, row.within_macadam_D65 ? "内" : "外", row.within_pointer ? "内" : "外", row.within_visible_spectrum ? "内" : "外"]), { mono: [0] }) : null,
  ].filter(Boolean),
};

LIVE.temperature = {
  endpoint: "POST /api/v1/temperature",
  hint: "换色温：xy 派与 uv 派方法表互不通用，正反解分开看。",
  fields: [
    { key: "cct", label: "色温 K", kind: "select", options: ["2700", "4000", "5000", "6500", "9000"], value: "6500" },
    { key: "colors", label: "待测颜色（可选）", kind: "text", value: "#FFFFFF" },
  ],
  body: (s) => ({ cct: parseInt(s.cct, 10), colors: splitList(s.colors) }),
  blocks: (p) => [
    B.table("xy → CCT（4 种反解）", ["样本", ...Object.keys(p.xy_to_cct[0].results)],
      p.xy_to_cct.map((row) => [row.sample, ...Object.values(row.results).map((v) => (v === null ? "—" : num(v, 1) + " K"))]), { mono: [0] }),
    B.table("uv → CCT（含 D_uv）", ["样本", ...Object.keys(p.uv_to_cct[0].results)],
      p.uv_to_cct.map((row) => [row.sample, ...Object.values(row.results).map((v) => (v && v.cct !== null ? `${num(v.cct, 1)} K` : "—"))]), { mono: [0], note: "Ohno 2013 / Robertson 1968 返回 (CCT, D_uv) 二元组" }),
    B.table(`CCT → xy / uv（${p.input.cct} K）`, ["方法", "xy", "uv"],
      p.cct_to_xy.map((row, i) => [row.method, fixed(row.xy, 5), fixed((p.cct_to_uv[i] || {}).uv, 5)]), { mono: [0, 1, 2] }),
    B.chart("普朗克轨迹（Planck 1900）", [series("黑体轨迹", p.planckian_locus.map((row) => [row.xy[0], row.xy[1]]), { mode: "scatter" })],
      { xlabel: "x", ylabel: "y", height: 300 }),
  ],
};

LIVE.quality = {
  endpoint: "POST /api/v1/quality",
  hint: "四套显色口径并列：Ra / Qa / Rf·Rg / SSI，结论会互相打架。",
  fields: [
    { key: "illuminants", label: "光源（逗号分隔）", kind: "text", value: "D65, FL2, A, FL11" },
    { key: "reference", label: "SSI 参考", kind: "select", options: ["D65", "D50", "A"], value: "D65" },
  ],
  body: (s) => ({ illuminants: splitList(s.illuminants), reference: s.reference }),
  blocks: (p) => [
    B.table("显色指标", ["光源", "CRI Ra", "Ra(CIE 2024)", "CQS Qa", "TM-30 Rf", "TM-30 Rg", "SSI"],
      p.rows.map((row) => [row.illuminant, num(row.Ra, 2), num(row.Ra_2024, 2), num(row.Qa, 2), num(row.Rf, 2), num(row.Rg, 2), num(row.ssi, 3)]), { mono: [0] }),
    p.special_indices.length ? B.table(`CRI 特殊显色指数（${p.special_indices[0].illuminant}）`,
      ["色样", ...Object.keys(p.special_indices[0]).filter((k) => k !== "illuminant")],
      [["Ri", ...Object.entries(p.special_indices[0]).filter(([k]) => k !== "illuminant").map(([, v]) => num(v, 1))]], { mono: [0] }) : null,
  ].filter(Boolean),
};

LIVE["image-lut"] = {
  endpoint: "POST /api/v1/lut",
  hint: "3D LUT 的两种插值方式在同一批颜色上的差异。",
  fields: [
    { key: "colors", label: "取样颜色", kind: "text", value: "#3B82F6, #808080, #E9C46A" },
    { key: "size", label: "LUT 尺寸", kind: "select", options: ["9", "17", "33"], value: "17" },
    { key: "gains", label: "通道增益 R,G,B", kind: "text", value: "1.2, 0.85, 1.05" },
  ],
  body: (s) => ({ colors: splitList(s.colors), size: parseInt(s.size, 10), gains: splitList(s.gains).map(Number) }),
  blocks: (p) => [
    B.table(`LUT ${p.size}³（${p.table_points} 格点）`, ["输入", "Trilinear", "Tetrahedral", "两法差"],
      p.rows.map((row) => [row.input, row.outputs.Trilinear ? row.outputs.Trilinear.hex : "—", row.outputs.Tetrahedral ? row.outputs.Tetrahedral.hex : "—", num(row.interpolator_spread, 5)]),
      { mono: [0, 1, 2], note: p.domain }),
    { type: "swatches", title: "灰阶带（LUT 后）", cols: Math.min(9, p.ramp.length), items: p.ramp.map((row) => ({ hex: row.output, label: row.output, sub: row.input })) },
  ],
};

LIVE.adaptation = {
  endpoint: "POST /api/v1/adapt",
  hint: "7 种色适应方法（含需要补观察条件的 4 个）+ vK20 不完全适应。",
  fields: [
    { key: "colors", label: "颜色", kind: "text", value: "#3B82F6" },
    { key: "source", label: "源白点", kind: "select", options: ["A", "D50", "D65", "D93", "FL2"], value: "A" },
    { key: "target", label: "目标白点", kind: "select", options: ["D65", "D50", "D93"], value: "D65" },
  ],
  body: (s) => ({ colors: splitList(s.colors), source: s.source, target: s.target }),
  blocks: (p) => [
    B.table(`适应后结果（${p.source.name} → ${p.target.name}）`, ["方法", "xy", "sRGB", "ΔE(原色)"],
      Object.entries(p.rows[0].results).map(([method, value]) => [method, value ? fixed(value.xy) : "—", value ? value.hex : "—", value ? num(value.delta_e, 2) : "—"]),
      { mono: [1, 2] }),
    B.table("vK20（不完全适应）", ["颜色", "xy", "sRGB"],
      Object.entries(p.vK20).map(([input, value]) => [input, value ? fixed(value.xy) : "—", value ? value.hex : "—"]), { mono: [1, 2] }),
    B.table("CAT 矩阵", ["名称", "3×3 系数"], p.cat_matrices.map((row) => [row.name, row.matrix.map((r) => r.map((v) => num(v, 4)).join(", ")).join(" | ")]), { mono: [1] }),
  ],
};

LIVE.appearance = {
  endpoint: "POST /api/v1/appearance",
  hint: "12 个外观模型对同一 XYZ 给出不同的 J/C/h；ZCAM 用 0–1 域，其余多数 0–100。",
  fields: [
    { key: "colors", label: "颜色", kind: "text", value: "#3B82F6" },
    { key: "L_A", label: "L_A（cd·m⁻²）", kind: "select", options: ["4.07", "20", "100", "318.31"], value: "4.07" },
    { key: "surround", label: "环绕", kind: "select", options: ["Average", "Dim", "Dark"], value: "Average" },
  ],
  body: (s) => ({ colors: splitList(s.colors), L_A: Number(s.L_A), surround: s.surround }),
  blocks: (p) => [
    B.table(`外观模型输出（L_A=${p.conditions.L_A.toFixed(2)}, Y_b=${p.conditions.Y_b}, ${p.conditions.surround}）`,
      ["模型", "J", "C", "h", "M", "H", "往返误差", "域"],
      Object.entries(p.rows[0].results).map(([model, value]) => [model, num(value.J, 2), num(value.C, 2), num(value.h, 1), num(value.M, 2), num(value.H, 1), value.roundtrip_error === null ? "无逆变换" : value.roundtrip_error.toExponential(1), p.models[model].scale === 1 ? "0–1" : "0–100"]),
      { mono: [0, 1, 2, 3, 4, 5] }),
  ],
};

LIVE["phenomena-vision"] = {
  endpoint: "POST /api/v1/phenomena-vision",
  hint: "H-K 效应 + Barten CSF（亮度经瞳孔换成视网膜照度再算）。",
  fields: [
    { key: "colors", label: "样本颜色", kind: "text", value: "#3B82F6" },
    { key: "luminances", label: "亮度 cd·m⁻²（逗号分隔）", kind: "text", value: "10, 100, 1000" },
  ],
  body: (s) => ({ colors: splitList(s.colors), luminances: splitList(s.luminances).map(Number), points: 32 }),
  blocks: (p) => [
    B.chart("Helmholtz–Kohlrausch 效应", ["VCC", "VAC"].map((method) => series(method, p.hk.chromas.map((c, i) => [c, p.hk.curves[method][i]]))), { xlabel: "彩度 C", ylabel: "亮度增益因子", height: 280 }),
    B.chart("Barten 1999 对比敏感度", Object.entries(p.csf.curves).map(([level, values]) => series(`Y₀=${level} cd·m⁻²`, p.csf.frequencies.map((f, i) => [f, values[i]]))), { xlabel: "空间频率 / cpd", ylabel: "S", height: 280 }),
    B.table("派生量", ["亮度", "瞳孔直径 mm", "视网膜照度 Td", "CSF 峰值 cpd"],
      p.csf.derived.map((row) => [num(row.luminance, 0), num(row.pupil_diameter_mm, 3), num(row.retinal_illuminance_td, 1), num(row.peak_frequency_cpd, 2)]), { mono: [0, 1, 2, 3] }),
  ],
};

LIVE.corresponding = {
  endpoint: "POST /api/v1/corresponding",
  hint: "Breneman 实验 × 5 个模型：预测点离实测终点有多远。",
  fields: [
    { key: "experiment", label: "实验编号", kind: "select", options: ["1", "2", "3", "4", "6", "8", "11", "12"], value: "1" },
  ],
  body: (s) => ({ experiment: parseInt(s.experiment, 10) }),
  blocks: (p) => [
    B.table(`实验 ${p.experiment}：各模型预测偏差`, ["模型", "均值 u′v′ 距离", "最大", "样本数"],
      p.rows.map((row) => [row.model, row.mean_uv_error === undefined ? "—" : num(row.mean_uv_error, 5), row.max_uv_error === undefined ? "—" : num(row.max_uv_error, 5), (row.samples || []).length]), { mono: [0, 1, 2] }),
    B.table("8 组实验的横向对比", ["模型", "参与实验数", "平均偏差"], p.leaderboard.map((row) => [row.model, row.experiments, num(row.mean_uv_error, 5)]), { mono: [0, 2] }),
    B.note(p.unavailable_experiments.map((item) => `实验 ${item.experiment} 不可用：${item.reason}`).join("；"), "warn"),
  ],
};

LIVE.cvd = {
  endpoint: "POST /api/v1/cvd",
  hint: "Machado 2009：类型 + 严重度 → 模拟后的调色板与可区分性指标。",
  fields: [
    { key: "colors", label: "调色板", kind: "text", value: "#264653, #2A9D8F, #E9C46A, #F4A261, #E76F51" },
    { key: "deficiency", label: "类型", kind: "select", options: ["Protanomaly", "Deuteranomaly", "Tritanomaly"], value: "Deuteranomaly" },
    { key: "severity", label: "严重度（0–1）", kind: "range", min: 0, max: 1, step: 0.05, value: "1" },
  ],
  body: (s) => ({ colors: splitList(s.colors), deficiency: s.deficiency, severity: Number(s.severity) }),
  blocks: (p) => [
    { type: "swatches", title: `原始调色板`, cols: Math.min(8, p.rows.length), items: p.rows.map((row, i) => ({ hex: row.hex, label: `#${i + 1}`, sub: row.hex })) },
    { type: "swatches", title: `${p.label}（severity=${p.severity.toFixed(2)}）`, cols: Math.min(8, p.rows.length), items: p.rows.map((row, i) => ({ hex: row.simulated_hex, label: `#${i + 1}`, sub: `ΔE ${num(row.delta_e, 1)}` })) },
    B.kv("可区分性", [
      ["原色 vs 模拟 ΔE（均值）", num(p.metrics.mean_delta_e, 2), "越大差异越大"],
      ["模拟后相邻最小 ΔE", num(p.metrics.min_adjacent_delta_e, 2), `阈值 ${p.metrics.indistinguishable_threshold}`],
      ["不可区分相邻对", String(p.metrics.collisions.length), "低于阈值的相邻对"],
    ]),
  ],
};
