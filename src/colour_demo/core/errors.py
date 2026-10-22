"""统一错误模型。

方案 6.3：`detail` 带 `type`，前端据此决定提示文案。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ApiError(Exception):
    """业务错误，映射到 `{"detail": {"type": ..., "message": ...}}`。"""

    type: str
    message: str
    status_code: int = 422


def value_error(message: str) -> ApiError:
    return ApiError(type="value_error", message=message)


def not_found(message: str) -> ApiError:
    return ApiError(type="not_found", message=message, status_code=404)


def too_large(message: str) -> ApiError:
    return ApiError(type="too_large", message=message, status_code=413)


def forbidden(message: str) -> ApiError:
    return ApiError(type="forbidden", message=message, status_code=403)
