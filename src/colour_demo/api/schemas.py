"""请求模型：校验一律在服务层之外完成（方案 6.3：不合法输入不进入 colour）。

颜色字面量在 pydantic 阶段就预解析一次，坏色值不会进入计算层。
"""

from __future__ import annotations

from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from ..config import DEFAULT_ILLUMINANT, DEFAULT_METHOD, MAX_COLOURS, MAX_STEPS
from ..core.parsing import ColourParseError, parse_colour


def _validate_colour(value: str) -> str:
    try:
        parse_colour(value)
    except ColourParseError as error:
        raise ValueError(str(error)) from error
    return value


ColourStr = Annotated[str, Field(min_length=1, max_length=64), AfterValidator(_validate_colour)]
ColourList = Annotated[list[ColourStr], Field(min_length=1, max_length=MAX_COLOURS)]


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ConvertRequest(_Base):
    colors: ColourList
    target_spaces: list[str] | None = Field(default=None, max_length=32)
    source: str = Field(default="sRGB", max_length=32)
    target: str | None = Field(default=None, max_length=32)


class ChromaRequest(_Base):
    colors: ColourList
    illuminant: str = Field(default=DEFAULT_ILLUMINANT, max_length=32)


class SpectralRequest(_Base):
    illuminant: str = Field(default=DEFAULT_ILLUMINANT, max_length=32)
    start: float = Field(default=380.0, ge=360.0, le=830.0)
    end: float = Field(default=780.0, ge=360.0, le=830.0)
    interval: float = Field(default=5.0, gt=0, le=50)
    blackbody_temperature: float | None = Field(default=None, ge=1000, le=25000)


class PhotometryRequest(_Base):
    colors: ColourList
    white: ColourStr = "#FFFFFF"


class DeltaERequest(_Base):
    colors: Annotated[list[ColourStr], Field(min_length=2, max_length=MAX_COLOURS)]
    method: str = Field(default=DEFAULT_METHOD, max_length=32)


class GradientRequest(_Base):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    start_colour: ColourStr = Field(alias="from")
    end_colour: ColourStr = Field(alias="to")
    space: str = Field(default="CIE Lab", max_length=32)
    steps: int = Field(default=11, ge=2, le=MAX_STEPS)
    method: str = Field(default=DEFAULT_METHOD, max_length=32)
