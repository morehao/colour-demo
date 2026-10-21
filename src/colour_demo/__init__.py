"""colour-demo 服务端包。

单一 FastAPI 进程，全部色彩计算委托给锁定版本的 colour-science；
本包只做「校验 → 调 colour → 序列化」，不实现任何色彩算法。
"""

from __future__ import annotations

__version__ = "0.1.0"

# 方案 7.2：版本断言，0.4.7 与 develop 分支 API 有差异，必须锁死
SUPPORTED_COLOUR_VERSION = "0.4.7"


class ColourVersionError(RuntimeError):
    """colour-science 版本与锁定版本不一致。"""


def assert_colour_version() -> str:
    """启动时校验 colour 版本，不一致直接拒绝启动（方案 7.2 / 12 版本漂移门禁）。"""

    import colour

    if colour.__version__ != SUPPORTED_COLOUR_VERSION:
        raise ColourVersionError(
            f"需要 colour-science {SUPPORTED_COLOUR_VERSION}，当前 {colour.__version__}。"
            " 数值口径依赖锁定版本，请勿在未验证黄金值的情况下升级。"
        )
    return colour.__version__
