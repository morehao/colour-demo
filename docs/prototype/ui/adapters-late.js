/* adapters-late.js：M3/M4 面板与收尾适配器（19–28、03/04/07） */

/* ---- M3（面板 19–25）适配器 ---- */
LIVE.recovery = {
  endpoint: "POST /api/v1/recovery",
  hint: "同一支 RGB 的重建光谱：曲线不同、积分回三刺激值后应当一致（同色异谱）。",
  fields: [{ key: "colors", label: "输入色", kind: "text", value: "#3B82F6" }],
  body: (s) => ({ colors: splitList(s.colors) }),
  blocks: (p) => [
    B.chart("重建光谱（横轴波长 nm）",
      p.curves.map((row) => series(row.name, row.wavelengths.map((w, i) => [w, row.values[i]]))),
      { xlabel: "波长 / nm", ylabel: "反射率", height: 300, zero: true }),
    B.table("重建精度（ΔE CIE 2000）", ["方法", "入参域", "重建 sRGB", "ΔE", "采样点", "范围 nm"],
      p.rows.map((row) => [row.method, row.domain, row.hex || "—", num(row.delta_e, 3), row.samples || "—", (row.range_nm || []).join("–")]),
      { mono: [0, 2, 3] }),
  ],
};

LIVE.characterisation = {
  endpoint: "POST /api/v1/correction",
  hint: "24 色卡：模拟 A 光源下拍摄 → 三种校正方法把平均 ΔE 压回去。",
  fields: [],
  body: () => ({}),
  blocks: (p) => [
    { type: "strips", title: "24 色卡前 12 色：校正前后", items: p.stages.filter((stage) => stage.swatches.length).map((stage) => ({
      label: stage.stage, note: `${p.capture_model}`, colors: stage.swatches,
      stats: [["平均 ΔE", num(stage.mean_delta_e, 2)], ["最大 ΔE", num(stage.max_delta_e, 2)]],
    })) },
    B.table("校正效果", ["阶段", "平均 ΔE", "最大 ΔE"], p.stages.map((stage) => [stage.stage, num(stage.mean_delta_e, 2), num(stage.max_delta_e, 2)]), { mono: [1, 2] }),
    B.table("矩阵方法", ["方法", "矩阵维度"], p.matrices.map((row) => [row.method, `${row.shape[0]}×${row.shape[1]}`]), { mono: [1] }),
  ],
};

LIVE.notation = {
  endpoint: "POST /api/v1/notation",
  hint: "Munsell / CSS 关键字 / HEX 三种写法互相解析；反向不唯一。",
  fields: [
    { key: "munsell", label: "Munsell 记号", kind: "text", value: "5R 5/12" },
    { key: "keyword", label: "CSS 关键字", kind: "text", value: "tomato" },
    { key: "hex", label: "HEX", kind: "text", value: "#3B82F6" },
  ],
  body: (s) => ({ munsell: s.munsell, keyword: s.keyword, hex: s.hex }),
  blocks: (p) => [
    B.kv("解析结果", [
      ["Munsell → xyY", `${p.munsell.input} → ${fixed(p.munsell.xyY, 4)}`, p.munsell.hex],
      ["xyY → Munsell", p.munsell.back, p.munsell.roundtrip_matches ? "往返一致" : "往返不一致"],
      ["CSS 关键字", `${p.keyword.input} → ${p.keyword.hex}`, fixed(p.keyword.rgb, 3)],
      ["HEX", `${p.hex.input} → ${p.hex.canonical}`, fixed(p.hex.rgb, 5)],
      ["色名集合", `CSS ${p.counts.css_color_3}（基础 ${p.counts.css_basic}）/ Munsell ${p.counts.munsell_all} 个色样`, "CSS Color 3"],
    ]),
    B.table("七种 Munsell 明度换算", ["方法", `V(Y=${p.value_y})`], p.value_methods.map((row) => [row.method, num(row.value, 4)]), { mono: [0, 1] }),
    { type: "swatches", title: "CSS Color 3 的 16 个基础色名", cols: 8, items: p.css_basic.map((row) => ({ hex: row.hex, label: row.name, sub: row.hex })) },
  ],
};

