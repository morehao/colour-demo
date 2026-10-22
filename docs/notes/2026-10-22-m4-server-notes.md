# M4 服务端笔记（面板 26–28，2026-10-22）

能力目录、白名单调用、OpenAPI 控制台收口，端点 28 → **30**，测试 70 → **75** 全绿。
前端同时补齐剩余适配器：**除 00 概览外，27 个面板全部可实时调用**。

## 1. `/catalog`：把「覆盖全部功能」变成可查询的表

口径与原型 `gen/catalog.py` 同源，但搬到服务层（内存里算一次、LRU 缓存）：

| 指标 | 值 |
| --- | --- |
| 子模块导出之和 | **1284**（跨模块有重复，所以是“之和”不是去重） |
| 顶层名称 | 439（其中 321 个可调用） |
| 归属 | 面板 **826** / 数据集 **238** / 内部 **220** |
| 覆盖率 | **100.0%**（构建断言：不允许出现未分类） |

实现要点：

- 归属先匹配**名称级规则**（`RULES`，如 `^(eotf|oetf|log_encoding…)` → 面板 08），再落到**子模块默认**（`MODULE_PANEL`）；
- 状态再按值类型分一层：落在“内部” → 内部；常量/数据集（`SDS_`/`CAT_`/`VIEWING_CONDITIONS` 等）→ 数据集；其余 → 面板；
- 这个过程要 `import` colour 的全部 25 个子模块（首次约 40 ms），整张表 `lru(maxsize=1)` 缓存，之后只做内存过滤；
- 空字符串按“未过滤”处理（表单/前端很容易送来 `q=&status=`）——这个不处理会直接 422，前端联调时踩到过。

## 2. `/catalog/invoke`：白名单是静态表，不做反射

方案 11 要求“不用 eval / exec / 动态导入”，所以白名单里每一条都写死**函数对象 + 参数声明**：

```
Entry(name, label, panel, returns, params=(Param(...), ...), example, fn)
```

- `Param` 声明类型（float/int/vector/string）、区间、枚举、向量长度、是否走 kwargs；
- 用户输入逐项 `_coerce()` 校验：类型、区间、长度、枚举都在进 colour 之前挡住（422）；
- 非白名单 → **403** `forbidden`，响应里列出可选函数（不泄露内部对象）；
- 支持三种写法：`params`（显式）、`args` + `kwargs`（贴合方案 6.2 的示例）、混用会报重复；
- 返回值统一 JSON 安全化：ndarray → 嵌套 list、numpy 标量 → Python 标量、nan/inf → `null`；
- colour 的告警原样回传 `warnings[]`（McCamy 非双射这类提示要能被看见）。

当前白名单 11 条（都是纯函数、无 I/O、无全局状态）：
`CCT_to_xy`、`xy_to_CCT`、`delta_E`、`XYZ_to_Lab`、`sRGB_to_XYZ`、`XYZ_to_Oklab`、
`colorimetry.luminance`、`volume.is_within_pointer_gamut`、`notation.munsell_colour_to_xyY`、
`notation.keyword_to_RGB_CSSColor3`、`blindness.matrix_cvd_Machado2009`。

黄金值：`CCT_to_xy(6500, McCamy 1992)` → `[0.312315, 0.332563]`（与面板 11 的结果一致），
`delta_E(黑, 白) = 100.0`。

## 3. 面板 28 没有新代码

它本来就是 FastAPI 的 `/openapi.json` + `/docs`。测试 `test_openapi_console_is_available`
断言「`/meta` 列的每个端点都在 OpenAPI 里」，防止端点清单和实际路由漂移。

## 4. 前端收尾

- 新增 26/27/28 与 03/04/07 适配器；`fields` 支持函数形式（面板 27 的白名单下拉框要运行时才知道）；
- 探测 `/api/v1/health` 成功后顺带取一次 `/api/v1/catalog?limit=1`，把白名单塞进下拉框；
- 修一个分支判断 bug：`runLive` 原先用「有没有 query」区分“图端点”和“普通 GET”，
  导致目录/空间图鉴这类纯 GET 适配器去调不存在的 `dataEndpoint`，直接报“调用失败”。
  现在按 `spec.dataEndpoint` 是否存在分支。

验证：headless Chrome 逐面板，**27 个面板全部 `live=yes` 且无「调用失败」**。

## 5. 剩下的只有工程化

功能面已闭合（面板 00–28 端点齐全、原型与实时双模可用）。还没做的是部署与 CI：
Dockerfile、GitHub Actions（`pytest` + 版本漂移门禁 `colour.__version__ == 0.4.7`）、
以及把本地过程文档（原 `.dsh/docs/`，已 gitignore）整理成仓库内的 `docs/`。

> 2026-10-22 补记：以上三项已在 `feat/ci-deploy` 落地 —— `Dockerfile` + `.github/workflows/ci.yml`
> 已加，过程文档已搬到仓库 `docs/specs/`、`docs/notes/`。
