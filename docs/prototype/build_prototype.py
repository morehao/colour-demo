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
    python docs/prototype/build_prototype.py --merge
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", choices=["1", "2", "3"], help="分批构建")
    parser.add_argument(
        "--panel",
        choices=sorted(BATCH3_PANELS),
        help="单跑一个 19–25 面板并并入 b3.json（低内存，可逐个累积）",
    )
    parser.add_argument("--merge", action="store_true", help="合并各批并写 index.html")
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
    elif args.merge:
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
        }
        payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        template = (HERE / "index.template.html").read_text(encoding="utf-8")
        (HERE / "index.html").write_text(template.replace("/*__DATA__*/", payload), encoding="utf-8")
        size_kb = (HERE / "index.html").stat().st_size / 1024
        print(
            f"merged {len(panels)} panels ({data['stats']['ready']} ready / {data['stats']['pending']} pending) "
            f"-> index.html ({size_kb:.0f} KB, data {len(payload) / 1024:.0f} KB, {time.perf_counter() - started:.1f}s)"
        )
    else:
        parser.error("需要 --batch 1|2|3 或 --merge")


if __name__ == "__main__":
    main()