LIVE.signals = {
  endpoint: "POST /api/v1/interpolate",
  hint: "FL11（含汞灯尖线）从 20 nm 粗采样插回 5 nm：看各插值器的过冲与残差。",
  fields: [
    { key: "illuminant", label: "光源", kind: "select", options: ["FL11", "FL2", "A", "D65"], value: "FL11" },
    { key: "coarse_step", label: "粗采样间隔 nm", kind: "select", options: ["10", "20", "40"], value: "20" },
  ],
  body: (s) => ({ illuminant: s.illuminant, coarse_step: Number(s.coarse_step), target_step: 5 }),
  blocks: (p) => [
    B.chart(`${p.illuminant}：粗采样 → ${p.shape.target_step} nm 重建`,
      [series("真实", p.curves.truth.wavelengths.map((w, i) => [w, p.curves.truth.values[i]]), { dashed: true }),
       series("粗采样", p.curves.coarse.wavelengths.map((w, i) => [w, p.curves.coarse.values[i]]), { mode: "scatter" }),
       ...p.curves.reconstructions.map((row) => series(row.name, row.wavelengths.map((w, i) => [w, row.values[i]])))],
      { xlabel: "波长 / nm", ylabel: "相对功率", height: 300 }),
    B.chart("重建误差（各方法 − 真值）",
      p.curves.residuals.map((row) => series(row.name, row.wavelengths.map((w, i) => [w, row.values[i]]))),
      { xlabel: "波长 / nm", ylabel: "误差", height: 240, zero: true }),
    B.table("重建误差", ["插值器", "最大绝对误差", "平均绝对误差", "负值点数"],
      p.rows.map((row) => [row.interpolator, num(row.max_abs_error, 2), num(row.mean_abs_error, 2), row.negative_points]), { mono: [1, 2, 3] }),
    B.kv("3D LUT 表插值（9³ 非线性合成表）", [
      ["探测点", fixed(p.lut.probe, 2), `${p.lut.probes} 个随机点`],
      ["Trilinear", fixed(p.lut.trilinear, 4), "—"],
      ["Tetrahedral", fixed(p.lut.tetrahedral, 4), "—"],
      ["两法差异", `最大 ${num(p.lut.max_gap_codes, 2)} /255、平均 ${num(p.lut.mean_gap_codes, 2)} /255`, "恒等表上必然为 0"],
    ]),
  ],
};

LIVE.geometry = {
  endpoint: "POST /api/v1/geometry",
  hint: "MacAdam 椭圆：60 个采样点 → 二次曲线 → 标准形，反推原始参数。",
  fields: [{ key: "ellipse_index", label: "椭圆序号（1–25）", kind: "select", options: ["1", "6", "11", "16", "21", "25"], value: "11" }],
  body: (s) => ({ ellipse_index: Math.max(0, Math.min(24, parseInt(s.ellipse_index, 10) - 1)) }),
  blocks: (p) => [
    B.chart(`第 ${p.ellipse_index + 1} 组椭圆：采样点与拟合曲线`,
      [series("原始可辨椭圆", p.ellipse.original_points),
       series("拟合结果", p.ellipse.fitted_points, { dashed: true }),
       series("采样点", p.ellipse.original_points.filter((_, i) => i % 6 === 0), { mode: "scatter" })],
      { xlabel: "CIE x", ylabel: "CIE y", height: 300 }),
    B.table("拟合还原参数", ["参数", "原始", "拟合", "说明"], p.compare.map((row) => [row.parameter, row.original, row.fitted, row.note]), { mono: [1, 2] }),
    B.table("二次型残差（应接近 0）", ["点", "x", "y", "残差"], p.residuals.map((row) => [row.point, num(row.x, 6), num(row.y, 6), row.residual]), { mono: [1, 2, 3] }),
    B.kv("图元与线段", [
      ...p.primitives.map((row) => [row.call, row.vertices_shape ? `顶点形状 ${JSON.stringify(row.vertices_shape)}` : "不可用", "geometry"]),
      [p.segments[0].case, `交点 ${JSON.stringify(p.segments[0].point)}`, `intersect=${p.segments[0].intersect}`],
      [p.segments[1].case, "无交点", `parallel=${p.segments[1].parallel}`],
    ]),
  ],
};

LIVE.optics = {
  endpoint: "POST /api/v1/optics",
  hint: "薄膜干涉 / 瑞利散射 / Michaelis–Menten：colour 也算物理光学。",
  fields: [{ key: "thicknesses", label: "膜厚 nm（逗号分隔）", kind: "text", value: "200, 350, 500" }],
  body: (s) => ({ thicknesses: splitList(s.thicknesses).map(Number) }),
  blocks: (p) => [
    B.chart("单层薄膜反射率（空气 / 膜 n=1.38 / 空气）",
      p.film.curves.map((row) => series(row.name, row.wavelengths.map((w, i) => [w, row.values[i]]))),
      { xlabel: "波长 / nm", ylabel: "R", height: 280, zero: true }),
    B.table("薄膜数值", ["膜厚 nm", "R @550", "R 最大", "R 平均", "T 平均", "R+T"], p.film.rows.map((row) => [num(row.thickness_nm, 0), num(row.reflectance_550, 5), num(row.reflectance_max, 5), num(row.reflectance_mean, 5), num(row.transmittance_mean, 5), num(row.rt_sum_mean, 4)]), { mono: [1, 2, 3, 4, 5] }),
    B.chart("瑞利散射", [series("散射强度", p.rayleigh.curve.wavelengths.map((w, i) => [w, p.rayleigh.curve.values[i]]))], { xlabel: "波长 / nm", ylabel: "相对强度", height: 240, zero: true }),
    B.table("是否真的 1/λ⁴", ["波长比", "实测", "理论", "偏差 %"], p.rayleigh.rows.map((row) => [row.pair_nm, num(row.measured_ratio, 3), num(row.theory_ratio, 3), num(row.deviation_pct, 2)]), { mono: [1, 2, 3] }),
    B.chart("Michaelis–Menten：经典式 vs Abebe 2017",
      [series("Michaelis 1913", p.kinetics.substrate.map((s, i) => [s, p.kinetics.michaelis[i]])),
       series("Abebe 2017", p.kinetics.substrate.map((s, i) => [s, p.kinetics.abebe[i]]))],
      { xlabel: "底物浓度 S", ylabel: "反应速率 v", height: 240, zero: true }),
  ],
};

