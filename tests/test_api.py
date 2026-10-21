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


def test_demo_page_is_served():
    response = client.get("/demo/")
    assert response.status_code == 200
    assert "colour-demo" in response.text
