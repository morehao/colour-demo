#!/usr/bin/env python3
"""生成 docs/prototype/index.html —— 覆盖 colour 0.4.7 全部公开能力的静态原型。

低内存构建：分三批、每批一个进程、每个面板结束立即释放 matplotlib 资源，
并做峰值内存守卫（超过阈值主动退出，不让机器进入 swap 挤压）。
页面里的每个数字、色值、图表都由 colour-science 0.4.7 真实计算。

用法：
    python docs/prototype/build_prototype.py --batch 1
    python docs/prototype/build_prototype.py --batch 2
    python docs/prototype/build_prototype.py --batch 3
    python docs/prototype/build_prototype.py --panel notation   # 单跑 19–25 中的一个
    python docs/prototype/build_prototype.py --tasks    # 6 任务 × 3 预设快照
    python docs/prototype/build_prototype.py --merge
    python docs/prototype/build_prototype.py --merge --strict   # 发布门禁
"""

from __future__ import annotations

import argparse
import gc
import json
import os
import resource
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = HERE.parents[1] / ".tmp" / "panels"
CACHE.mkdir(parents=True, exist_ok=True)

# UI 源码按固定顺序拼接；禁止 import/export，禁止出现 </script>
UI_FILES = [
    "core.js",
    "glossary.js",
    "blocks.js",
    "charts.js",
    "components.js",
    "adapters.js",
    "adapters-late.js",
    "live.js",
    "panels.js",
    "tasks.js",
    "app.js",
]
os.environ.setdefault("MPLCONFIGDIR", str(HERE.parents[1] / ".tmp" / "mpl"))
os.makedirs(os.environ["MPLCONFIGDIR"], exist_ok=True)

import matplotlib  # noqa: E402

matplotlib.use("Agg")

import numpy as np  # noqa: E402

import colour  # noqa: E402

MEMORY_LIMIT_MB = int(os.environ.get("BUILD_MEMORY_LIMIT_MB", "700"))


def peak_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024 / 1024


def guard(stage: str) -> None:
    used = peak_mb()
    if used > MEMORY_LIMIT_MB:
        print(f"[guard] 峰值 {used:.0f} MB 超过上限 {MEMORY_LIMIT_MB} MB（阶段：{stage}），主动退出。", file=sys.stderr)
        raise SystemExit(3)


def run_panels(factories) -> list[dict]:
    panels = []
    for name, factory in factories:
        started = time.perf_counter()
        panel = factory()
        json.dumps(panel, ensure_ascii=False)  # 提前暴露不可序列化的问题
        panels.append(panel)
        import matplotlib.pyplot as plt

        plt.close("all")
        gc.collect()
        print(
            f"  {name:14s} {time.perf_counter() - started:5.2f}s  peak={peak_mb():6.0f} MB",
            flush=True,
        )
        guard(name)
    return panels


def batch1() -> list[dict]:
    from gen import panels_core as core
    from gen.catalog import build_catalog

    catalog = build_catalog()
    summary = {
        "version": catalog["version"],
        "submodules": len(catalog["modules"]),
        "names": catalog["total"],
        "top_level": catalog.get("top_level_names", 0),
        "callables": len([n for n in dir(colour) if not n.startswith("_") and callable(getattr(colour, n))]),
        "spaces": len(colour.RGB_COLOURSPACES),
    }
    return run_panels(
        [
            ("overview", lambda: core.panel_overview(summary)),
            ("convert", core.panel_convert),
            ("chroma", core.panel_chroma),
            ("observers", core.panel_observers),
            ("photometry", core.panel_photometry),
            ("delta-e", core.panel_delta_e),
            ("gradient", core.panel_gradient),
            ("rgb-spaces", core.panel_rgb_spaces),
            ("transfer", core.panel_transfer),
        ]
    )


def batch2() -> list[dict]:
    from gen import panels_visual as vis

    return run_panels(
        [
            ("chromaticity", vis.panel_chromaticity),
            ("gamut-volume", vis.panel_gamut_volume),
            ("temperature", vis.panel_temperature),
            ("quality", vis.panel_quality),
            ("image-lut", vis.panel_image_lut),
            ("adaptation", vis.panel_adaptation),
            ("appearance", vis.panel_appearance),
            ("phenomena", vis.panel_phenomena_vision),
            ("corresponding", vis.panel_corresponding),
            ("cvd", vis.panel_cvd),
        ]
    )


