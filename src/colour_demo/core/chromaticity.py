"""面板 09：色度图与色域（`GET /api/v1/chromaticity`、`GET /api/v1/chromaticity.svg`）。

这是全项目**唯一返回位图/矢量图的端点**，因为色度图的底色是连续光谱轨迹围成的区域，
没有“数据版”可替代（方案 D7：只有必须渲染的图才用 matplotlib）。

三条工程约定：
1. 画幅与 dpi 固定（`FIGURE`），不接受用户任意尺寸——这是资源控制，不是样式偏好；
2. **不用 `bbox_inches="tight"`**：artist 多的图（色度图、黑体轨迹）会吃满内存被 SIGKILL，
   这是原型阶段实测过的坑；
3. matplotlib 的 SVG 里带 `<dc:date>`，字节每次不同，所以 `ETag` 由**规范化参数**算出，
   不依赖响应字节；同时把日期剥掉，让同样参数得到同样的字节（便于中间层缓存）。
"""

from __future__ import annotations

import hashlib
import io
import os
import re
import tempfile
from pathlib import Path

import numpy as np

import colour

from ..core.cache import lru
from ..core.errors import value_error
from ..core.parsing import parse_colours, rgb_to_hex

OBSERVER = "CIE 1931 2 Degree Standard Observer"
# 画幅与 dpi 固定（方案 6.1 限额）
FIGURE = {"size": (6.2, 5.2), "dpi": 100}

DIAGRAMS = {
    "CIE 1931": "plot_chromaticity_diagram_CIE1931",
    "CIE 1960 UCS": "plot_chromaticity_diagram_CIE1960UCS",
    "CIE 1976 UCS": "plot_chromaticity_diagram_CIE1976UCS",
}
DEFAULT_GAMUTS = ("sRGB", "Display P3", "ITU-R BT.2020")
GAMUT_STYLES = {
    "sRGB": ("#111111", "-"),
    "Display P3": ("#3B82F6", "--"),
    "ITU-R BT.2020": ("#E76F51", "--"),
}
MAX_GAMUTS = 4
MAX_POINTS = 12

_DATE_RE = re.compile(r"<dc:date>.*?</dc:date>", re.DOTALL)


def _backend():
    """延迟到第一次画图才导入 matplotlib，并把配置目录指到可写的临时目录。

    colour 只做计算时不需要 matplotlib；服务启动也不该为一张图付出导入代价。
    """

    os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "colour-demo-mpl"))
    import matplotlib

    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    return plt


def _validate_diagram(diagram: str) -> str:
    if diagram not in DIAGRAMS:
        raise value_error(f"未知色度图 {diagram!r}，可选：{list(DIAGRAMS)}")
    return diagram


def _validate_gamuts(gamuts: tuple[str, ...]) -> tuple[str, ...]:
    if len(gamuts) > MAX_GAMUTS:
        raise value_error(f"色域最多 {MAX_GAMUTS} 个，当前 {len(gamuts)} 个")
    for name in gamuts:
        if name not in colour.RGB_COLOURSPACES:
            raise value_error(f"未知色彩空间 {name!r}（示例：{sorted(colour.RGB_COLOURSPACES)[:6]}）")
    return gamuts


def _primaries(name: str) -> np.ndarray:
    return np.asarray(colour.RGB_COLOURSPACES[name].primaries, dtype=float)


def _gamut_area(name: str) -> float:
    (x1, y1), (x2, y2), (x3, y3) = _primaries(name)
    return abs((x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2)) / 2)


