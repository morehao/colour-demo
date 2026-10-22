"""原型数据构建的公共工具：颜色解析、块构造、图表数据、图像编码。

设计意图：原型与最终实现共用同一套"面板 = 元数据 + 数据块"的结构，
渲染层只认识块类型（kv / matrix / chart / image / table / ...），
新增能力时只需要在 panels_*.py 里加一段数据，不用改 HTML。
"""

from __future__ import annotations

import base64
import io
import os
from pathlib import Path

import numpy as np

os.environ.setdefault(
    "MPLCONFIGDIR", str(Path(__file__).resolve().parents[3] / ".tmp" / "mpl")
)
os.makedirs(os.environ["MPLCONFIGDIR"], exist_ok=True)

import matplotlib  # noqa: E402

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402

# 图上标注含中文：按平台优先级挑一个可用的 CJK 字体（Docker 里换成 fonts-noto-cjk）
matplotlib.rcParams["font.sans-serif"] = [
    "PingFang SC", "Hiragino Sans GB", "Heiti SC", "Songti SC",
    "Noto Sans CJK SC", "Source Han Sans SC", "Arial Unicode MS", "DejaVu Sans",
]
matplotlib.rcParams["axes.unicode_minus"] = False


# --------------------------------------------------------------------------- #
# 颜色与数值
# --------------------------------------------------------------------------- #
def hex_to_rgb(value: str) -> list[float]:
    value = value.strip().lstrip("#")
    if len(value) == 3:
        value = "".join(c * 2 for c in value)
    return [int(value[i : i + 2], 16) / 255 for i in (0, 2, 4)]


def rgb_to_hex(rgb) -> str:
    channels = [int(round(max(0.0, min(1.0, float(c))) * 255)) for c in np.asarray(rgb)[:3]]
    return "#" + "".join(f"{c:02X}" for c in channels)


def fnum(value, digits: int = 4) -> str:
    return f"{float(value):.{digits}f}"


def vec(values, digits: int = 4) -> str:
    return " ".join(f"{float(v):.{digits}f}" for v in np.asarray(values).ravel())


def lab(hex_value: str) -> np.ndarray:
    import colour

    return colour.XYZ_to_Lab(colour.sRGB_to_XYZ(hex_to_rgb(hex_value)))


def delta_e(a: str, b: str, method: str = "CIE 2000") -> float:
    import colour

    return float(colour.delta_E(lab(a), lab(b), method=method))


def adjacent_delta_e(hexes: list[str], method: str = "CIE 2000") -> list[float]:
    return [delta_e(hexes[i], hexes[i + 1], method) for i in range(len(hexes) - 1)]


# --------------------------------------------------------------------------- #
# 数据块
# --------------------------------------------------------------------------- #
def kv(rows, title: str | None = None) -> dict:
    """rows: [(标签, 数值, 口径/说明)]"""
    return {"type": "kv", "title": title, "rows": [list(r) for r in rows]}


def stats(items, title: str | None = None) -> dict:
    """items: [(数值, 标签, 说明)]"""
    return {"type": "stats", "title": title, "items": [list(i) for i in items]}


def matrix(colors: list[str], values, title: str | None = None, caption: str = "") -> dict:
    return {
        "type": "matrix",
        "title": title,
        "colors": [c.upper() for c in colors],
        "values": [[round(float(v), 2) for v in row] for row in values],
        "caption": caption,
    }


def swatches(items, title: str | None = None, cols: int = 8) -> dict:
    """items: [(hex, 标签, 副标题)]"""
    return {
        "type": "swatches",
        "title": title,
        "cols": cols,
        "items": [{"hex": h.upper(), "label": str(a), "sub": str(b)} for h, a, b in items],
    }


def strip(label: str, note: str, colors: list[str], stats_pairs=None, curve=None) -> dict:
    return {
        "label": label,
        "note": note,
        "colors": [c.upper() for c in colors],
        "stats": [[str(k), str(v)] for k, v in (stats_pairs or [])],
        "curve": curve,
    }


def strips(items, title: str | None = None, caption: str = "") -> dict:
    return {"type": "strips", "title": title, "items": items, "caption": caption}


def table(head: list[str], rows, title: str | None = None, mono=None, widths=None, note: str = "") -> dict:
    return {
        "type": "table",
        "title": title,
        "head": head,
        "rows": [[str(c) for c in row] for row in rows],
        "mono": mono or [],
        "widths": widths,
        "note": note,
    }


