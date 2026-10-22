# 面板 19（光谱重建）改写记录：chart 块验证 + 两个 colour 口径坑

日期：2026-10-21 ｜ 分支 `feat/web-demo` ｜ 相关文件：`docs/prototype/gen/panels_engineering.py`、`docs/prototype/index.template.html`、`docs/prototype/build_prototype.py`

## 1. 结论速览

| 项 | 结果 |
| --- | --- |
| 单面板峰值 | **126 MB**（SOP 阈值 < 300 MB，通过）；耗时 0.99 s；面板 JSON 6.9 KB |
| matplotlib | 面板 19 已完全移除，改用 `chart` 块（前端 SVG），D7 决策首次落地 |
| chart 渲染器宽度自适应 | **已验证**：`viewBox="0 0 880 H"` + `width:100%`，1400/1080/900 px 均正常，无裁切 |
| 数据真伪 | 4 条曲线 + 4 行 ΔE 全部来自 colour 0.4.7 实算；Mallett/Jakob/Meng 的 ΔE 精确 0.00，Smits 1999 为 1.25（方法局限，已写进页面 note） |

## 2. 坑一：重建函数要**线性** RGB，不是 gamma 编码值

原实现把 `hex_to_rgb("#3B82F6")`（编码 sRGB，0–255/255）直接喂给
`RGB_to_sd_Smits1999` / `RGB_to_sd_Mallett2019`。colour 文档示例是 `XYZ_to_sRGB(XYZ, apply_cctf_encoding=False)`，
即这两个方法要线性光 RGB。传编码值的后果：ΔE ≈ 16.9 且肉眼可见「变淡变亮」。

修法：

```python
encoded = hex_to_rgb(DEMO)
linear = colour.cctf_decoding(encoded)     # ← 关键
colour.recovery.RGB_to_sd_Smits1999(linear)
colour.recovery.RGB_to_sd_Mallett2019(linear)
```

对照实测（#3B82F6）：

| 方法 | 编码 RGB | 线性 RGB |
| --- | --- | --- |
| Smits 1999 | ΔE 16.88 | ΔE **1.25** |
| Mallett 2019 | ΔE 16.85 | ΔE **0.00** |

## 3. 坑二：`sd_to_XYZ` 是 0–100 量纲，且要按「反射率 × D65」积分

`colour.sd_to_XYZ(sd)` 默认按自发光 SPD 积分，返回 **0–100**；直接把结果喂 `XYZ_to_sRGB`
（要 0–1 域）会全部被裁成 `#FFFFFF`、ΔE 只有 41.24 一个值——这正是原表格四行完全相同的根因。

正确口径：把重建 SD 当作**反射率**，在 CIE 1931 2° 观察者 + D65 光源下积分，再 /100：

```python
xyz_back = colour.sd_to_XYZ(samples, illuminant=colour.SDS_ILLUMINANTS["D65"]) / 100
rgb_back = np.clip(colour.XYZ_to_sRGB(xyz_back), 0, 1)
```

验证：Jakob 2019 / Meng 2015 在该口径下往返 ΔE = 0.00（说明口径正确，若口径错不可能是 0）。

另：Smits 1999 的采样是 380–720 非等间隔（10 点），ASTM E308 只接受 1/5/10/20 nm，
不先重采样到 5 nm 会抛 `ValueError`。原代码的重采样分支保留。

## 4. 渲染器修的两处缺陷

1. **legend 压曲线**：原来 legend 画在 `y=12`，落在绘图区内被曲线覆盖（截图可见「Smits 1999」被压穿）。
   改为按有无 series 预留顶部 20 px 带（`pad.t = 12 + legendBand`）。
2. **窄屏字号过小**：viewBox 等比缩放会把 9px 字号一起缩小。改为 `.chart-wrap{overflow-x:auto;min-width:0}`
   + `.chart{min-width:620px}`，窄屏在容器内横滚而不缩字。`min-width:0` 是必须的，否则 svg 的最小宽度
   会撑开单列网格、裁掉整页。
3. 顺带补上 `ylabel` 渲染（原渲染器只画了 `xlabel`，`chart(ylabel=...)` 是静默失效）。

## 5. 构建器断链修复

`--merge` 原先只拼 `b1.json` + `b2.json` + `meta.json`，**从不读 `b3.json`**：
即使 `--batch 3` 跑通，19–25 的数据也进不了页面。已改为 `b3.json` 存在即并入，缺失面板继续走占位。

## 6. 环境风险（未变）

`vm.swapusage = 0`。面板 19 单跑仅 126 MB 是安全的，但 `--batch 3` 七个面板连跑仍可能在满载时触发系统级内存回收
（此前两次事故见 `2026-10-21-build-memory-notes.md`）。建议跑 batch 3 前先腾内存或开 swap。

## 7. 已知但未处理

- ≤600 px 视口下整页右侧被裁：**模板既有问题**（未含 chart 的 baseline 页同样被裁），与本次改动无关，
  本次不修（超出「不重写方案结构」的边界）。
- `chart` 的 Y 轴刻度固定 3 位小数（如 0.198/0.395），量纲跨度大的面板（如光学面板）可能需要按量级格式化，届时再改。
- `note` 块不解析 markdown：面板文案里不要写 `**加粗**`，否则星号会原样显示。
