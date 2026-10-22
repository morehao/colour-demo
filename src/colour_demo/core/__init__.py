"""服务层：一个面板一个模块，模块之间不互相 import（方案 7.1）。

这里的函数全部是**纯函数**：入参已由 pydantic 校验，出参可 JSON 序列化，
内部不做任何 HTTP 相关的事——CI 与测试直接调用它们做黄金值校验。
"""

from __future__ import annotations
