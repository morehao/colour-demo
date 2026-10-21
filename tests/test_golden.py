"""黄金值 / 往返 / ΔE 参考数据 —— 方案第 12 节的三道门禁。

这些测试直接调服务层纯函数（不经 HTTP），对应方案 7.1 的「CI 复用同一套服务层做黄金值校验」。
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

import colour

from colour_demo import SUPPORTED_COLOUR_VERSION, assert_colour_version
from colour_demo.core import delta_e as delta_e_core
from colour_demo.core.parsing import parse_colour

DATA_DIR = Path(__file__).parent / "data"

GOLDEN_HEX = "#3B82F6"
GOLDEN_XYZ = (0.2642, 0.2355, 0.9034)
GOLDEN_LAB = (55.63, 17.55, -64.42)


def test_colour_version_is_pinned():
    """方案 12：版本漂移即阻断。"""

    assert colour.__version__ == SUPPORTED_COLOUR_VERSION
    assert assert_colour_version() == "0.4.7"


def test_golden_xyz():
    rgb = parse_colour(GOLDEN_HEX)
    xyz = np.asarray(colour.sRGB_to_XYZ(rgb), dtype=float)
    # 方案 12：abs(diff) ≤ 1e-3
    np.testing.assert_allclose(xyz, np.array(GOLDEN_XYZ), atol=1e-3, rtol=0)


def test_golden_lab():
    rgb = parse_colour(GOLDEN_HEX)
    # colour 0.4.7 的 XYZ_to_Lab 收 Domain1（0–1）XYZ，输出 0–100 的 Lab
    lab = np.asarray(colour.XYZ_to_Lab(colour.sRGB_to_XYZ(rgb)), dtype=float)
    # 方案里给的是 2 位小数，容差按 1e-2；同时锁 4 位小数的实测值，避免「碰巧通过」
    np.testing.assert_allclose(lab, np.array(GOLDEN_LAB), atol=1e-2, rtol=0)
    np.testing.assert_allclose(lab, np.array([55.6333, 17.5542, -64.4155]), atol=1e-3, rtol=0)


@pytest.mark.parametrize(
    ("source", "target", "atol"),
    [
        ("CIE Lab", "CIE XYZ", 1e-6),
        ("CIE XYZ", "CIE Lab", 1e-6),
        ("Oklab", "CIE XYZ", 1e-6),
        ("CIE XYZ", "Oklab", 1e-6),
        # sRGB 往返受 cctf 精度限制：实测 5.7e-5，达不到方案设想的 1e-6，
        # 这是 colour 0.4.7 的 sRGB EOTF/OETF 互逆残差，不是我们的实现问题。
        ("sRGB", "CIE XYZ", 1e-4),
        ("CIE XYZ", "sRGB", 1e-4),
    ],
)
def test_round_trip(source, target, atol):
    """方案 12：线性域往返最大绝对误差 ≤ 1e-6；sRGB 因 cctf 残差放宽到 1e-4。"""

    rgb = parse_colour(GOLDEN_HEX)
    xyz = np.asarray(colour.sRGB_to_XYZ(rgb), dtype=float)
    # 起点要与 source 空间一致：sRGB 起点传 rgb，其余（Lab/Oklab/XYZ）传 xyz
    start = rgb if source == "sRGB" else xyz
    forward = np.asarray(colour.convert(start, source, target), dtype=float)
    backward = np.asarray(colour.convert(forward, target, source), dtype=float)
    np.testing.assert_allclose(backward, start, atol=atol, rtol=0)


def test_delta_e_2000_sharma_dataset():
    """方案 12：与 Sharma (2005) 参考数据同口径，|diff| ≤ 0.02。

    夹具提取自上游 `colour/difference/tests/test_delta_e.py::test_delta_E_CIE2000_Sharma2004`，
    与上游一致排除第 14 对（np.arctan2 跨平台差异），故为 33 对。
    """

    payload = json.loads((DATA_DIR / "sharma2005_delta_e2000.json").read_text(encoding="utf-8"))
    pairs = payload["pairs"]
    assert len(pairs) == 33, "上游同口径应为 33 对（34 对去掉第 14 对）"

    computed = [
        float(np.asarray(colour.delta_E(np.array(pair["lab_1"]), np.array(pair["lab_2"]), method="CIE 2000")).ravel()[0])
        for pair in pairs
    ]
    expected = [pair["delta_e_2000"] for pair in pairs]
    worst = float(np.max(np.abs(np.array(computed) - np.array(expected))))
    assert worst <= 0.02, f"最大偏差 {worst:.4f} 超过 0.02"


def test_delta_e_matrix_matches_spec_example():
    """方案 6.2 里写死的示例数值必须能复现（这是契约的一部分）。"""

    result = delta_e_core.delta_e_matrix(
        ["#264653", "#2A9D8F", "#E9C46A", "#F4A261", "#E76F51"], method="CIE 2000"
    )
    assert result["matrix"][0] == pytest.approx([0.0, 33.53, 61.41, 57.7, 50.74], abs=1e-2)
    assert result["pairs"]["closest"] == {"a": "#E9C46A", "b": "#F4A261", "value": pytest.approx(16.1, abs=1e-1)}
    assert result["pairs"]["farthest"]["value"] == pytest.approx(61.41, abs=1e-2)


def test_gradient_uniformity_is_finite():
    from colour_demo.core import gradient

    result = gradient.gradient_data("#264653", "#E9C46A", space="CIE Lab", steps=11)
    assert len(result["rows"]) == 11
    assert result["uniformity"]["mean"] is not None
    assert result["uniformity"]["ratio"] is not None and result["uniformity"]["ratio"] >= 1.0


# --------------------------------------------------------------------------- #
# M2（面板 09–18）的锚点：这些数值是模块实现的口径证据，不是随手写的常量
# --------------------------------------------------------------------------- #
def test_m2_quality_anchors():
    """CRI 的参照光源必须接近 100；FL2 的 Ra 与 TM-30 Rf 口径不同、不能相等。"""

    from colour_demo.core.quality import quality_data

    body = quality_data(illuminants=["D65", "FL2"])
    d65, fl2 = body["rows"]
    assert d65["Ra"] == pytest.approx(100.0, abs=0.2)
    # 实测 64.23 / 70.12：两套指标对同一支灯给出不同结论，这正是面板 12 的论点
    assert fl2["Ra"] == pytest.approx(64.23, abs=0.05)
    assert fl2["Rf"] == pytest.approx(70.12, abs=0.05)


def test_m2_gamut_volume_is_deterministic():
    """固定种子 + 关掉 multiprocessing 后，同一请求必须逐位可复现。"""

    from colour_demo.core.volume import volume_data

    first = volume_data(spaces=["sRGB", "Display P3"], samples=5000)
    second = volume_data(spaces=["sRGB", "Display P3"], samples=5000)
    assert first["rows"] == second["rows"]

    ratios = {row["space"]: row["relative_to_reference"] for row in first["rows"]}
    assert ratios["sRGB"] == pytest.approx(1.0, abs=1e-9)
    assert ratios["Display P3"] > 1.3  # P3 的色域体积明显大于 sRGB


def test_m2_appearance_roundtrip_is_tight():
    """CAM16 正逆必须闭合；量级照方案 12 的 1e-6 门禁（实测 4.4e-16）。"""

    from colour_demo.core.appearance import appearance_data

    body = appearance_data(colours=["#3B82F6"], models=["CAM16", "ZCAM"])
    cam16 = body["rows"][0]["results"]["CAM16"]
    zcam = body["rows"][0]["results"]["ZCAM"]
    assert cam16["roundtrip_error"] <= 1e-6
    assert zcam["roundtrip_error"] <= 1e-6
    # 域陷阱：ZCAM 走 0–1、CAM16 走 0–100，两者 J 不应相同
    assert cam16["J"] != zcam["J"]


def test_m2_csf_peak_is_physiological():
    """Barten CSF 的峰值频率必须在 1–10 cpd（把 cd·m⁻² 当 Y_0 传会得到 0.5 的假峰）。"""

    from colour_demo.core.phenomena import phenomena_data

    body = phenomena_data(colours=["#3B82F6"], luminances=[10.0, 1000.0], points=24)
    for row in body["csf"]["derived"]:
        assert 1.0 <= row["peak_frequency_cpd"] <= 10.0
    # 亮度越高，视网膜照度越大
    assert body["csf"]["derived"][1]["retinal_illuminance_td"] > body["csf"]["derived"][0]["retinal_illuminance_td"]
