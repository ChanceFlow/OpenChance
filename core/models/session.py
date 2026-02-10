"""会话模型

定义 AI 会话的数据结构,用于 Thread ↔ AI Bot 会话的映射与持久化。
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class SessionType(Enum):
    """会话类型

    ASK  — 一般对话,不授予工具权限
    CODE — 编码任务,允许 Bash/Read/Edit 工具
    """

    ASK = "ask"
    CODE = "code"


class BotType(Enum):
    """Bot 类型枚举

    标识会话使用的底层 AI 后端。
    """

    CLAUDE_AGENT = "claude_agent"
    # 未来可扩展:
    # OPENAI = "openai"
    # GEMINI = "gemini"


@dataclass
class SessionInfo:
    """AI 会话信息

    存储一个 Discord Thread 对应的 AI Bot 会话状态。
    支持 JSON 序列化/反序列化,用于持久化到磁盘。

    字段说明:
    - session_id: 内部 UUID,用于在 ClaudeAgentService._clients 中索引
    - cli_session_id: Claude CLI 的 session ID (来自 ResultMessage.session_id),
      用于 ``--resume`` 恢复对话上下文。重启后凭此 ID 继承完整对话历史。
    """

    # 内部会话 ID (由 ClaudeAgentService 生成的 UUID)
    session_id: str

    # 会话类型
    session_type: SessionType

    # Bot 类型
    bot_type: BotType

    # 创建者的 Discord 用户 ID
    creator_id: str

    # 已授权的工具列表 (在会话创建时确定,供展示使用)
    allowed_tools: list[str] = field(default_factory=list)

    # Claude CLI session ID (用于 --resume 恢复上下文)
    cli_session_id: str | None = None

    # 创建时间 (UTC)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典 (用于 JSON 持久化)

        Returns:
            可 JSON 序列化的字典
        """
        return {
            "session_id": self.session_id,
            "session_type": self.session_type.value,
            "bot_type": self.bot_type.value,
            "creator_id": self.creator_id,
            "allowed_tools": self.allowed_tools,
            "cli_session_id": self.cli_session_id,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionInfo":
        """从字典反序列化

        Args:
            data: JSON 反序列化后的字典

        Returns:
            SessionInfo 实例
        """
        return cls(
            session_id=data["session_id"],
            session_type=SessionType(data["session_type"]),
            bot_type=BotType(data["bot_type"]),
            creator_id=data["creator_id"],
            allowed_tools=data.get("allowed_tools", []),
            cli_session_id=data.get("cli_session_id"),
            created_at=datetime.fromisoformat(data["created_at"]),
        )
