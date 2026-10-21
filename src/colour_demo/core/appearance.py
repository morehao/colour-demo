"""面板 15：外观模型（`POST /api/v1/appearance`）。

12 个模型对同一个 XYZ 给出不同的 J/C/h/M/H——因为它们对“观察者状态”的假设不同。
两个域陷阱（方案 7.2）：

- CAM16 / CIECAM02 / CIECAM16 / Hellwig 2022 / Hunt / RLAB / LLAB / Kim 2009 /
  Nayatani 95 / ATD 95 / sCAM 用 **0–100** 域（`Domain100`）；
- ZCAM 用 **0–1** 域。传错不会报错，只会静默偏差，所以每个模型在表里都标了 `scale`。

另外：Hunt 不给 `CCT_w` / `L_AS` 会直接 ValueError（原型里那行“不可用”就是这个），
这里显式给 `CCT_w=6500`，并把 colour 因缺参发出的近似告警原样回传。
"""

from __future__ import annotations

import numpy as np

import colour

from ..config import CAM16_L_A, MAX_COLOURS
from ..core.diagnostics import WarningCollector, number
from ..core.errors import value_error
from ..core.parsing import parse_colours, rgb_to_hex

OBSERVER = "CIE 1931 2 Degree Standard Observer"
XYZ_W = np.asarray(colour.xy_to_XYZ(colour.CCS_ILLUMINANTS[OBSERVER]["D65"]), dtype=float)
SURROUNDS = ("Average", "Dim", "Dark")
# Hunt 的环绕条件表用的是自己的命名，不能直接拿 "Average" 去查
HUNT_SURROUNDS = {
    "Average": "Normal Scenes",
    "Dim": "Television & CRT, Dim Surrounds",
    "Dark": "Projected Transparencies, Dark Surrounds",
}
MAX_MODELS = 12

MODELS: dict[str, dict] = {}


def _register(name: str, *, conditions: str, scale: float, forward, inverse=None) -> None:
    MODELS[name] = {"conditions": conditions, "scale": scale, "forward": forward, "inverse": inverse}


