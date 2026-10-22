"""API 契约测试：状态码 + `detail.type`（方案 6.3 / 12「7 类错误路径」的 M1 子集）。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from colour_demo.main import app

client = TestClient(app)

PALETTE = ["#264653", "#2A9D8F", "#E9C46A", "#F4A261", "#E76F51"]


def _assert_error(response, status: int, kind: str):
    assert response.status_code == status, response.text
    detail = response.json()["detail"]
    assert detail["type"] == kind, detail
    assert detail["message"], detail


def test_health():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["colour_version"] == "0.4.7"


def test_meta_lists_methods():
    body = client.get("/api/v1/meta").json()
    assert "CIE 2000" in body["methods"]["delta_e"]
    assert body["counts"]["rgb_colourspaces"] > 50
    assert any("delta-e" in endpoint for endpoint in body["endpoints"])


def test_spaces():
    body = client.get("/api/v1/spaces").json()
    assert body["total"] > 50
    names = {space["name"] for space in body["spaces"]}
    assert "sRGB" in names


def test_convert_contract():
    response = client.post("/api/v1/convert", json={"colors": ["#3B82F6"], "target_spaces": ["CIE Lab"]})
    assert response.status_code == 200
    row = response.json()["rows"][0]
    assert row["hex"] == "#3B82F6"
    assert row["xyz"] == pytest.approx([0.2642, 0.2355, 0.9034], abs=1e-3)
    # 域口径：Lab 是 0–100（不是 Lab/100），与 /delta-e 返回的 Lab 一致
    assert row["values"]["CIE Lab"] == pytest.approx([55.6333, 17.5542, -64.4155], abs=1e-3)


def test_convert_default_spaces_all_resolve():
    """默认 14 个核心空间必须全部出数（CAM16 UCS 在换算图里叫 cam16ucs，需要别名）。"""

    body = client.post("/api/v1/convert", json={"colors": ["#3B82F6"], "target": "CAM16 UCS"}).json()
    assert len(body["spaces"]) == 14
    row = body["rows"][0]
    assert all(value is not None for value in row["values"].values()), row["values"]
    # 换算链路的节点名同样要走别名，否则 networkx 直接 NodeNotFound
    assert body["conversion_hops"] >= 1


def test_convert_unknown_space_is_422():
    response = client.post("/api/v1/convert", json={"colors": ["#3B82F6"], "target_spaces": ["No Such Space"]})
    _assert_error(response, 422, "value_error")


def test_chroma_contract():
    body = client.post("/api/v1/chroma", json={"colors": PALETTE, "illuminant": "D65"}).json()
    assert len(body["rows"]) == len(PALETTE)
    assert body["whitepoint_xy"] == pytest.approx([0.3127, 0.3290], abs=1e-3)


def test_spectral_contract_and_limits():
    body = client.post(
        "/api/v1/spectral",
        json={"illuminant": "D65", "start": 400, "end": 500, "interval": 10, "blackbody_temperature": 5000},
    ).json()
    assert body["shape"]["samples"] == 11
    assert len(body["series"]) == 2

    response = client.post("/api/v1/spectral", json={"start": 900, "end": 1000})
    _assert_error(response, 422, "value_error")


def test_photometry_contract():
    body = client.post("/api/v1/photometry", json={"colors": ["#808080"]}).json()
    row = body["rows"][0]
    assert row["Y"] == pytest.approx(21.59, abs=1e-2)
    assert row["lightness"]["CIE 1976"] == pytest.approx(53.59, abs=1e-2)


def test_delta_e_contract():
    body = client.post("/api/v1/delta-e", json={"colors": PALETTE, "method": "CIE 2000"}).json()
    assert body["method"] == "CIE 2000"
    assert len(body["matrix"]) == len(PALETTE)
    assert body["matrix"][0][1] == pytest.approx(33.53, abs=1e-2)
    assert body["pairs"]["closest"]["a"] in PALETTE


def test_delta_e_unknown_method_is_422():
    response = client.post("/api/v1/delta-e", json={"colors": PALETTE, "method": "Nope 2000"})
    _assert_error(response, 422, "value_error")


def test_delta_e_requires_two_colours():
    response = client.post("/api/v1/delta-e", json={"colors": ["#000000"]})
    _assert_error(response, 422, "value_error")


def test_colour_limit_is_12():
    too_many = [f"#{index:02X}0000" for index in range(13)]
    response = client.post("/api/v1/delta-e", json={"colors": too_many})
    _assert_error(response, 422, "value_error")


def test_bad_colour_reports_index():
    response = client.post("/api/v1/convert", json={"colors": ["#3B82F6", "nonsense-colour"]})
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["type"] == "value_error"
    assert "第 2 个颜色" in detail["message"]


def test_unknown_field_is_rejected():
    response = client.post("/api/v1/convert", json={"colors": ["#3B82F6"], "bogus": 1})
    _assert_error(response, 422, "value_error")


def test_gradient_contract_and_step_limits():
    body = client.post(
        "/api/v1/gradient", json={"from": "#264653", "to": "#E9C46A", "space": "CIE Lab", "steps": 11}
    ).json()
    assert body["steps"] == 11
    assert len(body["rows"]) == 11
    assert len(body["deltas"]) == 10

    _assert_error(client.post("/api/v1/gradient", json={"from": "#000000", "to": "#FFFFFF", "steps": 1}), 422, "value_error")
    _assert_error(client.post("/api/v1/gradient", json={"from": "#000000", "to": "#FFFFFF", "steps": 500}), 422, "value_error")


def test_demo_page_ships_live_layer():
    """原型页要带上「实时 API」层：健康探测 + 15 个面板适配器 + 离线退回静态快照。"""

    body = client.get("/demo/").text
    assert 'id="chip-api"' in body
    assert "async function apiProbe" in body
    for panel in ("convert", "delta-e", "chromaticity", "appearance", "cvd", "transfer"):
        assert f"LIVE.{panel} =" in body or f'LIVE["{panel}"] =' in body


def test_demo_page_is_served():
    response = client.get("/demo/")
    assert response.status_code == 200
    assert "colour-demo" in response.text


# --------------------------------------------------------------------------- #
# M2（面板 09–18）：11 个新端点
# --------------------------------------------------------------------------- #
GAMUTS = "sRGB,Display P3,ITU-R BT.2020"


def test_meta_lists_m2_surface():
    body = client.get("/api/v1/meta").json()
    assert len(body["endpoints"]) == 21
    assert "POST /api/v1/cvd" in body["endpoints"]
    assert "GET /api/v1/chromaticity.svg" in body["endpoints"]
    assert body["counts"]["cat_matrices"] == 13
    assert body["counts"]["appearance_models"] == 12
    # 两派色温方法表不能混：Ohno 2013 只在 uv 派里
    assert "Ohno 2013" in body["methods"]["temperature"]["uv_to_cct"]
    assert "Ohno 2013" not in body["methods"]["temperature"]["xy_to_cct"]


def test_transfer_contract():
    body = client.post("/api/v1/transfer", json={"colors": ["#3B82F6"], "samples": 9}).json()
    assert body["catalogue"]["counts"]["log_encodings"] == 32
    assert body["catalogue"]["counts"]["oetfs"] == 12

    curves = {row["name"]: row for row in body["curves"]}
    assert {"sRGB", "ITU-R BT.2100 PQ", "S-Log3"} <= set(curves)
    # 编码曲线必须单调递增（横轴线性光 0–1，纵轴编码值）
    assert all(curves[name]["invertible"] for name in curves)
    # 往返误差按方案 12 的 1e-6 门禁（实测 0）
    assert all(row["roundtrip_error"] is not None and row["roundtrip_error"] <= 1e-6 for row in curves.values())

    row = body["ycbcr"]["rows"][0]
    # BT.709 limited range 下 #3B82F6 的码值（8 bit）
    assert row["limited"]["codes"] == [123, 196, 86]
    assert row["limited"]["roundtrip_error"] <= 1e-6


def test_transfer_rejects_unknown_encoding():
    _assert_error(client.post("/api/v1/transfer", json={"encodings": ["No Such Curve"]}), 422, "value_error")
    _assert_error(client.post("/api/v1/transfer", json={"luma": "ITU-R BT.470"}), 422, "value_error")


def test_chromaticity_data():
    body = client.get("/api/v1/chromaticity", params={"colors": ",".join(PALETTE), "gamuts": GAMUTS}).json()
    areas = {row["name"]: row["area_xy"] for row in body["gamuts"]}
    assert areas["sRGB"] == pytest.approx(0.1120, abs=1e-3)
    assert areas["Display P3"] > areas["sRGB"]
    assert areas["ITU-R BT.2020"] > areas["Display P3"]
    # sRGB 里的颜色必然也落在 BT.2020 内；反推不成立
    assert all(sample["inside"]["ITU-R BT.2020"] for sample in body["samples"])
    assert all(sample["inside"]["sRGB"] for sample in body["samples"])


def test_chromaticity_svg_and_etag():
    response = client.get("/api/v1/chromaticity.svg", params={"colors": "#3B82F6"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/svg+xml")
    assert "<svg" in response.text
    # 同样的参数要给出同样的字节（matplotlib 的日期元数据已被剥掉）
    assert response.text == client.get("/api/v1/chromaticity.svg", params={"colors": "#3B82F6"}).text

    etag = response.headers["etag"]
    assert etag and response.headers["cache-control"].startswith("public")
    cached = client.get(
        "/api/v1/chromaticity.svg", params={"colors": "#3B82F6"}, headers={"If-None-Match": etag}
    )
    assert cached.status_code == 304


def test_chromaticity_rejects_unknown_diagram():
    _assert_error(client.get("/api/v1/chromaticity.svg", params={"diagram": "CIE 1900"}), 422, "value_error")


def test_volume_contract_is_reproducible():
    payload = {"spaces": ["sRGB", "Display P3"], "samples": 5000, "colors": PALETTE}
    first = client.post("/api/v1/volume", json=payload).json()
    second = client.post("/api/v1/volume", json=payload).json()
    # 固定种子 → 逐位可复现（关掉 multiprocessing 后不再受核数影响）
    assert first["rows"] == second["rows"]

    ratios = {row["space"]: row["relative_to_reference"] for row in first["rows"]}
    assert ratios["sRGB"] == pytest.approx(1.0, abs=1e-9)
    # MonteCarlo 有抽样噪声：5000 点实测 1.44、20000 点实测 1.49，只做量级断言
    assert ratios["Display P3"] == pytest.approx(1.45, abs=0.1)
    assert len(first["boundaries"]) == len(PALETTE)
    assert all(row["within_visible_spectrum"] for row in first["boundaries"])


def test_temperature_contract():
    body = client.post("/api/v1/temperature", json={"cct": 6500, "colors": ["#FFFFFF"]}).json()
    xy_results = body["xy_to_cct"][0]["results"]
    assert xy_results["CIE Illuminant D Series"] == pytest.approx(6500, abs=30)
    # Ohno 2013 属于 uv 派，反解返回 (CCT, D_uv) 二元组而不是标量
    ohno = body["uv_to_cct"][0]["results"]["Ohno 2013"]
    assert ohno["cct"] == pytest.approx(6500, abs=30)
    assert ohno["duv"] is not None

    assert len(body["cct_to_xy"]) == 4
    assert len(body["cct_to_uv"]) == 4
    assert len(body["planckian_locus"]) == 12
    assert body["mired"]["mired"] == pytest.approx(153.846, abs=0.01)


def test_temperature_rejects_out_of_range_cct():
    _assert_error(client.post("/api/v1/temperature", json={"cct": 100}), 422, "value_error")


def test_quality_contract():
    body = client.post("/api/v1/quality", json={"illuminants": ["D65", "FL2"]}).json()
    d65, fl2 = body["rows"]
    assert d65["Ra"] == pytest.approx(100.0, abs=0.2)
    assert d65["Rf"] == pytest.approx(100.0, abs=0.5)
    # FL2 是典型窄带荧光灯：Ra 掉到 60 出头，TM-30 的 Rf 与它不相等（口径不同）
    assert 60 < fl2["Ra"] < 70
    assert fl2["Rf"] == pytest.approx(70.12, abs=1.0)
    assert fl2["Rf"] != pytest.approx(fl2["Ra"], abs=1.0)
    assert len(body["special_indices"][1]) >= 15  # R1–R15


def test_quality_unknown_illuminant_is_422():
    _assert_error(client.post("/api/v1/quality", json={"illuminants": ["Nope"]}), 422, "value_error")


def test_lut_contract():
    body = client.post(
        "/api/v1/lut", json={"colors": ["#3B82F6"], "size": 17, "gains": [1.8, 0.5, 1.2]}
    ).json()
    assert body["table_points"] == 17**3
    assert body["domain"].startswith("编码值")

    row = body["rows"][0]
    assert set(row["outputs"]) == {"Trilinear", "Tetrahedral"}
    # 表是 `编码值 ** gains`：指数 >1 压暗、<1 提亮（x<1 时幂函数把值往 0 拉）
    assert row["outputs"]["Trilinear"]["rgb"][0] < row["rgb"][0]  # 1.8 → 压暗
    assert row["outputs"]["Trilinear"]["rgb"][1] > row["rgb"][1]  # 0.5 → 提亮
    assert len(body["ramp"]) == 9


def test_lut_rejects_unknown_interpolator():
    _assert_error(client.post("/api/v1/lut", json={"interpolators": ["Bicubic"]}), 422, "value_error")
    _assert_error(client.post("/api/v1/lut", json={"size": 64}), 422, "value_error")


def test_adapt_contract_covers_every_method():
    body = client.post("/api/v1/adapt", json={"colors": ["#3B82F6"], "source": "A", "target": "D65"}).json()
    results = body["rows"][0]["results"]
    # 7 个方法全部出数：CIE 1994 / CMCCAT2000 / Fairchild 1990 / Li 2025 要补观察条件
    assert set(results) == set(body["methods"])
    assert all(value is not None for value in results.values())
    assert body["vK20"]["#3B82F6"]["hex"].startswith("#")
    assert len(body["cat_matrices"]) == 13


def test_adapt_rejects_bad_arguments():
    _assert_error(client.post("/api/v1/adapt", json={"colors": ["#3B82F6"], "source": "A", "target": "A"}), 422, "value_error")
    _assert_error(client.post("/api/v1/adapt", json={"colors": ["#3B82F6"], "methods": ["Nope"]}), 422, "value_error")


def test_appearance_contract_and_cam16_golden():
    body = client.post("/api/v1/appearance", json={"colors": ["#3B82F6"]}).json()
    cam16 = body["rows"][0]["results"]["CAM16"]
    assert cam16["J"] == pytest.approx(45.23, abs=0.2)
    assert cam16["C"] == pytest.approx(63.83, abs=0.3)
    assert cam16["h"] == pytest.approx(266.30, abs=0.5)
    # 往返必须闭合（CAM16 是 0.4.7 里有逆变换的模型之一）
    assert cam16["roundtrip_error"] < 1e-9

    assert len(body["models"]) == 12
    assert all(value is not None for value in body["rows"][0]["results"].values())
    # ZCAM 是唯一的 0–1 域模型
    assert body["models"]["ZCAM"]["scale"] == 1


def test_appearance_rejects_unknown_model():
    _assert_error(client.post("/api/v1/appearance", json={"colors": ["#3B82F6"], "models": ["Nope"]}), 422, "value_error")


def test_phenomena_vision_contract():
    body = client.post(
        "/api/v1/phenomena-vision", json={"colors": ["#3B82F6"], "luminances": [10, 100], "points": 24}
    ).json()
    assert set(body["hk"]["curves"]) == {"VCC", "VAC"}
    # H-K：彩度越高越亮
    vcc = body["hk"]["curves"]["VCC"]
    assert vcc[-1] > vcc[0]
    # CSF 峰值频率应落在 1–10 cpd 的生理区间（把亮度当 Y_0 传会得到 0.5 cpd 的假峰）
    peaks = [row["peak_frequency_cpd"] for row in body["csf"]["derived"]]
    assert all(1.0 <= peak <= 10.0 for peak in peaks)


def test_corresponding_contract():
    body = client.post("/api/v1/corresponding", json={"experiment": 1}).json()
    assert len(body["rows"]) == 5
    assert all(row["mean_uv_error"] is not None for row in body["rows"])
    # CIE 1994 在 Breneman 实验 1 上误差最小（实测 0.0137，其余 0.08 量级）
    assert body["leaderboard"][0]["model"] == "CIE 1994"
    assert 9 in [item["experiment"] for item in body["unavailable_experiments"]]


def test_corresponding_unavailable_experiment_is_422():
    _assert_error(client.post("/api/v1/corresponding", json={"experiment": 9}), 422, "value_error")


def test_cvd_contract():
    body = client.post(
        "/api/v1/cvd", json={"colors": PALETTE, "deficiency": "Deuteranomaly", "severity": 1.0}
    ).json()
    assert body["severity"] == 1.0
    assert len(body["matrix_by_severity"]) == 5
    assert body["metrics"]["mean_delta_e"] > 1

    # severity=0 时矩阵是单位阵，模拟结果必须等于原色
    zero = client.post("/api/v1/cvd", json={"colors": PALETTE, "severity": 0.0}).json()
    assert [row["simulated_hex"] for row in zero["rows"]] == [row["hex"] for row in zero["rows"]]


def test_cvd_rejects_unknown_deficiency():
    _assert_error(client.post("/api/v1/cvd", json={"colors": PALETTE, "deficiency": "Nope"}), 422, "value_error")


def test_responses_carry_compute_time_header():
    assert float(client.get("/api/v1/health").headers["x-compute-ms"]) >= 0


def test_oversized_body_is_413():
    # 中间件按 Content-Length 拦截，请求体不进路由（方案 6.1 的 32 KB 限额）
    payload = {"colors": ["#3B82F6"], "target_spaces": ["CIE Lab"], "pad": "x" * 40000}
    _assert_error(client.post("/api/v1/convert", json=payload), 413, "too_large")
