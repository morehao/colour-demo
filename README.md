# colour-demo

> 基于 [colour-science/colour](https://github.com/colour-science/colour) 的色彩科学演示项目。

**状态：M2 完成（28 面板方案已定稿；原型 29 页全部出真实数据；服务端 `/api/v1` 可跑，面板 00–18 全覆盖，21 个端点 + 58 个测试全绿）**

<p>
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-blue.svg"></a>
  <img alt="Python 3.11+" src="https://img.shields.io/badge/python-3.11%2B-3776AB.svg">
  <img alt="colour-science 0.4.7+" src="https://img.shields.io/badge/colour--science-0.4.7%2B-ff6f61.svg">
</p>

颜色不是三个字节，而是「物理量 + 观察条件 + 感知模型」。这个仓库想把这条链路用几条命令、几张图串起来：
`sRGB → 线性光 → CIE XYZ → Lab / Oklab → ΔE、色域与色觉模拟`。

---

## 这个仓库是什么

- 一个围绕 [`colour-science/colour`](https://github.com/colour-science/colour) 的学习型演示项目，形态是一个**带 Web 界面的演示站**：左边选面板，右边看结论；
- 目标：把色彩科学里最常用的几件事，做成可直接运行、结果能看懂的小工具；
- 非目标：不做完整的色彩管理系统，也不替代 `colour` 本身——所有计算最终都交给它。

## Web 演示

> 原型可直接打开：`docs/prototype/index.html`（单文件、离线可用）。页面里的每个色值、矩阵、曲线都由 **colour-science 0.4.7** 真实计算，由 `docs/prototype/build_prototype.py` 分批生成。**原型按阶段补充**：已有数据的页面正常展示，未完成的页面以「数据待补充 + 补齐清单」占位。

覆盖口径（v0.4.7 实测）：25 个子模块 / **1284 条子模块导出** / **439 个顶层名称**，映射为 826 条面板覆盖 + 238 条数据集 + 220 条内部复用，覆盖率 100%（构建脚本断言）。

| 分组 | 面板 | 状态 |
| --- | --- | --- |
| 起点 | 00 概览（色彩链路 + 全站地图 + 分期） | 已出 |
| 基础换算 | 01 颜色转换与换算图 · 02 色度学属性 · 03 观察者与光源 · 04 光度/明度/白度黄度 | 已出 |
| 差异与均匀性 | 05 ΔE 全家桶（14 种） · 06 均匀空间与渐变 · 07 RGB 色彩空间图鉴（96 个） · 08 传递函数与视频信号 | 已出 |
| 色域与光源 | 09 色度图与色域 · 10 色域体与边界 · 11 色温与黑体轨迹 · 12 色彩质量（CRI/CQS/TM-30/SSI） | 已出 |
| 工程与数据 | 13 图像与 3D LUT | 已出 |
| 外观与感知 | 14 色适应 · 15 外观模型（12 个） · 16 视觉模型与感知现象 · 17 对应色 · 18 色觉障碍 | 已出 |
| 数据与算法 | 19 光谱重建 · 20 色彩校正与 ACES · 21 记号与解析 · 22 连续信号与插值器 · 23 几何与椭圆拟合 · 24 光学现象与响应动力学 · 25 图表画廊 | 已出 |
| 元能力 | 26 能力目录（1284 条可搜索） · 27 参数化调用 · 28 API 控制台（29 端点） | 已出 |

技术方案：`.dsh/docs/specs/2026-10-21-colour-web-demo-design.md`（含架构图 `colour-demo-web-architecture.svg`；构建事故与防护见 `.dsh/docs/notes/2026-10-21-build-memory-notes.md`）。技术栈 Python + FastAPI + 原生前端，图表默认由前端 SVG 从数据绘制，仅色度图/色域体/图表画廊用服务端 matplotlib，版本锁定 `colour-science==0.4.7`。

## CLI 形态（备选）

Web 演示是主线，同样的能力也可以做成脚本化 CLI。下表是早期规划，保留作为参考：

| 能力 | 主要依赖的 `colour` API | 产出 |
| --- | --- | --- |
| 色彩空间转换 | `sRGB_to_XYZ`、`XYZ_to_Lab`、`XYZ_to_Luv`、`XYZ_to_Oklab` | 终端表格 + `--json` |
| CIE 1931 色度图 | `colour.plotting.plot_chromaticity_diagram_CIE1931` | PNG，叠加 sRGB / Display P3 / BT.2020 色域与样本点 |
| 感知差异 ΔE | `colour.delta_E`（CIE 2000 / 1976 / 1994 / CMC） | 成对 ΔE 矩阵热力图 |
| 渐变插值 | Oklab 空间线性插值 | sRGB / 线性 sRGB / Oklab 三段对比，标注步长均匀性 |
| 色觉障碍模拟 | `colour.blindness.matrix_cvd_Machado2009` | 红色盲 / 绿色盲 / 蓝色盲下的同一组调色板 |
| 一键报告 | 以上组合 | `out/report.md` + 全部配图 |

## 服务端（M2，可跑）

```bash
# 安装（colour-science 版本被锁死，黄金值测试依赖它）
uv venv .venv && uv pip install --python .venv/bin/python -e ".[dev]"

# 启动：一条命令，零前端构建（G3）
.venv/bin/python -m uvicorn colour_demo.main:app --port 8000
# 不想装包也可以：PYTHONPATH=src .venv/bin/python -m uvicorn colour_demo.main:app --port 8000
# 打开 http://127.0.0.1:8000/docs 看 OpenAPI；静态原型在 http://127.0.0.1:8000/demo/

# 测试：黄金值 + Sharma ΔE 参考对 + 接口契约
.venv/bin/python -m pytest
```

已实现 **21 个端点**，覆盖面板 00–18（面板 19–25 的服务端是 M3）：

| 端点 | 说明 | 面板 |
| --- | --- | --- |
| `GET /api/v1/health` | 版本自检（`colour.__version__` 断言 0.4.7） | 28 |
| `GET /api/v1/meta` | 版本、全站方法枚举、计数、端点清单 | 00 / 26 |
| `GET /api/v1/spaces` | 96 个 RGB 色彩空间（基色 / 白点 / 传递函数） | 07 |
| `POST /api/v1/convert` | 换算到 14 个核心空间 + 换算链路 | 01 |
| `POST /api/v1/chroma` | xy / uv / u′v′、主波长、激发与色度纯度 | 02 |
| `POST /api/v1/spectral` | SPD 采样、观察者摘要、黑体光谱 | 03 |
| `POST /api/v1/photometry` | 明度（7 种）/ 亮度 / 白度 / 黄度 | 04 |
| `POST /api/v1/delta-e` | 14 种 ΔE 的对称矩阵 + 最近 / 最远一对 | 05 |
| `POST /api/v1/gradient` | N 步插值 + 步长 ΔE 均匀度 | 06 |
| `POST /api/v1/transfer` | OETF / Log 编码曲线 + 往返误差 + YCbCr（BT.709/2020/601） | 08 |
| `GET /api/v1/chromaticity` | 色域三角形面积、样本点 xy / u′v′、是否在色域内 | 09 |
| `GET /api/v1/chromaticity.svg` | 色度图（唯一出图的端点，ETag 命中回 304） | 09 |
| `POST /api/v1/volume` | MonteCarlo 色域体积 + MacAdam / Pointer / 可见光谱判据 | 10 |
| `POST /api/v1/temperature` | xy 派 / uv 派色温正反解 + mired + 普朗克轨迹 | 11 |
| `POST /api/v1/quality` | CRI Ra（1995/2024）、CQS、TM-30 Rf/Rg、SSI | 12 |
| `POST /api/v1/lut` | 17³ LUT 的三线性 / 四面体插值对比 + 灰阶带 | 13 |
| `POST /api/v1/adapt` | 7 种色适应方法 + vK20 + 13 个 CAT 矩阵 | 14 |
| `POST /api/v1/appearance` | 12 个外观模型的 J/C/h/M/H + 往返误差 | 15 |
| `POST /api/v1/phenomena-vision` | H-K 效应（VCC/VAC）+ Barten 1999 CSF | 16 |
| `POST /api/v1/corresponding` | Breneman 8 组实验 × 5 个模型的 u′v′ 偏差 | 17 |
| `POST /api/v1/cvd` | Machado 2009 三类锥体 × 连续严重度 + 可区分性指标 | 18 |

错误一律 `{"detail": {"type": ..., "message": ...}}`（方案 6.3）：坏色值指出「第几个」、
超上限给「最多 12 个」、未知方法列出可选枚举、请求体超 32 KB 直接 413、500 只返回 `trace_id`。
每条响应带 `X-Compute-Ms`。

面板 08 的编码目录不硬编码函数名，而是从 `colour.OETFS` / `LOG_ENCODINGS` / `LOG_DECODINGS`
现取，逆函数按 `oetf_inverse_<后缀>` 约定配对；0.4.7 里 `oetf_SMPTE240M` 没有逆函数，
响应会如实标成 `invertible: false` 而不是假装能往返。

## 前端：静态快照 + 实时 API 两种模式

`docs/prototype/index.html` 是单文件原型，默认展示**构建时**由 colour 算好的快照（离线可用）。
本地起了服务端后，同一个页面会自动切换成**实时调用**：

```bash
.venv/bin/python -m uvicorn colour_demo.main:app --port 8000
# 打开 http://127.0.0.1:8000/demo/ —— 控件可改，点「调用 API」或直接回车，数字由服务端现算
# 也可以直接开文件（file:// 打开时会去 http://127.0.0.1:8000 找服务端）：
#   docs/prototype/index.html?api=http://127.0.0.1:8000
```

| 能力 | 说明 |
| --- | --- |
| 自动探测 | 首次加载打 `GET /api/v1/health`；在线就把顶栏换成「API 在线 · colour 0.4.7」，离线退回静态快照并保留全部内容 |
| 已接适配器的面板 | 01 转换、02 色度学、05 ΔE、06 渐变、08 传递函数、09 色度图、10 色域体、11 色温、12 质量、13 LUT、14 色适应、15 外观、16 感知、17 对应色、18 CVD |
| 交互 | 下拉/文本框真实可改；改完回车或点按钮重算；每次请求都能展开看**请求与响应 JSON**（面板 28 的轻量版） |
| 快照共存 | 实时结果在上，构建时的静态快照折叠在下，断网也能讲完整个故事 |
| 未接的面板 | 00 概览、03 观察者、04 光度、07 空间图鉴、19–28（含能力目录的搜索仍可用）保持静态 |

联调时抓到过一个真 bug：默认空间表里的 `CAM16 UCS` 在换算图里的节点名是 `cam16ucs`，
`colour.convert` 直接抛 `NodeNotFound: Target cam16 ucs is not in G`——已加别名映射与回归测试。

## 示例：现在就能跑的 `colour` 代码

以下片段只依赖 `colour-science`，不需要本仓库的代码，可直接对照理解后续 CLI 的输入输出。

```python
import colour

rgb = [59 / 255, 130 / 255, 246 / 255]   # #3B82F6

xyz = colour.sRGB_to_XYZ(rgb)            # CIE XYZ (D65)，Y ∈ [0, 1]
lab = colour.XYZ_to_Lab(xyz)             # L* 55.63, a* 17.55, b* -64.42
oklab = colour.XYZ_to_Oklab(xyz)         # Oklab：适合做插值与感知均匀的渐变

print(lab.round(2), oklab.round(3))

red_lab = colour.XYZ_to_Lab(colour.sRGB_to_XYZ([1.0, 0.0, 0.0]))
print(round(colour.delta_E(lab, red_lab, method="CIE 2000"), 2))   # ≈ 50.06
```

> 说明：`colour.convert()` 的自动转换图还需要 `networkx`，绘图还需要 `matplotlib` 与 `scipy`。
> 按需补装即可：`pip install colour-science matplotlib networkx scipy`。

## 目标 CLI（待实现）

```bash
# 单个颜色的全部表示：sRGB / 线性 sRGB / XYZ / xyY / Lab / Luv / Oklab / OKLCH / HSL / HSV
colour-demo convert "#3B82F6"

# 把颜色画到 CIE 1931 色度图上，并叠加三种 RGB 色域
colour-demo gamut "#264653" "#2A9D8F" "#E9C46A" "#F4A261" "#E76F51" --out out/gamut.png

# 成对 ΔE 矩阵（终端表格 + 热力图）
colour-demo delta-e "#264653" "#E9C46A" --method cie2000

# 同一组端点，三种插值空间的观感差异
colour-demo gradient "#264653" "#E9C46A" --steps 11

# 色觉障碍模拟
colour-demo cvd --severity 1.0

# 一次生成全部图表与 Markdown 报告
colour-demo report --out out
```

## 环境要求

| 依赖 | 版本 | 说明 |
| --- | --- | --- |
| Python | ≥ 3.11 | `colour-science` 0.4.7 的硬性要求 |
| colour-science | ≥ 0.4.7 | 全部色彩计算 |
| NumPy | ≥ 2.0 | 数组与矩阵运算 |
| Matplotlib | ≥ 3.9 | 色度图、热力图、色板 |
| NetworkX | ≥ 3.3 | `colour.convert()` 转换图 |
| SciPy | ≥ 1.11 | `colour.plotting` 的平滑与插值 |
| FastAPI | ≥ 0.115 | 服务端框架（`/api/v1`） |
| Uvicorn | ≥ 0.30 | ASGI 服务器，单进程跑起来 |

## 目录结构

```text
colour-demo/
├── docs/
│   └── prototype/          # 已产出：静态原型 + 分阶段构建
│       ├── index.html      #   单文件原型（29 页，内联数据）
│       ├── index.template.html
│       ├── build_prototype.py   # --batch 1|2|3 / --merge
│       └── gen/            #   面板定义、块类型、能力目录映射、占位清单
├── src/colour_demo/        # 已实现（M1）：FastAPI 应用
│   ├── main.py             #   应用装配：路由、静态、异常、版本断言
│   ├── api/                #   pydantic 契约（schemas）与 /api/v1 端点（routes）
│   └── core/               #   一个面板一个模块（纯函数）：convert/chroma/spectral/…
├── tests/                  # 已实现：黄金值、Sharma ΔE 参考对、接口契约
│   └── data/               #   sharma2005_delta_e2000.json（取自上游同口径）
├── LICENSE                 # MIT
└── README.md
```

## 路线图

- [x] 技术方案（28 面板全量覆盖、API 契约、覆盖自检、分阶段交付、性能与验收）
- [x] 原型骨架 + 29 页真实数据（00–28，含 7 个前端 SVG chart 块）
- [x] 补齐原型面板 19–25（M3，`--panel` 逐面板独立进程构建，单面板峰值 126–160 MB）
- [x] M1：FastAPI 骨架 + 面板 00–07 端点（9 个）+ 黄金值测试（28 项全绿）
- [x] M2：色域/色温/质量/LUT/适应/外观/感知/对应色/CVD 端点（面板 09–18，11 个端点）
- [x] M2 补齐：面板 08 传递函数与视频信号（`POST /api/v1/transfer`）
- [x] 前端接 API：15 个面板的实时适配器 + 离线退回静态快照
- [ ] M4：能力目录、参数化调用、OpenAPI、部署与 CI

## 参考资料

- [colour-science/colour](https://github.com/colour-science/colour) —— 本项目全部计算的来源
- [colour 文档](https://colour.readthedocs.io/) —— API 与色彩空间定义
- Björn Ottosson, *A perceptual color space for image processing*（Oklab，2020）
- Machado, Oliveira & Fernandes, *A Physiologically-based Model for Simulation of Color Vision Deficiency*（2009）
- [WCAG 2.2 对比度要求](https://www.w3.org/TR/WCAG22/#contrast-minimum)
- CIE 15:2004 *Colorimetry* —— XYZ、Lab、ΔE 的标准定义

## License

[MIT](LICENSE) © 2026 morehao
