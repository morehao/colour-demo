/* tasks-more.js：T1/T3/T4/T5/T6 的输入、在线重算与新手结果 */

const TASK_SPECS = {
  purity: {
    endpoint: "POST /api/v1/chroma",
    body: (state) => ({ colors: state.colors, illuminant: state.illuminant }),
  },
  gradient: {
    endpoint: "POST /api/v1/gradient",
    body: (state) => ({
      from: state.from,
      to: state.to,
      space: state.space,
      steps: Number(state.steps),
    }),
  },
  cvd: {
    endpoint: "POST /api/v1/cvd",
    body: (state) => ({ colors: state.colors, deficiency: state.deficiency }),
  },
  light: {
    endpoint: "POST /api/v1/adapt",
    body: (state) => ({
      colors: state.colors,
      source: state.source,
      target: state.target,
      include_matrices: false,
    }),
  },
  notation: {
    endpoint: "POST /api/v1/notation",
    body: (state) => notationBody(state.value),
  },
};

function normalizeHex(value) {
  const text = String(value || "").trim().toUpperCase();
  const short = /^#([0-9A-F])([0-9A-F])([0-9A-F])$/.exec(text);
  if (short) return `#${short[1]}${short[1]}${short[2]}${short[2]}${short[3]}${short[3]}`;
  return /^#[0-9A-F]{6}$/.test(text) ? text : null;
}

function notationBody(value) {
  const text = String(value || "").trim();
  if (text.startsWith("#")) return { hex: text };
  if (text.includes("/")) return { munsell: text };
  return { keyword: text };
}

function findTaskPreset(task, state) {
  let preset = task.presets.find((item) => sameState(item.state, state));
  // 渐变快照一次包含三个空间；换“重点看哪个”仍算同一个预设
  if (!preset && task.id === "gradient") {
    preset = task.presets.find((item) =>
      ["from", "to", "steps"].every((key) => String(item.state[key]) === String(state[key]))
    );
  }
  return preset;
}

function renderTaskPage(task) {
  const state = taskStateFor(task);
  const active = task.presets.find((preset) => sameState(preset.state, state)) || findTaskPreset(task, state);
  $("#main").innerHTML = `
    ${taskHeader(task)}
    <div class="task-grid-2">
      <section class="card task-controls">
        <div class="card-head"><h2>你的输入</h2><span class="hint">改完自动算</span></div>
        <div class="card-body" id="task-fields">${task.fields.map((field) => renderTaskField(field, state)).join("")}</div>
        <div class="card-foot"><div id="preset-host">${renderPresets(task, active && active.id)}</div></div>
      </section>
      <section id="task-result" class="task-result" aria-live="polite" aria-busy="true"></section>
    </div>
    ${renderPrinciples(task)}`;
  wireTaskPage(task, state);
  computeTask(task, state);
}

function renderTaskField(field, state) {
  const key = esc(field.key);
  const label = `<span>${esc(field.label)}</span>`;
  const value = state[field.key];
  if (field.kind === "colors") {
    return `<div class="field">${label}
      <div id="task-colors">${renderColorList(value, { min: field.min || 1, max: field.max || 12 })}</div>
    </div>`;
  }
  if (field.kind === "color") {
    return `<label class="field">${label}
      <div class="single-color">
        <input type="color" data-field="${key}" value="${esc(value)}" aria-label="${esc(field.label)}">
        <input type="text" class="hex-input" data-field="${key}" value="${esc(value)}" spellcheck="false"
          autocomplete="off" aria-label="${esc(field.label)} 的十六进制值">
      </div>
    </label>`;
  }
  if (field.kind === "select" || field.kind === "method") {
    const labels = field.option_labels || {};
    return `<label class="field">${label}
      <select data-field="${key}">${(field.options || [])
        .map((option) => `<option value="${esc(option)}"${String(option) === String(value) ? " selected" : ""}>${esc(labels[option] || option)}</option>`)
        .join("")}</select>
    </label>`;
  }
  if (field.kind === "number") {
    return `<label class="field">${label}
      <input type="number" data-field="${key}" value="${esc(value)}" min="${esc(field.min)}" max="${esc(field.max)}" step="1">
    </label>`;
  }
  return `<label class="field">${label}
    <input type="text" data-field="${key}" value="${esc(value)}" spellcheck="false" autocomplete="off">
    ${field.hint ? `<span class="small muted">${esc(field.hint)}</span>` : ""}
  </label>`;
}

