"""进程内 LRU 缓存（方案 7.1：共享能力放 core，图表/重算端点用）。

只缓存可哈希的入参，返回值必须是不可变或只读结构；命中率靠端点参数天然重复。
"""

from __future__ import annotations

import functools
from typing import Any, Callable, TypeVar

F = TypeVar("F", bound=Callable[..., Any])

# 非图表端点实测 1–8 ms，缓存主要服务图表端点与重复查询
DEFAULT_MAXSIZE = 256


def lru(maxsize: int = DEFAULT_MAXSIZE) -> Callable[[F], F]:
    """薄封装：统一缓存大小与语义，方便以后换成外部缓存。"""

    return functools.lru_cache(maxsize=maxsize)


def cache_info(func: F):
    """读取缓存命中情况；未包装过的函数返回 None。"""

    info = getattr(func, "cache_info", None)
    return info() if info else None


def cache_clear(func: F) -> None:
    clear = getattr(func, "cache_clear", None)
    if clear:
        clear()