def batch3() -> tuple[list[dict], dict]:
    from gen import panels_engineering as eng
    from gen import panels_meta as meta
    from gen.catalog import build_catalog

    catalog = build_catalog()
    panels = run_panels(
        [
            ("recovery", eng.panel_recovery),
            ("characterisation", eng.panel_characterisation),
            ("notation", eng.panel_notation),
            ("signals", eng.panel_signals),
            ("geometry", eng.panel_geometry),
            ("optics", eng.panel_optics),
            ("gallery", eng.panel_gallery),
            ("catalog", lambda: meta.panel_catalog(catalog)),
            ("invoke", meta.panel_invoke),
            ("api", meta.panel_api),
        ]
    )
    summary = {
        "total": catalog["total"],
        "counts": catalog["counts"],
        "coverage": catalog["coverage"],
        "modules": catalog["modules"],
        "panel_titles": catalog["panel_titles"],
    }
    return panels, summary


def save(name: str, payload) -> None:
    target = CACHE / f"{name}.json"
    target.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    print(f"  -> {target.relative_to(HERE.parents[1])} ({target.stat().st_size / 1024:.0f} KB)")


BATCH3_PANELS = {
    "recovery": "19",
    "characterisation": "20",
    "notation": "21",
    "signals": "22",
    "geometry": "23",
    "optics": "24",
    "gallery": "25",
}


def run_single_panel(name: str) -> None:
    """单跑一个面板：一个进程只跑一个，结果并入 b3.json（可反复执行逐个累积）。

    swap=0 的机器上，这是 19–25 的安全跑法：峰值 = 单个面板 + 解释器基线，
    不会像 `--batch 3` 那样七个面板连在一个进程里越跑越高。
    """
    from gen import panels_engineering as eng

    factory = getattr(eng, f"panel_{name}", None)
    if factory is None:
        raise SystemExit(f"找不到 gen.panels_engineering.panel_{name}")
    panels = run_panels([(name, factory)])

    path = CACHE / "b3.json"
    existing = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"panels": []}
    panel = panels[0]
    kept = [p for p in existing.get("panels", []) if p["id"] != panel["id"]]
    kept.append(panel)
    existing["panels"] = sorted(kept, key=lambda p: p["no"])
    save("b3", existing)
    have = [p["no"] for p in existing["panels"]]
    print(f"  b3 现有面板: {', '.join(have)}（{len(have)}/{len(BATCH3_PANELS)}）")


# --------------------------------------------------------------------------- #
# 任务快照（6 任务 × 3 预设），直接复用服务端 core，保证与在线结果同源
# --------------------------------------------------------------------------- #
def _notation_call(value: str) -> dict:
    from colour_demo.core.notation import notation_data

    text = str(value).strip()
    if text.startswith("#") or text.lower().startswith(("rgb(", "hsl(")):
        return notation_data(hex_value=text)
    if "/" in text:
        return notation_data(munsell=text)
    return notation_data(keyword=text)


def _task_call(task_id: str, state: dict) -> dict:
    if task_id == "purity":
        from colour_demo.core.chroma import chroma_data

        return chroma_data(state["colors"], illuminant=state.get("illuminant", "D65"))
    if task_id == "delta-e":
        from colour_demo.core.delta_e import delta_e_matrix

        return delta_e_matrix(state["colors"], method=state.get("method", "CIE 2000"))
    if task_id == "gradient":
        from colour_demo.core.gradient import gradient_data

        return gradient_data(
            state["from"],
            state["to"],
            space=state.get("space", "Oklab"),
            steps=int(state.get("steps", 11)),
        )
    if task_id == "cvd":
        from colour_demo.core.cvd import cvd_data

        return cvd_data(state["colors"], deficiency=state.get("deficiency", "Deuteranomaly"))
    if task_id == "light":
        from colour_demo.core.adapt import adapt_data

        return adapt_data(
            state["colors"],
            source=state.get("source", "A"),
            target=state.get("target", "D65"),
            include_matrices=False,
        )
    if task_id == "notation":
        return _notation_call(state["value"])
    raise SystemExit(f"未知任务 {task_id!r}")