function wireTaskPage(task, state) {
  let timer = null;
  const schedule = () => {
    clearTimeout(timer);
    timer = setTimeout(() => computeTask(task, state), 250);
  };
  const colors = $("#task-colors");
  if (colors) {
    const field = task.fields.find((item) => item.kind === "colors");
    wireColorList(colors, state, { min: field.min || 1, max: field.max || 12 }, schedule);
  }

  const host = $("#task-fields");
  host.addEventListener("input", (event) => {
    const key = event.target.dataset.field;
    if (!key) return;
    const field = task.fields.find((item) => item.key === key);
    if (!field) return;
    if (field.kind === "color") {
      const row = event.target.closest(".single-color");
      const hex = normalizeHex(event.target.value);
      if (!hex) {
        event.target.classList.add("is-bad");
        return;
      }
      event.target.classList.remove("is-bad");
      const text = row.querySelector(".hex-input");
      const picker = row.querySelector('input[type="color"]');
      text.value = hex;
      if (picker) picker.value = hex;
      state[key] = hex;
      schedule();
    } else if (field.kind === "notation") {
      state[key] = event.target.value;
      schedule();
    }
  });

  host.addEventListener("change", (event) => {
    const key = event.target.dataset.field;
    if (!key) return;
    const field = task.fields.find((item) => item.key === key);
    if (!field) return;
    if (field.kind === "select" || field.kind === "method") {
      state[key] = event.target.value;
      computeTask(task, state);
    } else if (field.kind === "number") {
      const min = Number(field.min);
      const max = Number(field.max);
      let next = Math.round(Number(event.target.value));
      if (!Number.isFinite(next)) next = Number(field.value);
      next = Math.max(min, Math.min(max, next));
      event.target.value = String(next);
      state[key] = next;
      computeTask(task, state);
    }
  });

  $("#preset-host").addEventListener("click", (event) => {
    const button = event.target.closest("[data-preset]");
    if (!button) return;
    const preset = task.presets.find((item) => item.id === button.dataset.preset);
    if (!preset) return;
    Object.entries(preset.state).forEach(([key, value]) => {
      state[key] = Array.isArray(value) ? [...value] : value;
    });
    renderTaskPage(task);
  });

  $("#task-result").addEventListener("click", (event) => {
    if (event.target.closest("[data-retry]")) computeTask(task, state);
    const copy = event.target.closest("[data-copy-value]");
    if (copy && typeof copyText === "function") copyText(copy.dataset.copyValue);
  });
}

let taskSequence = 0;

async function computeTask(task, state) {
  const result = $("#task-result");
  if (!result) return;
  const sequence = ++taskSequence;
  const preset = findTaskPreset(task, state);
  result.setAttribute("aria-busy", "true");

  if (task.id === "light" && state.source === state.target) {
    result.innerHTML = renderNote(
      "info",
      "同一盏灯不用换",
      "现在的光和要换到的光是同一盏，颜色不会变。把其中一个换成别的光再算。"
    );
    result.removeAttribute("aria-busy");
    return;
  }

  if (!api.ok) {
    if (!preset) {
      result.innerHTML = renderNote(
        "info",
        "离线只能看预设",
        "当前这组参数没有构建期快照。启动本地服务后即可任意改；也可以点下面的预设先看示例。"
      );
      result.removeAttribute("aria-busy");
      return;
    }
    renderTaskResult(task, result, task.snapshots[preset.id], state, { offline: true, presetLabel: preset.label });
    result.removeAttribute("aria-busy");
    return;
  }

  try {
    const { payload, elapsed } = await fetchTaskPayload(task, state);
    if (sequence !== taskSequence) return;
    renderTaskResult(task, result, payload, state, { elapsed });
  } catch (error) {
    if (sequence !== taskSequence) return;
    const message = task.id === "notation"
      ? "这个写法没认出来。支持 #3B82F6、tomato、5R 5/12。"
      : humanError(error);
    result.innerHTML = `<div class="note-box note-warn">
      <span class="b">没算出来</span><span>${esc(message)}</span>
      <button type="button" class="btn-ghost" data-retry>重试</button>
    </div>`;
  } finally {
    if (sequence === taskSequence) result.removeAttribute("aria-busy");
  }
}

async function fetchTaskPayload(task, state) {
  if (task.id !== "gradient") {
    const { payload, elapsed } = await apiCall(TASK_SPECS[task.id], state);
    return { payload, elapsed };
  }
  const spaces = {};
  let elapsed = 0;
  for (const space of ["Oklab", "CIE Lab", "sRGB"]) {
    const spec = {
      endpoint: TASK_SPECS.gradient.endpoint,
      body: (current) => ({ ...TASK_SPECS.gradient.body(current), space }),
    };
    const result = await apiCall(spec, state);
    spaces[space] = result.payload;
    elapsed += result.elapsed;
  }
  return { payload: { spaces }, elapsed };
}

function taskMeta(meta) {
  let html = "";
  if (meta.offline) {
    html += renderNote("info", "离线快照", `当前显示预设「${esc(meta.presetLabel)}」的构建期结果；改参数需要本地服务。`);
  }
  if (meta.elapsed) {
    html += `<p class="small muted">实时结果 · ${meta.elapsed} ms · colour ${esc(api.version || "")}</p>`;
  }
  return html;
}

