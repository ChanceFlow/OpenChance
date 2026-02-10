"""消息处理服务

提供非命令消息处理的公用逻辑。
命令已由各平台的 Slash Commands (Cogs) 处理。
"""

from loguru import logger

from core.models.message import Message, MessageType


class MessageHandler:
    """消息处理器 - 公用业务逻辑

    处理非命令的普通文本消息。Slash Commands 由各平台 Cogs 直接处理。
    """

    async def handle_message(self, message: Message) -> str | None:
        """处理消息

        Args:
            message: 统一消息模型

        Returns:
            回复内容,如果返回 None 则不回复
        """
        logger.debug(
            "处理消息 - 平台: {platform}, 用户: {user}, 内容: {content}",
            platform=message.platform,
            user=message.user_name,
            content=message.content[:50] + "..." if len(message.content) > 50 else message.content,
        )

        if message.type == MessageType.TEXT:
            return await self._handle_text(message)

        return None

    async def _handle_text(self, message: Message) -> str | None:
        """处理文本消息

        Args:
            message: 消息对象

        Returns:
            回复内容
        """
        # TODO: 这里可以集成 AI 对话服务 (如被 @提及时自动回复)
        # 目前不回复普通文本消息
        return None
