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

/* 参考面板入口：专家模式保持原样；新手模式先给一句说明（W5 逐页换成新手模板） */
function renderRefPanel(panel) {
  renderPanel(panel);
  if (State.mode !== "beginner") return;
  const main = $("#main");
  if (!main) return;
  const note = document.createElement("div");
  note.className = "beginner-note";
  note.innerHTML = "<b>这一页的新手说明还在接入</b><span>下面先显示专业原文；首页的 6 个任务已经是人话版。</span>";
  main.prepend(note);
}
