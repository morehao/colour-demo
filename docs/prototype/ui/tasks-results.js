/* tasks-results.js：T4/T5/T6 的新手结果视图 */

function renderCvdResult(payload, container, meta) {
  const rows = payload.rows || [];
  const metrics = payload.metrics || {};
  const min = metrics.min_adjacent_delta_e;
  if (min == null) {
    container.innerHTML = renderNote("warn", "这套配色算不出相邻差", "至少给两个颜色。");
    return;
  }
  const collisions = metrics.collisions || [];
  const extra = `${esc(payload.label)} 下，相邻两块最小只剩 ${Verdict.format("cvd", min)}；${
    collisions.length ? `有 ${collisions.length} 对会糊在一起。` : "没有明显冲突。"
  }`;
  const before = B.swatches("原来的配色", rows.map((row, index) => ({ hex: row.hex, label: `#${index + 1}`, sub: row.hex })), Math.min(8, rows.length));
  const after = B.swatches(`${payload.label} 看到的样子`, rows.map((row, index) => ({ hex: row.simulated_hex, label: `#${index + 1}`, sub: `ΔE ${num(row.delta_e, 1)}` })), Math.min(8, rows.length));
  const collisionNote = collisions.length
    ? renderNote("warn", "这几对会糊在一起", collisions.map((item) => `${esc(item.a)} ↔ ${esc(item.b)}（${Verdict.format("cvd", item.delta_e)}）`).join("；"))
    : "";
  container.innerHTML = `
    ${Verdict.card({ title: "最接近的两块", ruleId: "cvd", value: min, extra })}
    ${renderBlock(before)}
    ${renderBlock(after)}
    ${collisionNote}
    ${taskMeta(meta)}`;
}

function renderLightResult(payload, container, meta) {
  const methods = payload.methods || [];
  const method = methods[0] || "CIE 1994";
  const rows = (payload.rows || [])
    .map((row) => ({ ...row, result: row.results && row.results[method] }))
    .filter((row) => row.result);
  if (!rows.length) {
    container.innerHTML = renderNote("warn", "换灯结果为空", "换一个颜色或光源再试。");
    return;
  }
  const worst = rows.reduce((a, b) => (Number(b.result.delta_e) > Number(a.result.delta_e) ? b : a));
  const extra = `${esc(payload.source.name)} → ${esc(payload.target.name)}，按 ${esc(method)} 算：${esc(worst.hex)} 会变成 ${esc(worst.result.hex)}，差 ${Verdict.format("shift", worst.result.delta_e)}。换方法数字会变。`;
  const compare = `<div class="card"><div class="card-head"><h2>前后对比</h2></div><div class="card-body">${rows
    .map((row, index) => `<div class="compare-pair">
      <div class="compare-item"><span>原来 #${index + 1}</span>
        <div class="compare-sw" style="background:${esc(row.hex)}"></div><code>${esc(row.hex)}</code></div>
      <span class="compare-arrow">→</span>
      <div class="compare-item"><span>换到 ${esc(payload.target.name)}</span>
        <div class="compare-sw" style="background:${esc(row.result.hex)}"></div><code>${esc(row.result.hex)}</code>
        <em>ΔE ${num(row.result.delta_e, 2)}</em></div>
    </div>`)
    .join("")}</div></div>`;
  container.innerHTML = `
    ${Verdict.card({ title: `换到 ${esc(payload.target.name)} 后`, ruleId: "shift", value: worst.result.delta_e, extra })}
    ${compare}
    ${taskMeta(meta)}`;
}

function renderNotationResult(payload, state, container, meta) {
  const text = String(state.value || "").trim();
  let item = null;
  if (text.startsWith("#")) {
    item = { kind: "HEX", input: text, hex: payload.hex && payload.hex.canonical, rgb: payload.hex && payload.hex.rgb, munsell: null };
  } else if (text.includes("/")) {
    item = { kind: "Munsell", input: text, hex: payload.munsell && payload.munsell.hex, rgb: payload.munsell && payload.munsell.rgb, munsell: payload.munsell && payload.munsell.back };
  } else {
    item = { kind: "CSS 颜色名", input: text, hex: payload.keyword && payload.keyword.hex, rgb: payload.keyword && payload.keyword.rgb, munsell: null };
  }
  if (!item.hex) {
    container.innerHTML = renderNote("warn", "这个写法没认出来", "支持 #3B82F6、tomato、5R 5/12。换一个再试。");
    return;
  }
  const rgb = Array.isArray(item.rgb) ? item.rgb.map((value) => Math.round(Number(value) * 255)).join(", ") : "—";
  const sentence = Verdict.text("translate", { input: `「${text}」`, hex: item.hex, rgb });
  const munsell = item.munsell ? ` 往回写成 Munsell 是 <b>${esc(item.munsell)}</b>。` : "";
  const cards = [
    ["HEX", item.hex, true],
    ["RGB", rgb, true],
    ["识别为", item.kind, false],
  ];
  if (item.munsell) cards.push(["Munsell", item.munsell, true]);
  container.innerHTML = `
    ${Verdict.plain({ title: "同一个颜色，几种写法", html: sentence + munsell })}
    <div class="notation-cards">${cards
      .map(([label, value, copy]) => `<div class="notation-card"><span>${esc(label)}</span><b>${esc(value)}</b>
        ${copy ? `<button type="button" class="btn-ghost" data-copy-value="${esc(value)}">复制</button>` : ""}</div>`)
      .join("")}</div>
    ${taskMeta(meta)}`;
}