def build_tasks() -> None:
    from gen.tasks import TASKS

    built = []
    for task in TASKS:
        item = json.loads(json.dumps(task, ensure_ascii=False))
        item["snapshots"] = {}
        for preset in task["presets"]:
            started = time.perf_counter()
            try:
                item["snapshots"][preset["id"]] = _task_call(task["id"], preset["state"])
            except Exception as error:  # noqa: BLE001 - 构建期要把上下文带出来
                raise SystemExit(
                    f"任务 {task['id']} 预设 {preset['id']} 计算失败：{error}"
                ) from error
            print(
                f"  {task['id']:10s}/{preset['id']:12s} {time.perf_counter() - started:5.2f}s",
                flush=True,
            )
        built.append(item)

    payload = {"tasks": built}
    # 任务快照要进前端 JSON.parse：NaN/Infinity 不是合法 JSON，构建期就拦住
    text = json.dumps(payload, ensure_ascii=False, allow_nan=False)
    target = CACHE / "tasks.json"
    target.write_text(text, encoding="utf-8")
    print(f"  -> {target.relative_to(HERE.parents[1])} ({target.stat().st_size / 1024:.0f} KB)")


# --------------------------------------------------------------------------- #
# 门禁：开发期文案只警告，发布期 --strict 全失败
# --------------------------------------------------------------------------- #
def _validate_glossary() -> list[str]:
    from gen.glossary import GLOSSARY
    from gen.manifest import PANEL_IDS

    errors: list[str] = []
    seen: dict[str, str] = {}
    for key, entry in GLOSSARY.items():
        for alias in entry.get("aliases", []):
            if alias in seen and seen[alias] != key:
                errors.append(f"术语别名重复：{alias!r} 同时属于 {seen[alias]} 和 {key}")
            seen[alias] = key
        see = entry.get("see")
        if see:
            panel_id = see.removeprefix("#/ref/")
            if panel_id not in PANEL_IDS:
                errors.append(f"术语 {key} 的 see 指向不存在的面板：{see}")
        if len(entry.get("plain", "")) > 80:
            errors.append(f"术语 {key} 的解释超过 80 字")
    return errors


def _validate_verdicts() -> list[str]:
    from gen.verdicts import TONES, VERDICTS, resolve

    errors: list[str] = []
    for key in VERDICTS:
        rule = resolve(key)
        if rule.get("kind") != "band":
            continue
        limits = [band["lt"] for band in rule["bands"]]
        if limits[-1] is not None:
            errors.append(f"结论规则 {key} 缺兜底档（末项 lt 必须为 null）")
        numbers = [value for value in limits if value is not None]
        if numbers != sorted(numbers):
            errors.append(f"结论规则 {key} 的档位未递增")
        for band in rule["bands"]:
            if band.get("tone") not in TONES:
                errors.append(f"结论规则 {key} 的 tone 非法：{band.get('tone')}")
    return errors


def _validate_tasks(tasks: list[dict], *, require_snapshots: bool) -> list[str]:
    from gen.glossary import GLOSSARY
    from gen.manifest import LIVE_PANEL_IDS, PANEL_IDS, TASK_IDS
    from gen.verdicts import VERDICTS

    errors: list[str] = []
    ids = [task.get("id") for task in tasks]
    if ids != TASK_IDS:
        errors.append(f"任务 id/顺序与 manifest 不一致：{ids} != {TASK_IDS}")
    for task in tasks:
        label = f"任务 {task.get('id')}"
        if task.get("tool") not in PANEL_IDS:
            errors.append(f"{label} tool 不是面板：{task.get('tool')}")
        elif task["tool"] not in LIVE_PANEL_IDS:
            errors.append(f"{label} tool 没有实时适配器：{task['tool']}")
        if task.get("outcome") not in VERDICTS:
            errors.append(f"{label} outcome 不在 verdicts：{task.get('outcome')}")
        field_keys = {field["key"] for field in task.get("fields", [])}
        if not field_keys:
            errors.append(f"{label} 没有字段")
        if len(task.get("presets", [])) != 3:
            errors.append(f"{label} 预设必须 3 个")
        for preset in task.get("presets", []):
            if set(preset.get("state", {})) != field_keys:
                errors.append(f"{label} 预设 {preset.get('id')} 的 state 与字段不一致")
            if require_snapshots and preset.get("id") not in task.get("snapshots", {}):
                errors.append(f"{label} 缺预设 {preset.get('id')} 的快照")
        for panel_id in task.get("related", []):
            if panel_id not in PANEL_IDS:
                errors.append(f"{label} related 指向不存在的面板：{panel_id}")
        for term in task.get("jargon", []):
            if term not in GLOSSARY:
                errors.append(f"{label} jargon 指向不存在的术语：{term}")
    return errors


