"""面板 10：色域体与边界（`POST /api/v1/volume`）。

体积用 `RGB_colourspace_volume_MonteCarlo` 抽样估算。两个必须做的处理：

1. **关掉 multiprocessing**：该函数默认开 `multiprocessing.Pool`（进程数 = CPU 核数）。
   在 Web 服务里每次请求都 fork 一池子进程是灾难（也解释了原型 `--batch 3` 为何被内存回收打死）。
   实测关掉后 5000 采样只要 ~2 ms，比开池子稳得多；
2. **固定种子**：抽样法本身有随机性，不固定就无法回归。按 (空间, 采样数, 种子) 做 LRU 缓存。

注意 volume 的口径：MonteCarlo 值随采样数与 CPU 核数分摊方式波动，
只适合做“色域大小”的相对比较，不是精确体积。
"""

from __future__ import annotations

import threading

import numpy as np

import colour
from colour.utilities import disable_multiprocessing

from ..core.cache import lru
from ..core.diagnostics import WarningCollector, number, numbers
from ..core.errors import value_error
from ..core.parsing import parse_colours, rgb_to_hex

DEFAULT_SPACES = ("sRGB", "Display P3", "ITU-R BT.2020", "ACES2065-1")
REFERENCE_SPACE = "sRGB"
DEFAULT_SAMPLES = 20000
DEFAULT_SEED = 7
SAMPLES_RANGE = (1000, 200000)
MAX_SPACES = 8

D65_XY = np.asarray(
    colour.CCS_ILLUMINANTS["CIE 1931 2 Degree Standard Observer"]["D65"], dtype=float
)

# `disable_multiprocessing()` 改的是模块级全局开关，多线程下必须串行进这段
_POOL_LOCK = threading.Lock()


def _space(name: str):
    try:
        return colour.RGB_COLOURSPACES[name]
    except Exception as error:
        sample = sorted(colour.RGB_COLOURSPACES.keys())[:8]
        raise value_error(f"未知色彩空间 {name!r}（示例：{sample}）") from error


@lru(maxsize=64)
def _montecarlo_volume(name: str, samples: int, seed: int) -> float:
    """抽样体积（进程内缓存）；同一 (空间, 采样数, 种子) 结果完全可复现。"""

    space = _space(name)
    with _POOL_LOCK, disable_multiprocessing():
        volume = colour.volume.RGB_colourspace_volume_MonteCarlo(
            space,
            samples=samples,
            illuminant_Lab=np.array(D65_XY),
            random_state=np.random.RandomState(seed),
        )
    return float(volume)


def _boundaries(specs: list[str]) -> list[dict]:
    """三套边界判据：MacAdam 极限（光源允许的最饱和物体色）、Pointer 色域、可见光谱。"""

    rows = []
    for spec, rgb in zip(specs, parse_colours(specs)):
        xyz = np.asarray(colour.sRGB_to_XYZ(rgb), dtype=float)
        xyY = np.asarray(colour.XYZ_to_xyY(xyz), dtype=float)
        rows.append(
            {
                "input": spec,
                "hex": rgb_to_hex(rgb),
                "xyz": numbers(xyz, 6),
                "within_macadam_D65": bool(
                    np.asarray(colour.volume.is_within_macadam_limits(xyY, "D65")).ravel()[0]
                ),
                "within_pointer": bool(
                    np.asarray(colour.volume.is_within_pointer_gamut(xyz)).ravel()[0]
                ),
                "within_visible_spectrum": bool(
                    np.asarray(colour.volume.is_within_visible_spectrum(xyz)).ravel()[0]
                ),
            }
        )
    return rows


def volume_data(
    spaces: list[str] | None = None,
    samples: int = DEFAULT_SAMPLES,
    seed: int = DEFAULT_SEED,
    colours: list[str] | None = None,
) -> dict:
    names = list(spaces or DEFAULT_SPACES)
    if len(names) > MAX_SPACES:
        raise value_error(f"色彩空间最多 {MAX_SPACES} 个，当前 {len(names)} 个")
    low, high = SAMPLES_RANGE
    if not (low <= samples <= high):
        raise value_error(f"samples 需在 {low}–{high}，当前 {samples}")
    if seed < 0:
        raise value_error("seed 需为非负整数")

    with WarningCollector() as log:
        reference = _montecarlo_volume(REFERENCE_SPACE, samples, seed)
        if REFERENCE_SPACE not in names:
            names.insert(0, REFERENCE_SPACE)

        rows = []
        for name in names:
            try:
                volume = _montecarlo_volume(name, samples, seed)
                limits = np.asarray(colour.volume.RGB_colourspace_limits(_space(name)), dtype=float)
                rows.append(
                    {
                        "space": name,
                        "volume": number(volume, 3),
                        "relative_to_reference": number(volume / reference, 4) if reference else None,
                        "lab_limits": [numbers(row, 3) for row in limits],
                    }
                )
            except Exception as error:
                rows.append({"space": name, "volume": None, "relative_to_reference": None, "lab_limits": None})
                log.add("unavailable", f"{name} 的体积估算失败：{type(error).__name__}")

        boundaries = _boundaries(colours) if colours else []
        log.add(
            "note",
            f"体积是 {samples} 点 MonteCarlo 抽样估算（种子 {seed}），"
            "相对比较可用、绝对量不可当精确值；multiprocessing 已关闭，"
            "按 CPU 核数分摊的原始实现会让结果随机器核数漂移。",
        )

    return {
        "reference_space": REFERENCE_SPACE,
        "samples": samples,
        "seed": seed,
        "rows": rows,
        "boundaries": boundaries,
        "warnings": log.payload,
    }
