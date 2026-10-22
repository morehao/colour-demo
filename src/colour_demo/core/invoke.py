"""面板 27：参数化调用（`POST /api/v1/catalog/invoke`）。

给面板没展开的通路开一个口子：按函数名 + 参数调用 colour 的公开函数。

安全设计（方案 11：不用 `eval` / `exec` / 动态导入）：

- **白名单是静态表**：每个条目写死函数对象、参数名、类型、范围与枚举，
  不按用户输入反射取属性，也不 `getattr(colour, user_input)`；
- 参数逐个按声明校验（类型、区间、长度、枚举），坏参数在进 colour 之前就被挡掉（422）；
- 非白名单 → 403 `forbidden`，响应里给可选函数列表；
- 返回值统一做 JSON 安全化：ndarray → 嵌套 list，nan/inf → null，numpy 标量 → Python 标量；
- colour 的告警原样带回 `warnings[]`（近似模型/非双射方法要能被看见）。

白名单只收**纯函数**：无文件 I/O、无网络、无全局状态、参数规模有限。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np

import colour

from ..core.diagnostics import WarningCollector, number
from ..core.errors import forbidden, value_error

OBSERVER = "CIE 1931 2 Degree Standard Observer"
MAX_VECTOR = 3
MAX_STRING = 64


@dataclass(frozen=True, slots=True)
class Param:
    """一个入参的声明（就是这张表挡住了所有“随便传”）。"""

    name: str
    kind: str  # float / int / vector / string
    label: str
    default: Any = None
    minimum: float | None = None
    maximum: float | None = None
    enum: tuple[str, ...] | None = None
    length: int | None = None
    keyword: bool = False  # 以 kwargs 形式传（如 method=...）
    required: bool = True


@dataclass(frozen=True, slots=True)
class Entry:
    name: str
    label: str
    panel: str
    returns: str
    params: tuple[Param, ...]
    example: dict = field(default_factory=dict)
    fn: Callable[..., Any] = field(default=None, repr=False)  # type: ignore[assignment]


_METHODS_DELTA_E = tuple(name for name in colour.difference.DELTA_E_METHODS if name[0].isupper())
_METHODS_XY_TO_CCT = tuple(name for name in colour.temperature.XY_TO_CCT_METHODS if name[0].isupper())
_METHODS_CCT_TO_XY = tuple(name for name in colour.temperature.CCT_TO_XY_METHODS if name[0].isupper())

WHITELIST: dict[str, Entry] = {}


def _register(entry: Entry) -> None:
    WHITELIST[entry.name] = entry


_register(
    Entry(
        name="colour.temperature.CCT_to_xy",
        label="色温 → CIE xy",
        panel="11",
        returns="CIE xy（2 个元素）",
        params=(
            Param("cct", "float", "相关色温 K", minimum=800.0, maximum=100000.0),
            Param("method", "string", "方法", default="CIE Illuminant D Series", enum=_METHODS_CCT_TO_XY, keyword=True),
        ),
        example={"cct": 6500.0, "method": "McCamy 1992"},
        fn=colour.temperature.CCT_to_xy,
    )
)
_register(
    Entry(
        name="colour.temperature.xy_to_CCT",
        label="CIE xy → 色温",
        panel="11",
        returns="相关色温 K",
        params=(
            Param("xy", "vector", "CIE xy", length=2),
            Param("method", "string", "方法", default="CIE Illuminant D Series", enum=_METHODS_XY_TO_CCT, keyword=True),
        ),
        example={"xy": [0.3127, 0.3290]},
        fn=colour.temperature.xy_to_CCT,
    )
)
_register(
    Entry(
        name="colour.delta_E",
        label="两个 Lab 的色差",
        panel="05",
        returns="ΔE（标量）",
        params=(
            Param("Lab_1", "vector", "Lab 1（0–100 域）", length=3),
            Param("Lab_2", "vector", "Lab 2（0–100 域）", length=3),
            Param("method", "string", "ΔE 方法", default="CIE 2000", enum=_METHODS_DELTA_E, keyword=True),
        ),
        example={"Lab_1": [55.63, 17.55, -64.42], "Lab_2": [53.24, 80.09, 67.20], "method": "CIE 2000"},
        fn=colour.delta_E,
    )
)
_register(
    Entry(
        name="colour.XYZ_to_Lab",
        label="XYZ → CIE Lab",
        panel="01",
        returns="Lab（0–100 域）",
        params=(Param("XYZ", "vector", "XYZ（0–1 域）", length=3),),
        example={"XYZ": [0.2642, 0.2355, 0.9034]},
        fn=colour.XYZ_to_Lab,
    )
)
_register(
    Entry(
        name="colour.sRGB_to_XYZ",
        label="sRGB → XYZ",
        panel="01",
        returns="XYZ（0–1 域）",
        params=(Param("RGB", "vector", "sRGB 编码值（0–1）", length=3),),
        example={"RGB": [0.2314, 0.5098, 0.9647]},
        fn=colour.sRGB_to_XYZ,
    )
)
_register(
    Entry(
        name="colour.XYZ_to_Oklab",
        label="XYZ → Oklab",
        panel="01",
        returns="Oklab（L / a / b）",
        params=(Param("XYZ", "vector", "XYZ（0–1 域）", length=3),),
        example={"XYZ": [0.2642, 0.2355, 0.9034]},
        fn=colour.XYZ_to_Oklab,
    )
)
_register(
    Entry(
        name="colour.colorimetry.luminance",
        label="Y → 亮度（多种算法）",
        panel="04",
        returns="亮度值",
        params=(
            Param("Y", "float", "Y（0–100 域）", minimum=0.0, maximum=100.0),
            Param("method", "string", "方法", default="CIE 1976", enum=("CIE 1976", "Newhall 1943", "ASTM D1535", "Fairchild 2011"), keyword=True),
        ),
        example={"Y": 21.59},
        fn=colour.colorimetry.luminance,
    )
)
_register(
    Entry(
        name="colour.volume.is_within_pointer_gamut",
        label="是否在 Pointer 色域内",
        panel="10",
        returns="布尔值",
        params=(Param("XYZ", "vector", "XYZ（0–1 域）", length=3),),
        example={"XYZ": [0.2642, 0.2355, 0.9034]},
        fn=colour.volume.is_within_pointer_gamut,
    )
)
_register(
    Entry(
        name="colour.notation.munsell_colour_to_xyY",
        label="Munsell 记号 → xyY",
        panel="21",
        returns="xyY（3 个元素）",
        params=(Param("munsell_colour", "string", "Munsell 记号（如 5R 5/12）"),),
        example={"munsell_colour": "5R 5/12"},
        fn=colour.notation.munsell_colour_to_xyY,
    )
)
_register(
    Entry(
        name="colour.notation.keyword_to_RGB_CSSColor3",
        label="CSS 关键字 → sRGB",
        panel="21",
        returns="sRGB（3 个元素）",
        params=(Param("keyword", "string", "CSS Color 3 关键字（如 tomato）"),),
        example={"keyword": "tomato"},
        fn=colour.notation.keyword_to_RGB_CSSColor3,
    )
)
_register(
    Entry(
        name="colour.blindness.matrix_cvd_Machado2009",
        label="色觉障碍模拟矩阵",
        panel="18",
        returns="3×3 矩阵",
        params=(
            Param("deficiency", "string", "类型", enum=("Protanomaly", "Deuteranomaly", "Tritanomaly")),
            Param("severity", "float", "严重度", minimum=0.0, maximum=1.0),
        ),
        example={"deficiency": "Deuteranomaly", "severity": 1.0},
        fn=colour.blindness.matrix_cvd_Machado2009,
    )
)


def whitelist_rows() -> list[dict]:
    """给前端/目录用的白名单摘要（不含函数对象）。"""

    return [
        {
            "name": entry.name,
            "label": entry.label,
            "panel": entry.panel,
            "returns": entry.returns,
            "params": [
                {
                    "name": param.name,
                    "kind": param.kind,
                    "label": param.label,
                    "default": param.default,
                    "minimum": param.minimum,
                    "maximum": param.maximum,
                    "enum": list(param.enum) if param.enum else None,
                    "length": param.length,
                }
                for param in entry.params
            ],
            "example": entry.example,
        }
        for entry in WHITELIST.values()
    ]


def _coerce(param: Param, value: Any) -> Any:
    """逐个按声明校验，别把用户输入直接塞进 colour。"""

    if param.kind == "float":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise value_error(f"{param.name} 需要数字，收到 {type(value).__name__}")
        number_value = float(value)
        if param.minimum is not None and number_value < param.minimum:
            raise value_error(f"{param.name} 需 ≥ {param.minimum:g}")
        if param.maximum is not None and number_value > param.maximum:
            raise value_error(f"{param.name} 需 ≤ {param.maximum:g}")
        return number_value

    if param.kind == "int":
        if isinstance(value, bool) or not isinstance(value, int):
            raise value_error(f"{param.name} 需要整数")
        return int(value)

    if param.kind == "vector":
        if not isinstance(value, (list, tuple)):
            raise value_error(f"{param.name} 需要数组")
        if param.length is not None and len(value) != param.length:
            raise value_error(f"{param.name} 需要 {param.length} 个元素，收到 {len(value)} 个")
        if len(value) > MAX_VECTOR:
            raise value_error(f"{param.name} 最多 {MAX_VECTOR} 个元素")
        numbers = []
        for index, item in enumerate(value):
            if isinstance(item, bool) or not isinstance(item, (int, float)):
                raise value_error(f"{param.name}[{index}] 需要数字")
            numbers.append(float(item))
        return np.asarray(numbers, dtype=float)

    if param.kind == "string":
        if not isinstance(value, str):
            raise value_error(f"{param.name} 需要字符串")
        text = value.strip()
        if not text:
            raise value_error(f"{param.name} 不能为空")
        if len(text) > MAX_STRING:
            raise value_error(f"{param.name} 最长 {MAX_STRING} 个字符")
        if param.enum is not None and text not in param.enum:
            raise value_error(f"{param.name} 不支持 {text!r}，可选：{list(param.enum)}")
        return text

    raise value_error(f"未支持的参数类型 {param.kind!r}")  # pragma: no cover


def _json_safe(value: Any) -> Any:
    """colour 的返回值 → JSON 安全结构。"""

    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, np.ndarray):
        if value.ndim == 0:
            return _json_safe(value.item())
        return [_json_safe(item) for item in value.tolist()]
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (int, float, np.integer, np.floating)):
        return number(value, 6)
    if isinstance(value, str):
        return value
    # SpectralDistribution / CAM 规格对象之类：给字符串表示，避免返回不可序列化的对象
    return str(value)


def _collect(entry: Entry, body: dict) -> tuple[list[Any], dict[str, Any]]:
    """把 params / args / kwargs 三种写法统一成 (位置参数, 关键字参数)。"""

    by_name = {param.name: param for param in entry.params}
    values: dict[str, Any] = {}

    if body.get("params"):
        unknown = [key for key in body["params"] if key not in by_name]
        if unknown:
            raise value_error(f"未知参数 {unknown}，可选：{list(by_name)}")
        values.update(body["params"])

    if body.get("args"):
        args = body["args"]
        if len(args) > len(entry.params):
            raise value_error(f"{entry.name} 最多 {len(entry.params)} 个参数")
        for index, value in enumerate(args):
            name = entry.params[index].name
            if name in values:
                raise value_error(f"参数 {name} 重复（args 与 params 同时给了）")
            values[name] = value

    if body.get("kwargs"):
        for name, value in body["kwargs"].items():
            if name not in by_name:
                raise value_error(f"未知参数 {name}，可选：{list(by_name)}")
            if name in values:
                raise value_error(f"参数 {name} 重复（kwargs 与前面同时给了）")
            values[name] = value

    positional: list[Any] = []
    keyword: dict[str, Any] = {}
    for param in entry.params:
        if param.name in values:
            value = _coerce(param, values[param.name])
        elif param.default is not None:
            value = param.default
        elif param.required:
            raise value_error(f"缺少参数 {param.name}（{param.label}）")
        else:  # pragma: no cover - 目前没有非必填且无默认值的参数
            continue
        if param.keyword:
            keyword[param.name] = value
        else:
            positional.append(value)
    return positional, keyword


def invoke(body: dict) -> dict:
    name = str(body.get("function") or "").strip()
    if not name:
        raise value_error("缺少 function")
    entry = WHITELIST.get(name)
    if entry is None:
        raise forbidden(
            f"函数未在能力目录白名单内：{name!r}；可选：{list(WHITELIST)}"
        )

    positional, keyword = _collect(entry, body)
    with WarningCollector() as log:
        try:
            result = entry.fn(*positional, **keyword)
        except Exception as error:
            raise value_error(f"{name} 计算失败：{type(error).__name__}: {error}") from error
        safe = _json_safe(result)
        log.add(
            "note",
            "白名单只含纯函数（无 I/O、无全局状态、参数有限）；colour 的告警原样回传，"
            "近似模型与非双射方法的偏差请按告警读。",
        )

    return {
        "function": name,
        "label": entry.label,
        "panel": entry.panel,
        "returns": entry.returns,
        "request": {"positional": [_json_safe(value) for value in positional], "keyword": keyword},
        "result": safe,
        "warnings": log.payload,
    }
