/* tasks.js：6 个任务页（M2 先接 ΔE，其余给快照与延伸入口） */

function taskById(id) {
  return DATA.tasks.find((task) => task.id === id);
}

function taskHeader(task) {
  return `<div class="panel-head task-head">
    <div class="eyebrow"><a href="#/">← 全部任务</a> · 约 ${esc(task.est)}</div>
    <h1>${esc(task.title)}</h1>
    <p class="lead js-prose">${esc(task.intro)}</p>
    ${renderSteps(task.steps)}
    <div class="task-share">
      <button type="button" class="btn-ghost btn-mini" data-share-task>复制本页链接</button>
      <span class="small muted">链接会带上当前输入</span>
    </div>
  </div>`;
}

function renderPrinciples(task) {
  return `<details class="principles">
    <summary>原理与专业参数</summary>
    <div class="principles-body js-prose">
      <p class="small muted">档位是经验参考，不是标准强制值；换算法、换观察条件，数字都会变。</p>
      ${task.explain.map((paragraph) => `<p>${esc(paragraph)}</p>`).join("")}
      <p class="small">术语：${task.jargon
        .map((key) => DATA.glossary[key] && DATA.glossary[key].term)
        .filter(Boolean)
        .join(" · ")}</p>
      <p class="small">相关参考页：${task.related
        .map((id) => {
          const panel = DATA.panels.find((item) => item.id === id);
          return panel ? `<a href="#/ref/${panel.id}">${esc(panel.title_plain || panel.title)}</a>` : "";
        })
        .filter(Boolean)
        .join(" · ")}</p>
    </div>
  </details>`;
}

function renderTask(route) {
  const task = taskById(route.id);
  if (!task) {
    navigate("#/");
    return;
  }
  if (task.id === "delta-e") renderDeltaETask(task);
  else if (typeof renderTaskPage === "function") renderTaskPage(task);
  else renderTaskPlaceholder(task);
}

function taskStateFor(task) {
  if (!State.taskState[task.id]) {
    const preset = task.presets[0];
    const state = { ...preset.state };
    if (Array.isArray(preset.state.colors)) state.colors = [...preset.state.colors];
    State.taskState[task.id] = state;
  }
  const state = State.taskState[task.id];
  // 分享链接把输入放在 hash 的 query 里：`#/task/purity?colors=%23...&illuminant=A`
  // 每次进入任务页都读一次，保证同一会话里点分享链接也能覆盖旧状态。
  const params = new URLSearchParams((location.hash.split("?")[1] || ""));
  task.fields.forEach((field) => {
    if (!params.has(field.key)) return;
    const raw = params.get(field.key);
    if (field.kind === "colors") {
      const colors = raw.split(",").map(normalizeHex).filter(Boolean);
      if (colors.length >= (field.min || 1) && colors.length <= (field.max || 12)) state.colors = colors;
    } else if (field.kind === "number") {
      const value = Number(raw);
      if (Number.isFinite(value)) {
        state[field.key] = Math.max(Number(field.min), Math.min(Number(field.max), Math.round(value)));
      }
    } else if (field.kind === "color") {
      const hex = normalizeHex(raw);
      if (hex) state[field.key] = hex;
    } else if (field.kind === "select" || field.kind === "method") {
      // 色差任务的 task.fields 只放默认算法，完整选项在 LIVE 适配器里
      const live = typeof LIVE !== "undefined" ? LIVE[task.tool] : null;
      const liveFields = live ? (typeof live.fields === "function" ? live.fields() : live.fields || []) : [];
      const liveField = liveFields.find((item) => item.key === field.key);
      const options = (field.options || []).length > 1 ? field.options : (liveField && liveField.options) || field.options || [];
      if (options.includes(raw)) state[field.key] = raw;
    } else if (raw) {
      state[field.key] = raw;
    }
  });
  return state;
}

