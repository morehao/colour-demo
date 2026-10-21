"""全局限制与常量（方案 6.3：超出数量/步数上限返回 422，不进入 colour）。"""

from __future__ import annotations

import math

# 一次请求最多处理的颜色数
MAX_COLOURS = 12
# 渐变最大步数
MAX_STEPS = 101
# 光谱采样点数上限
MAX_SPECTRAL_SAMPLES = 401
# 允许的光谱范围（nm）
SPECTRAL_RANGE = (360.0, 830.0)

DEFAULT_ILLUMINANT = "D65"
DEFAULT_OBSERVER = "CIE 1931 2 Degree Standard Observer"
DEFAULT_METHOD = "CIE 2000"

# 方案 7.2：CAM16 观察条件必须显式给全，否则静默偏差
CAM16_L_A = 64 / math.pi / 5
CAM16_Y_B = 20.0
