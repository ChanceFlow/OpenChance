"""OC-Discord 应用适配器

连接 Discord 平台客户端和 core 的公用服务。
使用 Application Commands (Slash Commands),不使用前缀命令。
"""

from pathlib import Path

import discord
from discord.ext import commands
from loguru import logger

from apps.oc_discord.client import DiscordClient
from core.config.settings import Settings
from core.models.message import Message, MessageType
from core.models.platform import Platform
from core.services.message_handler import MessageHandler


class OCDiscordAdapter:
    """OC-Discord 应用适配器

    负责:
    1. 使用 DiscordClient 连接 Discord 平台
    2. 将 Discord 消息转换为统一的 Message 模型
    3. 调用 core.MessageHandler 处理非命令消息
    4. 将响应发送回 Discord
    """

    def __init__(self, settings: Settings) -> None:
        """初始化适配器

        Args:
            settings: 应用配置
        """
        self.settings: Settings = settings

        # 创建消息处理器 (使用 core 的公用服务)
        self.message_handler: MessageHandler = MessageHandler()

        # 创建 Discord 平台客户端
        self.discord_client: DiscordClient = DiscordClient(
            token=settings.discord_token,
            owner_id=settings.bot_owner_id,
        )

        # 注册事件处理
        self._register_handlers()

    def _register_handlers(self) -> None:
        """注册事件处理器"""

        async def on_ready_handler() -> None:
            """ready 事件回调"""
            logger.info("OC-Discord 适配器就绪")

        self.discord_client.on_ready(on_ready_handler)

        async def on_message_handler(discord_msg: discord.Message) -> None:
            """message 事件回调 (处理非命令消息)"""
            await self._handle_message(discord_msg)

        self.discord_client.on_message(on_message_handler)

    async def _handle_message(self, discord_msg: discord.Message) -> None:
        """处理 Discord 非命令消息

        命令已由 Slash Commands (Cogs) 处理,此方法仅处理普通文本消息。

        Args:
            discord_msg: Discord 消息对象
        """
        # 转换为统一消息模型
        message: Message = self._convert_message(discord_msg)

        try:
            # 调用 core 的消息处理器
            response: str | None = await self.message_handler.handle_message(message)

            # 发送回复
            if response:
                await discord_msg.channel.send(response)

        except Exception as e:
            logger.opt(exception=True).error(f"处理消息时出错: {e}")

    def _convert_message(self, discord_msg: discord.Message) -> Message:
        """将 Discord 消息转换为统一消息模型

        Args:
            discord_msg: Discord 消息对象

        Returns:
            统一消息模型
        """
        return Message(
            id=str(discord_msg.id),
            content=discord_msg.content,
            type=MessageType.TEXT,
            user_id=str(discord_msg.author.id),
            user_name=discord_msg.author.name,
            channel_id=str(discord_msg.channel.id),
            channel_name=getattr(discord_msg.channel, "name", None),
            platform=Platform.DISCORD.value,
            timestamp=discord_msg.created_at,
            raw_message=discord_msg,
        )

    async def load_cogs(self, cogs_path: Path) -> None:
        """加载 Cogs

        Args:
            cogs_path: Cogs 目录路径
        """
        await self.discord_client.load_cogs(
            cogs_path=cogs_path,
            module_prefix="apps.oc_discord.cogs",
        )

    async def start(self) -> None:
        """启动适配器"""
        logger.info("正在启动 OC-Discord 适配器...")
        await self.discord_client.start()

    async def stop(self) -> None:
        """停止适配器"""
        logger.info("正在停止 OC-Discord 适配器...")
        await self.discord_client.stop()

    def get_discord_bot(self) -> commands.Bot:
        """获取 discord.py Bot 实例 (供 Cogs 使用)

        Returns:
            discord.py Bot 实例
        """
        return self.discord_client.get_bot()
