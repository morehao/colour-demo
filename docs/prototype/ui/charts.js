/* charts.js：SVG 图表 */

/* ---------------- chart ---------------- */
function renderChart(b) {
  const W = 880, H = b.height || 260;
  const series = b.series.filter((s) => s.points.length);
  const colors = ["#2A9D8F", "#3B82F6", "#E76F51", "#E9C46A", "#8E44AD", "#264653", "#F4A261", "#111827"];
  // 图例按估算文字宽度分行排布：固定间距会让长名字（中文/括号）互相压字
  const PAD_L = 46, PAD_R = 26, PAD_B = 30;  // 右侧留白要够放最后一个 X 刻度标签
  const textWidth = (s) => [...s].reduce((w, ch) => w + (/[\u2E80-\u9FFF\uFF00-\uFFEF]/.test(ch) ? 10.5 : 5.8), 0);
  const legendItems = series
    .filter((s) => s.mode !== "scatter" || series.length < 9)
    .slice(0, 8)
    .map((s) => ({ name: s.name, color: s.color || colors[series.indexOf(s) % colors.length] }));
  const legendRows = [];
  let rowItems = [], rowWidth = 0;
  legendItems.forEach((it) => {
    const itemWidth = 14 + textWidth(it.name) + 16;
    if (rowItems.length && rowWidth + itemWidth > W - PAD_L - PAD_R) {
      legendRows.push(rowItems);
      rowItems = [];
      rowWidth = 0;
    }
    rowItems.push(it);
    rowWidth += itemWidth;
  });
  if (rowItems.length) legendRows.push(rowItems);
  // 图例单独占顶部带，避免落在绘图区里被曲线压住
  const legendBand = legendRows.length * 18;
  const pad = { l: PAD_L, r: PAD_R, t: 12 + legendBand, b: PAD_B };
  let xmin = Infinity, xmax = -Infinity, ymin = Infinity, ymax = -Infinity;
  series.forEach((s) => s.points.forEach(([x, y]) => {
    if (isFinite(x)) { xmin = Math.min(xmin, x); xmax = Math.max(xmax, x); }
    if (isFinite(y)) { ymin = Math.min(ymin, y); ymax = Math.max(ymax, y); }
  }));
  if (!isFinite(xmin)) return "";
  if (b.zero) ymin = Math.min(0, ymin);
  if (ymin === ymax) { ymin -= 1; ymax += 1; }
  const sx = (x) => pad.l + ((x - xmin) / (xmax - xmin || 1)) * (W - pad.l - pad.r);
  const sy = (y) => H - pad.b - ((y - ymin) / (ymax - ymin || 1)) * (H - pad.t - pad.b);

  const ticksY = 5, ticksX = 6;
  let grid = "", axis = "";
  for (let i = 0; i <= ticksY; i++) {
    const value = ymin + ((ymax - ymin) * i) / ticksY;
    const y = sy(value);
    grid += `<line x1="${pad.l}" y1="${y}" x2="${W - pad.r}" y2="${y}" stroke="#EFEFEA" stroke-width="1"/>`;
    axis += `<text x="${pad.l - 6}" y="${y + 3}" text-anchor="end">${fmt(value, ymax - ymin)}</text>`;
  }
  for (let i = 0; i <= ticksX; i++) {
    const value = xmin + ((xmax - xmin) * i) / ticksX;
    const x = sx(value);
    axis += `<line x1="${x}" y1="${H - pad.b}" x2="${x}" y2="${H - pad.b + 3}" stroke="#D3D3CB" stroke-width="1"/>`;
    axis += `<text x="${x}" y="${H - pad.b + 14}" text-anchor="middle">${fmt(value, xmax - xmin)}</text>`;
  }
  let paths = "";
  series.forEach((s, i) => {
    const color = s.color || colors[i % colors.length];
    if (s.mode === "scatter") {
      paths += s.points.map(([x, y]) => `<circle cx="${sx(x)}" cy="${sy(y)}" r="2.2" fill="${color}"/>`).join("");
    } else if (s.mode === "bar") {
      const w = Math.max(2, (W - pad.l - pad.r) / s.points.length * 0.7);
      paths += s.points.map(([x, y]) => {
        const x0 = sx(x) - w / 2;
        const y0 = sy(Math.max(0, y));
        return `<rect x="${x0}" y="${y0}" width="${w}" height="${Math.abs(sy(y) - sy(0))}" fill="${color}" opacity="0.85"/>`;
      }).join("");
    } else {
      const d = s.points.map(([x, y], k) => `${k === 0 ? "M" : "L"}${sx(x).toFixed(1)},${sy(y).toFixed(1)}`).join(" ");
      paths += `<path d="${d}" fill="none" stroke="${color}" stroke-width="1.5" ${s.dashed ? 'stroke-dasharray="4 3"' : ""} stroke-linejoin="round"/>`;
    }
  });
  const legend = legendRows
    .map((items, rowIndex) => {
      const y = 12 + rowIndex * 18;
      let x = pad.l;
      return items
        .map((it) => {
          const gx = x;
          x += 14 + textWidth(it.name) + 16;
          return `<g><rect x="0" y="0" width="10" height="3" rx="1.5" fill="${it.color}" transform="translate(${gx},${y})"/>
            <text class="legend" x="${gx + 14}" y="${y + 4}" fill="#555A63">${esc(it.name)}</text></g>`;
        })
        .join("");
    })
    .join("");

  return `<div class="chart-wrap">
    <svg class="chart" viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid meet" style="width:100%;height:auto;display:block" role="img" aria-label="${esc(b.title || b.caption || "chart")}">
      ${grid}${paths}${axis}
      <text x="${W - pad.r}" y="${H - 4}" text-anchor="end">${esc(b.xlabel || "")}</text>
      ${b.ylabel ? `<text transform="translate(11,${(H - pad.b + pad.t) / 2}) rotate(-90)" text-anchor="middle">${esc(b.ylabel)}</text>` : ""}
      ${legend}
    </svg>
    ${b.caption ? `<div class="chart-caption">${esc(b.caption)}</div>` : ""}
  </div>`;
}
