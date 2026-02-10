"""平台枚举"""
from enum import Enum


class Platform(Enum):
    """支持的平台"""

    DISCORD = "discord"
    TELEGRAM = "telegram"
    SLACK = "slack"
    WECHAT = "wechat"
    # 可以继续添加其他平台
