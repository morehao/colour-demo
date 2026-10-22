/* blocks.js：通用块构造器与渲染 */

/* 块构造器：与 renderBlock 的入参严格对齐，避免两端格式漂移 */
const cell = (v) => (v === null || v === undefined || (typeof v === "number" && !isFinite(v)) ? "—" : String(v));
const num = (v, digits = 4) => (v === null || v === undefined || !isFinite(Number(v)) ? "—" : Number(v).toFixed(digits));
const fixed = (v, digits = 4) => (Array.isArray(v) ? v.map((x) => num(x, digits)).join(", ") : num(v, digits));
const B = {
  table: (title, head, rows, opts = {}) => ({
    type: "table", title, head, rows: rows.map((row) => row.map(cell)), mono: opts.mono, widths: opts.widths, note: opts.note,
  }),
  kv: (title, rows) => ({ type: "kv", title, rows }),
  matrix: (title, colors, values, caption) => ({ type: "matrix", title, colors, values, caption }),
  chart: (title, series, opts = {}) => ({
    type: "chart", title, series, height: opts.height || 260, xlabel: opts.xlabel, ylabel: opts.ylabel, caption: opts.caption, zero: opts.zero,
  }),
  swatches: (title, items, cols) => ({ type: "swatches", title, items, cols: cols || Math.max(1, Math.min(8, items.length)) }),
  image: (src, caption, maxw) => ({ type: "image", src, caption, alt: caption || "chart", maxw: maxw || "520px" }),
  note: (text, tone) => ({ type: "note", text, tone: tone || "info", title: tone === "warn" ? "注意" : "说明" }),
  json: (title, value) => ({ type: "json", title, code: JSON.stringify(value, null, 2) }),
};

/* ---------------- blocks ---------------- */
function blockTitle(b) {
  return b.title ? `<div class="card-head"><h2>${esc(b.title)}</h2></div>` : "";
}

function renderBlock(b) {
  switch (b.type) {
    case "kv":
      return `<div class="card">${blockTitle(b)}<div class="card-body"><table class="kv">${b.rows
        .map(([k, v, n]) => `<tr><td class="k">${esc(k)}</td><td class="v">${esc(v)}</td><td class="n">${esc(n || "")}</td></tr>`)
        .join("")}</table></div></div>`;
    case "stats":
      return `<div class="card">${blockTitle(b)}<div class="card-body"><div class="stats">${b.items
        .map(([v, k, n]) => `<div class="stat"><b>${esc(v)}</b><span>${esc(k)}${n ? " · " + esc(n) : ""}</span></div>`)
        .join("")}</div></div></div>`;
    case "matrix": {
      const max = Math.max(...b.values.flat().filter((v, i) => Number.isFinite(v)));
      const head = `<tr><th></th>${b.colors.map((_, i) => `<th>${i + 1}</th>`).join("")}</tr>`;
      const body = b.values
        .map((row, i) => `<tr><th>${i + 1}</th>${row
          .map((v, j) => {
            if (i === j) return `<td class="diag">—</td>`;
            const t = Math.min(1, v / (max || 1));
            return `<td style="background:rgba(59,130,246,${(0.06 + 0.5 * t).toFixed(3)});color:${t > 0.62 ? "#0B2A5B" : "#15161A"}">${v.toFixed(1)}</td>`;
          })
          .join("")}</tr>`)
        .join("");
      return `<div class="card">${blockTitle(b)}<div class="card-body">
        <div class="matrix-head">${b.colors.map((c, i) => `<span class="tag" style="gap:5px"><i style="background:${c}"></i>${i + 1}. ${c}</span>`).join("")}</div>
        <table class="matrix">${head}${body}</table>
        ${b.caption ? `<div class="table-note">${esc(b.caption)}</div>` : ""}
      </div></div>`;
    }
    case "swatches":
      return `<div class="card">${blockTitle(b)}<div class="card-body"><div class="sw-grid" style="grid-template-columns:repeat(${b.cols},minmax(0,1fr))">${b.items
        .map((it) => `<div class="sw"><div class="sw-color" style="background:${it.hex}"></div><div class="sw-hex">${esc(it.label)}</div>${it.sub ? `<div class="sw-sub">${esc(it.sub)}</div>` : ""}</div>`)
        .join("")}</div></div></div>`;
    case "strips":
      return `<div class="card">${blockTitle(b)}<div class="card-body">${b.items
        .map((s) => {
          const grad = `linear-gradient(90deg, ${s.colors.join(", ")})`;
          const cells = s.colors.map((c) => `<div class="step" style="background:${c}" title="${c}"></div>`).join("");
          return `<div class="strip-block">
            <div class="strip-head"><h3>${esc(s.label)}</h3><span class="note">${esc(s.note)}</span>
              <div class="stats">${s.stats.map(([k, v]) => `<span class="tag">${esc(k)} ${esc(v)}</span>`).join("")}</div></div>
            <div class="bar" style="background:${grad}"></div>
            <div class="steps" style="grid-template-columns:repeat(${s.colors.length},minmax(0,1fr))">${cells}</div>
          </div>`;
        })
        .join("")}${b.caption ? `<div class="table-note">${esc(b.caption)}</div>` : ""}</div></div>`;
    case "table": {
      const filterable = b.rows.length > 40;
      return `<div class="card">${blockTitle(b)}<div class="card-body">
        <div class="table-wrap"><table class="data" ${filterable ? 'data-filterable="1"' : ""}>
          <thead><tr>${b.head.map((h, i) => `<th${b.widths ? ` style="width:${b.widths[i] || "auto"}"` : ""}>${esc(h)}</th>`).join("")}</tr></thead>
          <tbody>${b.rows.map((row) => `<tr>${row.map((cell, i) => `<td class="${(b.mono || []).includes(i) ? "mono" : ""}">${esc(cell)}</td>`).join("")}</tr>`).join("")}</tbody>
        </table></div>
        ${b.note ? `<div class="table-note">${esc(b.note)}</div>` : ""}
      </div></div>`;
    }
    case "chart":
      return `<div class="card">${blockTitle(b)}<div class="card-body">${renderChart(b)}</div></div>`;
    case "image":
      return `<div class="card"><div class="card-body"><figure class="fig"><img src="${b.src}" alt="${esc(b.alt)}" style="max-width:${b.maxw || "520px"}">${b.caption ? `<figcaption>${esc(b.caption)}</figcaption>` : ""}</figure></div></div>`;
    case "note":
      return `<div class="note-box ${b.tone === "warn" ? "note-warn" : "note-info"}"><span class="b">${esc(b.title || (b.tone === "warn" ? "注意" : "说明"))}</span><span>${esc(b.text)}</span></div>`;
    case "json":
      return `<div class="card">${blockTitle(b)}<div class="card-body"><div class="code"><button class="copy" data-copy>复制</button><pre>${highlight(b.code)}</pre></div></div></div>`;
    case "cards":
      return `<div class="card">${blockTitle(b)}<div class="card-body"><div class="cards">${b.items
        .map((it) => `<div class="mini"><h3>${esc(it.title)}</h3><p>${esc(it.text)}</p><code>${esc(it.foot)}</code></div>`)
        .join("")}</div></div></div>`;
    case "chain":
      return `<div class="card"><div class="card-body"><div class="chain">${b.nodes
        .map(([name, color, desc]) => `<div class="chain-node"><div class="chain-bar" style="background:${color}"></div><strong>${esc(name)}</strong><p>${esc(desc)}</p></div>`)
        .join("")}</div></div></div>`;
    default:
      return "";
  }
}
