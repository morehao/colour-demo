"""面板 26：能力目录（`GET /api/v1/catalog`）。

这份映射就是「覆盖全部功能」的可验证定义：colour 0.4.7 的每个公开名称都必须落到
某个面板、某个数据集、或「内部基础设施（被服务层复用）」，**不允许出现未分类**。

实现口径（与原型 `docs/prototype/gen/catalog.py` 同源）：

- 逐个子模块取 `__all__`（跨模块有重复，所以是「子模块导出之和」而不是去重后的名字数）；
- 归属先看**名称级规则**（`RULES`），再看**子模块默认归属**（`MODULE_PANEL`）；
- 状态按值类型再分一层：落在「内部」→ 内部；常量/数据集 → 数据集；其余 → 面板。

注意：这个过程会 `import` colour 的全部子模块（约 25 个），第一次调用有明显开销，
所以整张表用 LRU 缓存住，之后只做内存过滤。
"""

from __future__ import annotations

import importlib
import pkgutil
import re

import colour

from ..core.cache import lru
from ..core.errors import value_error

PANEL_TITLES = {
    "00": "概览",
    "01": "颜色转换与换算图",
    "02": "色度学属性",
    "03": "观察者与光源",
    "04": "光度、明度与白度黄度",
    "05": "ΔE 全家桶",
    "06": "均匀空间与渐变",
    "07": "RGB 色彩空间图鉴",
    "08": "传递函数与视频信号",
    "09": "色度图与色域",
    "10": "色域体与边界",
    "11": "色温与黑体轨迹",
    "12": "色彩质量",
    "13": "图像与 3D LUT",
    "14": "色适应",
    "15": "外观模型",
    "16": "视觉模型与感知现象",
    "17": "对应色",
    "18": "色觉障碍",
    "19": "光谱重建",
    "20": "色彩校正与 ACES",
    "21": "记号与解析",
    "22": "连续信号与插值器",
    "23": "几何与椭圆拟合",
    "24": "光学现象与响应动力学",
    "25": "图表画廊",
    "26": "能力目录",
    "27": "参数化调用",
    "28": "API 控制台",
}

MODULE_PANEL = {
    "adaptation": "14",
    "algebra": "22",
    "appearance": "15",
    "biochemistry": "24",
    "blindness": "18",
    "characterisation": "20",
    "colorimetry": "02",
    "constants": "内部",
    "continuous": "22",
    "contrast": "16",
    "corresponding": "17",
    "difference": "05",
    "geometry": "23",
    "graph": "01",
    "hints": "内部",
    "io": "13",
    "models": "01",
    "notation": "21",
    "phenomena": "24",
    "plotting": "25",
    "quality": "12",
    "recovery": "19",
    "temperature": "11",
    "utilities": "内部",
    "volume": "10",
}

# 名称级覆盖（优先于子模块默认）
RULES = [
    # colorimetry → 03 数据集与光谱
    (
        r"^(MSDS_|SDS_|CCS_|TVS_|SpectralShape$|SpectralDistribution$|MultiSpectralDistributions$|"
        r"RGB_ColourMatchingFunctions$|XYZ_ColourMatchingFunctions$|LMS_ConeFundamentals$|"
        r"RGB_Basis|msds_|sds_|sd_|sd$|reshape_|spectral_|SPECTRAL_SHAPE_)",
        "03",
    ),
    # colorimetry → 04 光度/明度/白度/黄度
    (
        r"^(lightness|luminance|whiteness|yellowness|luminous_|LIGHT_LUMINANCE|LUMINANCE_METHODS|"
        r"LIGHTNESS_METHODS|WHITENESS_METHODS|YELLOWNESS_|intermediate_|mesopic_|BANDPASS_)",
        "04",
    ),
    # colorimetry → 11 色温相关
    (r"(planck_law|blackbody|daylight_locus|rayleigh_jeans)", "11"),
    # colorimetry → 02 其余（主波长/纯度/色度坐标/波长到 XYZ）
    (r"^(dominant_wavelength|complementary_wavelength|excitation_purity|colorimetric_purity|wavelength_to_XYZ)", "02"),
    # appearance → 16 感知效应
    (r"(HelmholtzKohlrausch|HKE_|coefficient_K_Br|coefficient_q_)", "16"),
    # models → 07 RGB 空间
    (
        r"^(RGB_COLOURSPACE|RGB_Colourspace$|RGB_COLOURSPACES|normalised_primary_matrix|"
        r"chromatically_adapted_primaries|primaries_whitepoint|RGB_COLOURSPACES_TEXTURE)",
        "07",
    ),
    # models → 08 传递函数与视频信号
    (
        r"^(eotf|oetf|ootf|cctf|log_encoding|log_decoding|LOG_|EOTF|OETF|OOTF|CCTF|BT2100_|"
        r"matrix_YCbCr|offset_YCbCr|WEIGHTS_YCBCR|MATRIX_COEFFICIENTS_|TRANSFER_CHARACTERISTICS_|"
        r"describe_video_signal|exponent_function|gamma_function|linear_function|"
        r"logarithmic_function|LOG3G10)",
        "08",
    ),
    # models → 06 均匀空间
    (r"(sUCS|IPT_hue_angle|^IPT$)", "06"),
    # io → 13 LUT/图像
    (
        r"^(LUT|read_LUT|write_LUT|read_image|write_image|as_3_channels_image|convert_bit_depth|"
        r"MAPPING_BIT_DEPTH|Image_Specification|READ_IMAGE|WRITE_IMAGE|LUT_)",
        "13",
    ),
]

