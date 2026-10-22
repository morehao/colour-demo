/* core.js：工具、格式化、状态、路由、模式 */

/* ---------------- helpers ---------------- */
const $ = (s, r = document) => r.querySelector(s);
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const fmt = (v, span) => {
  const n = Number(v);
  if (!isFinite(n)) return String(v);
  const a = Math.abs(n);
  if (a === 0) return "0";
  // span 给定时按刻度总跨度选小数位，避免相邻刻度四舍五入成同一个数字
  if (span > 0) {
    const digits = Math.max(0, Math.min(6, Math.ceil(-Math.log10(span / 5))));
    if (a < 1e-4) return n.toExponential(1);
    return n.toFixed(digits);
  }
  if (a >= 1000) return n.toFixed(0);
  if (a >= 100) return n.toFixed(a % 1 === 0 ? 0 : 1);
  if (a >= 10) return n.toFixed(a % 1 === 0 ? 0 : 1);
  if (a >= 1) return n.toFixed(2);
  if (a >= 0.01) return n.toFixed(3);
  return n.toExponential(1);
};
function toast(text) {
  const t = $("#toast");
  t.textContent = text;
  t.classList.add("show");
  clearTimeout(t._t);
  t._t = setTimeout(() => t.classList.remove("show"), 1400);
}
function copyText(text) {
  const fallback = () => {
    const area = document.createElement("textarea");
    area.value = text; area.style.position = "fixed"; area.style.opacity = "0";
    document.body.appendChild(area); area.select();
    try { document.execCommand("copy"); toast("已复制"); } catch (e) { toast("复制失败"); }
    document.body.removeChild(area);
  };
  if (navigator.clipboard && window.isSecureContext) navigator.clipboard.writeText(text).then(() => toast("已复制"), fallback);
  else fallback();
}
function highlight(text) {
  return esc(text).replace(/(&quot;(?:\\.|[^&])*?&quot;)(\s*:)?|\b(-?\d+\.?\d*(?:[eE][+-]?\d+)?)\b|\b(true|false|null)\b/g,
    (m, str, colon, num, lit) => {
      if (str) return colon ? `<span class="k-key">${str}</span>${colon}` : `<span class="k-str">${str}</span>`;
      if (num) return `<span class="k-num">${num}</span>`;
      if (lit) return `<span class="k-num">${lit}</span>`;
      return m;
    });
}
const PHASE_CLASS = { M1: "tag--m1", M2: "tag--m2", M3: "tag--m3", M4: "tag--m4", M0: "tag--m1" };

/* ---------------- 状态、路由与模式 ---------------- */
const DEFAULT_MODE = "beginner";   // 回滚开关：改成 "expert" 即恢复旧默认
const MODE_KEY = "colour-demo.mode";

const State = {
  mode: DEFAULT_MODE,
  route: { type: "home" },
  taskState: {},
};

function readMode() {
  const query = new URLSearchParams(location.search).get("mode");
  if (query === "beginner" || query === "expert") {
    try { localStorage.setItem(MODE_KEY, query); } catch (error) { /* 隐私模式忽略 */ }
    return query;
  }
  try {
    const stored = localStorage.getItem(MODE_KEY);
    if (stored === "beginner" || stored === "expert") return stored;
  } catch (error) { /* 隐私模式忽略 */ }
  return DEFAULT_MODE;
}

function setMode(mode, options = {}) {
  const next = mode === "expert" ? "expert" : "beginner";
  State.mode = next;
  document.documentElement.dataset.mode = next;
  if (options.persist !== false) {
    try { localStorage.setItem(MODE_KEY, next); } catch (error) { /* 忽略 */ }
  }
  updateChrome();
  if (options.rerender !== false) applyRoute();
}

function parseHash(hash) {
  const raw = String(hash || "").replace(/^#/, "");
  if (!raw || raw === "/") return { type: "home" };
  if (!raw.startsWith("/")) {
    const legacy = raw.split("?")[0];
    return DATA.panels.some((panel) => panel.id === legacy)
      ? { type: "legacy", id: legacy }
      : { type: "home" };
  }
  const [pathPart, queryPart] = raw.split("?");
  const parts = pathPart.split("/").filter(Boolean);
  const query = Object.fromEntries(new URLSearchParams(queryPart || ""));
  if (parts[0] === "task" && parts[1]) return { type: "task", id: parts[1], query };
  if (parts[0] === "ref" && parts[1]) return { type: "ref", id: parts[1], query };
  if (parts[0] === "ref") return { type: "reference" };
  if (parts[0] === "glossary") return { type: "glossary", query };
  if (parts[0] === "tour") return { type: "tour" };
  return { type: "home" };
}

function routeHash(route) {
  if (route.type === "home") return "#/";
  if (route.type === "reference") return "#/ref";
  if (route.type === "glossary") return "#/glossary";
  if (route.type === "tour") return "#/tour";
  const base = route.type === "task" ? "#/task/" : "#/ref/";
  const params = new URLSearchParams(route.query || {});
  const suffix = params.toString();
  return `${base}${route.id}${suffix ? `?${suffix}` : ""}`;
}

function navigate(path) {
  if (location.hash === path) applyRoute();
  else location.hash = path;
}

function updateChrome() {
  const mode = State.mode;
  document.documentElement.dataset.mode = mode;
  const topnav = $("#topnav");
  if (topnav) topnav.hidden = mode !== "beginner";
  const side = $("#side");
  if (side) side.hidden = mode !== "expert";
  document.querySelectorAll("[data-mode-btn]").forEach((button) => {
    button.setAttribute("aria-pressed", String(button.dataset.modeBtn === mode));
  });
  if (typeof updateActiveNav === "function") updateActiveNav();
  if (typeof renderApiChip === "function") renderApiChip();
}

function applyRoute() {
  if (!DATA || !DATA.panels) return;
  const route = parseHash(location.hash);
  if (route.type === "legacy") {
    history.replaceState(null, "", `#/ref/${route.id}`);
    return applyRoute();
  }
  State.route = route;
  updateChrome();
  const main = $("#main");
  if (!main) return;
  try {
    if (route.type === "home") renderHome();
    else if (route.type === "reference") renderReferenceIndex();
    else if (route.type === "glossary") renderGlossaryPage();
    else if (route.type === "tour") renderTour();
    else if (route.type === "task") {
      if (!DATA.tasks.some((task) => task.id === route.id)) {
        history.replaceState(null, "", "#/");
        return applyRoute();
      }
      renderTask(route);
    } else if (route.type === "ref") {
      const panel = DATA.panels.find((item) => item.id === route.id);
      if (!panel) {
        history.replaceState(null, "", "#/ref");
        return applyRoute();
      }
      renderRefPanel(panel);
    }
  } catch (error) {
    console.error(error);
    main.innerHTML = `<div class="note-box note-warn"><span class="b">这一页没渲染出来</span><span>${esc(error.message)}</span></div>`;
  }
  if (route.type !== "ref" && typeof annotateTerms === "function") annotateTerms(main);
  window.scrollTo(0, 0);
  main.focus({ preventScroll: true });
}