@lru(maxsize=32)
def render_svg(diagram: str, gamuts: tuple[str, ...], colours: tuple[str, ...]) -> str:
    """画图并返回 SVG 文本；(diagram, gamuts, colours) 相同则直接命中缓存。"""

    _validate_diagram(diagram)
    _validate_gamuts(gamuts)
    if len(colours) > MAX_POINTS:
        raise value_error(f"colors 最多 {MAX_POINTS} 个，当前 {len(colours)} 个")

    plt = _backend()
    plotter = getattr(colour.plotting, DIAGRAMS[diagram])

    figure, axes = plt.subplots(figsize=FIGURE["size"], dpi=FIGURE["dpi"])
    try:
        plotter(axes=axes, show=False)
        axes.set_title(diagram)
        axes.set_axis_off()

        for name in gamuts:
            primaries = _primaries(name)
            closed = np.vstack([primaries, primaries[0]])
            css, linestyle = GAMUT_STYLES.get(name, ("#6B7280", ":"))
            axes.plot(closed[:, 0], closed[:, 1], color=css, linewidth=1.1, linestyle=linestyle, zorder=8)
            axes.annotate(
                name,
                (float(primaries[:, 0].mean()), float(primaries[:, 1].mean())),
                fontsize=6,
                color=css,
                ha="center",
                va="center",
                zorder=9,
            )

        if colours:
            for index, (spec, rgb) in enumerate(zip(colours, parse_colours(list(colours))), start=1):
                xy = np.asarray(colour.XYZ_to_xy(colour.sRGB_to_XYZ(rgb)), dtype=float)
                axes.scatter([xy[0]], [xy[1]], s=42, c=[rgb_to_hex(rgb)], edgecolors="#1C1C1E", linewidths=0.7, zorder=20)
                axes.annotate(
                    str(index), (xy[0], xy[1]), xytext=(5.0, 3.0), textcoords="offset points", fontsize=6, zorder=21
                )

        buffer = io.StringIO()
        # 绝不用 bbox_inches="tight"：artist 一多就会被系统 SIGKILL（原型实测）
        figure.savefig(buffer, format="svg", facecolor="white")
        svg = buffer.getvalue()
    finally:
        plt.close(figure)

    # 剥掉生成时间：同样参数要得到同样字节，否则下游缓存永远不命中
    return _DATE_RE.sub("", svg)


def svg_etag(diagram: str, gamuts: tuple[str, ...], colours: tuple[str, ...]) -> str:
    """ETag 由规范化参数 + colour 版本算出（matplotlib 的 SVG 字节不稳定）。"""

    payload = "|".join([diagram, ",".join(gamuts), ",".join(colours), colour.__version__])
    return '"' + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32] + '"'


def chromaticity_data(diagram: str = "CIE 1931", gamuts: tuple[str, ...] | None = None, colours: tuple[str, ...] | None = None) -> dict:
    """色度图的“数据版”：色域三角形面积 + 样本点 xy + 是否落在各色域内。"""

    _validate_diagram(diagram)
    names = _validate_gamuts(tuple(gamuts or DEFAULT_GAMUTS))
    specs = list(colours or ())

    reference_area = _gamut_area("sRGB")
    gamut_rows = [
        {
            "name": name,
            "primaries": [[round(float(channel), 6) for channel in xy] for xy in _primaries(name)],
            "area_xy": round(_gamut_area(name), 6),
            "relative_to_sRGB": round(_gamut_area(name) / reference_area, 4) if reference_area else None,
        }
        for name in names
    ]

    samples = []
    for spec, rgb in zip(specs, parse_colours(specs)):
        xyz = np.asarray(colour.sRGB_to_XYZ(rgb), dtype=float)
        xy = np.asarray(colour.XYZ_to_xy(xyz), dtype=float)
        samples.append(
            {
                "input": spec,
                "hex": rgb_to_hex(rgb),
                "xy": [round(float(channel), 6) for channel in xy],
                "uv_1960": [round(float(channel), 6) for channel in colour.models.xy_to_UCS_uv(xy)],
                "uv_1976": [round(float(channel), 6) for channel in colour.models.xy_to_Luv_uv(xy)],
                "inside": {name: _inside(name, xyz) for name in names},
            }
        )

    return {
        "diagram": diagram,
        "diagrams": list(DIAGRAMS),
        "observer": OBSERVER,
        "gamuts": gamut_rows,
        "samples": samples,
        "warnings": [],
    }


def _inside(space: str, xyz: np.ndarray) -> bool:
    """落在色域内 = 该空间下的**编码值**全在 0–1。

    不能走 `colour.convert`：Display P3 / BT.2020 这些名字不是换算图里的节点
    （`NodeNotFound: display p3`），要直接用色彩空间自己声明的
    `matrix_XYZ_to_RGB` 与 `cctf_encoding`——这两个就是该空间的定义，不算重写算法。
    """

    colourspace = colour.RGB_COLOURSPACES.get(space)
    if colourspace is None:
        return False
    linear = np.asarray(colourspace.matrix_XYZ_to_RGB, dtype=float) @ np.asarray(xyz, dtype=float)
    encoded = np.asarray(colourspace.cctf_encoding(linear), dtype=float).ravel()
    return bool(np.all(encoded >= -1e-6) and np.all(encoded <= 1 + 1e-6))
