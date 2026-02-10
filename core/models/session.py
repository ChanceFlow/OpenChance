"""会话模型

定义 AI 会话的数据结构,用于 Thread ↔ Claude Code 会话的映射。
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class SessionType(Enum):
    """会话类型

    ASK  — 一般对话,不授予工具权限
    CODE — 编码任务,允许 Bash/Read/Edit 工具
    """

    ASK = "ask"
    CODE = "code"


@dataclass
class SessionInfo:
    """AI 会话信息

    存储一个 Discord Thread 对应的 Claude Code 会话状态。
    """

    # Claude Code 会话 ID (用于 --resume)
    session_id: str

    # 会话类型
    session_type: SessionType

    # 创建者的 Discord 用户 ID
    creator_id: str

    # Claude Code 已授权的工具列表 (用于 --allowedTools, 续接会话时复用)
    allowed_tools: list[str] = field(default_factory=list)

    # 创建时间 (UTC)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
