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


# --------------------------------------------------------------------------- #
# M3（面板 19–25）：7 个新端点
# --------------------------------------------------------------------------- #
def test_recovery_contract():
    body = client.post("/api/v1/recovery", json={"colors": ["#3B82F6"]}).json()
    rows = {row["method"]: row for row in body["rows"]}
    assert set(rows) == {"Smits 1999", "Mallett 2019", "Jakob 2019", "Meng 2015"}
    # XYZ 派重建必须几乎精确回到原色
    assert rows["Jakob 2019"]["delta_e"] < 0.05
    assert rows["Meng 2015"]["delta_e"] < 0.05
    # Smits 用平滑基函数，蓝端残差约 1 个 ΔE——这是方法局限，不是实现误差
    assert 0.5 < rows["Smits 1999"]["delta_e"] < 3.0
    assert len(body["curves"]) == 4


def test_recovery_rejects_bad_step_and_method():
    _assert_error(client.post("/api/v1/recovery", json={"step": 3}), 422, "value_error")
    _assert_error(client.post("/api/v1/recovery", json={"methods": ["Nope"]}), 422, "value_error")


def test_correction_contract():
    body = client.post("/api/v1/correction", json={}).json()
    stages = {stage["stage"]: stage for stage in body["stages"]}
    before = body["stages"][0]
    assert before["mean_delta_e"] > 10  # A 光源下拍摄，偏色明显
    # 三种方法都必须把平均 ΔE 压下来
    for stage in body["stages"][1:]:
        assert stage["mean_delta_e"] < before["mean_delta_e"]
        assert len(stage["swatches"]) == 12
    assert body["best"]["mean_delta_e"] < 3
    assert len(body["matrices"]) == 3
    assert len(stages) == 4


def test_notation_contract():
    body = client.post("/api/v1/notation", json={"hex": "#3B82F6"}).json()
    assert body["munsell"]["roundtrip_matches"] is True
    assert body["munsell"]["back"].startswith("5")
    assert body["keyword"]["hex"] == "#FF6347"  # tomato
    assert body["hex"]["canonical"] == "#3B82F6"
    assert len(body["value_methods"]) == 7
    assert body["counts"]["css_basic"] == 16
    assert len(body["css_basic"]) == 16


def test_notation_rejects_bad_inputs():
    _assert_error(client.post("/api/v1/notation", json={"keyword": "not-a-css-colour"}), 422, "value_error")
    _assert_error(client.post("/api/v1/notation", json={"value_y": 200}), 422, "value_error")


def test_interpolate_contract():
    body = client.post("/api/v1/interpolate", json={}).json()
    rows = {row["interpolator"]: row for row in body["rows"]}
    assert set(rows) == {"Linear", "Sprague", "PCHIP", "Cubic Spline"}
    # 20 nm 采样漏掉汞灯尖线 → 各方法误差都在同一量级，但过冲不同
    assert rows["Sprague"]["max_abs_error"] > 5
    assert rows["Sprague"]["negative_points"] > 0  # Sprague 会过冲到负功率
    assert rows["Linear"]["negative_points"] == 0
    # 非线性合成表上两种 LUT 插值必须有差异（恒等表上必然为 0）
    assert body["lut"]["max_gap_codes"] > 0.5
    assert len(body["curves"]["residuals"]) == 4


def test_interpolate_rejects_bad_steps():
    _assert_error(client.post("/api/v1/interpolate", json={"coarse_step": 5, "target_step": 5}), 422, "value_error")
    _assert_error(client.post("/api/v1/interpolate", json={"interpolators": ["Nope"]}), 422, "value_error")


