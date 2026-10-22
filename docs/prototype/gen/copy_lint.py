"""新手文案 lint：禁用词、长度、问句。

纯标准库，构建脚本与测试共用；不导入 colour / matplotlib，保证 CI 里跑得飞快。
"""

from __future__ import annotations

# 新手可见区域出现即失败：这些词默认读者是同行
HARD_FORBIDDEN = (
    "子模块",
    "导出",
    "端点",
    "覆盖率",
    "归一化",
    "判据",
    "可逆",
    "往返误差",
    "JSON",
    "API",
    "参数化",
)

# 出现时只提醒：术语本身可能无法回避，但应尽量放进原理折叠区
WARN_FORBIDDEN = ("矩阵", "插值", "观察者", "白点", "传递函数", "色度学")

# 字数上限（按字符数）
LIMITS = {
    "title_plain": 20,
    "question": 30,
    "plain": 80,
    "why": 50,
}

PANEL_COPY_FIELDS = ("title_plain", "question", "plain", "why")


def lint_text(value: str, *, max_len: int | None = None, question: bool = False) -> list[str]:
    """返回问题列表；空列表表示通过。"""
    problems: list[str] = []
    text = (value or "").strip()
    if not text:
        return ["为空"]
    if max_len is not None and len(text) > max_len:
        problems.append(f"长度 {len(text)} 超过 {max_len}")
    if question and not text.endswith(("？", "?")):
        problems.append("不是问句（应以 ？ 结尾）")
    for word in HARD_FORBIDDEN:
        if word in text:
            problems.append(f"含禁用词「{word}」")
    return problems


def lint_warnings(value: str) -> list[str]:
    text = (value or "").strip()
    return [f"含专业词「{word}」" for word in WARN_FORBIDDEN if word in text]


def validate_panel_copy(panel: dict) -> tuple[list[str], list[str]]:
    """校验单个面板的新手文案字段，返回 (errors, warnings)。"""
    errors: list[str] = []
    warnings: list[str] = []
    label = f"面板 {panel.get('no', '?')}（{panel.get('id', '?')}）"

    for field in PANEL_COPY_FIELDS:
        value = panel.get(field, "")
        for problem in lint_text(
            value,
            max_len=LIMITS[field],
            question=(field == "question"),
        ):
            errors.append(f"{label} {field}：{problem}")
        warnings.extend(f"{label} {field}：{item}" for item in lint_warnings(value))

    verdict = panel.get("verdict")
    if verdict and not isinstance(verdict, str):
        errors.append(f"{label} verdict 必须是字符串或 null")

    presets = panel.get("presets") or []
    if len(presets) not in (0, 3):
        errors.append(f"{label} presets 必须是 0 或 3 个，当前 {len(presets)}")
    for preset in presets:
        if not preset.get("id") or not preset.get("label") or not preset.get("state"):
            errors.append(f"{label} 预设缺 id/label/state：{preset!r}")

    return errors, warnings
