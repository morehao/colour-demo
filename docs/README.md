# docs 索引

过程性文档（技术方案、架构图、各阶段排查记录）都在这里；代码在 `src/`，静态原型在 `docs/prototype/`。

| 产出 | 路径 | 说明 |
| --- | --- | --- |
| 技术方案（v2，定稿） | [`specs/2026-10-21-colour-web-demo-design.md`](specs/2026-10-21-colour-web-demo-design.md) | 28 功能面板 + 概览的全量设计、API 契约、覆盖自检口径、M1–M4 分阶段交付 |
| 小白友好改造（终局） | [`specs/2026-10-22-beginner-mode-plan.md`](specs/2026-10-22-beginner-mode-plan.md) | 任务层 + 双模式 + 数据化文案/阈值：IA、数据模型、6 个任务页、29 面板口径、构建门禁与排期 |
| 架构图 | [`specs/colour-demo-web-architecture.svg`](specs/colour-demo-web-architecture.svg) | 四层结构（前端 / API / core / colour）+ 缓存、能力目录、CI |
| 静态原型 | [`prototype/index.html`](prototype/index.html) | 29 页单文件原型，双击可开；构建脚本 `prototype/build_prototype.py` |

## 笔记（按时间）

| 笔记 | 主题 |
| --- | --- |
| [`notes/2026-10-21-build-memory-notes.md`](notes/2026-10-21-build-memory-notes.md) | 原型批量构建把机器打死：swap=0、SIGKILL 归因与「单面板构建」纪律 |
| [`notes/2026-10-21-m1-server-notes.md`](notes/2026-10-21-m1-server-notes.md) | M1 骨架 + 面板 00–07 端点 |
| [`notes/2026-10-21-m2-server-notes.md`](notes/2026-10-21-m2-server-notes.md) | M2 面板 09–18 端点与色度图缓存/ETag |
| [`notes/2026-10-21-panel19-recovery-notes.md`](notes/2026-10-21-panel19-recovery-notes.md) | 光谱重建：Smits 重建后 ΔE 26 → 1.15 的传输函数方向 bug |
| [`notes/2026-10-21-panels20-25-notes.md`](notes/2026-10-21-panels20-25-notes.md) | 校正 / 记号 / 插值 / 几何 / 光学 / 画册六个面板的口径陷阱 |
| [`notes/2026-10-22-frontend-live-notes.md`](notes/2026-10-22-frontend-live-notes.md) | 前端双模（在线实时 / 离线快照）与 27 个适配器联调 |
| [`notes/2026-10-22-m3-server-notes.md`](notes/2026-10-22-m3-server-notes.md) | M3 面板 19–25 端点 |
| [`notes/2026-10-22-m4-server-notes.md`](notes/2026-10-22-m4-server-notes.md) | M4 能力目录、白名单调用、OpenAPI 控制台 |
| [`notes/2026-10-22-ci-deploy-notes.md`](notes/2026-10-22-ci-deploy-notes.md) | CI 首跑抓到的三件事（依赖漏声明 / 跨平台断言 / 路由数不到）+ Dockerfile 的坑 |

## 方案与实现的偏差（有意为之）

方案 v2 写的是「29 个端点 / 28 面板 + 概览」；实现到 M4 时把「能力目录 + 参数化调用」做成了
两个真端点（`GET /api/v1/catalog`、`POST /api/v1/catalog/invoke`），因此最终是 **30 个端点**，
面板 00–28 全覆盖、无需占位。版本基线始终是 **colour-science 0.4.7**（启动断言 + CI 门禁 `assert_colour_version()`），
测试 **75 项**。