LIVE.gallery = {
  endpoint: "POST /api/v1/plot",
  hint: "服务端 matplotlib 出图（全站唯一例外）：画幅/dpi 固定，返回 PNG。",
  fields: [{ key: "plots", label: "要渲染的图（逗号分隔）", kind: "text", value: "visible-spectrum, blackbody, macadam-ellipses" }],
  body: (s) => ({ plots: splitList(s.plots) }),
  blocks: (p) => [
    ...p.plots.map((row) => (row.png_base64
      ? B.image(`data:image/png;base64,${row.png_base64}`, row.caption, `${row.width}px`)
      : B.note(`${row.label} 渲染失败：${row.error}`, "warn"))),
    B.table("plot_* 函数分组", ["分组", "数量", "举例"], p.groups.map((row) => [row.group, row.count, row.examples.join(" · ") + (row.more ? " …" : "")]), { mono: [1] }),
  ],
};

/* ---- M4（面板 26–28）+ 收尾适配器（03/04/07） ---- */
LIVE.observers = {
  endpoint: "POST /api/v1/spectral",
  hint: "观察者与光源：SPD 采样 + 黑体合成谱。",
  fields: [
    { key: "illuminant", label: "光源", kind: "select", options: ["D65", "D50", "A", "FL2", "FL11"], value: "D65" },
    { key: "blackbody", label: "叠加黑体 K（空=不叠）", kind: "text", value: "5000" },
  ],
  body: (s) => ({ illuminant: s.illuminant, start: 380, end: 780, interval: 5, blackbody_temperature: s.blackbody ? Number(s.blackbody) : null }),
  blocks: (p) => [
    B.chart("光谱功率分布",
      p.series.map((row) => series(row.name, row.wavelengths.map((w, i) => [w, row.values[i]]))),
      { xlabel: "波长 / nm", ylabel: "相对功率", height: 280, zero: true }),
    B.table("曲线摘要", ["系列", "峰值", "均值"], p.series.map((row) => [row.name, num(row.peak, 2), num(row.mean, 2)]), { mono: [1, 2] }),
    B.kv("口径", [
      ["采样", `${p.shape.samples} 点（${p.shape.start}–${p.shape.end} nm / ${p.shape.interval} nm）`, "SpectralShape"],
      ["观察者", p.observers.slice(0, 3).join(" · "), "MSDS_CMFS"],
      ["光源总数", String(p.illuminants_total), "SDS_ILLUMINANTS"],
    ]),
  ],
};

LIVE.photometry = {
  endpoint: "POST /api/v1/photometry",
  hint: "明度（7 种）/ 亮度 / 白度 / 黄度：注意 Y 走 0–100 域。",
  fields: [{ key: "colors", label: "颜色", kind: "text", value: "#808080, #3B82F6, #E9C46A" }],
  body: (s) => ({ colors: splitList(s.colors) }),
  blocks: (p) => [
    B.table("明度（7 种算法）", ["颜色", "Y（0–100）", ...Object.keys(p.rows[0].lightness)],
      p.rows.map((row) => [row.hex, num(row.Y, 2), ...Object.values(row.lightness).map((v) => (typeof v === "number" ? num(v, 2) : v))]),
      { mono: [0, 1] }),
    B.table("白度 / 黄度", ["颜色", ...Object.keys(p.rows[0].whiteness).slice(0, 3), ...Object.keys(p.rows[0].yellowness).slice(0, 2)],
      p.rows.map((row) => [row.hex,
        ...Object.values(row.whiteness).slice(0, 3).map((v) => (typeof v === "number" ? num(v, 2) : v)),
        ...Object.values(row.yellowness).slice(0, 2).map((v) => (typeof v === "number" ? num(v, 2) : v))]),
      { mono: [0], note: p.domain }),
  ],
};

