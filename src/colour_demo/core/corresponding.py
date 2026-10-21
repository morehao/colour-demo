"""面板 17：对应色与记忆色（`POST /api/v1/corresponding`）。

Breneman 1987 的经典实验给了 12 组“在 A 灯下看的颜色 ↔ 在 D65 下看是一样的”数据，
5 个模型分别去拟合它们。这里用 u′v′ 平面上的欧氏距离当误差，逐实验、逐模型回报。

注意：`experiment=9` 在 colour 0.4.7 里会让内部 `convert_experiment_results_Breneman1987`
抛 IndexError（该组数据缺亮度样本），所以 9 不在可用列表里，响应明确写清楚，不静默跳过。
"""

from __future__ import annotations

import numpy as np

import colour

from ..core.diagnostics import WarningCollector, number, numbers
from ..core.errors import value_error

# 4/6/8/11/12 都可跑；9 见模块文档（0.4.7 缺样本，predict 内部 IndexError）
EXPERIMENTS = (1, 2, 3, 4, 6, 8, 11, 12)
UNAVAILABLE_EXPERIMENTS = {9: "colour 0.4.7 的 Breneman 实验 9 缺少亮度样本，预测函数内部 IndexError"}
# 只留规范写法（colour 里另有一个 'vonkries' 小写别名；CMCCAT2000 没有空格，别用空格判断）
MODELS = tuple(
    name for name in colour.corresponding.CORRESPONDING_CHROMATICITIES_PREDICTION_MODELS if name[0].isupper()
)


def _predictions(experiment: int, model: str):
    return colour.corresponding.corresponding_chromaticities_prediction(
        experiment=experiment, model=model
    )


def _uv_error(prediction) -> float | None:
    predicted = np.asarray(prediction.uv_p, dtype=float)
    target = np.asarray(prediction.uv_t, dtype=float)
    if predicted.shape != target.shape:
        return None
    value = float(np.linalg.norm(predicted - target))
    return value if np.isfinite(value) else None


def corresponding_data(
    experiment: int = 1,
    models: list[str] | None = None,
    include_leaderboard: bool = True,
) -> dict:
    if experiment not in EXPERIMENTS:
        if experiment in UNAVAILABLE_EXPERIMENTS:
            raise value_error(f"实验 {experiment} 不可用：{UNAVAILABLE_EXPERIMENTS[experiment]}")
        raise value_error(f"实验可选：{list(EXPERIMENTS)}")

    names = list(models or MODELS)
    unknown = [name for name in names if name not in MODELS]
    if unknown:
        raise value_error(f"未知模型 {unknown}，可选：{list(MODELS)}")

    with WarningCollector() as log:
        rows = []
        for model in names:
            try:
                predictions = _predictions(experiment, model)
            except Exception as error:
                rows.append({"model": model, "error": f"{type(error).__name__}: {error}"})
                log.add("unavailable", f"实验 {experiment} 的 {model} 预测失败：{type(error).__name__}")
                continue

            samples = []
            errors = []
            for prediction in predictions:
                error = _uv_error(prediction)
                if error is not None:
                    errors.append(error)
                samples.append(
                    {
                        "uv_m": numbers(prediction.uv_m, 6),
                        "uv_t": numbers(prediction.uv_t, 6),
                        "uv_p": numbers(prediction.uv_p, 6),
                        "distance": round(error, 6) if error is not None else None,
                    }
                )
            rows.append(
                {
                    "model": model,
                    "mean_uv_error": round(float(np.mean(errors)), 6) if errors else None,
                    "max_uv_error": round(float(np.max(errors)), 6) if errors else None,
                    "samples": samples,
                }
            )

        leaderboard = []
        if include_leaderboard:
            for model in names:
                per_experiment = []
                for candidate in EXPERIMENTS:
                    try:
                        errors = [
                            error
                            for error in (
                                _uv_error(prediction) for prediction in _predictions(candidate, model)
                            )
                            if error is not None
                        ]
                    except Exception as error:
                        log.add(
                            "unavailable",
                            f"实验 {candidate} 的 {model} 预测失败：{type(error).__name__}",
                        )
                        continue
                    if errors:
                        per_experiment.append(float(np.mean(errors)))
                leaderboard.append(
                    {
                        "model": model,
                        "experiments": len(per_experiment),
                        "mean_uv_error": round(float(np.mean(per_experiment)), 6)
                        if per_experiment
                        else None,
                    }
                )
            leaderboard.sort(key=lambda row: (row["mean_uv_error"] is None, row["mean_uv_error"] or 0.0))

        log.add(
            "note",
            "误差是 u′v′ 平面上的欧氏距离，只反映“预测点离实测终点多远”，"
            "不代表模型在其它观察条件下的表现；不同实验的观察者与参考白都不同，跨实验平均仅作横向粗比。",
        )

    return {
        "experiment": experiment,
        "available_experiments": list(EXPERIMENTS),
        "unavailable_experiments": [
            {"experiment": key, "reason": value} for key, value in UNAVAILABLE_EXPERIMENTS.items()
        ],
        "models": list(MODELS),
        "rows": rows,
        "leaderboard": leaderboard,
        "warnings": log.payload,
    }
