"""结论档位与文案模板：8 类规则。

渲染层只允许通过 `band_for()` / `render()` 取文案，**不得自己写死阈值或句子**。
`kind: band` 的末段 `lt` 必须为 None（兜底），保证任何取值都能落到一档。
"""

from __future__ import annotations

TONES = ("ok", "warn", "bad")

VERDICTS: dict[str, dict] = {
    "deltaE": {
        "kind": "band",
        "unit": "ΔE",
        "precision": 1,
        "bands": [
            {"lt": 1, "label": "几乎看不出", "tone": "ok", "say": "只有仪器能测出差别，肉眼分不出。"},
            {"lt": 2, "label": "仔细看能发现", "tone": "ok", "say": "并排看得出，日常可以当成同一个颜色。"},
            {"lt": 5, "label": "看得出来", "tone": "warn", "say": "并排比较明显，但还不至于认错。"},
            {"lt": 10, "label": "明显不同", "tone": "warn", "say": "一眼就是两个颜色。"},
            {"lt": None, "label": "完全不同", "tone": "bad", "say": "属于两个色系，不建议放在一起比较。"},
        ],
    },
    "purity": {
        "kind": "band",
        "unit": "%",
        "scale": 100,
        "precision": 0,
        "bands": [
            {"lt": 0.15, "label": "接近灰白", "tone": "ok", "say": "几乎看不出颜色，像带了一点色味的灰。"},
            {"lt": 0.35, "label": "偏柔和", "tone": "ok", "say": "有颜色，但很淡，适合当背景。"},
            {"lt": 0.60, "label": "明显有色", "tone": "warn", "say": "颜色清楚，日常用色大多落在这里。"},
            {"lt": 0.80, "label": "鲜艳", "tone": "warn", "say": "很抢眼，适合做强调色。"},
            {"lt": None, "label": "非常鲜艳", "tone": "bad", "say": "已经接近单色光，面积一大容易刺眼。"},
        ],
    },
    "uniformity": {
        "kind": "band",
        "unit": "×",
        "precision": 2,
        "bands": [
            {"lt": 1.5, "label": "均匀", "tone": "ok", "say": "每一步的间隔差不多，过渡看不出接缝。"},
            {"lt": 2.5, "label": "轻微不均", "tone": "warn", "say": "中间会有一小段显得挤，细看能发现。"},
            {"lt": None, "label": "明显不均", "tone": "bad", "say": "中间被压扁了，看起来会发灰或发脏。"},
        ],
    },
    "cvd": {
        "kind": "band",
        "unit": "ΔE",
        "precision": 1,
        "bands": [
            {"lt": 3, "label": "几乎分不清", "tone": "bad", "say": "这两个颜色会糊在一起，建议换掉其中一个。"},
            {"lt": 6, "label": "勉强能分", "tone": "warn", "say": "仔细看能分开，但快速浏览时容易混。"},
            {"lt": 10, "label": "能分清", "tone": "ok", "say": "一般情况下能区分。"},
            {"lt": None, "label": "很容易分清", "tone": "ok", "say": "差别很明显，不用担心。"},
        ],
    },
    # 色适应前后也用 ΔE 判定，不重复维护阈值
    "shift": {"extends": "deltaE"},
    "temperature": {
        "kind": "band",
        "unit": "K",
        "precision": 0,
        "bands": [
            {"lt": 3300, "label": "暖黄", "tone": "warn", "say": "像白炽灯或烛光，偏黄偏暖。"},
            {"lt": 5300, "label": "中性", "tone": "ok", "say": "不冷不暖，接近日常室内白光。"},
            {"lt": 7000, "label": "日光", "tone": "ok", "say": "接近正午日光，D65 就在这一段。"},
            {"lt": None, "label": "偏冷", "tone": "warn", "say": "偏蓝，常见于阴天或冷白 LED。"},
        ],
    },
    "translate": {
        "kind": "custom",
        "template": "{input} 就是 {hex}；Lab 是 {lab}；Munsell 记作 {munsell}。",
    },
    "quality": {
        "kind": "custom",
        "template": "Ra {ra}、Qa {qa}、Rf {rf}、Rg {rg}——四个口径不完全一致，别只看 Ra。",
    },
}


def resolve(rule_id: str) -> dict:
    """解析 `extends`，返回完整规则。"""
    if rule_id not in VERDICTS:
        raise KeyError(f"未知结论规则 {rule_id!r}，可选：{sorted(VERDICTS)}")
    rule = VERDICTS[rule_id]
    if "extends" not in rule:
        return rule
    base = resolve(rule["extends"])
    merged = dict(base)
    merged.update({key: value for key, value in rule.items() if key != "extends"})
    return merged


def band_for(rule_id: str, value: float) -> dict:
    """按取值返回命中的档位；`kind != band` 时抛错。"""
    rule = resolve(rule_id)
    if rule.get("kind") != "band":
        raise ValueError(f"{rule_id} 不是档位规则（kind={rule.get('kind')}）")
    for band in rule["bands"]:
        limit = band["lt"]
        if limit is None or value < limit:
            return band
    raise AssertionError(f"{rule_id} 的档位没有兜底项")


def render(rule_id: str, **context) -> str:
    """渲染 custom 模板；band 规则请用 `band_for()` 取 label/say。"""
    rule = resolve(rule_id)
    if rule.get("kind") != "custom":
        raise ValueError(f"{rule_id} 不是模板规则（kind={rule.get('kind')}）")
    return rule["template"].format(**context)


if __name__ == "__main__":
    # 自检：单调性与兜底
    for name, rule in VERDICTS.items():
        full = resolve(name)
        if full.get("kind") != "band":
            continue
        limits = [band["lt"] for band in full["bands"]]
        assert limits[-1] is None, f"{name} 缺少兜底档"
        numbers = [value for value in limits if value is not None]
        assert numbers == sorted(numbers), f"{name} 档位未递增"
        for band in full["bands"]:
            assert band["tone"] in TONES, f"{name} tone 非法：{band['tone']}"
    print("verdicts ok:", ", ".join(sorted(VERDICTS)))
