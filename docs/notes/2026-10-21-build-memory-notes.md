# 原型构建导致的本机内存事故 · 排查记录

**日期**：2026-10-21
**范围**：colour-demo 原型构建（`docs/prototype/build_prototype.py` 及探针脚本）
**机器**：Mac16,8（M4 Pro）/ 24 GB / macOS 27.0.1，`vm.swapusage` 为 `total = 0.00M`（无 swap）

## 现象

1. 17:36:54 内核 `memorystatus: killing Python [35358] due to low-swap`；我的构建进程以 `exit 137`（SIGKILL）结束。
2. 17:38:44 DSH 桌面渲染进程被 SIGKILL（`crash-2026-10-21T09-38-44-331Z-renderer.log`）。
3. 17:43:21 内核 `System is unhealthy`，压缩器约 9.3 GB；17:43 批量杀死守护进程；17:44:45 强制复位。
4. 18:12 再次复现：`--batch 3` 在 `optics` 之后中断（图表画廊 panel 未完成）。

## 归因

- **直接诱因在构建侧**：一次进程内渲染全部面板（26 个面板、含 27 张 matplotlib 图 + 蒙特卡洛色域体积 + 96 行色彩空间表），且叠了一次探针脚本触发 `plot_RGB_scatter` 内部 multiprocessing 池（stderr 刷出 205 KB）。
- **根因在环境侧**：swap = 0，常驻大户（OrbStack 2.2 GB、gopls 1.3 GB、VS Code、Edge、WebKit、DSH）已把余量吃紧；10-19、10-20 已有两次 jetsam。构建只是压垮它的最后一股负载。
- 与项目代码 bug 无关：被杀的 Python 进程本身也是受害者。

## 处置

| 措施 | 落地 |
| --- | --- |
| 分批构建 | `--batch 1/2/3` + `--merge`，每批一个进程，产物落 `.tmp/panels/*.json` |
| 内存守卫 | 每面板后打印峰值；超过 `BUILD_MEMORY_LIMIT_MB`（默认 700）退出码 3 |
| 资源释放 | 每面板 `plt.close("all")` + `gc.collect()` |
| 图表策略 | 后续面板默认前端 SVG（`chart` 块）；matplotlib 仅保留 09/10/13/25 |
| 探针纪律 | 禁用内部用 multiprocessing 的绘图函数；不后台跑重任务；跑前看 `vm.swapusage` / `memory_pressure` |

## 实测（分批后）

| 批次 | 面板 | 峰值 | 耗时 | 产物 |
| --- | --- | --- | --- | --- |
| batch1 | 00–08 | 210 MB | 0.7 s | 84 KB |
| batch2 | 09–18 | 213 MB | 5.2 s | 88 KB |
| 元能力 | 26–28 | 128 MB | 0.4 s | 98 KB |
| merge | 全站 | < 100 MB | < 0.1 s | 295 KB |

## 遗留

- `--batch 3`（面板 19–25）暂停，原型里以「数据待补充」占位；补齐时按面板逐个跑，单面板 < 300 MB。
- 建议开启 swap 或给 OrbStack 设内存上限；否则任何批量构建都存在同样风险。
