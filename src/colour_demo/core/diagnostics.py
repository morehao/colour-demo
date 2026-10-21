"""共享诊断工具：把 colour 自己发出的告警收成响应里的 `warnings` 数组（方案 6.2）。

colour 的 `ColourUsageWarning` 不是噪声，而是**结论的一部分**：近似模型、非双射方法、
“某个参数没给、我替你猜了一个”都会从这里出来。面板 18 的口径就是“UI 原样展示”，
所以服务端必须把它们带回去，而不是只丢进日志。

用法（注意：`payload` 要在 `with` 块**结束之后**读，告警是在退出时才归一化）：

    with WarningCollector() as log:
        value = colour.some_noisy_call(...)
    return {"value": value, "warnings": log.payload}
"""

from __future__ import annotations

import warnings
from typing import Any

import numpy as np

# 一条响应最多回传多少条告警（同类去重后）；再多对 UI 没意义
MAX_WARNINGS = 8


class WarningCollector:
    """收集 `colour` 的告警，去重、截断，输出 `[{"type", "message"}]`。"""

    def __init__(self, limit: int = MAX_WARNINGS) -> None:
        self._limit = limit
        self._items: list[dict] = []
        self._seen: set[str] = set()
        self._manager: Any = None
        self._caught: list | None = None

    def __enter__(self) -> "WarningCollector":
        self._manager = warnings.catch_warnings(record=True)
        self._caught = self._manager.__enter__()
        # 总是记录：colour 用 default 过滤时，同一条只报一次，跨请求就丢了
        warnings.simplefilter("always")
        return self

    def __exit__(self, *exc_info: object) -> None:
        self._manager.__exit__(*exc_info)
        for item in self._caught or []:
            self.add(item.category.__name__, str(item.message))

    def add(self, kind: str, message: str) -> None:
        """手工追加一条（用于服务端自己发现的口径说明）。"""

        text = " ".join(str(message).split())
        if not text or text in self._seen or len(self._items) >= self._limit:
            return
        self._seen.add(text)
        self._items.append({"type": kind, "message": text})

    @property
    def payload(self) -> list[dict]:
        return list(self._items)

    def __bool__(self) -> bool:
        return bool(self._items)


def number(value: Any, ndigits: int = 6) -> float | None:
    """`None` / `nan` / `inf` / numpy 标量 → JSON 安全的浮点数或 `None`。

    外观模型（ATD95 没有 J、Nayatani 95 没有 H）会返回 `None` 属性，
    直接 `float()` 会抛 TypeError，所以统一走这里。
    """

    if value is None:
        return None
    try:
        array = np.asarray(value, dtype=float).ravel()
    except (TypeError, ValueError):
        return None
    if array.size == 0:
        return None
    scalar = float(array[0])
    return round(scalar, ndigits) if np.isfinite(scalar) else None


def numbers(values: Any, ndigits: int = 6) -> list[float | None]:
    """向量版本：逐元素 `number()`，保持长度。"""

    return [number(value, ndigits) for value in np.asarray(values, dtype=float).ravel()]
