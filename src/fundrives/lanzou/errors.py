"""蓝奏云驱动的领域异常。

按 SPEC §8.2 的要求，本包不再直接抛出 `Exception`，而是抛出下面这些带上下文的
领域异常，便于调用方按失败原因分别处理。
"""

__all__ = [
    "LanZouError",
    "NoAvailableDomainError",
]


class LanZouError(Exception):
    """蓝奏云驱动所有异常的基类。"""


class NoAvailableDomainError(LanZouError):
    """所有候选蓝奏云域名都探测不通，无法继续发起请求。"""