# 数据集类（不可当函数调用）
DATA_HINTS = (
    "SDS_",
    "MSDS_",
    "CCS_",
    "TVS_",
    "RGB_COLOURSPACE",
    "CAT_",
    "VIEWING_CONDITIONS",
    "DATA_",
    "CONSTANTS_",
    "SDS_TCS",
    "MUNSELL_",
    "CSS_COLOR_3",
    "BRENEMAN_",
    "CLUSTER_MEANS",
    "PCA_",
    "BASIS_FUNCTIONS",
    "MATRIX_COEFFICIENTS",
    "WEIGHTS_",
    "TRANSFER_CHARACTERISTICS",
    "MAPPING_",
    "PATTERN_",
    "LOG_",
    "EOTF",
    "OETF",
)

STATUSES = ("面板", "数据集", "内部")
DEFAULT_LIMIT = 60
MAX_LIMIT = 500


def _kind_of(name: str, value) -> str:
    if isinstance(value, type):
        return "类"
    if name.isupper() or any(name.startswith(prefix) for prefix in DATA_HINTS):
        return "常量/数据集"
    if callable(value):
        return "函数"
    return "对象"


def _target_of(submodule: str, name: str) -> str:
    for pattern, panel_no in RULES:
        if re.match(pattern, name):
            return panel_no
    return MODULE_PANEL.get(submodule, "内部")


@lru(maxsize=1)
def build_catalog() -> dict:
    """整张表（子模块导出之和），跑一次缓存住。"""

    inventory: dict[str, list[str]] = {}
    for module_info in pkgutil.iter_modules(colour.__path__):
        module = importlib.import_module(f"colour.{module_info.name}")
        names = getattr(module, "__all__", None) or [n for n in dir(module) if not n.startswith("_")]
        inventory[module_info.name] = sorted(names)

    rows = []
    counts = {status: 0 for status in STATUSES}
    per_panel: dict[str, int] = {}
    for submodule, names in inventory.items():
        module = importlib.import_module(f"colour.{submodule}")
        for name in names:
            target = _target_of(submodule, name)
            kind = _kind_of(name, getattr(module, name, None))
            if target == "内部":
                status = "内部"
            elif kind == "常量/数据集":
                status = "数据集"
            else:
                status = "面板"
            counts[status] += 1
            if status == "面板":
                per_panel[target] = per_panel.get(target, 0) + 1
            rows.append(
                {"module": submodule, "name": name, "kind": kind, "target": target, "status": status}
            )

    modules = [
        {
            "name": submodule,
            "count": len(names),
            "panel": MODULE_PANEL.get(submodule, "内部"),
            "panel_title": PANEL_TITLES.get(MODULE_PANEL.get(submodule, ""), "内部复用"),
        }
        for submodule, names in inventory.items()
    ]
    modules.sort(key=lambda row: row["count"], reverse=True)

    top_level = [name for name in dir(colour) if not name.startswith("_")]
    return {
        "version": colour.__version__,
        "total": len(rows),
        "top_level_names": len(top_level),
        "top_level_callables": len([name for name in top_level if callable(getattr(colour, name))]),
        "counts": counts,
        "per_panel": per_panel,
        "panel_titles": PANEL_TITLES,
        "modules": modules,
        "rows": rows,
        "coverage": round(sum(1 for row in rows if row["target"]) / len(rows) * 100, 2),
    }


def catalog_index(
    query: str | None = None,
    status: str | None = None,
    module: str | None = None,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
) -> dict:
    # 空字符串按“未过滤”处理：GET 表单/前端很容易送来 q=&status=
    query = (query or "").strip() or None
    status = (status or "").strip() or None
    module = (module or "").strip() or None

    if status is not None and status not in STATUSES:
        raise value_error(f"status 可选：{list(STATUSES)}（或省略表示全部）")
    if not (1 <= limit <= MAX_LIMIT):
        raise value_error(f"limit 需在 1–{MAX_LIMIT}")
    if offset < 0:
        raise value_error("offset 不能为负")

    catalog = build_catalog()
    needle = (query or "").strip().lower()
    rows = [
        row
        for row in catalog["rows"]
        if (not needle or needle in row["name"].lower() or needle in row["module"].lower())
        and (status is None or row["status"] == status)
        and (module is None or row["module"] == module)
    ]

    from ..core import invoke  # 局部导入：invoke 依赖本模块的面板标题，避免循环

    return {
        "version": catalog["version"],
        "total": catalog["total"],
        "matched": len(rows),
        "offset": offset,
        "limit": limit,
        "rows": rows[offset : offset + limit],
        "counts": catalog["counts"],
        "per_panel": catalog["per_panel"],
        "panel_titles": catalog["panel_titles"],
        "modules": catalog["modules"],
        "coverage": catalog["coverage"],
        "top_level": {"names": catalog["top_level_names"], "callables": catalog["top_level_callables"]},
        "whitelist": invoke.whitelist_rows(),
        "warnings": [],
    }