def test_geometry_contract():
    body = client.post("/api/v1/geometry", json={}).json()
    compare = {row["parameter"]: row for row in body["compare"]}
    assert compare["中心 x₀"]["fitted"] == pytest.approx(compare["中心 x₀"]["original"], abs=1e-6)
    # 长短半轴互换、θ 差约 90°（标准形约定），这是拟合正确而非误差
    # 原始数据只给到 4 位有效数字（a=2.1×10⁻³）；拟合值受平台 LAPACK 影响略有差异
    # （本机 macOS/arm64 ≈0.00210，CI Linux/x86 0.002085），所以按 5% 相对误差比，
    # 不用 1e-5 死比 —— 那是「同机才成立」的断言，跨平台必挂。
    assert compare["半轴 1"]["fitted"] == pytest.approx(compare["半轴 1"]["original"], rel=0.05)
    assert 85 < abs(compare["旋转角 θ°"]["fitted"] - compare["旋转角 θ°"]["original"]) < 95
    assert all(abs(float(row["residual"])) < 1e-6 for row in body["residuals"])
    assert body["segments"][0]["point"] == pytest.approx([0.5, 0.5])
    assert body["segments"][1]["parallel"] is True
    assert len(body["ellipses"]) == 25


def test_geometry_rejects_bad_index():
    _assert_error(client.post("/api/v1/geometry", json={"ellipse_index": 99}), 422, "value_error")


def test_optics_contract():
    body = client.post("/api/v1/optics", json={}).json()
    # 无损介质：R + T ≈ 1，是传输矩阵实现的健全性检查
    for row in body["film"]["rows"]:
        assert row["rt_sum_mean"] == pytest.approx(1.0, abs=1e-3)
    # 瑞利散射：实测比纯 1/λ⁴ 高几个百分点
    for row in body["rayleigh"]["rows"]:
        assert 0 < row["deviation_pct"] < 10
    # Abebe 2017 的 b_m<1 把速率整体抬高
    for row in body["kinetics"]["rows"]:
        assert row["abebe"] > row["michaelis"]


def test_plot_contract():
    body = client.post("/api/v1/plot", json={"plots": ["visible-spectrum"]}).json()
    assert len(body["plots"]) == 1
    plot = body["plots"][0]
    assert plot["media_type"] == "image/png"
    assert len(plot["png_base64"]) > 1000  # 真的编码出位图了
    assert body["counts"]["plot_functions"] > 50
    assert body["groups"]

    _assert_error(client.post("/api/v1/plot", json={"plots": ["nope"]}), 422, "value_error")
    _assert_error(client.post("/api/v1/plot", json={"plots": ["visible-spectrum"] * 5}), 422, "value_error")


def test_cvd_grey_is_invariant():
    """方向性判断：CVD 矩阵保持消色差轴，灰色模拟后仍是灰色。

    `eotf_sRGB`（码值→线性）与 `eotf_inverse_sRGB`（线性→码值）写反不会报错，
    但会多做一次编码、把灰色压暗——这条测试就是钉住方向的。
    """

    body = client.post("/api/v1/cvd", json={"colors": ["#808080"], "severity": 1.0}).json()
    assert body["rows"][0]["simulated_hex"] == "#808080"


# --------------------------------------------------------------------------- #
# M4（面板 26–28）：能力目录 / 参数化调用 / OpenAPI
# --------------------------------------------------------------------------- #
def test_catalog_contract():
    body = client.get("/api/v1/catalog", params={"limit": 5}).json()
    # 口径与方案一致：25 个子模块 / 1284 条导出 / 439 个顶层名称
    assert body["total"] == 1284
    assert body["top_level"]["names"] == 439
    assert len(body["modules"]) == 25
    assert body["coverage"] == 100.0
    counts = body["counts"]
    assert counts["面板"] + counts["数据集"] + counts["内部"] == body["total"]
    assert counts == {"面板": 826, "数据集": 238, "内部": 220}
    assert len(body["rows"]) == 5
    assert all(row["target"] for row in body["rows"])  # 不允许未分类
    assert len(body["whitelist"]) >= 10


