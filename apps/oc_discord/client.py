"""Discord 平台客户端

封装 discord.py SDK,提供 Discord 平台的连接、事件监听和 Cog 加载能力。
这是 apps 前端接入层的一部分,不包含业务逻辑。
"""

from pathlib import Path
from typing import Awaitable, Callable

import discord
from discord import app_commands
from discord.ext import commands
from loguru import logger


class DiscordClient:
    """Discord 平台客户端封装

    基于 discord.py 2.6+ 的 Application Commands 体系,
    不使用前缀命令 (Prefix Commands)。
    """

    def __init__(
        self,
        token: str,
        owner_id: int | None = None,
    ) -> None:
        """初始化 Discord 客户端

        Args:
            token: Discord Bot Token
            owner_id: Bot 所有者的 Discord 用户 ID
        """
        self.token: str = token

        # 配置 Intents
        intents: discord.Intents = discord.Intents.default()
        intents.message_content = True  # 非命令消息处理 (Privileged Intent)
        intents.members = True  # 成员信息查询 (Privileged Intent)

        self.bot: commands.Bot = commands.Bot(
            command_prefix=commands.when_mentioned,  # 仅供 Cog 系统使用,不注册前缀命令
            intents=intents,
            help_command=None,
            owner_id=owner_id,
        )

        # 事件回调
        self._on_ready_callback: Callable[[], Awaitable[None]] | None = None
        self._on_message_callback: Callable[[discord.Message], Awaitable[None]] | None = None

        # 注册事件和钩子
        self._register_events()
        self._configure_hooks()

    def _configure_hooks(self) -> None:
        """配置 setup_hook 和全局 Application Command 错误处理"""
        bot = self.bot

        # 覆盖 setup_hook: 在连接 Gateway 前同步命令树
        async def _setup_hook() -> None:
            """同步 Application Commands 到 Discord"""
            logger.info("正在同步命令树...")
            await bot.tree.sync()
            logger.info("✅ 命令树已同步")

        bot.setup_hook = _setup_hook  # type: ignore[method-assign]

        # 全局 Application Command 错误处理
        @bot.tree.error
        async def on_app_command_error(
            interaction: discord.Interaction,
            error: app_commands.AppCommandError,
        ) -> None:
            """处理 Slash Command 执行错误"""
            if isinstance(error, app_commands.MissingPermissions):
                message = "❌ 你没有权限执行此命令"
            elif isinstance(error, app_commands.CommandOnCooldown):
                message = f"❌ 命令冷却中,请等待 {error.retry_after:.1f} 秒"
            elif isinstance(error, app_commands.CheckFailure):
                message = "❌ 权限检查失败"
            else:
                logger.opt(exception=error).error(f"应用命令错误: {error}")
                message = "❌ 命令执行出错,请稍后重试"

            if not interaction.response.is_done():
                await interaction.response.send_message(message, ephemeral=True)
            else:
                await interaction.followup.send(message, ephemeral=True)

    def _register_events(self) -> None:
        """注册 Discord Gateway 事件"""

        @self.bot.event
        async def on_ready() -> None:
            """当机器人连接成功时"""
            logger.info(f"Discord 已登录: {self.bot.user}")
            logger.info(f"Bot ID: {self.bot.user.id}")
            logger.info(f"已加入 {len(self.bot.guilds)} 个服务器")

            if self._on_ready_callback:
                await self._on_ready_callback()

        @self.bot.event
        async def on_message(message: discord.Message) -> None:
            """当收到消息时 (用于非命令消息处理)"""
            if message.author.bot:
                return

            if self._on_message_callback:
                await self._on_message_callback(message)

        @self.bot.event
        async def on_error(event: str, *args: object, **kwargs: object) -> None:
            """当发生 Gateway 事件错误时"""
            logger.opt(exception=True).error(f"Discord 事件错误: {event}")

    def on_ready(self, callback: Callable[[], Awaitable[None]]) -> None:
        """注册 ready 事件回调

        Args:
            callback: 回调函数
        """
        self._on_ready_callback = callback

    def on_message(self, callback: Callable[[discord.Message], Awaitable[None]]) -> None:
        """注册 message 事件回调

        Args:
            callback: 回调函数
        """
        self._on_message_callback = callback

    async def load_cogs(self, cogs_path: Path, module_prefix: str) -> None:
        """加载 Cogs

        Args:
            cogs_path: Cogs 目录路径
            module_prefix: 模块前缀 (如 "apps.oc_discord.cogs")
        """
        if not cogs_path.exists():
            logger.warning(f"Cogs 路径不存在: {cogs_path}")
            return

        logger.info(f"正在从 {cogs_path} 加载 Cogs...")

        for cog_file in cogs_path.glob("*.py"):
            if cog_file.name.startswith("_"):
                continue

            cog_name: str = cog_file.stem
            extension_path: str = f"{module_prefix}.{cog_name}"

            try:
                await self.bot.load_extension(extension_path)
                logger.info(f"✅ 已加载 Cog: {cog_name}")
            except Exception as e:
                logger.opt(exception=True).error(f"❌ 加载 Cog {cog_name} 失败: {e}")

    async def start(self) -> None:
        """启动 Discord 客户端"""
        logger.info("正在启动 Discord 客户端...")
        try:
            await self.bot.start(self.token)
        except discord.LoginFailure:
            logger.error("Discord 登录失败,请检查 token")
            raise
        except Exception as e:
            logger.opt(exception=True).error(f"Discord 客户端启动失败: {e}")
            raise

    async def stop(self) -> None:
        """停止 Discord 客户端"""
        logger.info("正在停止 Discord 客户端...")
        if self.bot and not self.bot.is_closed():
            await self.bot.close()
        logger.info("Discord 客户端已停止")

    def get_bot(self) -> commands.Bot:
        """获取 discord.py Bot 实例 (供 Cogs 使用)

        Returns:
            discord.py Bot 客户端
        """
        return self.bot
