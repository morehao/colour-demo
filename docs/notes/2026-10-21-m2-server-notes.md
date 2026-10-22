# M2 服务端实现笔记（面板 09–18，2026-10-21）

> 结论先行：M2 的 10 个面板模块全部落地（11 条路由），`pytest` 54 项全绿。
> 过程中挖出 **13 条 colour 0.4.7 的口径/接口陷阱**，其中 6 条是原型阶段就静默「不可用」的行——
> 也就是说原型有 6 处表格单元格是空的或错的，服务端这次才对上。

## 1. 落地的模块

| 面板 | 模块 | 端点 | 关键调用 |
| --- | --- | --- | --- |
| 09 色度图 | `core/chromaticity.py` | `GET /chromaticity`、`GET /chromaticity.svg` | `plot_chromaticity_diagram_CIE1931/1960/1976` |
| 10 色域体 | `core/volume.py` | `POST /volume` | `RGB_colourspace_volume_MonteCarlo`、`is_within_*` |
| 11 色温 | `core/temperature.py` | `POST /temperature` | `xy_to_CCT` / `uv_to_CCT` / `CCT_to_xy` / `CCT_to_uv` / `CCT_to_mired` |
| 12 质量 | `core/quality.py` | `POST /quality` | `colour_rendering_index` / `colour_quality_scale` / `colour_fidelity_index` / `spectral_similarity_index` |
| 13 LUT | `core/lut.py` | `POST /lut` | `io.LUT3D` + `algebra.table_interpolation_*` |
| 14 色适应 | `core/adapt.py` | `POST /adapt` | `chromatic_adaptation`（7 方法）+ `chromatic_adaptation_vK20` + 13 个 `CAT_*` |
| 15 外观 | `core/appearance.py` | `POST /appearance` | 12 个 `XYZ_to_<model>` |
| 16 感知 | `core/phenomena.py` | `POST /phenomena-vision` | `HelmholtzKohlrausch_effect_object_Nayatani1997`、`contrast_sensitivity_function_Barten1999` |
| 17 对应色 | `core/corresponding.py` | `POST /corresponding` | `corresponding_chromaticities_prediction` |
| 18 CVD | `core/cvd.py` | `POST /cvd` | `matrix_cvd_Machado2009` |

另加一个共享件 `core/diagnostics.py`：把 colour 的 `ColourUsageWarning` 收成响应里的 `warnings[]`
（去重 + 截断 + `None`/`nan` 安全的 `number()`）。`payload` 要在 `with` 块**之后**读，注意别踩。

## 2. 原型里「不可用」的 6 行，根因都在服务端这轮查清了

| 面板 | 原型里的症状 | 真正原因 | 修法 |
| --- | --- | --- | --- |
| 11 色温 | `Ohno 2013` / `Robertson 1968` 走 `xy_to_CCT` → 不可用 | 这两个是 **uv 派**方法，`xy_to_CCT` 不认 | 拆成 xy 派 / uv 派两张表分别调 |
| 11 色温 | —（原型没做正解） | `CCT_to_uv` 返回形状不统一：Ohno/Robertson `(2,)`、Krystek/Planck `(2,2)` | `reshape(-1, 2)[0]` 取第一组 |
| 14 色适应 | CIE 1994 / CMCCAT2000 / Fairchild 1990 四行「不可用」 | 通用入口对这四个方法缺参数 → TypeError | 按方法补 `Y_o/E_o1/E_o2`、`L_A1/L_A2`、`Y_n`、`L_A/F_surround` |
| 15 外观 | Hunt 行「不可用」 | 不给 `CCT_w`/`L_AS` 直接 ValueError；且 `VIEWING_CONDITIONS_HUNT` 键名是 `Normal Scenes` 等 | 显式传 `CCT_w=6500` + 键名映射 |
| 16 感知 | CSF 曲线「几乎全零」 | `Y_0` 是**视角（度）**不是亮度；`sigma` 是线扩散标准差（默认 0.00879 度），原型传 0.3 | 亮度 → 瞳孔直径 → 视网膜照度 `E`，再算 CSF |
| 13 LUT | 两种插值「不可用」 | `interpolator=` 要可调用对象，不是 `"Trilinear"` 字符串 | 传 `colour.algebra.table_interpolation_*` |

