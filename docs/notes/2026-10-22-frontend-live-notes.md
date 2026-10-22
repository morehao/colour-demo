# 前端联调笔记：静态快照 → 实时 API（2026-10-22）

## 做了什么

`docs/prototype/index.template.html` 里加了一层「live API 层」（约 470 行 JS），
`build_prototype.py --merge` 仍按原样产出单文件页：

1. **自动探测**：首屏 `GET /api/v1/health`；在线 → 顶栏 `API 在线 · colour 0.4.7`，
   面板上出现「实时 API」徽标；离线 → 保持静态快照，控件 disabled，并提示怎么起服务。
2. **适配器注册表 `LIVE`**：每个面板声明 `fields`（控件）、`body`/`query`（请求）、
   `blocks`（把响应翻成块）。块构造器 `B.*` 与 `renderBlock` 的入参严格对齐。
3. **15 个面板接了适配器**：01 02 05 06 08 09 10 11 12 13 14 15 16 17 18。
   面板 id 用的是 `DATA.panels` 里的真实 id（`gamut-volume` / `image-lut` / `adaptation`，
   不是模块名 `volume` / `lut` / `adapt`——第一次写错，页面静默不出实时结果）。
4. **请求可见**：每次调用下方可展开 `请求 / 响应 JSON`，等于面板 28 的轻量版。

页面尺寸 382 KB（数据 295 KB），比之前 355 KB 涨了 ~27 KB，全是这层 JS。

## 验证方法（可复现）

```bash
.venv/bin/python -m uvicorn colour_demo.main:app --port 8000 &
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new \
  --user-data-dir=/tmp/chrome-prof --virtual-time-budget=9000 \
  --dump-dom "http://127.0.0.1:8000/demo/#chromaticity" > /tmp/dom.html
```

- 在线：`#live-status` 显示 `实时结果 · 10 ms · POST /api/v1/...`，`#live-out` 里有 1–4 张卡；
- 离线（`file://` 直接打开）：`#chip-api` 显示「静态快照 · 未连 API」，主区域只有静态块、没有 `live-out`。

**坑**：用 `grep 'id="live-out"'` 验证是无效的——`<script>` 源码里也有同样的字符串，
必须切出 `<main id="main">…</main>` 再看。

## 联调顺手抓到的服务端 bug

`/api/v1/convert` 的默认空间表里 `CAM16 UCS` 在换算图里的节点名是 `cam16ucs`（没有空格），
`colour.convert(xyz, "CIE XYZ", "CAM16 UCS")` 直接 `NodeNotFound: Target cam16 ucs is not in G`。
M1 的测试只测过显式传 `target_spaces: ["CIE Lab"]`，所以一直没暴露——前端第一次用默认参数就炸。
已加 `GRAPH_ALIASES` 并补回归测试 `test_convert_default_spaces_all_resolve`（断言 14 个空间全出数）。

同类风险：任何“展示名 → 换算图节点名”的地方都要走别名（`conversion_path` 也一样）。

## 还没接面板的适配器

00 概览、03 观察者与光源、04 光度/明度、07 RGB 空间图鉴、19–28。
它们目前只有静态快照；03/04/07 的端点均已存在，补适配器即可（约 15 行/个）。
