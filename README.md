# colour-demo

> 基于 [colour-science/colour](https://github.com/colour-science/colour) 的色彩科学演示项目。

**状态：早期规划（仓库骨架 + 设计说明，代码尚未实现）**

<p>
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-blue.svg"></a>
  <img alt="Python 3.11+" src="https://img.shields.io/badge/python-3.11%2B-3776AB.svg">
  <img alt="colour-science 0.4.7+" src="https://img.shields.io/badge/colour--science-0.4.7%2B-ff6f61.svg">
</p>

颜色不是三个字节，而是「物理量 + 观察条件 + 感知模型」。这个仓库想把这条链路用几条命令、几张图串起来：
`sRGB → 线性光 → CIE XYZ → Lab / Oklab → ΔE、色域与色觉模拟`。

---

## 这个仓库是什么

- 一个围绕 [`colour-science/colour`](https://github.com/colour-science/colour) 的学习型演示项目；
- 目标：把色彩科学里最常用的几件事，做成可直接运行、结果能看懂的小工具；
- 非目标：不做完整的色彩管理系统，也不替代 `colour` 本身——所有计算最终都交给它。

## 规划中的演示内容

| 能力 | 主要依赖的 `colour` API | 产出 |
| --- | --- | --- |
| 色彩空间转换 | `sRGB_to_XYZ`、`XYZ_to_Lab`、`XYZ_to_Luv`、`XYZ_to_Oklab` | 终端表格 + `--json` |
| CIE 1931 色度图 | `colour.plotting.plot_chromaticity_diagram_CIE1931` | PNG，叠加 sRGB / Display P3 / BT.2020 色域与样本点 |
| 感知差异 ΔE | `colour.delta_E`（CIE 2000 / 1976 / 1994 / CMC） | 成对 ΔE 矩阵热力图 |
| 渐变插值 | Oklab 空间线性插值 | sRGB / 线性 sRGB / Oklab 三段对比，标注步长均匀性 |
| 色觉障碍模拟 | `colour.blindness.matrix_cvd_Machado2009` | 红色盲 / 绿色盲 / 蓝色盲下的同一组调色板 |
| 一键报告 | 以上组合 | `out/report.md` + 全部配图 |

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

## 目录结构（规划）

```text
colour-demo/
├── src/colour_demo/
│   ├── cli.py          # argparse 子命令
│   ├── color.py        # 解析、转换、ΔE、插值、CVD 模拟
│   ├── plotting.py     # 四类图表的渲染
│   └── report.py       # Markdown 报告与配图
├── tests/              # pytest：已知色值、ΔE 参考对、往返转换
├── docs/images/        # README 与报告用图
├── .github/workflows/  # CI：ruff + pytest
├── LICENSE             # MIT
└── README.md
```

## 路线图

- [ ] `convert`：色彩空间转换表与 `--json`
- [ ] `gamut`：CIE 1931 色度图 + sRGB / P3 / BT.2020 色域叠加
- [ ] `delta-e`：ΔE 矩阵与热力图
- [ ] `gradient`：sRGB / 线性 / Oklab 插值对比
- [ ] `cvd`：Machado 2009 色觉障碍模拟
- [ ] `report`：一键生成图表与报告
- [ ] 测试与 CI（已知色值、Sharma ΔE 参考数据、往返转换）

## 参考资料

- [colour-science/colour](https://github.com/colour-science/colour) —— 本项目全部计算的来源
- [colour 文档](https://colour.readthedocs.io/) —— API 与色彩空间定义
- Björn Ottosson, *A perceptual color space for image processing*（Oklab，2020）
- Machado, Oliveira & Fernandes, *A Physiologically-based Model for Simulation of Color Vision Deficiency*（2009）
- [WCAG 2.2 对比度要求](https://www.w3.org/TR/WCAG22/#contrast-minimum)
- CIE 15:2004 *Colorimetry* —— XYZ、Lab、ΔE 的标准定义

## License

[MIT](LICENSE) © 2026 morehao
