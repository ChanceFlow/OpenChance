"""Bot 能力层

提供 Bot 的核心能力 (Claude Agent SDK),不依赖任何平台 SDK。
平台相关的接入实现在 apps/ 层。
"""
from .claude_agent import ClaudeAgentService

__all__ = ["ClaudeAgentService"]