顺带修掉的：色域内外判定原想用 `colour.convert(xyz, "CIE XYZ", "Display P3")`，
`Display P3` 不是换算图节点（`NodeNotFound: display p3`），改走色彩空间自带的
`matrix_XYZ_to_RGB` + `cctf_encoding`。

## 3. 服务端特有的工程点

1. **体积 MonteCarlo 必须关 multiprocessing**：`RGB_colourspace_volume_MonteCarlo` 内部开
   `multiprocessing.Pool`（进程数 = CPU 核数）。Web 服务里每次请求 fork 一池子进程不可接受，
   也解释得通原型 `--batch 3` 为何被系统回收打死。用 `disable_multiprocessing()` 包住 + 全局锁
   （它是模块级开关，多线程下必须串行），实测 5000 采样 ~2 ms，比开池子稳。
2. **`Domain100` 标量参数也按 0–1 传**：`Y_o=0.2` 才是 20%。传 20 会触发
   `"Y_o" ... must be in [18, 100]` 的假告警——这条告警本身是误报，别去调参数迎合它。
3. **matplotlib 只在图端点导入**：`core/chromaticity.py` 里延迟 `import matplotlib` 并
   `MPLCONFIGDIR` 指向临时目录（本机 `~/.matplotlib` 不可写）。
4. **SVG 日期剥离**：matplotlib 的 SVG 带 `<dc:date>`，字节每次不同 → ETag 由规范化参数 + colour 版本
   算出，同时把日期正则剥掉，让同参数请求得到同字节（测试里断言了两份响应文本相等）。
5. **响应统一带 `X-Compute-Ms`**，请求体超 32 KB 由中间件直接 413（不进路由）。

## 4. 测试

54 项：M1 的 28 项 + M2 契约 26 项（`tests/test_api.py::*m2*` 与新增的 4 项黄金值
`tests/test_golden.py::test_m2_*`）。

黄金值锚点（实测，写进测试防漂移）：

| 项 | 值 |
| --- | --- |
| CRI D65 / FL2（CIE 1995） | 100.00 / 64.23 |
| TM-30 Rf D65 / FL2 | 100.00 / 70.12（FL2 的 Rg 86.42） |
| CAM16（`#3B82F6`，D65，L_A=64/π/5，Y_b=20） | J 45.23 / C 63.83 / h 266.30 |
| CAM16 往返 | 4.4e-16；ZCAM 2.1e-14；Kim 2009 6.0e-6（库内近似） |
| CSF 峰值频率（10–1000 cd·m⁻²） | 3.63 cpd |
| sRGB / P3 / BT.2020 色域面积（xy 平面） | 0.1120 / 0.1520 / 0.2119 |
| 体积比（20000 采样，seed=7） | P3 1.49× / BT.2020 2.23× / ACES2065-1 4.42× |
| Breneman 实验 1 的 u′v′ 偏差 | CIE 1994 0.0137，其余 0.076–0.086 |

## 5. 仍然缺的

- **面板 08 传递函数**（`POST /api/v1/transfer`，`EOTFS`/`OETFS`/`LOG_ENCODINGS`/`RGB_to_YCbCr`）：
  方案里属 M2，本轮按「面板 09–18 + 10 模块」实现，未含。补齐后 `meta.endpoints` 会从 20 变 21。
- 前端仍未接 API（`index.html` 的控件还是静态占位）。
- 用户明确说本轮不追性能：未做 p95 基准，`core/cache.py` 的 LRU 只为去重计算，不代表实测收益。
