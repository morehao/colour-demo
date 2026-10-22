/* panels.js：参考面板视图（专家视图沿用原渲染） */

/* ---------------- panels ---------------- */
function renderControls(panel) {
  const spec = LIVE[panel.id];
  if (spec && api.ok) {
    return `<div class="controls">${liveFields(spec).map(renderField).join("")}
      <div class="field field--run"><span>&nbsp;</span><button id="run-live" type="button">调用 API</button></div>
    </div>
    <div class="ctrl-note" id="live-status">${esc(spec.hint || "改完参数点「调用 API」，结果由服务端现算。")}</div>`;
  }
  if (!panel.controls.length) return "";
  return `<div class="controls">${panel.controls
    .map((c) => {
      if (c.kind === "color") {
        return `<div class="field"><span>${esc(c.label)}</span><div class="color-field"><input type="color" value="${esc(c.value)}" disabled><input type="text" value="${esc(c.value)}" disabled></div></div>`;
      }
      if (c.kind === "select") {
        return `<div class="field"><span>${esc(c.label)}</span><select disabled>${c.options.map((o) => `<option${o === c.value ? " selected" : ""}>${esc(o)}</option>`).join("")}</select></div>`;
      }
      if (c.kind === "range") {
        return `<div class="field"><span>${esc(c.label)}</span><input type="range" min="0" max="100" step="5" value="${esc(c.value)}" disabled></div>`;
      }
      return `<div class="field"><span>${esc(c.label)}</span><input type="text" value="${esc(c.value)}" disabled></div>`;
    })
    .join("")}</div>
    <div class="ctrl-note">${spec ? "本页有实时适配器，但没连上本地服务端：启动 <code>uvicorn colour_demo.main:app --port 8000</code> 后刷新即可切换为实时调用。" : "原型为静态快照：导航与能力目录搜索可用，其余控件为样式占位（正式版接 API 后启用）。"}</div>`;
}