def chart(series_list, xlabel: str = "", ylabel: str = "", title: str | None = None,
          caption: str = "", height: int = 240, markers=None, zero: bool = False) -> dict:
    return {
        "type": "chart",
        "title": title,
        "xlabel": xlabel,
        "ylabel": ylabel,
        "caption": caption,
        "height": height,
        "markers": markers or [],
        "zero": zero,
        "series": series_list,
    }


def series(name: str, xs, ys, color: str | None = None, dashed: bool = False,
           mode: str = "line") -> dict:
    return {
        "name": name,
        "color": color,
        "dashed": dashed,
        "mode": mode,
        "points": [[round(float(x), 5), round(float(y), 6)] for x, y in zip(xs, ys)],
    }


def image(fig, caption: str = "", alt: str = "", dpi: int = 110, maxw: str = "520px",
          tight: bool = True) -> dict:
    """tight=False 用于 artist 极多的图（如黑体辐射、色度图）：
    bbox_inches='tight' 会遍历每个 artist 计算边界，在本机（swap=0）会直接触发 jetsam 击杀进程。"""
    return {
        "type": "image",
        "src": fig_to_data_uri(fig, dpi=dpi, tight=tight),
        "caption": caption,
        "alt": alt or caption,
        "maxw": maxw,
    }


def note(text: str, tone: str = "info", title: str | None = None) -> dict:
    return {"type": "note", "tone": tone, "title": title, "text": text}


def json_block(code: str, title: str | None = None) -> dict:
    return {"type": "json", "title": title, "code": code}


def cards(items, title: str | None = None) -> dict:
    """items: [(标题, 说明, 脚注)]"""
    return {
        "type": "cards",
        "title": title,
        "items": [{"title": t, "text": d, "foot": f} for t, d, f in items],
    }


def chain(nodes) -> dict:
    """nodes: [(名称, 颜色, 说明)]"""
    return {"type": "chain", "nodes": [list(n) for n in nodes]}


# --------------------------------------------------------------------------- #
# 图像编码
# --------------------------------------------------------------------------- #
def fig_to_data_uri(fig, dpi: int = 110, tight: bool = True) -> str:
    buffer = io.BytesIO()
    if tight:
        fig.savefig(
            buffer,
            format="png",
            dpi=dpi,
            bbox_inches="tight",
            pad_inches=0.04,
            transparent=True,
        )
    else:
        fig.savefig(buffer, format="png", dpi=dpi, transparent=True)
    plt.close(fig)
    return "data:image/png;base64," + base64.b64encode(_shrink(buffer.getvalue())).decode("ascii")


def _shrink(png_bytes: bytes) -> bytes:
    """调色板量化，把内联图片压到原来的 1/3 左右（图表仍是矢量数据，这里只是位图容器）。"""
    from PIL import Image

    image_obj = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    quantized = image_obj.quantize(colors=256, method=Image.FASTOCTREE, dither=Image.NONE)
    out = io.BytesIO()
    quantized.save(out, format="PNG", optimize=True)
    return out.getvalue()


def new_axes(figsize=(4.0, 2.6), dpi: int = 110):
    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
    fig.patch.set_alpha(0)
    ax.set_facecolor("none")
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.tick_params(labelsize=6, colors="#555A63", length=2)
    return fig, ax


# --------------------------------------------------------------------------- #
# 面板装配
# --------------------------------------------------------------------------- #
def panel(pid: str, group: str, no: str, title: str, lead: str, blocks,
          phase: str = "M1", apis=None, controls=None, footer: str = "",
          title_plain: str = "", question: str = "", plain: str = "",
          why: str = "", presets=None, verdict: str | None = None,
          jargon=None) -> dict:
    """装配一个面板。

    前 6 个位置参数是专业视图（专家模式）；后面是新手工字段，缺省时构建期只警告，
    `--strict` 时失败。新手视图只读这些字段，不复制事实文本。
    """
    return {
        "id": pid,
        "group": group,
        "no": no,
        "title": title,
        "lead": lead,
        "phase": phase,
        "apis": apis or [],
        "controls": controls or [],
        "blocks": blocks,
        "footer": footer,
        # 新手层（可选，构建期 lint）
        "title_plain": title_plain,
        "question": question,
        "plain": plain,
        "why": why,
        "presets": presets or [],
        "verdict": verdict,
        "jargon": jargon or [],
    }
