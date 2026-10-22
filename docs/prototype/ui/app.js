/* app.js：外壳、首页、参考手册、术语页与启动 */

function navItem(href, index, label, key, extra = "") {
  return `<a class="nav-btn" href="${href}" data-nav="${esc(key)}">
    <span class="nav-index">${esc(index)}</span>${esc(label)}${extra}
  </a>`;
}

function buildSide() {
  const side = $("#side");
  if (!side) return;
  const tasks = `<div class="side-group"><div class="side-label">任务</div>${DATA.tasks
    .map((task) => navItem(`#/task/${task.id}`, task.no.replace("T", ""), task.nav || task.title, `task:${task.id}`))
    .join("")}</div>`;
  const groups = DATA.groups
    .map(
      (group) => `<div class="side-group"><div class="side-label">${esc(group)}</div>${DATA.panels
        .filter((panel) => panel.group === group)
        .map((panel) =>
          navItem(
            `#/ref/${panel.id}`,
            panel.no,
            panel.title_plain || panel.title,
            `ref:${panel.id}`,
            panel.pending ? '<span class="nav-pending" title="数据待补充"></span>' : ""
          )
        )
        .join("")}</div>`
    )
    .join("");
  side.innerHTML = `${tasks}${groups}
    <div class="side-foot">全部 ${DATA.catalog.total} 条公开名称均已归属：面板 ${DATA.catalog.counts["面板"]} · 数据集 ${DATA.catalog.counts["数据集"]} · 内部 ${DATA.catalog.counts["内部"]}。</div>`;
}

function buildTopnav() {
  const topnav = $("#topnav");
  if (!topnav) return;
  topnav.innerHTML = `${DATA.tasks
    .map((task) => `<a class="topnav-link" href="#/task/${task.id}" data-nav="task:${task.id}">${esc(task.nav || task.title)}</a>`)
    .join("")}
    <a class="topnav-link" href="#/ref" data-nav="ref">参考手册</a>
    <a class="topnav-link" href="#/glossary" data-nav="glossary">术语表</a>`;
}

function updateActiveNav() {
  const route = State.route || { type: "home" };
  const keys = new Set();
  if (route.type === "home") keys.add("home");
  if (route.type === "task") keys.add(`task:${route.id}`);
  if (route.type === "ref") {
    keys.add("ref");
    keys.add(`ref:${route.id}`);
  }
  if (route.type === "glossary") keys.add("glossary");
  document.querySelectorAll("[data-nav]").forEach((link) => {
    if (keys.has(link.dataset.nav)) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  });
}

function taskCard(task) {
  return `<a class="task-card" href="#/task/${task.id}">
    <div class="task-card-top"><span class="task-no">${esc(task.no)}</span><span class="task-est">${esc(task.est)}</span></div>
    <h2>${esc(task.title)}</h2>
    <p>${esc(task.intro)}</p>
    <span class="task-go">开始 →</span>
  </a>`;
}

function renderHome() {
  $("#main").innerHTML = `
    <section class="hero">
      <div class="eyebrow">colour-demo · 颜色演示</div>
      <h1>把颜色讲清楚。</h1>
      <p class="hero-sub js-prose">两个颜色看着一样、色差却很大？屏幕上的颜色印不出来？挑一个问题，30 秒拿到结论。</p>
      <p class="hero-meta">所有数字由 colour-science ${esc(DATA.lib.version)} 真实计算；不连服务也能看示例。</p>
    </section>
    <div class="task-grid">${DATA.tasks.map(taskCard).join("")}</div>
    <section class="home-links">
      <a class="home-link" href="#/ref" data-nav="ref"><b>参考手册</b><span>${DATA.panels.length} 个主题，查完整数据与原理</span></a>
      <a class="home-link" href="#/glossary" data-nav="glossary"><b>术语表</b><span>${Object.keys(DATA.glossary).length} 个词，一句话讲清</span></a>
    </section>
    <footer class="page-foot">新手模式只显示结论与关键数字；需要原始表格、公式和请求详情时，切到右上角「专家」。</footer>`;
}

function renderReferenceIndex() {
  const groups = DATA.groups
    .map((group) => {
      const panels = DATA.panels.filter((panel) => panel.group === group);
      if (!panels.length) return "";
      return `<section class="ref-group">
        <h2>${esc(group)}</h2>
        <div class="ref-grid">${panels
          .map((panel) => {
            const plain = panel.title_plain || panel.title;
            return `<a class="ref-card" href="#/ref/${panel.id}" data-nav="ref:${panel.id}">
              <span class="ref-no">${esc(panel.no)}</span>
              <b>${esc(plain)}</b>
              ${plain !== panel.title ? `<span class="ref-sub">${esc(panel.title)}</span>` : ""}
            </a>`;
          })
          .join("")}</div>
      </section>`;
    })
    .join("");
  $("#main").innerHTML = `
    <div class="panel-head">
      <div class="eyebrow">参考手册</div>
      <h1>按主题查完整数据</h1>
      <p class="lead js-prose">${DATA.panels.length} 个主题，每个都保留原始表格、公式与请求详情。第一次来，建议先回首页挑一个任务。</p>
    </div>
    <div class="ref-tools">
      <input id="ref-search" class="ref-search" type="search" placeholder="搜主题：色差 / 色温 / 光谱 / 相机 …" aria-label="搜索参考主题">
      <span id="ref-count">${DATA.panels.length} 个主题</span>
    </div>
    ${groups}
    <p id="ref-empty" class="hint" hidden>没有匹配的主题，试试「色差」或「光谱」。</p>`;

  const search = $("#ref-search");
  if (search) search.oninput = filterRefs;
}

function filterRefs() {
  const query = ($("#ref-search").value || "").trim().toLowerCase();
  let shown = 0;
  document.querySelectorAll(".ref-group").forEach((group) => {
    let groupShown = 0;
    group.querySelectorAll(".ref-card").forEach((card) => {
      const hit = !query || card.textContent.toLowerCase().includes(query);
      card.hidden = !hit;
      if (hit) {
        groupShown += 1;
        shown += 1;
      }
    });
    group.hidden = groupShown === 0;
  });
  $("#ref-count").textContent = query ? `${shown} 个匹配` : `${DATA.panels.length} 个主题`;
  $("#ref-empty").hidden = shown > 0;
}

function renderTour() {
  $("#main").innerHTML = `
    <div class="panel-head">
      <div class="eyebrow">30 秒上手</div>
      <h1>先挑一个问题，再看原理</h1>
      <p class="lead">这个页面不要求你先懂色度学。按下面三步走即可。</p>
    </div>
    <div class="card"><div class="card-body">
      <ol class="steps steps--big">
        <li><span>1</span>回首页，选一个你现在真的遇到的问题。</li>
        <li><span>2</span>用预设看结论；想改颜色就改，结果会自动更新。</li>
        <li><span>3</span>需要原始数据时，展开「原理与专业参数」，或切到专家模式。</li>
      </ol>
      <p class="placeholder-links"><a class="btn-ghost" href="#/">去首页挑问题 →</a>
        <a class="btn-ghost" href="#/glossary">先看术语表 →</a></p>
    </div></div>`;
}

function boot() {
  buildSide();
  buildTopnav();
  const version = $("#lib-version");
  if (version) version.textContent = DATA.lib.version;
  const coverage = $("#chip-coverage");
  if (coverage) coverage.innerHTML = `${DATA.catalog.total} 条导出全部归属 · ${DATA.catalog.coverage.toFixed(1)}%`;
  const progress = $("#chip-progress");
  if (progress) progress.textContent = `面板数据 ${DATA.stats.ready}/${DATA.panels.length} 已出`;

  document.querySelectorAll("[data-mode-btn]").forEach((button) => {
    button.addEventListener("click", () => setMode(button.dataset.modeBtn));
  });
  const skip = document.querySelector(".skip-link");
  if (skip) skip.addEventListener("click", (event) => {
    event.preventDefault();
    $("#main").focus();
  });
  window.addEventListener("hashchange", applyRoute);
  // `/` 聚焦当前页的搜索框（参考手册 / 术语表），输入框里不抢键
  document.addEventListener("keydown", (event) => {
    if (event.key !== "/" || event.metaKey || event.ctrlKey || event.altKey) return;
    const target = event.target;
    if (target && (target.closest("input, textarea, select, [contenteditable]") || target.isContentEditable)) return;
    const search = $("#ref-search") || $("#glossary-search");
    if (!search) return;
    event.preventDefault();
    search.focus();
  });
  setMode(readMode(), { persist: false, rerender: false });
  applyRoute();

  // 首帧已经画完，再异步探测服务；探测完成只升级当前页，不阻塞
  apiProbe().then(() => {
    if (State.route.type === "ref") applyRoute();
    else if (typeof refreshTaskResult === "function") refreshTaskResult();
  });
}

boot();
