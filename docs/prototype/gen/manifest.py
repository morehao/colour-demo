"""面板 / 实时适配器 / 任务 id 的单一来源。

构建脚本、前端与测试都从这里取清单，避免 HTML、gen、tests 三处各写一份导致漂移。
新增面板或任务时，改这里 + 对应的 gen 模块 + 附录 B 表格。
"""

from __future__ import annotations

# 29 个参考面板（00–28），顺序与导航一致
PANEL_IDS = [
    "overview",
    "convert",
    "chroma",
    "observers",
    "photometry",
    "delta-e",
    "gradient",
    "rgb-spaces",
    "transfer",
    "chromaticity",
    "gamut-volume",
    "temperature",
    "quality",
    "image-lut",
    "adaptation",
    "appearance",
    "phenomena-vision",
    "corresponding",
    "cvd",
    "recovery",
    "characterisation",
    "notation",
    "signals",
    "geometry",
    "optics",
    "gallery",
    "catalog",
    "invoke",
    "api",
]

# 有实时适配器（LIVE[...]）的面板；overview 只有静态内容
LIVE_PANEL_IDS = [panel_id for panel_id in PANEL_IDS if panel_id != "overview"]

# 6 个任务页
TASK_IDS = ["purity", "delta-e", "gradient", "cvd", "light", "notation"]

# 旧链接兼容：裸 hash `#<panel-id>` → 新路由
OLD_HASH_REDIRECTS = {panel_id: f"#/ref/{panel_id}" for panel_id in PANEL_IDS}

assert len(PANEL_IDS) == 29, "面板应为 29 个"
assert len(set(PANEL_IDS)) == 29, "面板 id 不能重复"
assert len(TASK_IDS) == 6, "任务应为 6 个"
