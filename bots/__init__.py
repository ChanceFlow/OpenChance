"""Bot 能力层

提供 Bot 的核心能力 (如 Claude Code 调用),不依赖任何平台 SDK。
平台相关的接入实现在 apps/ 层。
"""
from .claude_code import ClaudeCodeService

__all__ = ["ClaudeCodeService"]
