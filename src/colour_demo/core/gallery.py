"""面板 25：图表画廊（`POST /api/v1/plot`）。

`colour.plotting` 是全库唯一**必须**用 matplotlib 的地方（方案 D7 例外）：这些函数自带色度背景、
图例与坐标轴样式，改写成数据块等于重做一套渲染器。

服务端渲染的三个硬约束（原型阶段全部踩过）：

1. **绝不用 `bbox_inches="tight"`**：这些图的 artist 成百上千（色度图、黑体轨迹），
   tight bbox 会把进程推到内存回收边缘，实测 exit 137；
2. `plot_blackbody_spectral_radiance` 往传入 axes 画却不设坐标范围，还返回一个空白 figure——
   必须自己按曲线数据定轴，并丢掉落内部新建的画布；
3. 每张图编码完立刻 `plt.close(fig)`，不要同时驻留多张。

画幅/dpi 固定，响应给 PNG 的 base64（比内联 SVG 小一个量级，也更适合“画廊”这种用法）。
"""

from __future__ import annotations

import base64
import gc
import io
import os
import tempfile
import warnings

import numpy as np

import colour

from ..core.cache import lru
from ..core.errors import value_error

# 画幅与 dpi 固定（方案 6.1 限额）
FIGURE = {"size": (4.0, 2.6), "dpi": 110}
MAX_PLOTS = 4


def _backend():
    os.environ.setdefault("MPLCONFIGDIR", str(__import__("pathlib").Path(tempfile.gettempdir()) / "colour-demo-mpl"))
    import matplotlib

    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    return plt


def _paint_visible_spectrum(axes) -> None:
    colour.plotting.plot_visible_spectrum(axes=axes, show=False)


def _paint_blackbody(axes, temperature: float) -> None:
    """该函数画进传入 axes 却不定坐标范围，返回的 figure 是空模板。"""

    before = axes.get_xlim()
    colour.plotting.plot_blackbody_spectral_radiance(temperature, axes=axes, show=False)
    if axes.get_xlim() == before and axes.get_lines():
        xs = np.concatenate([np.asarray(line.get_xdata(), dtype=float) for line in axes.get_lines()])
        ys = np.concatenate([np.asarray(line.get_ydata(), dtype=float) for line in axes.get_lines()])
        axes.set_xlim(float(xs.min()), float(xs.max()))
        axes.set_ylim(0.0, float(ys.max()) * 1.05)


def _paint_macadam(axes) -> None:
    # 内部画椭圆时会抛 numpy ComplexWarning（虚部恒 0），属库内噪声
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", np.exceptions.ComplexWarning)
        colour.plotting.plot_ellipses_MacAdam1942_in_chromaticity_diagram_CIE1931(axes=axes, show=False)


def _paint_chromaticity(axes) -> None:
    colour.plotting.plot_chromaticity_diagram_CIE1931(axes=axes, show=False)


PLOTS = {
    "visible-spectrum": {
        "label": "可见光谱色带",
        "caption": "plot_visible_spectrum：把 380–780 nm 渲染成连续色带，是「波长 → 颜色」最直观的一次演示。",
        "paint": _paint_visible_spectrum,
        "size": (4.0, 1.6),
    },
    "blackbody": {
        "label": "黑体辐射",
        "caption": "plot_blackbody_spectral_radiance：黑体的光谱辐亮度，峰值随温度按维恩位移定律移动。",
        "paint": lambda axes: _paint_blackbody(axes, 5000),
        "size": (4.0, 2.4),
    },
    "macadam-ellipses": {
        "label": "MacAdam 椭圆",
        "caption": "plot_ellipses_MacAdam1942_in_chromaticity_diagram_CIE1931：25 组感知等距椭圆画在色度图上（数据见面板 23）。",
        "paint": _paint_macadam,
        "size": (4.0, 3.0),
    },
    "chromaticity": {
        "label": "CIE 1931 色度图",
        "caption": "plot_chromaticity_diagram_CIE1931：带光谱轨迹与色域底色的标准色度图。",
        "paint": _paint_chromaticity,
        "size": (4.0, 3.0),
    },
}
DEFAULT_PLOTS = ("visible-spectrum", "blackbody", "macadam-ellipses")


def _render_png(name: str) -> str:
    """渲染一张图，返回 PNG 的 base64（不含 data URL 前缀）。"""

    spec = PLOTS[name]
    plt = _backend()
    figure, axes = plt.subplots(figsize=spec["size"], dpi=FIGURE["dpi"])
    try:
        spec["paint"](axes)
        axes.set_title("")
        # 固定边距代替 bbox_inches="tight"（artist 太多，tight bbox 会撑爆内存）
        figure.subplots_adjust(left=0.16, right=0.97, top=0.92, bottom=0.2)
        buffer = io.BytesIO()
        figure.savefig(buffer, format="png", facecolor="white")
        return base64.b64encode(buffer.getvalue()).decode("ascii")
    finally:
        plt.close(figure)
        gc.collect()


@lru(maxsize=16)
def render_plot(name: str) -> str:
    return _render_png(name)


def _groups() -> list[dict]:
    groups = []
    for prefix, label in (
        ("plot_RGB_", "RGB 色域与截面"),
        ("plot_chromaticity", "色度图"),
        ("plot_sds_", "光谱在色度图上"),
        ("plot_single_", "单对象作图"),
        ("plot_multi_", "多对象对比"),
        ("plot_thin_film", "薄膜光学"),
        ("plot_ellipses", "MacAdam 椭圆"),
    ):
        names = [name for name in colour.plotting.__all__ if name.startswith(prefix)]
        if names:
            groups.append(
                {
                    "group": label,
                    "count": len(names),
                    "examples": names[:4],
                    "more": max(0, len(names) - 4),
                }
            )
    return groups


def gallery_data(names: list[str] | None = None) -> dict:
    requested = list(names or DEFAULT_PLOTS)
    if len(requested) > MAX_PLOTS:
        raise value_error(f"一次最多渲染 {MAX_PLOTS} 张图，当前 {len(requested)} 张")
    unknown = [name for name in requested if name not in PLOTS]
    if unknown:
        raise value_error(f"未知图 {unknown}，可选：{list(PLOTS)}")

    plots = []
    for name in requested:
        spec = PLOTS[name]
        try:
            plots.append(
                {
                    "name": name,
                    "label": spec["label"],
                    "caption": spec["caption"],
                    "media_type": "image/png",
                    "width": int(spec["size"][0] * FIGURE["dpi"]),
                    "height": int(spec["size"][1] * FIGURE["dpi"]),
                    "png_base64": render_plot(name),
                }
            )
        except Exception as error:
            plots.append({"name": name, "label": spec["label"], "error": f"{type(error).__name__}: {error}"})

    total = len([name for name in colour.plotting.__all__ if name.startswith("plot_")])
    return {
        "plots": plots,
        "available": [{"name": key, "label": value["label"]} for key, value in PLOTS.items()],
        "dpi": FIGURE["dpi"],
        "groups": _groups(),
        "counts": {"plot_functions": total, "exported": len(colour.plotting.__all__)},
        "warnings": [
            {
                "type": "note",
                "message": "全站只有这一页用服务端 matplotlib：其余面板走前端 SVG chart 块；"
                "这里固定画幅/dpi、禁用 tight bbox、每张图渲染后立即释放。",
            }
        ],
    }
