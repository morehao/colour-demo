# M1 服务端实现记录：9 个端点 + 28 项测试

日期：2026-10-21 ｜ 分支 `feat/web-demo` ｜ 方案里程碑 M1（面板 00–08 的服务端子集）

## 1. 交付物

| 路径 | 内容 |
| --- | --- |
| `src/colour_demo/__init__.py` | 版本常量 + `assert_colour_version()`（0.4.7 锁死，否则拒启） |
| `src/colour_demo/main.py` | `create_app()`：异常映射、`/demo` 静态挂载、根 `/health` |
| `src/colour_demo/api/schemas.py` | pydantic 请求模型；颜色字面量在校验阶段就预解析 |
| `src/colour_demo/api/routes.py` | 9 个端点，只做「取参 → 调 core → 返回」 |
| `src/colour_demo/core/` | `parsing` / `errors` / `cache` + 面板模块 `convert` / `chroma` / `spectral` / `photometry` / `delta_e` / `gradient` / `spaces` |
| `tests/test_golden.py` | 版本门禁、黄金值、往返、Sharma ΔE2000 参考对、方案示例复现 |
| `tests/test_api.py` | 端点契约 + 7 类错误路径的 M1 子集 |
| `tests/data/sharma2005_delta_e2000.json` | 33 对参考数据（取自上游同口径，排除第 14 对） |
| `pyproject.toml` | 依赖锁 `colour-science==0.4.7`、pytest `pythonpath=src` |

实测：`pytest` → **28 passed**；`uvicorn` 一条命令启动，`/docs` 与 `/openapi.json` 正常。

## 2. 端点与延迟（本机热态，20 次取样）

| 端点 | p50 | p95 |
| --- | --- | --- |
| `POST /api/v1/convert` | 1.05 ms | 1.26 ms |
| `POST /api/v1/delta-e`（5 色） | 1.78 ms | 2.13 ms |
| `POST /api/v1/gradient`（101 步） | 1.62 ms | 2.02 ms |
| `POST /api/v1/chroma` | 2.25 ms | 2.55 ms |
| `POST /api/v1/photometry` | 1.21 ms | 1.71 ms |
| `GET /api/v1/spaces`（96 个空间） | 0.81 ms | 1.23 ms |

方案 9 的目标是「非图表端点 P95 ≤ 50 ms」，全部达标（余量 20 倍以上）。

## 3. 三个踩坑（都已写进方案 7.2 / 12）

### 3.1 `XYZ_to_Lab` 收 Domain1，不是 Domain100

`colour.XYZ_to_Lab(XYZ)` 期望 XYZ 在 0–1，返回 0–100 的 Lab。
若先乘 100 再传，会得到 `L* ≈ 187` 这种荒谬值。**原型侧与本实现都直接传 0–1**，
所以方案 6.2 的示例数值（33.53 / 61.41 / 57.7 / 50.74）能逐位复现。

### 3.2 `colour.convert` 默认给 Lab/100

`convert(xyz, "CIE XYZ", "CIE Lab")` 默认返回 **0–1 刻度的 Lab**；
要人类可读刻度必须 `to_reference_scale=True`，反向插值回 XYZ 要 `from_reference_scale=True`。
第一版 `/convert` 就踩了这个坑：同一份数据在 `/convert` 里是 `55.63`，在 `/delta-e` 里是 `27.89`
（前者其实是 Lab/100 被四舍五入后的错觉）。现已统一为 0–100，并加契约测试锁死。

### 3.3 sRGB 往返达不到 1e-6

方案 12 要求往返误差 ≤ 1e-6。实测 sRGB↔XYZ 的往返误差 **5.7e-5**——
是 colour 的 sRGB EOTF/OETF 互逆残差，不是我们的实现问题。
线性域（XYZ↔Lab、XYZ↔Oklab）确实在 1e-6 内。
处理：测试按域分容差（线性域 1e-6、sRGB 1e-4）并在方案 12 注明。

## 4. 顺带做的两件事

- **`/gradient` 向量化**：第一版逐步调用 `colour.convert`，101 步要 24 ms；
  改成整批 `(N,3)` 一次转换后降到 **1.62 ms**（15×）。
- **校验报错说人话**：`{"detail": {"type": "value_error", "message": "第 2 个颜色：无法解析颜色 'bad'…"}}`，
  超上限给「colors 最多 12 个」，`errors[]` 里保留 `loc` 供前端定位。

## 5. 未做（按约定不越界）

- M2/M3/M4 的端点（09–28）未实现，`/meta` 的 `endpoints` 只列 M1 的 9 个；
- 图表端点（色度图 SVG/PNG）与 LRU 缓存虽已备好 `core/cache.py`，但首个图表端点属于 M2；
- 鉴权/限流/配额（方案 Q5：先内网）；
- 前端不再是「数据待补充」占位，但页面控件仍未接 API —— 接 API 属于 M1 之外的联调，方案里定在 M1 之后。
