/* glossary.js：术语高亮、浮层与术语表页 */

const Glossary = (() => {
  const entries = Object.entries(DATA.glossary).map(([key, entry]) => ({ key, ...entry }));
  const byAlias = new Map();
  entries.forEach((entry) => {
    entry.aliases.forEach((alias) => {
      if (alias.length >= 2) byAlias.set(alias, entry);
    });
  });
  const aliases = Array.from(byAlias.keys()).sort((a, b) => b.length - a.length);
  const pattern = aliases.length
    ? new RegExp(aliases.map((alias) => alias.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|"), "g")
    : null;
  return { entries, byAlias, pattern };
})();

function showTerm(anchor) {
  const entry = DATA.glossary[anchor.dataset.term];
  const pop = $("#term-pop");
  if (!entry || !pop) return;
  pop.innerHTML = `
    <div class="term-pop-head"><b>${esc(entry.term)}</b><span>${esc(entry.zh)}</span></div>
    <p>${esc(entry.plain)}</p>
    ${entry.note ? `<p class="term-pop-note">${esc(entry.note)}</p>` : ""}
    <div class="term-pop-links">
      ${entry.see ? `<a href="${esc(entry.see)}">去相关页 →</a>` : ""}
      <a href="#/glossary">术语表</a>
    </div>`;
  pop.hidden = false;
  const rect = anchor.getBoundingClientRect();
  const width = Math.min(300, window.innerWidth - 24);
  const left = Math.min(window.innerWidth - width - 12, Math.max(12, rect.left - 10));
  pop.style.width = `${width}px`;
  pop.style.left = `${left}px`;
  pop.style.top = `${rect.bottom + window.scrollY + 8}px`;
  pop.dataset.for = anchor.dataset.term;
}

function hideTerm() {
  const pop = $("#term-pop");
  if (pop) pop.hidden = true;
}

/**
 * 只处理 .js-prose 容器：最长匹配、每段每个术语最多挂一次，
 * 跳过 code/pre/a/button 与已经挂过的节点，避免破坏专业原文。
 */
function annotateTerms(root) {
  if (!root || !Glossary.pattern) return;
  const containers = root.classList && root.classList.contains("js-prose")
    ? [root]
    : Array.from(root.querySelectorAll(".js-prose"));
  containers.forEach((container) => annotateContainer(container));
}

function annotateContainer(root) {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
    acceptNode(node) {
      const parent = node.parentElement;
      if (!parent) return NodeFilter.FILTER_REJECT;
      if (parent.closest("code,pre,a,button,option,select,label,summary,script,style,.no-terms,.term")) {
        return NodeFilter.FILTER_REJECT;
      }
      return node.nodeValue && node.nodeValue.trim().length >= 2
        ? NodeFilter.FILTER_ACCEPT
        : NodeFilter.FILTER_REJECT;
    },
  });
  const nodes = [];
  let node;
  while ((node = walker.nextNode())) nodes.push(node);

  const used = new Set();
  nodes.forEach((textNode) => {
    const text = textNode.nodeValue;
    const matches = [];
    Glossary.pattern.lastIndex = 0;
    let match;
    while ((match = Glossary.pattern.exec(text))) {
      const entry = Glossary.byAlias.get(match[0]);
      if (!entry || used.has(entry.key)) continue;
      matches.push({ start: match.index, end: match.index + match[0].length, entry });
      used.add(entry.key);
      Glossary.pattern.lastIndex = match.index + match[0].length;
    }
    if (!matches.length) return;
    const fragment = document.createDocumentFragment();
    let cursor = 0;
    matches.forEach((item) => {
      fragment.appendChild(document.createTextNode(text.slice(cursor, item.start)));
      const span = document.createElement("button");
      span.type = "button";
      span.className = "term";
      span.dataset.term = item.entry.key;
      span.textContent = text.slice(item.start, item.end);
      span.setAttribute("aria-label", `${item.entry.term}，查看解释`);
      fragment.appendChild(span);
      cursor = item.end;
    });
    fragment.appendChild(document.createTextNode(text.slice(cursor)));
    textNode.parentNode.replaceChild(fragment, textNode);
  });
}

function renderGlossaryPage() {
  const items = Glossary.entries
    .map(
      (entry) => `
      <article class="glossary-item no-terms">
        <div class="glossary-term"><b>${esc(entry.term)}</b><span>${esc(entry.zh)}</span></div>
        <p>${esc(entry.plain)}</p>
        ${entry.note ? `<p class="small muted">${esc(entry.note)}</p>` : ""}
        ${entry.see ? `<a class="glossary-link" href="${esc(entry.see)}">相关页面 →</a>` : ""}
      </article>`
    )
    .join("");
  $("#main").innerHTML = `
    <div class="panel-head">
      <div class="eyebrow">术语表</div>
      <h1>颜色里的词，一次讲清</h1>
      <p class="lead">共 ${Glossary.entries.length} 条。按名称或英文缩写搜索；点「相关页面」可跳到对应面板。</p>
    </div>
    <div class="glossary-tools">
      <input id="glossary-search" type="text" placeholder="搜术语，如 色差 / ΔE / 白点" aria-label="搜索术语">
      <span class="muted small" id="glossary-count">${Glossary.entries.length} 条</span>
    </div>
    <div class="glossary-list" id="glossary-list">${items}</div>`;
  const search = $("#glossary-search");
  const count = $("#glossary-count");
  search.addEventListener("input", () => {
    const query = search.value.trim().toLowerCase();
    let shown = 0;
    document.querySelectorAll(".glossary-item").forEach((item) => {
      const hit = !query || item.textContent.toLowerCase().includes(query);
      item.hidden = !hit;
      if (hit) shown += 1;
    });
    count.textContent = `${shown} 条`;
  });
}

document.addEventListener("click", (event) => {
  const anchor = event.target.closest(".term");
  if (anchor) {
    event.preventDefault();
    showTerm(anchor);
    return;
  }
  if (!event.target.closest("#term-pop")) hideTerm();
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") hideTerm();
});
window.addEventListener("scroll", hideTerm, { passive: true });