def run_gates(data: dict, *, strict: bool, html_bytes: int, ui_bytes: int = 0) -> None:
    from gen.copy_lint import validate_panel_copy
    from gen.glossary import GLOSSARY
    from gen.manifest import LIVE_PANEL_IDS, PANEL_IDS
    from gen.verdicts import VERDICTS

    errors: list[str] = []
    warnings: list[str] = []

    missing_copy: list[str] = []
    for panel in data["panels"]:
        fields = ("title_plain", "question", "plain", "why")
        if not any(panel.get(field) for field in fields):
            missing_copy.append(panel["no"])
            continue
        panel_errors, panel_warnings = validate_panel_copy(panel)
        errors.extend(panel_errors)
        warnings.extend(panel_warnings)
        if panel.get("verdict") and panel["verdict"] not in VERDICTS:
            errors.append(f"面板 {panel['no']} verdict 不存在：{panel['verdict']}")
        for term in panel.get("jargon") or []:
            if term not in GLOSSARY:
                errors.append(f"面板 {panel['no']} jargon 不存在：{term}")

    if missing_copy:
        warnings.append(
            f"新手文案未就绪：{len(missing_copy)}/{len(data['panels'])} 个面板"
            f"（示例：{', '.join(missing_copy[:5])}）"
        )

    no_presets = [
        panel["id"]
        for panel in data["panels"]
        if panel["id"] in LIVE_PANEL_IDS and len(panel.get("presets") or []) != 3
    ]
    if no_presets:
        warnings.append(
            f"实时面板预设未就绪：{len(no_presets)}/{len(LIVE_PANEL_IDS)}"
            f"（示例：{', '.join(no_presets[:5])}）"
        )

    errors.extend(_validate_glossary())
    errors.extend(_validate_verdicts())
    errors.extend(_validate_tasks(data["tasks"], require_snapshots=False))

    if data["routes"]["legacy"].keys() != set(PANEL_IDS):
        errors.append("旧链接重定向表没有覆盖全部面板")

    if html_bytes > 700 * 1024:
        errors.append(f"产物 {html_bytes / 1024:.0f} KB 超过 700 KB 预算")
    if ui_bytes > 120 * 1024:
        errors.append(f"UI 源码 {ui_bytes / 1024:.0f} KB 超过 120 KB 预算")

    for warning in warnings:
        print(f"[gate][warn] {warning}")
    for error in errors:
        print(f"[gate][error] {error}", file=sys.stderr)
    if errors or (strict and warnings):
        raise SystemExit(f"构建门禁失败：{len(errors)} 个错误、{len(warnings)} 个警告")
    print(f"[gate] ok（{len(warnings)} 个警告，strict={strict}）")