function renderTaskResult(task, container, payload, state, meta) {
  if (task.id === "purity") renderPurityResult(payload, container, meta);
  else if (task.id === "gradient") renderGradientResult(payload, container, state, meta);
  else if (task.id === "cvd") renderCvdResult(payload, container, meta);
  else if (task.id === "light") renderLightResult(payload, container, meta);
  else if (task.id === "notation") renderNotationResult(payload, state, container, meta);
  if (typeof annotateTerms === "function") annotateTerms(container);
}

function renderPurityResult(payload, container, meta) {
  const rows = payload.rows || [];
  if (!rows.length) {
    container.innerHTML = renderNote("warn", "没有解析出颜色", "换一个 HEX 再试。");
    return;
  }
  const best = rows.reduce((a, b) => (Number(b.excitation_purity) > Number(a.excitation_purity) ? b : a));
  const wavelength = best.dominant_wavelength == null ? "没有明确主波长" : `最接近 ${num(best.dominant_wavelength, 0)} nm 的单色光`;
  const extra = `<b>${esc(best.hex)}</b> 是这组里最鲜艳的，${wavelength}；光源是 ${esc(payload.illuminant)}。`;
  const list = rows
    .map((row) => {
      const percent = Math.max(0, Math.min(100, Math.round(Number(row.excitation_purity || 0) * 100)));
      const band = Verdict.band("purity", row.excitation_purity);
      return `<div class="purity-item">
        <span class="purity-sw" style="background:${esc(row.hex)}"></span>
        <div><div class="meter"><i style="width:${percent}%"></i></div>
          <div class="small muted">${esc(row.hex)} · ${percent}% · 主波长 ${num(row.dominant_wavelength, 0)} nm</div></div>
        <span class="tag">${esc(band ? band.label : "")}</span>
      </div>`;
    })
    .join("");
  container.innerHTML = `
    ${Verdict.card({ title: "最鲜艳的一个", ruleId: "purity", value: best.excitation_purity, extra })}
    <div class="card"><div class="card-head"><h2>每个颜色的鲜艳度</h2></div>
      <div class="card-body"><div class="purity-list">${list}</div></div></div>
    ${taskMeta(meta)}`;
}

function renderGradientResult(payload, container, state, meta) {
  const spaces = payload.spaces || (payload.space ? { [payload.space]: payload } : {});
  const names = Object.keys(spaces);
  const selected = spaces[state.space] || spaces[names[0]];
  if (!selected || selected.uniformity.ratio == null) {
    container.innerHTML = renderNote("warn", "这条渐变算不出来", "换一组端点颜色再试。");
    return;
  }
  const uniformity = selected.uniformity;
  const deltas = (selected.deltas || []).filter((value) => Number.isFinite(Number(value)));
  const min = deltas.length ? Math.min(...deltas) : null;
  const extra = `在 ${esc(selected.space)} 里分 ${selected.steps} 步：相邻 ΔE 平均 ${num(uniformity.mean, 2)}，最挤的一步只有 ${num(min, 2)}。`;
  const ranked = names
    .map((name) => ({ name, ratio: spaces[name].uniformity.ratio }))
    .sort((a, b) => a.ratio - b.ratio);
  const best = ranked[0];
  const worst = ranked[ranked.length - 1];
  const ranking = `三条里最均匀的是 <b>${esc(best.name)}</b>（${Verdict.format("uniformity", best.ratio)}×），中段最挤的是 <b>${esc(worst.name)}</b>（${Verdict.format("uniformity", worst.ratio)}×）。`;
  const rows = names
    .map((name) => {
      const item = spaces[name];
      const hexes = (item.rows || []).map((row) => row.hex);
      const band = Verdict.band("uniformity", item.uniformity.ratio);
      return `<div class="gradient-row${name === selected.space ? " is-active" : ""}">
        <div class="gradient-head"><b>${esc(name)}</b>
          <span class="tag">${Verdict.format("uniformity", item.uniformity.ratio)}×</span>
          <span class="small muted">${esc(band ? band.label : "")}</span></div>
        <div class="strip-bar" style="background:linear-gradient(90deg,${hexes.join(",")})"></div>
      </div>`;
    })
    .join("");
  container.innerHTML = `
    ${Verdict.card({ title: `${selected.space} 过渡`, ruleId: "uniformity", value: uniformity.ratio, extra })}
    <div class="card"><div class="card-head"><h2>三种过渡方式</h2><span class="hint">点左侧换重点</span></div>
      <div class="card-body"><p class="small muted js-prose">${ranking}</p>${rows}</div></div>
    ${taskMeta(meta)}`;
}
