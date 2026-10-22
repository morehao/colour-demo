/* live.js：API 探测/调用 + 实时结果运行器 */

/* ---------------- live API 层 ----------------
   原型默认是构建时的静态快照（离线可用）；检测到本地服务端时，
   同一页切换成「实时调用」：控件真实可改，结果由 /api/v1 现算。 */
const API_BASE = (() => {
  const override = new URLSearchParams(location.search).get("api");
  if (override) return override.replace(/\/+$/, "");
  if (location.protocol === "file:") return "http://127.0.0.1:8000";
  // 由服务端托管（/demo/）时就是同源，省掉跨域
  return location.origin.startsWith("http") ? "" : "http://127.0.0.1:8000";
})();

const api = { checked: false, ok: false, version: null };

async function apiProbe() {
  if (api.checked) return api;
  api.checked = true;
  try {
    const response = await fetch(`${API_BASE}/api/v1/health`, { cache: "no-store" });
    const body = await response.json();
    api.ok = response.ok && body.status === "ok";
    api.version = body.colour_version;
  } catch (error) {
    api.ok = false;
  }
  if (api.ok) {
    try {
      const response = await fetch(`${API_BASE}/api/v1/catalog?limit=1`, { cache: "no-store" });
      api.whitelist = (await response.json()).whitelist || [];
    } catch (error) {
      api.whitelist = [];
    }
  }
  renderApiChip();
  return api;
}

function renderApiChip() {
  const chip = $("#chip-api");
  if (!chip) return;
  const expert = typeof State !== "undefined" && State.mode === "expert";
  const narrow = window.matchMedia("(max-width:600px)").matches;
  chip.textContent = narrow
    ? (api.ok ? "在线" : "离线")
    : api.ok
      ? (expert ? `API 在线 · colour ${api.version}` : "已连上本地服务")
      : (expert ? "静态快照 · 未连 API" : "离线快照 · 看预设");
  chip.classList.toggle("chip--ok", api.ok);
}

async function apiCall(spec, state) {
  const [method, path] = spec.endpoint.split(" ");
  let url = `${API_BASE}${path}`;
  if (spec.query) {
    const params = new URLSearchParams();
    Object.entries(spec.query(state)).forEach(([key, value]) => {
      if (value !== "" && value !== null && value !== undefined) params.append(key, value);
    });
    const query = params.toString();
    if (query) url += "?" + query;
  }
  const init = { method, headers: {}, cache: "no-store" };
  if (method !== "GET") {
    init.headers["content-type"] = "application/json";
    init.body = JSON.stringify(spec.body(state));
  }
  const started = performance.now();
  const response = await fetch(url, init);
  const elapsed = Math.round(performance.now() - started);
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = payload.detail || {};
    const parts = [response.status, detail.type, detail.message].filter(Boolean);
    throw new Error(parts.join(" · ") || `HTTP ${response.status}`);
  }
  return { payload, elapsed, request: init.body ? JSON.parse(init.body) : Object.fromEntries(new URLSearchParams(spec.query ? spec.query(state) : {})) };
}

function renderField(field) {
  const key = `data-live-key="${field.key}"`;
  if (field.kind === "select") {
    return `<div class="field"><span>${esc(field.label)}</span><select ${key}>${field.options.map((option) => `<option${option === field.value ? " selected" : ""}>${esc(option)}</option>`).join("")}</select></div>`;
  }
  if (field.kind === "range") {
    return `<div class="field"><span>${esc(field.label)}</span><div class="range-row"><input type="range" ${key} min="${field.min}" max="${field.max}" step="${field.step}" value="${esc(field.value)}"><output data-live-out="${field.key}">${esc(field.value)}</output></div></div>`;
  }
  return `<div class="field"><span>${esc(field.label)}</span><input type="text" ${key} value="${esc(field.value)}"></div>`;
}

function liveFields(spec) {
  return typeof spec.fields === "function" ? spec.fields() : spec.fields || [];
}

function collectState(spec) {
  const state = {};
  liveFields(spec).forEach((field) => {
    const element = document.querySelector(`[data-live-key="${field.key}"]`);
    if (element) state[field.key] = element.value;
  });
  return state;
}

function renderTrace(spec, state, payload, elapsed, request) {
  const body = spec.query ? spec.query(state) : request;
  return `<details class="trace"><summary>请求 / 响应 JSON（${elapsed} ms）</summary>
    <div class="code"><pre>${highlight(JSON.stringify({ endpoint: spec.endpoint, body }, null, 2))}</pre></div>
    <div class="code"><pre>${highlight(JSON.stringify(payload, null, 2))}</pre></div></details>`;
}

async function runLive(panel, spec) {
  const out = $("#live-out");
  const status = $("#live-status");
  if (!out) return;
  const state = collectState(spec);
  status.textContent = `调用 ${spec.endpoint} …`;
  try {
    if (spec.dataEndpoint) {
      // 色度图要分两个端点取：图是 SVG，数据是 JSON（面积/归属表）；
      // 其余 GET 适配器（目录/空间图鉴）只有 query，不要走这个分支
      const dataSpec = { endpoint: spec.dataEndpoint, query: spec.query };
      const { payload, elapsed } = await apiCall(dataSpec, state);
      out.innerHTML = spec.blocks(payload, state).map(renderBlock).join("") + renderTrace(spec, state, payload, elapsed, null);
      status.textContent = `实时结果 · ${spec.endpoint} + ${spec.dataEndpoint} · colour ${api.version}`;
    } else {
      const { payload, elapsed, request } = await apiCall(spec, state);
      out.innerHTML = spec.blocks(payload, state).map(renderBlock).join("") + renderTrace(spec, state, payload, elapsed, request);
      status.textContent = `实时结果 · ${elapsed} ms · ${spec.endpoint} · colour ${api.version}`;
    }
  } catch (error) {
    out.innerHTML = `<div class="note-box note-warn"><span class="b">调用失败</span><span>${esc(error.message)}</span></div>`;
    status.textContent = "调用失败：先启动服务端 .venv/bin/python -m uvicorn colour_demo.main:app --port 8000";
  }
}