def test_catalog_filters_and_paging():
    panels = client.get("/api/v1/catalog", params={"status": "面板", "limit": 3}).json()
    assert panels["matched"] == 826
    assert all(row["status"] == "面板" for row in panels["rows"])

    search = client.get("/api/v1/catalog", params={"q": "delta_e", "limit": 50}).json()
    assert search["matched"] > 0
    assert all("delta_e" in row["name"].lower() for row in search["rows"])

    paged = client.get("/api/v1/catalog", params={"limit": 5, "offset": 5}).json()
    first = client.get("/api/v1/catalog", params={"limit": 5}).json()
    assert paged["rows"] != first["rows"]

    # 空字符串按“未过滤”处理（表单式请求会送 q=&status=）
    empty = client.get("/api/v1/catalog", params={"q": "", "status": "", "limit": 5})
    assert empty.status_code == 200 and empty.json()["matched"] == empty.json()["total"]

    _assert_error(client.get("/api/v1/catalog", params={"status": "Nope"}), 422, "value_error")
    _assert_error(client.get("/api/v1/catalog", params={"limit": 0}), 422, "value_error")


def test_invoke_golden_and_parameter_styles():
    # 三种写法等价：args 位置 + kwargs 关键字
    body = client.post(
        "/api/v1/catalog/invoke",
        json={"function": "colour.temperature.CCT_to_xy", "args": [6500.0], "kwargs": {"method": "McCamy 1992"}},
    ).json()
    assert body["result"] == pytest.approx([0.3123, 0.3326], abs=1e-3)
    assert body["panel"] == "11"

    # params 显式写法；ΔE 黑/白应为 100 左右
    delta = client.post(
        "/api/v1/catalog/invoke",
        json={
            "function": "colour.delta_E",
            "params": {"Lab_1": [0.0, 0.0, 0.0], "Lab_2": [100.0, 0.0, 0.0], "method": "CIE 2000"},
        },
    ).json()
    assert delta["result"] == pytest.approx(100.0, abs=0.5)

    # 布尔结果也要 JSON 安全
    inside = client.post(
        "/api/v1/catalog/invoke",
        json={"function": "colour.volume.is_within_pointer_gamut", "params": {"XYZ": [0.2642, 0.2355, 0.9034]}},
    ).json()
    assert inside["result"] is False


def test_invoke_rejects_non_whitelist_and_bad_params():
    _assert_error(client.post("/api/v1/catalog/invoke", json={"function": "colour.os.system"}), 403, "forbidden")
    _assert_error(client.post("/api/v1/catalog/invoke", json={"function": "colour.delta_E"}), 422, "value_error")
    # 区间与枚举都要挡住
    _assert_error(
        client.post("/api/v1/catalog/invoke", json={"function": "colour.temperature.CCT_to_xy", "params": {"cct": 10}}),
        422,
        "value_error",
    )
    _assert_error(
        client.post(
            "/api/v1/catalog/invoke",
            json={"function": "colour.XYZ_to_Lab", "params": {"XYZ": [0.1, 0.2]}},
        ),
        422,
        "value_error",
    )
    _assert_error(
        client.post(
            "/api/v1/catalog/invoke",
            json={"function": "colour.blindness.matrix_cvd_Machado2009", "params": {"deficiency": "Nope", "severity": 1}},
        ),
        422,
        "value_error",
    )


def test_openapi_console_is_available():
    """面板 28 就是 FastAPI 自动生成的 OpenAPI：路径数要对得上端点清单。"""

    schema = client.get("/openapi.json").json()
    meta = client.get("/api/v1/meta").json()
    documented = {path for path in schema["paths"] if path.startswith("/api/v1")}
    listed = {endpoint.split(" ")[1] for endpoint in meta["endpoints"]}
    assert listed <= documented
    assert len(documented) >= 30


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
    assert len(body["endpoints"]) == 30
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
    # MonteCarlo 有抽样噪声，且噪声随平台/机器精度变化：本机 5000 点跨种子实测
    # 1.437–1.506、20000 点 1.485–1.523；CI(Linux/x86) 5000 点实测 1.5625。
    # 所以只断言量级（Display P3 约是 sRGB 的 1.5 倍），不钉具体值。
    assert 1.25 < ratios["Display P3"] < 1.75
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
