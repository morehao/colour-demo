/* components.js：结论卡、颜色输入、预设、步骤与错误态 */

const Verdict = {
  resolve(ruleId) {
    let rule = DATA.verdicts[ruleId];
    if (!rule) return null;
    const seen = new Set();
    while (rule.extends && !seen.has(rule.extends)) {
      seen.add(rule.extends);
      rule = { ...DATA.verdicts[rule.extends], ...rule };
    }
    return rule;
  },
  band(ruleId, value) {
    const rule = this.resolve(ruleId);
    if (!rule || rule.kind !== "band") return null;
    return rule.bands.find((band) => band.lt === null || value < band.lt) || null;
  },
  format(ruleId, value) {
    const rule = this.resolve(ruleId);
    const scaled = rule && rule.scale ? value * rule.scale : value;
    const digits = rule && Number.isFinite(rule.precision) ? rule.precision : 1;
    return Number(scaled).toFixed(digits);
  },
  unit(ruleId) {
    const rule = this.resolve(ruleId);
    return (rule && rule.unit) || "";
  },
  card({ title, ruleId, value, extra, tone } = {}) {
    const band = this.band(ruleId, value);
    const rule = this.resolve(ruleId);
    const toneClass = tone || (band ? band.tone : "ok");
    const number = this.format(ruleId, value);
    const display = rule && rule.unit_position === "prefix"
      ? `${esc(rule.unit)} ${number}`
      : `${number}${esc((rule && rule.unit) || "")}`;
    return `<section class="verdict verdict--${toneClass}">
      ${title ? `<div class="verdict-title">${esc(title)}</div>` : ""}
      <div class="verdict-line">
        <b class="verdict-value">${display}</b>
        ${band ? `<span class="verdict-band">${esc(band.label)}</span>` : ""}
      </div>
      ${band ? `<p class="verdict-say">${esc(band.say)}</p>` : ""}
      ${extra ? `<div class="verdict-extra js-prose">${extra}</div>` : ""}
    </section>`;
  },
};

function colorRow(hex, index, removable) {
  return `<div class="color-row" data-color-row>
    <input type="color" value="${esc(hex)}" aria-label="颜色 ${index + 1}">
    <input type="text" class="hex-input" value="${esc(hex)}" spellcheck="false"
      autocomplete="off" aria-label="颜色 ${index + 1} 的十六进制值">
    <button type="button" class="btn-icon" data-color-remove ${removable ? "" : "disabled"}
      aria-label="删掉颜色 ${index + 1}">×</button>
  </div>`;
}

function renderColorList(colors, options = {}) {
  const min = options.min ?? 2;
  const max = options.max ?? 12;
  return `<div class="color-list" data-color-list>
    ${colors.map((hex, index) => colorRow(hex, index, colors.length > min)).join("")}
    <button type="button" class="btn-ghost" data-color-add ${colors.length >= max ? "disabled" : ""}>+ 加一个颜色</button>
  </div>`;
}

function readColors(list) {
  return Array.from(list.querySelectorAll("[data-color-row]")).map((row) =>
    row.querySelector(".hex-input").value.trim().toUpperCase()
  );
}

function refreshColorButtons(list, min, max) {
  const rows = Array.from(list.querySelectorAll("[data-color-row]"));
  rows.forEach((row, index) => {
    row.querySelector("[data-color-remove]").disabled = rows.length <= min;
    row.querySelector("input[type=color]").setAttribute("aria-label", `颜色 ${index + 1}`);
  });
  const add = list.querySelector("[data-color-add]");
  if (add) add.disabled = rows.length >= max;
}

function wireColorList(root, state, options, onChange) {
  const list = root.querySelector("[data-color-list]");
  if (!list) return;
  const min = options.min ?? 2;
  const max = options.max ?? 12;

  list.oninput = (event) => {
    const row = event.target.closest("[data-color-row]");
    if (!row) return;
    if (event.target.type === "color") {
      row.querySelector(".hex-input").value = event.target.value.toUpperCase();
      row.querySelector(".hex-input").classList.remove("is-bad");
      state.colors = readColors(list);
      onChange();
    } else if (event.target.classList.contains("hex-input")) {
      const value = event.target.value.trim();
      if (/^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/.test(value)) {
        event.target.classList.remove("is-bad");
        const hex = value.length === 4
          ? `#${value[1]}${value[1]}${value[2]}${value[2]}${value[3]}${value[3]}`
          : value;
        row.querySelector("input[type=color]").value = hex;
        state.colors = readColors(list);
        onChange();
      } else {
        event.target.classList.add("is-bad");
      }
    }
  };

  list.onclick = (event) => {
    const remove = event.target.closest("[data-color-remove]");
    const add = event.target.closest("[data-color-add]");
    if (remove && !remove.disabled) {
      remove.closest("[data-color-row]").remove();
    } else if (add && !add.disabled) {
      add.insertAdjacentHTML("beforebegin", colorRow("#888888", list.querySelectorAll("[data-color-row]").length, true));
    } else {
      return;
    }
    refreshColorButtons(list, min, max);
    state.colors = readColors(list);
    onChange();
  };
}

function sameColors(a, b) {
  return Array.isArray(a) && Array.isArray(b) && a.length === b.length &&
    a.every((value, index) => String(value).toUpperCase() === String(b[index]).toUpperCase());
}

function sameState(a, b) {
  return Object.keys(a).length === Object.keys(b).length &&
    Object.keys(a).every((key) => {
      if (Array.isArray(a[key])) return sameColors(a[key], b[key]);
      return String(a[key]) === String(b[key]);
    });
}

function renderPresets(task, activeId) {
  return `<div class="preset-row" role="group" aria-label="快速示例">
    ${task.presets.map((preset) => `<button type="button" class="preset" data-preset="${esc(preset.id)}"
      aria-pressed="${String(preset.id === activeId)}">${esc(preset.label)}</button>`).join("")}
  </div>`;
}

function renderSteps(steps) {
  return `<ol class="steps">${steps
    .map((step, index) => `<li><span>${index + 1}</span>${esc(step)}</li>`)
    .join("")}</ol>`;
}

function renderNote(kind, title, body) {
  return `<div class="note-box note-${kind}"><span class="b">${esc(title)}</span><span>${body}</span></div>`;
}

function humanError(error) {
  const text = String((error && error.message) || error || "未知错误");
  if (/failed to fetch|networkerror|load failed/i.test(text)) {
    return "连不上本地服务。可以先用离线预设看结果；要改参数，请在项目目录启动服务端后刷新。";
  }
  return text;
}