function syncTaskQuery(task, state) {
  if (State.route.type !== "task" || State.route.id !== task.id) return;
  const params = new URLSearchParams();
  task.fields.forEach((field) => {
    const value = state[field.key];
    if (value === undefined || value === null || value === "") return;
    params.set(field.key, Array.isArray(value) ? value.join(",") : String(value));
  });
  const suffix = params.toString() ? `?${params.toString()}` : "";
  const next = `#/task/${task.id}${suffix}`;
  if (location.hash !== next) history.replaceState(null, "", next);
}

function renderTaskPlaceholder(task) {
  const links = task.related
    .map((id) => DATA.panels.find((panel) => panel.id === id))
    .filter(Boolean)
    .map((panel) => `<a class="btn-ghost" href="#/ref/${panel.id}">${esc(panel.title_plain || panel.title)} →</a>`)
    .join(" ");
  $("#main").innerHTML = `
    ${taskHeader(task)}
    <div class="card"><div class="card-body">
      <h2 class="placeholder-title">这个任务页正在接入</h2>
      <p class="lead js-prose">数据、预设和结论规则已经就绪。接入前，可以先看相关参考页的完整数据。</p>
      <p class="placeholder-links">${links}</p>
    </div></div>
    ${renderPrinciples(task)}`;
}

/* ---------------- T2：两个颜色差多少 ---------------- */
let deltaESequence = 0;

function renderDeltaETask(task) {
  const state = taskStateFor(task);
  const methods = (LIVE["delta-e"] && LIVE["delta-e"].fields.find((field) => field.key === "method").options) || ["CIE 2000"];
  const active = task.presets.find((preset) => sameState(preset.state, state));
  $("#main").innerHTML = `
    ${taskHeader(task)}
    <div class="task-grid-2">
      <section class="card task-controls">
        <div class="card-head"><h2>你的两个颜色</h2><span class="hint">改完自动算</span></div>
        <div class="card-body">
          <div id="color-list-host">${renderColorList(state.colors, { min: 2, max: 12 })}</div>
          <label class="field"><span>配色差的算法</span>
            <select id="de-method">${methods
              .map((method) => `<option${method === state.method ? " selected" : ""}>${esc(method)}</option>`)
              .join("")}</select>
          </label>
          <p class="small muted">不确定选哪个就用默认的 CIE 2000。</p>
        </div>
        <div class="card-foot"><div id="preset-host">${renderPresets(task, active && active.id)}</div></div>
      </section>
      <section id="task-result" class="task-result" aria-live="polite" aria-busy="true"></section>
    </div>
    ${renderPrinciples(task)}`;

  wireDeltaETask(task, state);
  computeDeltaE(task, state);
}

function wireDeltaETask(task, state) {
  let timer = null;
  const schedule = () => {
    clearTimeout(timer);
    timer = setTimeout(() => computeDeltaE(task, state), 250);
  };

  const host = $("#color-list-host");
  wireColorList(host, state, { min: 2, max: 12 }, schedule);

  $("#de-method").addEventListener("change", (event) => {
    state.method = event.target.value;
    computeDeltaE(task, state);
  });

  $("#preset-host").addEventListener("click", (event) => {
    const button = event.target.closest("[data-preset]");
    if (!button) return;
    const preset = task.presets.find((item) => item.id === button.dataset.preset);
    if (!preset) return;
    state.colors = [...preset.state.colors];
    state.method = preset.state.method;
    host.innerHTML = renderColorList(state.colors, { min: 2, max: 12 });
    wireColorList(host, state, { min: 2, max: 12 }, schedule);
    $("#de-method").value = state.method;
    document.querySelectorAll("[data-preset]").forEach((item) =>
      item.setAttribute("aria-pressed", String(item === button))
    );
    computeDeltaE(task, state);
  });

  const result = $("#task-result");
  result.addEventListener("click", (event) => {
    if (event.target.closest("[data-retry]")) computeDeltaE(task, state);
  });
}