def merge(*, strict: bool, started: float) -> None:
    from gen.glossary import GLOSSARY
    from gen.manifest import OLD_HASH_REDIRECTS
    from gen.tasks import TASKS
    from gen.verdicts import VERDICTS
    from gen.manifest_tail import stub_panels

    panels = (
        json.loads((CACHE / "b1.json").read_text(encoding="utf-8"))
        + json.loads((CACHE / "b2.json").read_text(encoding="utf-8"))
    )
    meta = json.loads((CACHE / "meta.json").read_text(encoding="utf-8"))
    panels += meta["panels"]

    # batch 3（19–25）按面板逐次补齐：b3.json 存在就并入，缺的面板继续走占位
    b3_path = CACHE / "b3.json"
    if b3_path.exists():
        b3 = json.loads(b3_path.read_text(encoding="utf-8"))
        panels += b3["panels"]
        print(f"  b3: 并入 {len(b3['panels'])} 个面板（{', '.join(p['no'] for p in b3['panels'])}）")

    # 19–25 尚无数据：以占位面板进入导航（明确标注「数据待补充」）
    have = {p["no"] for p in panels}
    for stub in stub_panels():
        if stub["no"] not in have:
            panels.append(stub)
    panels.sort(key=lambda p: p["no"])
    catalog = meta["catalog"]

    ids = [p["id"] for p in panels]
    assert len(ids) == len(set(ids)), "面板 id 重复"
    nums = {p["no"] for p in panels}
    missing = sorted(set(catalog["panel_titles"]) - nums)
    assert not missing, f"能力目录引用了不存在的面板编号：{missing}"
    unmapped = [m for m in catalog["modules"] if m["panel"] != "内部" and m["panel"] not in nums]
    assert not unmapped, f"子模块指向不存在的面板：{unmapped}"

    groups: list[str] = []
    for panel in panels:
        if panel["group"] not in groups:
            groups.append(panel["group"])

    # 任务快照：先跑 --tasks 才有；缺失时前端离线任务页会提示，不阻断构建
    tasks_path = CACHE / "tasks.json"
    if tasks_path.exists():
        tasks = json.loads(tasks_path.read_text(encoding="utf-8"))["tasks"]
        snapshot_errors = _validate_tasks(tasks, require_snapshots=True)
        if snapshot_errors:
            for error in snapshot_errors:
                print(f"[gate][error] {error}", file=sys.stderr)
            raise SystemExit("任务快照不完整，重新跑 --tasks")
        print(f"  tasks: 并入 {len(tasks)} 个任务、{sum(len(t['snapshots']) for t in tasks)} 组快照")
    else:
        tasks = [{**task, "snapshots": {}} for task in TASKS]
        print("  tasks: 无快照（先跑 --tasks）；离线任务页将不可用")

    data = {
        "lib": {
            "version": colour.__version__,
            "numpy": np.__version__,
            "matplotlib": matplotlib.__version__,
            "python": "3.13",
        },
        "groups": groups,
        "panels": panels,
        "catalog": catalog,
        "stats": {
            "ready": len([p for p in panels if not p.get("pending")]),
            "pending": len([p for p in panels if p.get("pending")]),
        },
        # 新手层（文案/术语/阈值/任务）；旧渲染器忽略这些键
        "tasks": tasks,
        "glossary": GLOSSARY,
        "verdicts": VERDICTS,
        "routes": {"legacy": OLD_HASH_REDIRECTS},
        "ui": {"schema": 2},
    }
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    template = (HERE / "index.template.html").read_text(encoding="utf-8")
    ui_parts = []
    for name in UI_FILES:
        path = HERE / "ui" / name
        if not path.exists():
            raise SystemExit(f"缺少 UI 源文件：{path}")
        source = path.read_text(encoding="utf-8")
        if "</script>" in source:
            raise SystemExit(f"{name} 含 </script>，拼接后会截断页面")
        lines = len(source.splitlines())
        if lines > 400:
            raise SystemExit(f"{name} 有 {lines} 行，超过 400 行上限，请继续拆分")
        ui_parts.append(source)
    ui = "\n\n".join(ui_parts)
    html = template.replace("/*__UI__*/", ui).replace("/*__DATA__*/", payload)
    ui_bytes = len(ui.encode())

    run_gates(data, strict=strict, html_bytes=len(html.encode()), ui_bytes=ui_bytes)
    (HERE / "index.html").write_text(html, encoding="utf-8")
    size_kb = (HERE / "index.html").stat().st_size / 1024
    print(
        f"merged {len(panels)} panels ({data['stats']['ready']} ready / {data['stats']['pending']} pending), "
        f"{len(tasks)} tasks -> index.html ({size_kb:.0f} KB, data {len(payload) / 1024:.0f} KB, "
        f"{time.perf_counter() - started:.1f}s)"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", choices=["1", "2", "3"], help="分批构建")
    parser.add_argument(
        "--panel",
        choices=sorted(BATCH3_PANELS),
        help="单跑一个 19–25 面板并并入 b3.json（低内存，可逐个累积）",
    )
    parser.add_argument("--tasks", action="store_true", help="构建 6 个任务的预设快照（复用 core）")
    parser.add_argument("--merge", action="store_true", help="合并各批并写 index.html")
    parser.add_argument("--strict", action="store_true", help="文案门禁按发布标准（警告即失败）")
    args = parser.parse_args()

    started = time.perf_counter()
    if args.panel:
        run_single_panel(args.panel)
    elif args.batch == "1":
        save("b1", batch1())
    elif args.batch == "2":
        save("b2", batch2())
    elif args.batch == "3":
        panels, summary = batch3()
        save("b3", {"panels": panels, "catalog": summary})
    elif args.tasks:
        build_tasks()
    elif args.merge:
        merge(strict=args.strict, started=started)
    else:
        parser.error("需要 --batch 1|2|3 / --panel / --tasks / --merge")


if __name__ == "__main__":
    main()
