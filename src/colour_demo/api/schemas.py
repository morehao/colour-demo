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


# --------------------------------------------------------------------------- #
# M2（面板 09–18）：图表查询参数在路由上直接校验，其余走下面这些模型
# --------------------------------------------------------------------------- #
class VolumeRequest(_Base):
    spaces: list[str] | None = Field(default=None, max_length=8)
    samples: int = Field(default=20000, ge=1000, le=200000)
    seed: int = Field(default=7, ge=0, le=2**31 - 1)
    colors: ColourList | None = None


class TemperatureRequest(_Base):
    colors: ColourList | None = None
    cct: float = Field(default=6500.0, ge=800, le=100000)
    duv: float = Field(default=0.0, ge=-0.05, le=0.05)
    locus_points: int = Field(default=12, ge=3, le=64)


class QualityRequest(_Base):
    illuminants: list[str] | None = Field(default=None, max_length=12)
    reference: str = Field(default="D65", max_length=32)
    include_special: bool = True


class LutRequest(_Base):
    colors: ColourList | None = None
    size: int = Field(default=17, ge=2, le=33)
    gains: list[float] | None = Field(default=None, min_length=3, max_length=3)
    interpolators: list[str] | None = Field(default=None, max_length=2)
    ramp_steps: int = Field(default=9, ge=2, le=33)


class AdaptRequest(_Base):
    colors: ColourList
    source: str = Field(default="A", max_length=32)
    target: str = Field(default="D65", max_length=32)
    methods: list[str] | None = Field(default=None, max_length=7)
    include_matrices: bool = True


class AppearanceRequest(_Base):
    colors: ColourList
    models: list[str] | None = Field(default=None, max_length=12)
    L_A: float | None = Field(default=None, ge=0.01, le=10000)
    Y_b: float = Field(default=20.0, ge=0.01, le=100)
    surround: str = Field(default="Average", max_length=16)


class PhenomenaRequest(_Base):
    colors: ColourList | None = None
    luminances: list[float] | None = Field(default=None, max_length=4)
    chroma_max: float = Field(default=120.0, ge=1, le=200)
    points: int = Field(default=40, ge=8, le=120)


class CorrespondingRequest(_Base):
    experiment: int = Field(default=1)
    models: list[str] | None = Field(default=None, max_length=5)
    include_leaderboard: bool = True


class CvdRequest(_Base):
    colors: ColourList
    deficiency: str = Field(default="Deuteranomaly", max_length=32)
    severity: float = Field(default=1.0, ge=0, le=1)
    severities: list[float] | None = Field(default=None, max_length=5)
