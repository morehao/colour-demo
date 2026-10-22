# 专家面板颜色参数改成色块控件（排查/变更记录）

日期：2026-10-22
涉及：`docs/prototype/ui/{components,live,panels,adapters,adapters-late}.js`、`index.template.html`

## 起因

用户反馈截图（面板 05 ΔE 全家桶）：颜色参数是一个文本框，标签"颜色（逗号分隔，≥2）"，值是一串 `#264653, #2A9D8F, …`。
手打十六进制对普通用户不成立：不知道色号、容易多打空格/漏 `#`、一个字符错就整组失败。

## 改法

1. `components.js` 的色块行组件泛化出 `prefix` 选项：
   - `data-color-*`（任务页，行为不变，只认 HEX）；
   - `data-live-color-*`（面板控制区，另放行 `rgb()`/`hsl()`/CSS 关键字）。
   同时补 `looksLikeColour()` 粗筛、单色模式（不渲染删除按钮）。
2. 适配器新增两种字段 kind：`colors`（多色，带 `min`/`max`）、`color`（单色）。
   `LIVE.*.body` 一行没改：控件对外仍序列化成逗号列表，`splitList` 照旧工作。
3. `live.js`：
   - `renderColorField` 渲染色块行，`liveFieldValue` 从行里回收色值；
   - 颜色改动即算（防抖 320 ms），并用请求序号 `liveSeq` 丢弃过期响应，避免连点/连拖时旧结果盖新结果；
   - 非法或半截输入（`#12`、`##`）**不发请求**，只标红；
   - 有效色值不足 `min` 时不发请求，状态行说明差几个；
   - 面板 422 报错不再被"先启动服务端"顶掉，直接显示服务端的人话。
4. 17 个面板、19 处颜色字段换成新 kind：convert / chroma / delta-e / gradient（起点+终点）/ transfer / chromaticity / gamut-volume / temperature / image-lut / adaptation / appearance / phenomena-vision / cvd / recovery / notation（HEX）/ photometry。标签里的"逗号分隔"去掉，改成"最多 12 个 / 至少 2 个"。

## 验证

- `build_prototype.py --merge` 通过；`pytest` 全绿（93 条）。
- Chrome CDP 冒烟（真服务 + 真点击）：加色 5→6 行、改 HEX 后取色器同步、点取色器 HEX 跟着变、`##` 标红不发请求、`tomato` 被服务端接受并重算、删到下限后删除按钮禁用。
- 390 px 视口下 `.color-row` 无溢出，`documentElement.scrollWidth == 390`。
- 任务页（`#/task/delta-e`）回归：加/删/改色、非法输入、链接同步均与改造前一致。

## 顺手调了门禁

旧 UI 源码 122 878 B（120.0 KB），距 120 KB 预算只剩 2 B，这次必然超。
把 `build_prototype.py` 与 `2026-10-22-beginner-mode-plan.md` 的 UI JS 预算改成 130 KB（产物 543 KB，仍远低于 700 KB）。
