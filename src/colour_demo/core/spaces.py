"""面板 07：RGB 色彩空间图鉴（`GET /api/v1/spaces`）。

列出 `colour.RGB_COLOURSPACES` 的基色、白点、传递函数与色域体积口径。
"""

from __future__ import annotations

import numpy as np

import colour


def _primaries(space) -> list[list[float]] | None:
    try:
        return [[round(float(channel), 6) for channel in xy] for xy in np.asarray(space.primaries, dtype=float)]
    except Exception:
        return None


def _whitepoint(space) -> list[float] | None:
    try:
        return [round(float(channel), 6) for channel in np.asarray(space.whitepoint, dtype=float)]
    except Exception:
        return None


def spaces_index(limit: int | None = None) -> dict:
    names = sorted(colour.RGB_COLOURSPACES.keys())
    selected = names[:limit] if limit else names
    rows = []
    for name in selected:
        space = colour.RGB_COLOURSPACES[name]
        rows.append(
            {
                "name": name,
                "primaries": _primaries(space),
                "whitepoint": _whitepoint(space),
                "cctf": getattr(space, "cctf", None) or getattr(space, "encoding_cctf", None) or "—",
                "linear": bool(getattr(space, "linear", False)),
                "labels": sorted(getattr(space, "labels", ()) or ()),
            }
        )
    return {
        "total": len(names),
        "count": len(rows),
        "spaces": rows,
        "warnings": [],
    }
