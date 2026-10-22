"""新手层数据契约测试（T1–T7）。

只依赖 `docs/prototype/gen/*.py` 的纯数据；除 T4 读一个常量外不触发 colour 计算，
CI 里跑得很快。
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PROTOTYPE = ROOT / "docs" / "prototype"
if str(PROTOTYPE) not in sys.path:
    sys.path.insert(0, str(PROTOTYPE))

from gen import copy_lint, glossary, manifest, panel_copy, tasks, verdicts  # noqa: E402

PANEL_IDS = set(manifest.PANEL_IDS)
GLOSSARY = glossary.GLOSSARY
TASKS = tasks.TASKS


# --------------------------------------------------------------------------- #
# T1 / T7：清单一致性
# --------------------------------------------------------------------------- #
def test_manifest_lists_are_consistent():
    assert len(manifest.PANEL_IDS) == 29
    assert len(PANEL_IDS) == 29
    assert set(manifest.LIVE_PANEL_IDS) <= PANEL_IDS
    assert "overview" not in manifest.LIVE_PANEL_IDS
    assert manifest.TASK_IDS == [task["id"] for task in TASKS]
    assert set(manifest.OLD_HASH_REDIRECTS) == PANEL_IDS


def test_legacy_redirects_point_to_new_routes():
    for panel_id, target in manifest.OLD_HASH_REDIRECTS.items():
        assert target == f"#/ref/{panel_id}"


# --------------------------------------------------------------------------- #
# T2：任务结构 + 预设与字段一致
# --------------------------------------------------------------------------- #
def test_task_references_are_valid():
    for task in TASKS:
        assert task.get("nav"), task["id"]
        assert task["tool"] in PANEL_IDS, task["id"]
        assert task["tool"] in manifest.LIVE_PANEL_IDS, task["id"]
        assert task["outcome"] in verdicts.VERDICTS, task["id"]
        assert task.get("related"), task["id"]
        for panel_id in task["related"]:
            assert panel_id in PANEL_IDS, (task["id"], panel_id)
        for term in task["jargon"]:
            assert term in GLOSSARY, (task["id"], term)
        assert task["title"].endswith("？"), task["id"]


def test_task_presets_match_fields():
    for task in TASKS:
        field_keys = {field["key"] for field in task["fields"]}
        assert field_keys, task["id"]
        assert len(task["presets"]) == 3, task["id"]
        assert len({preset["id"] for preset in task["presets"]}) == 3, task["id"]
        for preset in task["presets"]:
            assert set(preset["state"]) == field_keys, (task["id"], preset["id"])
            assert preset["label"], (task["id"], preset["id"])


def test_task_colour_counts_within_bounds():
    for task in TASKS:
        for field in task["fields"]:
            if field["kind"] != "colors":
                continue
            for preset in task["presets"]:
                count = len(preset["state"][field["key"]])
                assert field["min"] <= count <= field["max"], (
                    task["id"],
                    preset["id"],
                    field["min"],
                    count,
                    field["max"],
                )


def test_panel_copy_covers_all_panels():
    assert set(panel_copy.PANEL_COPY) == PANEL_IDS
    for panel_id, copy in panel_copy.PANEL_COPY.items():
        panel = {"no": panel_id, "id": panel_id, "presets": [], **copy}
        errors, warnings = copy_lint.validate_panel_copy(panel)
        assert not errors, (panel_id, errors)
        assert not warnings, (panel_id, warnings)
        assert 30 <= len(copy["plain"]) <= 80, (panel_id, len(copy["plain"]))
        assert len(copy["read"]) == 3, panel_id
        assert copy["preview"] in {"chain", "convert", "kv", "table", "swatches", "strips", "image", "chart", "stats"}, panel_id
        for term in copy["jargon"]:
            assert term in GLOSSARY, (panel_id, term)
        if copy.get("verdict"):
            assert copy["verdict"] in verdicts.VERDICTS, panel_id
            assert isinstance(copy.get("verdict_value"), (int, float)) or copy.get("verdict_html"), panel_id


# --------------------------------------------------------------------------- #
# T3：术语表
# --------------------------------------------------------------------------- #
def test_glossary_shape():
    assert len(GLOSSARY) == 40
    seen: dict[str, str] = {}
    for key, entry in GLOSSARY.items():
        assert entry["term"] and entry["zh"], key
        assert entry["plain"] and len(entry["plain"]) <= 80, key
        for alias in entry["aliases"]:
            assert alias not in seen, f"别名重复：{alias}"
            seen[alias] = key
        see = entry.get("see")
        if see:
            assert see.startswith("#/ref/")
            assert see.removeprefix("#/ref/") in PANEL_IDS, (key, see)


# --------------------------------------------------------------------------- #
# T4：结论规则
# --------------------------------------------------------------------------- #
def test_verdicts_are_well_formed():
    for key in verdicts.VERDICTS:
        rule = verdicts.resolve(key)
        if rule["kind"] != "band":
            assert rule.get("template"), key
            continue
        limits = [band["lt"] for band in rule["bands"]]
        assert limits[-1] is None, key
        numbers = [value for value in limits if value is not None]
        assert numbers == sorted(numbers), key
        for band in rule["bands"]:
            assert band["tone"] in verdicts.TONES, key
            assert band["label"] and band["say"], key


def test_task_field_kinds_are_supported():
    supported = {"colors", "color", "select", "method", "number", "notation"}
    for task in TASKS:
        for field in task["fields"]:
            assert field["kind"] in supported, (task["id"], field["key"], field["kind"])


def test_task_fields_are_shareable():
    """任务输入按 key 序列化到 URL；key 必须唯一，选择项必须可还原。"""
    for task in TASKS:
        keys = [field["key"] for field in task["fields"]]
        assert len(keys) == len(set(keys)), task["id"]
        for field in task["fields"]:
            if field["kind"] in {"select", "method"}:
                assert field["options"], (task["id"], field["key"])
                assert field["value"] in field["options"], (task["id"], field["key"])


def test_translate_template_uses_response_fields():
    template = verdicts.VERDICTS["translate"]["template"]
    placeholders = set(re.findall(r"\{(\w+)\}", template))
    # /notation 不返回 Lab，模板只能用输入、HEX 和 RGB
    assert placeholders <= {"input", "hex", "rgb"}, placeholders


def test_shift_reuses_delta_e_bands():
    shift = verdicts.resolve("shift")
    delta_e = verdicts.resolve("deltaE")
    assert shift["bands"] == delta_e["bands"]


def test_cvd_threshold_matches_server_constant():
    from colour_demo.core.cvd import INDISTINGUISHABLE_DELTA_E

    first = verdicts.resolve("cvd")["bands"][0]
    assert first["lt"] == INDISTINGUISHABLE_DELTA_E


def test_band_for_covers_extremes():
    assert verdicts.band_for("deltaE", 0)["label"] == "几乎看不出"
    assert verdicts.band_for("deltaE", 1e9)["label"] == "完全不同"
    assert verdicts.band_for("purity", 0.99)["label"] == "非常鲜艳"
    assert verdicts.band_for("temperature", 2700)["label"] == "暖黄"
    assert verdicts.band_for("temperature", 6500)["label"] == "日光"


# --------------------------------------------------------------------------- #
# T5：任务文案 lint
# --------------------------------------------------------------------------- #
def test_task_copy_has_no_hard_forbidden_words():
    for task in TASKS:
        chunks = [task["title"], task["intro"], *task["steps"], *task["explain"]]
        for chunk in chunks:
            for word in copy_lint.HARD_FORBIDDEN:
                assert word not in chunk, (task["id"], word, chunk)


def test_panel_lint_catches_missing_copy():
    errors, _ = copy_lint.validate_panel_copy({"no": "99", "id": "x"})
    assert any("为空" in error for error in errors)


# --------------------------------------------------------------------------- #
# 可选：本地跑过 --tasks 后，检查快照覆盖全部预设
# --------------------------------------------------------------------------- #
def test_task_snapshots_cover_presets_when_built():
    path = ROOT / ".tmp" / "panels" / "tasks.json"
    if not path.exists():
        pytest.skip("尚未构建任务快照（--tasks）")
    built = {task["id"]: task for task in json.loads(path.read_text(encoding="utf-8"))["tasks"]}
    for task in TASKS:
        snapshots = built[task["id"]]["snapshots"]
        assert set(snapshots) == {preset["id"] for preset in task["presets"]}