LIVE["rgb-spaces"] = {
  endpoint: "GET /api/v1/spaces",
  hint: "96 个 RGB 色彩空间的基色、白点与传递函数。",
  fields: [{ key: "limit", label: "显示前 N 个", kind: "select", options: ["10", "20", "96"], value: "10" }],
  query: (s) => ({ limit: s.limit }),
  body: null,
  blocks: (p) => [
    B.table(`RGB 色彩空间（共 ${p.total} 个，显示 ${p.count} 个）`, ["名称", "基色", "白点", "传递函数", "线性"],
      p.spaces.map((row) => [row.name,
        (row.primaries || []).map((xy) => `(${num(xy[0], 3)}, ${num(xy[1], 3)})`).join(" "),
        row.whitepoint ? `(${num(row.whitepoint[0], 4)}, ${num(row.whitepoint[1], 4)})` : "—",
        row.cctf, row.linear ? "是" : "否"]),
      { mono: [0, 2, 3] }),
  ],
};

LIVE.catalog = {
  endpoint: "GET /api/v1/catalog",
  hint: "1284 条子模块导出 × 归属状态，可按关键字/状态过滤。",
  fields: [
    { key: "q", label: "关键字", kind: "text", value: "" },
    { key: "status", label: "状态", kind: "select", options: ["全部", "面板", "数据集", "内部"], value: "全部" },
  ],
  query: (s) => ({ q: s.q || "", status: s.status === "全部" ? "" : s.status, limit: 60 }),
  body: null,
  blocks: (p) => [
    { type: "stats", title: "覆盖口径", items: [
      [String(p.total), "子模块导出", "25 个子模块"],
      [String(p.counts["面板"]), "面板", "可填表单的入口"],
      [String(p.counts["数据集"]), "数据集", "下拉框里的选项"],
      [String(p.counts["内部"]), "内部复用", "utilities / algebra / hints"],
      [`${p.coverage}%`, "覆盖率", "不允许未分类"],
    ] },
    B.table(`匹配 ${p.matched} 条（显示前 ${p.rows.length} 条）`, ["子模块", "名称", "类型", "归属面板", "状态"],
      p.rows.map((row) => [row.module, row.name, row.kind, row.target + (p.panel_titles[row.target] ? ` ${p.panel_titles[row.target]}` : ""), row.status]),
      { mono: [1] }),
    B.table("子模块分布", ["子模块", "导出数", "主归属"], p.modules.map((row) => [row.name, row.count, `${row.panel} ${row.panel_title}`]), { mono: [1] }),
  ],
};

LIVE.invoke = {
  endpoint: "POST /api/v1/catalog/invoke",
  hint: "白名单调用：选函数 → 按声明填参数（JSON）→ 服务端校验后调 colour，不用 eval。",
  fields: () => {
    const list = (api.whitelist || []).map((row) => row.name);
    return [
      { key: "function", label: "函数（白名单）", kind: "select", options: list.length ? list : ["（先连上服务端）"], value: list[0] || "" },
      { key: "params", label: "参数（JSON）", kind: "text", value: JSON.stringify((api.whitelist && api.whitelist[0] && api.whitelist[0].example) || {}) },
    ];
  },
  body: (s) => {
    let params = {};
    try { params = JSON.parse(s.params || "{}"); } catch (error) { params = {}; }
    return { function: s.function, params };
  },
  blocks: (p) => [
    B.kv("调用结果", [
      ["函数", p.function, p.panel ? `面板 ${p.panel}` : ""],
      ["返回", p.returns, "按白名单声明"],
      ["参数", JSON.stringify(p.request.keyword && Object.keys(p.request.keyword).length ? { positional: p.request.positional, keyword: p.request.keyword } : p.request.positional), "已校验"],
      ["结果", JSON.stringify(p.result), ""],
    ]),
    B.json("响应片段", { result: p.result, warnings: p.warnings.map((w) => w.message) }),
  ],
};

LIVE.api = {
  endpoint: "GET /openapi.json",
  hint: "面板 28 就是 FastAPI 自动生成的 OpenAPI：路径、请求体与错误模型都在这里。",
  fields: [],
  body: null,
  blocks: (p) => [
    B.kv("规范", [
      ["标题", p.info.title, ""],
      ["版本", p.info.version, "colour-demo"],
      ["路径数", String(Object.keys(p.paths).length), "含 /health、/demo"],
    ]),
    B.table("端点与摘要", ["路径", "方法", "摘要"],
      Object.entries(p.paths).flatMap(([path, methods]) => Object.entries(methods).map(([method, spec]) => [path, method.toUpperCase(), spec.summary || "—"])),
      { mono: [0, 1] }),
  ],
};