function renderPanel(panel) {
  const spec = LIVE[panel.id];
  const liveCapable = Boolean(spec) && api.ok;
  const snapshot = panel.blocks.map(renderBlock).join("");
  $("#main").innerHTML = `
    <div class="panel-head">
      <div class="eyebrow">Panel ${panel.no} · ${esc(panel.group)}
        <span class="tag ${PHASE_CLASS[panel.phase] || ""}" style="margin-left:8px">${esc(panel.phase)}</span>
        ${panel.pending ? '<span class="tag tag--pending" style="margin-left:6px">数据待补充</span>' : ""}
        ${liveCapable ? '<span class="tag tag--m2" style="margin-left:6px">实时 API</span>' : ""}</div>
      <h1>${esc(panel.title)}</h1>
      <p class="lead">${panel.lead.replace(/\*\*(.+?)\*\*/g, "<b>$1</b>")}</p>
    </div>
    <div class="card">${renderControls(panel)}</div>
    ${liveCapable
      ? `<div class="live-out" id="live-out"></div>
         <details class="snapshot"><summary>静态快照 · 构建时由 colour ${esc(DATA.lib.version)} 计算（离线可用）</summary>${snapshot}</details>`
      : snapshot}
    <footer class="page-foot">${panel.footer.replace(/`([^`]+)`/g, "<code>$1</code>")}<br>
      本页快照数据由 <code>colour-science ${DATA.lib.version}</code> 于构建时计算；APIs：${panel.apis.map((a) => `<code>${esc(a)}</code>`).join(" · ")}</footer>`;
  wirePanel(panel);
}

/* 能力目录：真实可用的搜索与状态过滤 */
function wirePanel(panel) {
  const spec = LIVE[panel.id];
  if (spec && api.ok) {
    const run = $("#run-live");
    if (run) run.addEventListener("click", () => runLive(panel, spec));
    document.querySelectorAll("[data-live-key]").forEach((element) => {
      element.addEventListener("keydown", (event) => {
        if (event.key === "Enter") runLive(panel, spec);
      });
      element.addEventListener("change", () => {
        const mirror = document.querySelector(`[data-live-out="${element.dataset.liveKey}"]`);
        if (mirror) mirror.textContent = element.value;
      });
    });
    // 打开面板就先跑一次：这一页的控件不是摆设，数字是现算的
    runLive(panel, spec);
    return;
  }
  if (panel.id !== "catalog") return;
  const search = $(".controls input[type=text]");
  const status = $(".controls select");
  const rows = Array.from(document.querySelectorAll('table.data[data-filterable] tbody tr'));
  const apply = () => {
    const q = (search?.value || "").toLowerCase();
    const st = status?.value || "全部";
    rows.forEach((tr) => {
      const text = tr.textContent.toLowerCase();
      const cells = tr.children;
      const rowStatus = cells[cells.length - 1].textContent.trim();
      tr.style.display = (!q || text.includes(q)) && (st === "全部" || rowStatus === st) ? "" : "none";
    });
  };
  if (search) { search.disabled = false; search.addEventListener("input", apply); }
  if (status) { status.disabled = false; status.addEventListener("change", apply); }
  const note = document.querySelector(".ctrl-note");
  if (note) note.textContent = "本页控件在本原型中真实可用：输入关键字过滤名称，或按状态（面板 / 数据集 / 内部）筛选。";
}

/* 新手预览：优先挑最直观的一块，表格只露前 8 行 */
function beginnerPreview(panel) {
  const order = ["swatches", "strips", "chain", "image", "chart", "matrix", "stats", "table", "kv"];
  const preferred = panel.preview ? panel.blocks.find((item) => item.type === panel.preview) : null;
  const block = preferred || order.map((type) => panel.blocks.find((item) => item.type === type)).find(Boolean);
  if (!block) return "";
  if (block.type === "table" && block.rows.length > 8) {
    return renderBlock({
      ...block,
      rows: block.rows.slice(0, 8),
      note: `只显示前 8 行；完整 ${block.rows.length} 行在「原理与专业参数」里。`,
    });
  }
  return renderBlock(block);
}

function panelVerdictCard(panel) {
  if (panel.verdict_html) {
    return Verdict.plain({ title: "一眼结论", html: panel.verdict_html, tone: panel.verdict_tone || "ok" });
  }
  if (!panel.verdict || !Number.isFinite(Number(panel.verdict_value))) return "";
  return Verdict.card({
    title: "一眼结论",
    ruleId: panel.verdict,
    value: Number(panel.verdict_value),
    extra: panel.verdict_extra || "",
  });
}

function panelPresetCard(panel) {
  if ((panel.presets || []).length !== 3) return "";
  const ready = api.ok;
  return `<section class="card preset-card"><div class="card-head"><h2>换组参数看看</h2>
    <span class="hint">${ready ? "点一下，实时重算" : "需要本地服务"}</span></div>
    <div class="card-body"><div class="preset-row" role="group" aria-label="参数示例">${panel.presets
      .map((preset) => `<button type="button" class="preset" data-panel-preset="${esc(preset.id)}" aria-pressed="false"${ready ? "" : " disabled"}>${esc(preset.label)}</button>`)
      .join("")}</div><div class="panel-live-out" id="panel-live-out">${ready
        ? "点上面的示例，结果会按当前参数重算。"
        : "当前是构建期快照；启动本地服务后，示例可实时重算。"}</div></div></section>`;
}

async function runPanelPreset(panel, presetId) {
  const spec = LIVE[panel.id];
  const preset = (panel.presets || []).find((item) => item.id === presetId);
  const out = $("#panel-live-out");
  if (!spec || !preset || !out) return;
  const state = Object.fromEntries(liveFields(spec).map((field) => [field.key, field.value]));
  Object.assign(state, preset.state);
  out.textContent = "重新计算…";
  try {
    const target = spec.dataEndpoint ? { endpoint: spec.dataEndpoint, query: spec.query } : spec;
    const { payload, elapsed } = await apiCall(target, state);
    out.innerHTML = `<p class="small muted">实时结果 · ${elapsed} ms · ${esc(spec.endpoint)}</p>` +
      spec.blocks(payload, state).map(renderBlock).join("");
    if (typeof annotateTerms === "function") annotateTerms(out);
  } catch (error) {
    out.innerHTML = renderNote("warn", "没算出来", esc(humanError(error)));
  }
}

function wirePanelPresets(panel) {
  const buttons = Array.from(document.querySelectorAll("[data-panel-preset]"));
  if (!buttons.length) return;
  buttons.forEach((button) => button.addEventListener("click", () => {
    buttons.forEach((item) => item.setAttribute("aria-pressed", String(item === button)));
    runPanelPreset(panel, button.dataset.panelPreset);
  }));
}

function renderReadCard(panel) {
  const lines = panel.read || [];
  if (!lines.length) return "";
  return `<div class="card read-card"><div class="card-head"><h2>这页的数字怎么读</h2></div>
    <div class="card-body"><ol class="read-list">${lines
      .map((line) => `<li class="js-prose">${esc(line)}</li>`)
      .join("")}</ol></div></div>`;
}

function renderBeginnerPanel(panel) {
  const all = DATA.panels;
  const index = all.findIndex((item) => item.id === panel.id);
  const prev = index > 0 ? all[index - 1] : null;
  const next = index >= 0 && index < all.length - 1 ? all[index + 1] : null;
  const task = DATA.tasks.find((item) => item.tool === panel.id);
  const lead = panel.lead.replace(/\*\*(.+?)\*\*/g, "<b>$1</b>");
  const footer = panel.footer
    ? `<footer class="page-foot">${panel.footer.replace(/`([^`]+)`/g, "<code>$1</code>")}</footer>`
    : "";
  $("#main").innerHTML = `
    <nav class="crumbs"><a href="#/">首页</a><span>›</span><a href="#/ref">参考手册</a>
      <span>›</span>${esc(panel.group)}<span>›</span>${esc(panel.title_plain)}</nav>
    <div class="panel-head beginner-head">
      <div class="eyebrow">Panel ${panel.no} · ${esc(panel.group)}
        <span class="tag ${PHASE_CLASS[panel.phase] || ""}" style="margin-left:8px">${esc(panel.phase)}</span>
        ${panel.pending ? '<span class="tag tag--pending" style="margin-left:6px">数据待补充</span>' : ""}</div>
      <h1>${esc(panel.title_plain)}</h1>
      <p class="pro-name">专业名：${esc(panel.title)}</p>
      <p class="lead js-prose">${esc(panel.plain)}</p>
      <div class="answer-tag"><span>这页能回答</span><b class="js-prose">${esc(panel.question)}</b></div>
      <p class="small muted">什么时候用：${esc(panel.why)}</p>
    </div>
    ${panelVerdictCard(panel)}
    ${beginnerPreview(panel)}
    ${panelPresetCard(panel)}
    ${renderReadCard(panel)}
    <details class="principles">
      <summary>原理与专业参数</summary>
      <div class="principles-body">
        <p class="small muted">档位是经验参考，不是标准强制值；换算法、换观察条件，数字都会变。</p>
        <p class="lead js-prose">${lead}</p>
        ${panel.blocks.map(renderBlock).join("")}
        ${footer}
        <p class="small muted">本页数据由 <code>colour-science ${DATA.lib.version}</code> 于构建时计算；相关接口：${panel.apis
          .map((api) => `<code>${esc(api)}</code>`)
          .join(" · ")}</p>
      </div>
    </details>
    <div class="next-row">
      ${task ? `<a class="btn-primary" href="#/task/${task.id}">去做：${esc(task.title)} →</a>` : ""}
      <a class="btn-ghost" href="#/glossary">翻术语表</a>
      ${prev ? `<a class="btn-ghost" href="#/ref/${prev.id}">← ${esc(prev.title_plain || prev.title)}</a>` : ""}
      ${next ? `<a class="btn-ghost" href="#/ref/${next.id}">${esc(next.title_plain || next.title)} →</a>` : ""}
    </div>`;
  if (typeof annotateTerms === "function") annotateTerms($("#main"));
  wirePanelPresets(panel);
}

/* 参考面板入口：专家模式保持原样；新手模式按 8.1 模板渲染 */
function renderRefPanel(panel) {
  if (State.mode === "beginner" && panel.title_plain) {
    renderBeginnerPanel(panel);
    return;
  }
  renderPanel(panel);
}
