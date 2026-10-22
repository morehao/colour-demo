"""能力目录：把 colour 0.4.7 的全部公开名称映射到「归属面板 / 数据集 / 内部」。

这份映射就是「覆盖全部功能」的可验证定义：
每个公开名称都必须落到某个面板、某个数据集或「内部基础设施（被服务层复用）」，
不允许出现「未分类」。
"""

from __future__ import annotations

import importlib
import pkgutil
import re

import colour

# 面板编号 → 标题（与 panels_*.py 的 no/title 保持一致）
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

# 子模块默认归属
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
    (r"^(MSDS_|SDS_|CCS_|TVS_|SpectralShape$|SpectralDistribution$|MultiSpectralDistributions$|"
     r"RGB_ColourMatchingFunctions$|XYZ_ColourMatchingFunctions$|LMS_ConeFundamentals$|"
     r"RGB_Basis|msds_|sds_|sd_|sd$|reshape_|spectral_|SPECTRAL_SHAPE_)", "03"),
    # colorimetry → 04 光度/明度/白度/黄度
    (r"^(lightness|luminance|whiteness|yellowness|luminous_|LIGHT_LUMINANCE|LUMINANCE_METHODS|"
     r"LIGHTNESS_METHODS|WHITENESS_METHODS|YELLOWNESS_|intermediate_|mesopic_|BANDPASS_)", "04"),
    # colorimetry → 11 色温相关
    (r"(planck_law|blackbody|daylight_locus|rayleigh_jeans)", "11"),
    # colorimetry → 02 其余（主波长/纯度/色度坐标/波长到 XYZ）
    (r"^(dominant_wavelength|complementary_wavelength|excitation_purity|colorimetric_purity|wavelength_to_XYZ)", "02"),
    # appearance → 16 感知效应
    (r"(HelmholtzKohlrausch|HKE_|coefficient_K_Br|coefficient_q_)", "16"),
    # models → 07 RGB 空间
    (r"^(RGB_COLOURSPACE|RGB_Colourspace$|RGB_COLOURSPACES|normalised_primary_matrix|"
     r"chromatically_adapted_primaries|primaries_whitepoint|RGB_COLOURSPACES_TEXTURE)", "07"),
    # models → 08 传递函数与视频信号
    (r"^(eotf|oetf|ootf|cctf|log_encoding|log_decoding|LOG_|EOTF|OETF|OOTF|CCTF|BT2100_|"
     r"matrix_YCbCr|offset_YCbCr|WEIGHTS_YCBCR|MATRIX_COEFFICIENTS_|TRANSFER_CHARACTERISTICS_|"
     r"describe_video_signal|exponent_function|gamma_function|linear_function|"
     r"logarithmic_function|LOG3G10)", "08"),
    # models → 06 均匀空间
    (r"(sUCS|IPT_hue_angle|^IPT$)", "06"),
    # io → 13 LUT/图像
    (r"^(LUT|read_LUT|write_LUT|read_image|write_image|as_3_channels_image|convert_bit_depth|"
     r"MAPPING_BIT_DEPTH|Image_Specification|READ_IMAGE|WRITE_IMAGE|LUT_)", "13"),
]

# 数据集类（不可当函数调用）
DATA_HINTS = ("SDS_", "MSDS_", "CCS_", "TVS_", "RGB_COLOURSPACE", "CAT_", "VIEWING_CONDITIONS",
              "DATA_", "CONSTANTS_", "SDS_TCS", "MUNSELL_", "CSS_COLOR_3", "BRENEMAN_",
              "CLUSTER_MEANS", "PCA_", "BASIS_FUNCTIONS", "MATRIX_COEFFICIENTS", "WEIGHTS_",
              "TRANSFER_CHARACTERISTICS", "MAPPING_", "PATTERN_", "LOG_", "EOTF", "OETF")


def submodule_inventory() -> dict:
    result = {}
    for module_info in pkgutil.iter_modules(colour.__path__):
        name = module_info.name
        module = importlib.import_module(f"colour.{name}")
        names = getattr(module, "__all__", None) or [n for n in dir(module) if not n.startswith("_")]
        result[name] = sorted(names)
    return result


def kind_of(name: str, value) -> str:
    if isinstance(value, type):
        return "类"
    if name.isupper() or name.upper() == name or any(name.startswith(p) for p in DATA_HINTS):
        return "常量/数据集"
    if callable(value):
        return "函数"
    return "对象"


def target_of(submodule: str, name: str) -> str:
    for pattern, panel_no in RULES:
        if re.match(pattern, name):
            return panel_no
    return MODULE_PANEL.get(submodule, "内部")


def build_catalog() -> dict:
    inventory = submodule_inventory()
    rows = []
    counts = {"面板": 0, "数据集": 0, "内部": 0}
    per_panel: dict[str, int] = {}
    for submodule, names in inventory.items():
        module = importlib.import_module(f"colour.{submodule}")
        for name in names:
            target = target_of(submodule, name)
            value = getattr(module, name, None)
            kind = kind_of(name, value)
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
                {
                    "module": submodule,
                    "name": name,
                    "kind": kind,
                    "target": target,
                    "status": status,
                }
            )

    total = len(rows)
    modules = []
    for submodule, names in inventory.items():
        module_rows = [r for r in rows if r["module"] == submodule]
        modules.append(
            {
                "name": submodule,
                "count": len(names),
                "panel": MODULE_PANEL.get(submodule, "内部"),
                "panel_title": PANEL_TITLES.get(MODULE_PANEL.get(submodule, ""), "内部复用"),
            }
        )

    top_level = [n for n in dir(colour) if not n.startswith("_")]
    return {
        "version": colour.__version__,
        "total": total,
        "top_level_names": len(top_level),
        "top_level_callables": len([n for n in top_level if callable(getattr(colour, n))]),
        "counts": counts,
        "per_panel": per_panel,
        "panel_titles": PANEL_TITLES,
        "modules": modules,
        "rows": rows,
        "coverage": round(sum(1 for r in rows if r["target"]) / total * 100, 2),
    }