def _register_all() -> None:
    a = colour.appearance

    _register(
        "CAM16",
        conditions="XYZ_w / L_A / Y_b（0–100 域）",
        scale=100,
        forward=lambda xyz, p: colour.XYZ_to_CAM16(
            xyz, XYZ_w=XYZ_W * 100, L_A=p["L_A"], Y_b=p["Y_b"], surround=a.VIEWING_CONDITIONS_CAM16[p["surround"]]
        ),
        inverse=lambda spec, p: colour.CAM16_to_XYZ(
            spec, XYZ_w=XYZ_W * 100, L_A=p["L_A"], Y_b=p["Y_b"], surround=a.VIEWING_CONDITIONS_CAM16[p["surround"]]
        ),
    )
    _register(
        "CIECAM02",
        conditions="XYZ_w / L_A / Y_b（0–100 域）",
        scale=100,
        forward=lambda xyz, p: colour.XYZ_to_CIECAM02(
            xyz, XYZ_w=XYZ_W * 100, L_A=p["L_A"], Y_b=p["Y_b"], surround=a.VIEWING_CONDITIONS_CIECAM02[p["surround"]]
        ),
        inverse=lambda spec, p: colour.CIECAM02_to_XYZ(
            spec, XYZ_w=XYZ_W * 100, L_A=p["L_A"], Y_b=p["Y_b"], surround=a.VIEWING_CONDITIONS_CIECAM02[p["surround"]]
        ),
    )
    _register(
        "CIECAM16",
        conditions="XYZ_w / L_A / Y_b（0–100 域）",
        scale=100,
        forward=lambda xyz, p: colour.XYZ_to_CIECAM16(
            xyz, XYZ_w=XYZ_W * 100, L_A=p["L_A"], Y_b=p["Y_b"], surround=a.VIEWING_CONDITIONS_CIECAM16[p["surround"]]
        ),
        inverse=lambda spec, p: colour.CIECAM16_to_XYZ(
            spec, XYZ_w=XYZ_W * 100, L_A=p["L_A"], Y_b=p["Y_b"], surround=a.VIEWING_CONDITIONS_CIECAM16[p["surround"]]
        ),
    )
    _register(
        "Hellwig 2022",
        conditions="XYZ_w / L_A / Y_b（0–100 域）",
        scale=100,
        forward=lambda xyz, p: colour.XYZ_to_Hellwig2022(
            xyz,
            XYZ_w=XYZ_W * 100,
            L_A=p["L_A"],
            Y_b=p["Y_b"],
            surround=a.VIEWING_CONDITIONS_HELLWIG2022[p["surround"]],
        ),
        inverse=lambda spec, p: colour.Hellwig2022_to_XYZ(
            spec,
            XYZ_w=XYZ_W * 100,
            L_A=p["L_A"],
            Y_b=p["Y_b"],
            surround=a.VIEWING_CONDITIONS_HELLWIG2022[p["surround"]],
        ),
    )
    _register(
        "ZCAM",
        conditions="XYZ_w / L_A / Y_b（0–1 域，唯一的例外）",
        scale=1,
        forward=lambda xyz, p: colour.XYZ_to_ZCAM(
            xyz, XYZ_w=XYZ_W, L_A=p["L_A"], Y_b=p["Y_b"], surround=a.VIEWING_CONDITIONS_ZCAM[p["surround"]]
        ),
        inverse=lambda spec, p: colour.ZCAM_to_XYZ(
            spec, XYZ_w=XYZ_W, L_A=p["L_A"], Y_b=p["Y_b"], surround=a.VIEWING_CONDITIONS_ZCAM[p["surround"]]
        ),
    )
    _register(
        "Hunt",
        conditions="XYZ_w / XYZ_b / L_A / CCT_w（0–100 域）",
        scale=100,
        forward=lambda xyz, p: colour.XYZ_to_Hunt(
            xyz,
            XYZ_w=XYZ_W * 100,
            XYZ_b=XYZ_W * 100 * 0.2,
            L_A=p["L_A"],
            CCT_w=6500.0,
            surround=a.VIEWING_CONDITIONS_HUNT[HUNT_SURROUNDS[p["surround"]]],
        ),
        # 0.4.7 没有 Hunt_to_XYZ：该模型只给了正变换，往返无法闭合
        inverse=None,
    )
    _register(
        "RLAB",
        conditions="XYZ_n / Y_n（无适应度参数，0–100 域）",
        scale=100,
        # 0.4.7 没有 RLAB_to_XYZ
        forward=lambda xyz, p: colour.XYZ_to_RLAB(xyz, XYZ_n=XYZ_W * 100, Y_n=p["Y_b"]),
        inverse=None,
    )
    _register(
        "LLAB",
        conditions="XYZ_0 / Y_b / L（0–100 域）",
        scale=100,
        # 0.4.7 没有 LLAB_to_XYZ
        forward=lambda xyz, p: colour.XYZ_to_LLAB(xyz, XYZ_0=XYZ_W * 100, Y_b=p["Y_b"], L=318.31),
        inverse=None,
    )
    _register(
        "Kim 2009",
        conditions="XYZ_w / L_A（含媒体参数，0–100 域）",
        scale=100,
        forward=lambda xyz, p: colour.XYZ_to_Kim2009(xyz, XYZ_w=XYZ_W * 100, L_A=p["L_A"]),
        inverse=lambda spec, p: colour.Kim2009_to_XYZ(spec, XYZ_w=XYZ_W * 100, L_A=p["L_A"]),
    )
    _register(
        "Nayatani 95",
        conditions="XYZ_n / Y_o / E_o / E_or（0–100 域）",
        scale=100,
        forward=lambda xyz, p: colour.XYZ_to_Nayatani95(
            xyz, XYZ_n=XYZ_W * 100, Y_o=p["Y_b"], E_o=5000.0, E_or=1000.0
        ),
        # 0.4.7 没有 Nayatani95_to_XYZ
        inverse=None,
    )
    _register(
        "ATD 95",
        conditions="XYZ_0 / Y_0 / k₁ / k₂（0–100 域，无 J）",
        scale=100,
        forward=lambda xyz, p: colour.XYZ_to_ATD95(
            xyz, XYZ_0=XYZ_W * 100, Y_0=p["Y_b"], k_1=0.0, k_2=50.0
        ),
        # 0.4.7 没有 ATD95_to_XYZ
        inverse=None,
    )
    _register(
        "sCAM",
        conditions="XYZ_w / L_A / Y_b（0–100 域）",
        scale=100,
        # 0.4.7 没有 VIEWING_CONDITIONS_sCAM 表，环绕条件用函数默认值
        forward=lambda xyz, p: colour.XYZ_to_sCAM(xyz, XYZ_w=XYZ_W * 100, L_A=p["L_A"], Y_b=p["Y_b"]),
        inverse=lambda spec, p: colour.sCAM_to_XYZ(spec, XYZ_w=XYZ_W * 100, L_A=p["L_A"], Y_b=p["Y_b"]),
    )


