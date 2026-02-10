"""消息模型"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class MessageType(Enum):
    """消息类型"""

    TEXT = "text"
    COMMAND = "command"
    SYSTEM = "system"


@dataclass
class Message:
    """统一消息模型

    平台无关的消息数据结构,由各平台适配器负责转换。
    """

    # 基础信息
    id: str
    content: str
    type: MessageType

    # 用户信息
    user_id: str
    user_name: str

    # 频道信息
    channel_id: str
    channel_name: str | None = None

    # 平台信息
    platform: str = "unknown"

    # 时间戳 (UTC)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # 原始平台对象 (用于平台特定操作)
    raw_message: object | None = None
