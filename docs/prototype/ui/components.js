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
  text(ruleId, context) {
    const rule = this.resolve(ruleId);
    if (!rule || !rule.template) return "";
    return rule.template.replace(/\{(\w+)\}/g, (_, key) => (context[key] == null ? "" : String(context[key])));
  },
  plain({ title, html, tone = "ok" } = {}) {
    return `<section class="verdict verdict--${tone}">
      ${title ? `<div class="verdict-title">${esc(title)}</div>` : ""}
      <div class="verdict-say js-prose">${html}</div>
    </section>`;
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

const HEX_TEXT = /^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/;
/* 服务端认识 #RRGGBB / rgb() / hsl() / CSS 关键字；客户端只做「像不像色值」的粗筛 */
const COLOUR_TEXT = /^(#([0-9a-fA-F]{3,8})|rgba?\([^)]*\)|hsla?\([^)]*\)|[a-zA-Z]{3,24})$/;

function looksLikeColour(value) {
  return COLOUR_TEXT.test(String(value || "").trim());
}

/* 一行色块：取色器 + 十六进制文本 + 吸管 + 删除。
   `prefix` 决定 data-* 属性名（data-color-* / data-live-color-*），
   让任务页与面板控器共用同一套 DOM 约定而不互相抢事件。 */
function colorRow(hex, index, options = {}) {
  const prefix = options.prefix || "data-color";
  const pick = typeof EyeDropper !== "undefined"
    ? `<button type="button" class="btn-pick" ${prefix}-pick aria-label="用吸管取颜色 ${index + 1}">吸管</button>`
    : "";
  const remove = options.single
    ? ""
    : `<button type="button" class="btn-icon" ${prefix}-remove ${options.removable === false ? "disabled" : ""}
      aria-label="删掉颜色 ${index + 1}">×</button>`;
  return `<div class="color-row" ${prefix}-row>
    <input type="color" value="${esc(hex)}" aria-label="颜色 ${index + 1}">
    <input type="text" class="hex-input" value="${esc(hex)}" spellcheck="false"
      autocomplete="off" aria-label="颜色 ${index + 1} 的十六进制值">
    ${pick}${remove}
  </div>`;
}

function renderColorList(colors, options = {}) {
  const prefix = options.prefix || "data-color";
  const min = options.min ?? 2;
  const max = options.max ?? 12;
  const list = (colors.length ? colors : ["#888888"]).slice(0, max);
  const add = options.add === false
    ? ""
    : `<button type="button" class="btn-ghost" ${prefix}-add ${list.length >= max ? "disabled" : ""}>+ 加一个颜色</button>`;
  const key = options.key ? ` data-live-key="${esc(options.key)}"` : "";
  return `<div class="color-list" ${prefix}-list${key}>
    ${list.map((hex, index) => colorRow(hex, index, { prefix, single: options.single, removable: list.length > min })).join("")}
    ${add}
  </div>`;
}

function readColors(list, prefix = "data-color") {
  return Array.from(list.querySelectorAll(`[${prefix}-row]`)).map((row) =>
    row.querySelector(".hex-input").value.trim().toUpperCase()
  );
}

function refreshColorButtons(list, min, max, prefix = "data-color") {
  const rows = Array.from(list.querySelectorAll(`[${prefix}-row]`));
  rows.forEach((row, index) => {
    const remove = row.querySelector(`[${prefix}-remove]`);
    if (remove) remove.disabled = rows.length <= min;
    row.querySelector("input[type=color]").setAttribute("aria-label", `颜色 ${index + 1}`);
  });
  const add = list.querySelector(`[${prefix}-add]`);
  if (add) add.disabled = rows.length >= max;
}

/* options.allowAny：允许 rgb()/关键字等 CSS 写法（面板用）；任务页只认 HEX。 */
function wireColorList(root, state, options, onChange) {
  const prefix = options.prefix || "data-color";
  const list = root.querySelector(`[${prefix}-list]`);
  if (!list) return;
  const min = options.min ?? 2;
  const max = options.max ?? 12;
  const sync = () => {
    state.colors = readColors(list);
    onChange();
  };

  list.oninput = (event) => {
    const row = event.target.closest(`[${prefix}-row]`);
    if (!row) return;
    if (event.target.type === "color") {
      const text = row.querySelector(".hex-input");
      text.value = event.target.value.toUpperCase();
      text.classList.remove("is-bad");
      sync();
    } else if (event.target.classList.contains("hex-input")) {
      const value = event.target.value.trim();
      const valid = options.allowAny ? looksLikeColour(value) : HEX_TEXT.test(value);
      event.target.classList.toggle("is-bad", !valid);
      const hex = normalizeHex(value);
      if (hex) row.querySelector("input[type=color]").value = hex;
      if (valid) sync();
    }
  };

  list.onclick = (event) => {
    const pick = event.target.closest(`[${prefix}-pick]`);
    if (pick && typeof EyeDropper !== "undefined") {
      const row = pick.closest(`[${prefix}-row]`);
      new EyeDropper().open().then((result) => {
        const hex = normalizeHex(result.sRGBHex);
        if (!hex) return;
        row.querySelector('input[type="color"]').value = hex;
        row.querySelector(".hex-input").value = hex;
        row.querySelector(".hex-input").classList.remove("is-bad");
        sync();
      }).catch(() => { /* 用户取消取色 */ });
      return;
    }
    const remove = event.target.closest(`[${prefix}-remove]`);
    const add = event.target.closest(`[${prefix}-add]`);
    if (remove && !remove.disabled) {
      remove.closest(`[${prefix}-row]`).remove();
    } else if (add && !add.disabled) {
      const count = list.querySelectorAll(`[${prefix}-row]`).length;
      add.insertAdjacentHTML("beforebegin", colorRow("#888888", count, { prefix, removable: true }));
    } else {
      return;
    }
    refreshColorButtons(list, min, max, prefix);
    sync();
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