async function computeDeltaE(task, state) {
  const result = $("#task-result");
  if (!result) return;
  const sequence = ++deltaESequence;
  syncTaskQuery(task, state);
  result.setAttribute("aria-busy", "true");

  if (!api.ok) {
    const preset = task.presets.find((item) => sameState(item.state, state));
    if (!preset) {
      result.innerHTML = renderNote(
        "info",
        "离线只能看预设",
        "当前颜色组合没有构建期快照。启动本地服务后即可任意改颜色；也可以点下面的预设先看示例。"
      );
      result.removeAttribute("aria-busy");
      return;
    }
    renderDeltaEResult(result, task.snapshots[preset.id], state, { offline: true, presetLabel: preset.label });
    result.removeAttribute("aria-busy");
    return;
  }

  try {
    const spec = {
      endpoint: "POST /api/v1/delta-e",
      body: (current) => ({ colors: current.colors, method: current.method }),
    };
    const { payload, elapsed } = await apiCall(spec, state);
    if (sequence !== deltaESequence) return;
    renderDeltaEResult(result, payload, state, { elapsed });
  } catch (error) {
    if (sequence !== deltaESequence) return;
    result.innerHTML = `<div class="note-box note-warn">
      <span class="b">没算出来</span><span>${esc(humanError(error))}</span>
      <button type="button" class="btn-ghost" data-retry>重试</button>
    </div>`;
  } finally {
    if (sequence === deltaESequence) result.removeAttribute("aria-busy");
  }
}

function renderDeltaEResult(container, payload, state, meta) {
  const pairs = payload.pairs || {};
  const closest = pairs.closest;
  const method = payload.method || state.method;
  if (!closest) {
    container.innerHTML = renderNote("warn", "这组颜色算不出结论", "至少需要两个颜色，且都能被识别。");
    return;
  }
  const sentence = `这组颜色里，最接近的一对是 <b>${esc(closest.a)}</b> 和 <b>${esc(closest.b)}</b>，差 <b>${Verdict.format("deltaE", closest.value)}</b>。`;
  const matrix = B.matrix(
    `ΔE 矩阵（${method}）`,
    payload.colors || state.colors,
    payload.matrix,
    "对角线不参与比较；颜色越深，差得越多。"
  );
  container.innerHTML = `
    ${Verdict.card({ title: "结论", ruleId: "deltaE", value: closest.value, extra: sentence })}
    ${renderBlock(matrix)}
    <div class="card">
      <div class="card-head"><h2>最远的一对</h2></div>
      <div class="card-body"><p>${esc(pairs.farthest.a)} ↔ ${esc(pairs.farthest.b)} · ΔE ${Verdict.format("deltaE", pairs.farthest.value)}</p></div>
    </div>
    ${meta.offline ? renderNote("info", "离线快照", `当前显示预设「${esc(meta.presetLabel)}」的构建期结果；改颜色需要本地服务。`) : ""}
    ${meta.elapsed ? `<p class="small muted">实时结果 · ${meta.elapsed} ms · colour ${esc(api.version || "")}</p>` : ""}`;
  if (typeof annotateTerms === "function") annotateTerms(container);
}

function refreshTaskResult() {
  if (State.route.type !== "task") return;
  const task = taskById(State.route.id);
  const state = task && State.taskState[task.id];
  if (!task || !state) return;
  if (task.id === "delta-e") computeDeltaE(task, state);
  else if (typeof computeTask === "function") computeTask(task, state);
}

/* 复制当前任务的输入链接；状态已同步在 hash 里，刷新/发给别人都能还原 */
document.addEventListener("click", (event) => {
  const button = event.target.closest("[data-share-task]");
  if (!button) return;
  if (State.route.type !== "task") return;
  const task = taskById(State.route.id);
  const state = task && State.taskState[task.id];
  if (!task || !state) return;
  syncTaskQuery(task, state);
  copyText(location.href);
});
