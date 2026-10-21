"""FastAPI 应用装配：版本断言、错误映射、静态原型挂载。

方案 6.3 / 11：500 不返回堆栈，只给 `trace_id`；校验错误统一 `detail.type = value_error`。
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

import colour
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from . import SUPPORTED_COLOUR_VERSION, __version__, assert_colour_version
from .api.routes import router
from .core.errors import ApiError
from .core.parsing import ColourParseError

logger = logging.getLogger("colour_demo")

# 校验报错里把字段名换成人话（方案 6.3：要能指出是哪个色值）
_FIELD_LABELS = {"colors": "颜色", "target_spaces": "目标空间", "method": "方法"}

PROTOTYPE_DIR = Path(__file__).resolve().parents[2] / "docs" / "prototype"


def _detail(kind: str, message: str, **extra) -> dict:
    return {"detail": {"type": kind, "message": message, **extra}}


def create_app() -> FastAPI:
    # 方案 7.2：版本不一致直接拒绝启动
    assert_colour_version()

    app = FastAPI(
        title="colour-demo",
        version=__version__,
        description=(
            "colour-science 0.4.7 的 Web 演示服务端。全部数值由 colour 真实计算，"
            f"锁定版本 {SUPPORTED_COLOUR_VERSION}。"
        ),
    )

    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=_detail(exc.type, exc.message))

    @app.exception_handler(ColourParseError)
    async def _parse_error(_: Request, exc: ColourParseError) -> JSONResponse:
        return JSONResponse(status_code=422, content=_detail("value_error", str(exc)))

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        errors = []
        for error in exc.errors():
            parts = [part for part in error.get("loc", ()) if part != "body"]
            location = ".".join(str(part) for part in parts)
            message = error.get("msg", "")
            label = _FIELD_LABELS.get(str(parts[0]), str(parts[0])) if parts else ""
            # 列表字段（colors）带下标时说清是第几个，方案 6.3 要求「指出第几个色值」
            if len(parts) >= 2 and isinstance(parts[1], int):
                message = f"第 {parts[1] + 1} 个{label}：{message.split('Value error, ')[-1]}"
            elif error.get("type") == "too_long":
                limit = (error.get("ctx") or {}).get("max_length")
                message = f"{parts[-1] if parts else '字段'} 最多 {limit} 个"
            elif error.get("type") == "too_short":
                limit = (error.get("ctx") or {}).get("min_length")
                message = f"{parts[-1] if parts else '字段'} 至少需要 {limit} 个"
            errors.append({"loc": location, "message": message})
        # 顶层 message 只拼人话，`loc` 留给 errors 数组供前端定位，避免出现「colors: colors 最多 12 个」
        message = "; ".join(item["message"] for item in errors) or "请求校验失败"
        return JSONResponse(status_code=422, content=_detail("value_error", message, errors=errors))

    @app.exception_handler(Exception)
    async def _unexpected(_: Request, exc: Exception) -> JSONResponse:
        trace_id = uuid.uuid4().hex[:12]
        logger.exception("unexpected error trace_id=%s", trace_id)
        return JSONResponse(status_code=500, content=_detail("internal_error", "服务内部错误", trace_id=trace_id))

    app.include_router(router)

    @app.get("/health")
    def root_health() -> dict:
        return {"status": "ok", "colour_version": colour.__version__}

    if PROTOTYPE_DIR.is_dir():
        # 原型单页直接由服务端托管，方便一条命令演示（方案 G3：零前端构建）
        app.mount("/demo", StaticFiles(directory=str(PROTOTYPE_DIR), html=True), name="demo")

    return app


app = create_app()
