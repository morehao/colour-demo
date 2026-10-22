# M3 服务端笔记（面板 19–25，2026-10-22）

7 个模块 7 条路由落地，端点总数 21 → **28**，测试 58 → **70** 全绿。
前端同时补了 7 个适配器，实时面板 15 → **22**（只剩 00/03/04/07 与 26–28 静态）。

## 1. 最重要的发现：sRGB 传输函数方向写反了（影响面板 18 与 19）

`colour.models.eotf_sRGB` 是**码值 → 线性光**（decoding），
`colour.models.eotf_inverse_sRGB` 是**线性 → 码值**（encoding）。

M2 的 `core/cvd.py` 和初版 `core/recovery.py` 都写成了 `linear = eotf_inverse_sRGB(rgb)`，
即“又编码了一次”。这不会抛异常，只会：

- 面板 19：Smits 1999 重建回算 ΔE **26**（正确应 ~1.1），Mallett 2019 ΔE 25.9（应为 0.003）；
- 面板 18：CVD 模拟把整块颜色系统性压暗，平均 ΔE 从 18.8 掉到 17.3。

修法：线性化用 `eotf_sRGB`，编码回用 `eotf_inverse_sRGB`。
钉住它的测试是 `test_cvd_grey_is_invariant`——CVD 矩阵保持消色差轴，灰 `#808080` 模拟后必须仍是 `#808080`；
方向写反会把灰压暗，一条断言就能抓住。

> 教训：colour 里成对的 `x` / `x_inverse` 一定要先用一个已知值验证方向
> （`eotf_sRGB(0.2314) = 0.0437` 才是线性光），别按名字猜。

## 2. 各面板的口径要点

| 面板 | 关键口径 |
| --- | --- |
| 19 光谱重建 | Smits/Mallett 收**线性 RGB**（先 `eotf_sRGB`），Jakob/Meng/Otsu 收 **XYZ 0–1**；重建结果是**反射率**，要 `sd_to_XYZ(sd, illuminant=D65)/100` 再转 sRGB；Smits 的 37.8 nm 非等间隔必须重采样到 5 nm 才能过 ASTME308 |
| 20 色彩校正 | `colour_correction(RGB, M_T 实测, M_R 真值)`，两边都传真值会退化成恒等变换；Finlayson 2015 默认 `degree=1` 与 Cheung 2004 数学等价，要 `degree=3` 才有差异 |
| 21 记号与解析 | Munsell 回程会把 `5R 5/12` 写成 `5.0R 5.0/12.0`，往返要**按数值比**不能按字符串比；`munsell_value` 的 Y 是 0–100 域 |
| 22 插值 | 演示光源必须选 FL11（含汞灯 435.8/546.1/611.6 nm 尖线）；D65 的 5 nm 表在 10 nm 间本来线性，看不出差别。LUT 对比必须用非线性合成表，恒等表上三线性/四面体必然相同 |
| 23 几何 | `ellipse_fitting` 返回 complex128（虚部恒 0），要 `.real`；拟合的半轴会互换、θ 差 ~90°，这是标准形约定不是误差；原始数据只有 4 位有效数字，断言要用绝对误差 |
| 24 光学 | `thin_film_tmm` 返回 (波长 × 偏振)，取第 0 列才是非偏振；R+T≈1 可作健全性检查；`reaction_rate_MichaelisMenten(method="Abebe 2017")` 必须传 `b_m`，不传 TypeError（原型那条曲线因此从未画出） |
| 25 画册 | 仍是全站唯一 matplotlib 端点：固定画幅/dpi、禁用 `bbox_inches="tight"`、每张图渲染后立即 close；`plot_blackbody_spectral_radiance` 不定坐标范围且返回空 figure，要自己按曲线数据定轴。响应给 PNG base64（比内联 SVG 小一个量级），3 张约 70 KB |

## 3. 实测锚点（写进测试）

| 项 | 值 |
| --- | --- |
| Smits 1999 / Mallett 2019 / Jakob 2019 / Meng 2015 的重建 ΔE | 1.147 / 0.003 / 0.005 / 0.001 |
| 24 色卡：校正前 → 最优 | 平均 ΔE 18.54 → 1.64（Finlayson 2015 · 3 阶）；Cheung 2004 2.51、Vandermonde 2.33 |
| Munsell `5R 5/12` | xyY (0.5071, 0.3194, Y 0.1927)，回程 `5.0R 5.0/12.0`（数值一致） |
| FL11 20 nm → 5 nm 重建 | Sprague 负值点 2、Cubic Spline 5、Linear/PCHIP 0 |
| MacAdam 第 11 组拟合 | 中心一致到 1e-6，半轴互换，θ 104.0° ↔ 14.06° |
| 薄膜 R+T（200/350/500 nm） | 均为 1.000 |
| 瑞利散射 vs 1/λ⁴ | 实测高 2.08–5.44% |
| 3 张画册 PNG | 8.6 KB / 12.6 KB / 48.8 KB（dpi 110） |

## 4. 仍未做

- M4：面板 26–28（能力目录 `/catalog`、参数化调用 `/catalog/invoke`、OpenAPI 控制台）；
  端点数 28 → 29–31 由 M4 决定。
- 前端 03（观察者）/ 04（光度）/ 07（空间图鉴）的适配器：端点都已存在，约 15 行/个。