_register_all()


def appearance_data(
    colours: list[str],
    models: list[str] | None = None,
    L_A: float | None = None,
    Y_b: float = 20.0,
    surround: str = "Average",
) -> dict:
    if len(colours) > MAX_COLOURS:
        raise value_error(f"colors 最多 {MAX_COLOURS} 个，当前 {len(colours)} 个")

    names = list(models or list(MODELS))
    unknown = [name for name in names if name not in MODELS]
    if unknown:
        raise value_error(f"未知外观模型 {unknown}，可选：{list(MODELS)}")
    if len(names) > MAX_MODELS:
        raise value_error(f"模型最多 {MAX_MODELS} 个")

    luminance = CAM16_L_A if L_A is None else float(L_A)
    if not (0.01 <= luminance <= 10000):
        raise value_error("L_A 需在 0.01–10000 cd·m⁻²")
    if not (0.01 <= Y_b <= 100):
        raise value_error("Y_b 需在 0.01–100")
    if surround not in SURROUNDS:
        raise value_error(f"surround 可选：{list(SURROUNDS)}")

    params = {"L_A": luminance, "Y_b": float(Y_b), "surround": surround}

    with WarningCollector(limit=12) as log:
        rows = []
        for spec, rgb in zip(colours, parse_colours(colours)):
            xyz = np.asarray(colour.sRGB_to_XYZ(rgb), dtype=float)
            results = {}
            for name in names:
                entry = MODELS[name]
                try:
                    specification = entry["forward"](xyz * entry["scale"], params)
                except Exception as error:
                    results[name] = None
                    log.add("unavailable", f"{name} 正变换失败：{type(error).__name__}")
                    continue

                values = {
                    key: number(getattr(specification, key, None), 3) for key in ("J", "C", "h", "M", "H")
                }
                roundtrip = None
                if entry["inverse"] is not None:
                    try:
                        restored = np.asarray(entry["inverse"](specification, params), dtype=float)
                        # 不四舍五入：往返误差的意义就在于它是 1e-15 还是 1e-3
                        roundtrip = float(np.max(np.abs(restored / entry["scale"] - xyz)))
                    except Exception as error:
                        log.add("unavailable", f"{name} 逆变换失败：{type(error).__name__}")
                results[name] = {**values, "roundtrip_error": roundtrip}

            rows.append({"input": spec, "hex": rgb_to_hex(rgb), "xyz": [round(float(c), 6) for c in xyz], "results": results})

        log.add(
            "note",
            "外观模型不是“更准的 Lab”：同一 XYZ 在不同 L_A / 环绕下得到不同 J、C、h，"
            "跨观察条件比较 J 没有意义。ZCAM 用 0–1 域，其余多数用 0–100 域。",
        )

    return {
        "observer": OBSERVER,
        "conditions": {
            "XYZ_w": [round(float(channel), 6) for channel in XYZ_W],
            "L_A": luminance,
            "Y_b": float(Y_b),
            "surround": surround,
        },
        "models": {name: {"conditions": MODELS[name]["conditions"], "scale": MODELS[name]["scale"]} for name in names},
        "rows": rows,
        "warnings": log.payload,
    }
