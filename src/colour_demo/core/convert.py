"""面板 01：颜色转换与换算图（`POST /api/v1/convert`）。

面板语义：给若干输入色，返回它们在各目标空间下的坐标；顺带给出一条换算链路。
"""

from __future__ import annotations

import numpy as np

import colour
from colour.graph import conversion_path

from ..config import DEFAULT_OBSERVER
from ..core.errors import value_error
from ..core.parsing import parse_colours, rgb_to_hex

# 面板 01 的 14 个核心空间（与原型 docs/prototype/gen/panels_core.py 保持一致）
CORE_SPACES = [
    "CIE XYZ",
    "CIE xyY",
    "CIE Lab",
    "CIE Luv",
    "CIE LCHab",
    "CIE LCHuv",
    "CIE UVW",
    "CIE 1960 UCS",
    "CIE 1976 UCS",
    "Oklab",
    "Oklch",
    "CAM16 UCS",
    "HCL",
    "sRGB",
]

DEFAULT_SOURCE = "sRGB"


def _convert_safe(xyz, target: str):
    """把 XYZ（Domain1）转到目标空间；不支持的空间名映射成 422。"""

    try:
        # to_reference_scale=True：让 Lab/Luv 这类空间输出 0–100 的人类可读刻度，
        # 否则 colour 会给 0–1（Lab/100），与 /delta-e 返回的 Lab 口径不一致。
        return np.asarray(
            colour.convert(np.asarray(xyz), "CIE XYZ", target, to_reference_scale=True), dtype=float
        )
    except Exception as error:
        raise value_error(f"无法转换到空间 {target!r}：{error}") from error


def convert_colours(
    colours: list[str],
    target_spaces: list[str] | None = None,
    source: str = DEFAULT_SOURCE,
    target: str | None = None,
) -> dict:
    """核心换算：输入色 → XYZ → 各目标空间。

    `source` 非 sRGB 时先经 `colour.convert` 归一化到 sRGB，再算 XYZ（面板 01 的口径）。
    """

    rgb_list = parse_colours(colours)
    spaces = target_spaces or CORE_SPACES
    rows = []
    for spec, rgb in zip(colours, rgb_list):
        norm_rgb = rgb
        if source != DEFAULT_SOURCE:
            try:
                norm_rgb = np.asarray(
                    colour.convert(np.asarray(rgb), source, DEFAULT_SOURCE), dtype=float
                )
            except Exception as error:
                raise value_error(f"无法从空间 {source!r} 转换：{error}") from error
        xyz = np.asarray(colour.sRGB_to_XYZ(norm_rgb), dtype=float)
        values = {space: [round(float(channel), 6) for channel in _convert_safe(xyz, space)] for space in spaces}
        rows.append(
            {
                "input": spec,
                "hex": rgb_to_hex(norm_rgb),
                "rgb": [round(float(channel), 6) for channel in norm_rgb],
                "xyz": [round(float(channel), 6) for channel in xyz],
                "values": values,
            }
        )

    payload = {"source": source, "spaces": spaces, "rows": rows, "warnings": []}
    if target:
        # CONVERSION_GRAPH 的节点名是小写内部名（cie xyz / cie lab / srgb），
        # 不能直接喂展示名，否则 networkx 报 NodeNotFound。
        try:
            steps = conversion_path(source.strip().lower(), target.strip().lower())
        except Exception as error:
            raise value_error(f"没有 {source!r} → {target!r} 的换算链路：{error}") from error
        payload["conversion_path"] = [getattr(step, "__name__", str(step)) for step in steps]
        payload["conversion_hops"] = len(steps)
    return payload


def observer_arguments() -> dict:
    """面板 01 用到的固定口径，随响应返回便于复核。"""

    return {"observer": DEFAULT_OBSERVER}
