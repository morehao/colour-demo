# 部署与 CI（feat/ci-deploy）

2026-10-22。补掉最后的工程化缺口：GitHub Actions、Docker 镜像、过程文档入库。

## 1. 先合并 PR #4（M3+M4）

`gh pr merge 4 --squash --delete-branch`，main 到 `92fca3d`（与 #3 同风格 squash）。
`--delete-branch` 顺带把远端 `feat/web-demo` 一起清理了（其内容早经 #3 入库，diff 为空）。
本地 `feat/m3-server` 已随合并删除，工作区干净。

## 2. CI 首跑就抓到了三件事

**① 依赖声明不全（真 bug，不是 CI 的问题）**

`pip install -e ".[dev]"` 装进干净 venv 后直接 `ModuleNotFoundError: networkx`。
原因：colour-science 0.4.7 把 `matplotlib` / `scipy` / `networkx` 全列成 **optional extra**：

```
Requires-Dist: matplotlib>=3.9; extra == 'optional'
Requires-Dist: networkx<4,>=3.3; extra == 'optional'
Requires-Dist: scipy<2,>=1.13.0; extra == 'optional'
```

而本项目三处都真的要用：出图端点（`colour.plotting`）、`colour.algebra` 内部实现、
换算图（`colour.graph` 需要 networkx）。之前本机 venv 是手工补装的，`pyproject.toml`
里从没写 —— 等于「只有我这台机器能装」。现在三个都进了 `dependencies`。

**② 两个断言是「同机才成立」的**

| 测试 | 本机（macOS/arm64） | CI（Linux/x86） | 原因 |
| --- | --- | --- | --- |
| `test_geometry_contract` 半轴 | ≈0.00210 | 0.00208529 | 二次曲线拟合走 LAPACK，平台间差 0.7% |
| `test_volume_..._reproducible` P3/sRGB | 1.437–1.506（跨种子） | 1.5625 | MonteCarlo 抽样噪声（5000 点约 ±5%，20000 点 ±3%） |

改法：几何按 `rel=0.05` 比（原始数据本身只有 4 位有效数字），体积改成量级断言
`1.25 < ratio < 1.75`。**可复现性断言（两次调用逐位相等）保留**，那才是这层的契约。
教训：跨机器的数值断言只能锁「量级/关系」，锁不住具体末位。

**③ `app.routes` 数不到子路由**

冒烟步骤原本想数路由，结果 `app.routes` 里 `include_router` 的产物是一个
`_IncludedRouter` 嵌套对象（没有 `.path`），直接遍历会漏报所有 `/api/v1/*`。
改成读 `app.openapi()["paths"]`，并断言 `/api/` 前缀路径恰好 30 个 —— 顺手把
「端点契约」变成 CI 门禁。

## 3. Dockerfile 的两个坑

- **必须可编辑安装**：`main.py` 用 `Path(__file__).resolve().parents[2] / "docs" / "prototype"`
  定位静态原型。装进 site-packages 后 `parents[2]` 指向不存在的位置，`is_dir()` 为假，
  `/demo` 会**静默不挂载**（不报错，只是 404）。所以镜像里 `pip install -e .`，源码树留在 `/app`。
- **不用 BuildKit 的 cache mount**：本机 docker 没有 buildx，`RUN --mount=type=cache` 直接报错。
  改用 `pip install --no-cache-dir`，经典构建器也能构建。

验证：`docker build` + `run -p 18000:8000` → `/health` 返回 `colour_version: 0.4.7`、
`/openapi.json` 30 个 `/api/` 路径、`/demo/` 200（407539 字节）、
`POST /api/v1/plot` 在容器内出图成功（非 root + Agg + 可写字体缓存）、`HEALTHCHECK` healthy。

## 4. 过程文档入库

`.dsh/docs/` 已 gitignore，方案与笔记只有本地一份。搬进仓库：

- `docs/specs/`：技术方案 v2 + 架构图 SVG
- `docs/notes/`：8 篇阶段记录（路径引用里的 `.dsh/docs/` 同步改成 `docs/`）
- `docs/README.md`：索引 + 记下「方案写 29 端点、实现到 30 端点」的有意偏差
  （M4 把能力目录/参数化调用做成两个真端点）

## 5. 结果

CI 绿（py3.11 / py3.14 两格），PR #5。仍未做：镜像发布（GHCR）、前端 headless 回归进 CI。

## 6. docker compose（补：部署验证）

`docker-compose.yml` 单服务编排，与 `docker run` 等价但把部署姿势固定下来：

```yaml
read_only: true          # 服务无状态：容器根只读
tmpfs: [/tmp:size=64m]   # matplotlib 字体缓存放内存（实测 28 KB）
init: true               # uvicorn 不当 PID 1，SIGTERM 能优雅退出
restart: unless-stopped
```

健康检查不重复写，继承镜像里的 `HEALTHCHECK`；端口 `${COLOUR_DEMO_PORT:-8000}` 可覆盖。

实测（`docker compose up -d --build`）：

| 检查 | 结果 |
| --- | --- |
| `docker compose ps` | `Up (healthy)`，`0.0.0.0:8000->8000/tcp` |
| `/health` | `{"status":"ok","colour_version":"0.4.7"}` |
| `/demo/` | 200，407539 字节 |
| `/openapi.json` | 30 个 `/api/` 路径 |
| `POST /api/v1/plot`（两张图） | 8632 / 13756 字符 base64，只读根 + tmpfs 下正常 |
| `GET /api/v1/chromaticity.svg` | 200，216269 字节 |
| `POST /api/v1/catalog/invoke` | 白名单内正常返回；`os.system` → 403 |
| `docker compose restart` | 10 s 后回 healthy，健康检查重新通过 |
| `docker compose down` | 容器与 network 干净移除 |

环境坑（本机）：这台机器的 docker 是 OrbStack 的 CLI，`docker compose` 插件装在
`~/.docker/cli-plugins`；一旦把 `DOCKER_CONFIG` 指到别处（沙箱里必须这么做，`~/.docker`
不可写）插件就找不到，报 `docker: unknown command: docker compose`。
解法是给自定义 `DOCKER_CONFIG` 目录建 `cli-plugins` 软链指向真实插件目录。
这只影响本机折腾，不影响仓库里的文件。
