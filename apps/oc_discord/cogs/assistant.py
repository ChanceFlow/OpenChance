"""AI 助理命令 Cog

提供 Slash Commands: /ask, /code, /claude-status
/ask 和 /code 会创建 Discord Thread,后续消息在 Thread 内自动续接会话。
"""

from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands
from loguru import logger

from core.models.session import SessionInfo, SessionType
from bots.claude_code import ClaudeCodeService

# Discord 单条消息字符上限
_DISCORD_MAX_LENGTH: int = 2000
# 安全余量 (为 markdown 格式预留)
_SAFE_MAX_LENGTH: int = 1900

# Claude Code 预授权工具列表 (避免 headless 模式弹出权限提示)
_CODE_ALLOWED_TOOLS: list[str] = [
    "Bash", "Read", "Edit", "Write", "MultiEdit",
]
_ASK_ALLOWED_TOOLS: list[str] = [
    "Bash", "Read",
]


class AssistantCommands(commands.Cog):
    """AI 助理命令组

    /ask 和 /code 会创建独立的 Discord Thread,
    每个 Thread 对应一个 Claude Code 持久会话 (session)。
    用户在 Thread 内发送普通消息即可继续对话,无需再使用命令。
    """

    def __init__(self, bot: commands.Bot) -> None:
        """初始化 AI 助理命令 Cog

        Args:
            bot: Discord Bot 实例
        """
        self.bot = bot
        self.claude_service = ClaudeCodeService(working_dir=Path.home())

        # Thread ID → SessionInfo 的内存映射
        self._sessions: dict[int, SessionInfo] = {}

    # ------------------------------------------------------------------ #
    #  事件监听
    # ------------------------------------------------------------------ #

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """当 Cog 加载完成时检查 Claude Code 可用性"""
        is_available: bool = await self.claude_service.check_available()
        if is_available:
            logger.info("✅ Claude Code CLI 可用")
        else:
            logger.warning("⚠️ Claude Code CLI 不可用,/ask 和 /code 将无法使用")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """监听 Thread 内的用户消息,自动续接 Claude Code 会话

        Args:
            message: Discord 消息对象
        """
        # 忽略 Bot 自身消息
        if message.author.bot:
            return

        # 仅处理 Thread 内的消息
        if not isinstance(message.channel, discord.Thread):
            return

        thread: discord.Thread = message.channel

        # 仅处理被管理的 Thread
        session: SessionInfo | None = self._sessions.get(thread.id)
        if session is None:
            return

        # 忽略空消息
        if not message.content.strip():
            return

        logger.info(
            f"Thread {thread.id} 收到消息 (session={session.session_id[:12]}...): "
            f"{message.content[:80]}..."
        )

        # 显示输入指示器 + 调用 Claude Code 续接会话
        try:
            async with thread.typing():
                response: str = await self.claude_service.continue_session(
                    session_id=session.session_id,
                    message=message.content,
                    allowed_tools=session.allowed_tools,
                    timeout=600 if session.session_type == SessionType.CODE else 300,
                )

            await self._send_long_message(thread, response)

        except Exception as e:
            logger.opt(exception=True).error(
                f"Thread {thread.id} 续接会话失败: {e}"
            )
            await thread.send(f"❌ AI 响应失败: {e}")

    # ------------------------------------------------------------------ #
    #  Slash Commands
    # ------------------------------------------------------------------ #

    @app_commands.command(name="ask", description="向 Claude 提问 (创建对话子区)")
    @app_commands.describe(question="问题内容")
    async def ask_claude(
        self,
        interaction: discord.Interaction,
        question: str,
    ) -> None:
        """向 Claude 提问,创建 Thread 进行多轮对话

        Args:
            interaction: 交互对象
            question: 问题内容
        """
        await self._start_thread_session(
            interaction=interaction,
            prompt=question,
            session_type=SessionType.ASK,
            thread_emoji="💬",
            timeout=300,
        )

    @app_commands.command(name="code", description="让 Claude 执行编码任务 (创建编码子区)")
    @app_commands.describe(task="任务描述")
    async def execute_code_task(
        self,
        interaction: discord.Interaction,
        task: str,
    ) -> None:
        """让 Claude 执行编码任务,创建 Thread 进行持续交互

        Args:
            interaction: 交互对象
            task: 任务描述
        """
        await self._start_thread_session(
            interaction=interaction,
            prompt=task,
            session_type=SessionType.CODE,
            thread_emoji="🤖",
            timeout=600,
        )

    @app_commands.command(name="claude-status", description="检查 Claude Code CLI 状态")
    async def check_claude(self, interaction: discord.Interaction) -> None:
        """检查 Claude Code CLI 状态

        Args:
            interaction: 交互对象
        """
        is_available: bool = await self.claude_service.check_available()

        if is_available:
            embed = discord.Embed(
                title="✅ Claude Code 状态",
                description="Claude Code CLI 已安装并可用",
                color=discord.Color.green(),
            )
        else:
            embed = discord.Embed(
                title="❌ Claude Code 状态",
                description=(
                    "Claude Code CLI 不可用\n\n"
                    "请确认已安装 Claude Code CLI:\n"
                    "```bash\n"
                    "npm install -g @anthropic-ai/claude-code\n"
                    "```\n"
                    "安装后命令为 `claude`"
                ),
                color=discord.Color.red(),
            )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="sessions", description="查看当前活跃的 AI 会话列表")
    async def list_sessions(self, interaction: discord.Interaction) -> None:
        """列出当前所有活跃的 Thread 会话

        Args:
            interaction: 交互对象
        """
        if not self._sessions:
            await interaction.response.send_message(
                "📭 当前没有活跃的 AI 会话", ephemeral=True
            )
            return

        lines: list[str] = []
        for thread_id, session in self._sessions.items():
            thread: discord.Thread | None = self.bot.get_channel(thread_id)  # type: ignore[assignment]
            thread_name: str = thread.mention if thread else f"(已删除: {thread_id})"
            type_icon: str = "💬" if session.session_type == SessionType.ASK else "🤖"
            lines.append(
                f"{type_icon} {thread_name} — "
                f"`{session.session_id[:12]}...` "
                f"by <@{session.creator_id}>"
            )

        embed = discord.Embed(
            title=f"📋 活跃 AI 会话 ({len(self._sessions)})",
            description="\n".join(lines),
            color=discord.Color.blue(),
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ------------------------------------------------------------------ #
    #  内部方法
    # ------------------------------------------------------------------ #

    async def _start_thread_session(
        self,
        interaction: discord.Interaction,
        prompt: str,
        session_type: SessionType,
        thread_emoji: str,
        timeout: int,
    ) -> None:
        """通用的 Thread + Session 创建流程

        Args:
            interaction: Discord 交互对象
            prompt: 用户输入的指令/问题
            session_type: 会话类型 (ASK / CODE)
            thread_emoji: Thread 名称前缀 emoji
            timeout: Claude Code 超时时间 (秒)
        """
        await interaction.response.defer(thinking=True)

        # 1. 启动 Claude Code 会话 (预授权所有工具,避免 headless 弹出权限提示)
        try:
            allowed_tools: list[str] = (
                _CODE_ALLOWED_TOOLS if session_type == SessionType.CODE
                else _ASK_ALLOWED_TOOLS
            )

            session_id, response = await self.claude_service.start_session(
                instruction=prompt,
                allowed_tools=allowed_tools,
                timeout=timeout,
            )

        except Exception as e:
            logger.opt(exception=True).error(f"启动 Claude Code 会话失败: {e}")
            await interaction.followup.send(content=f"❌ 启动会话失败: {e}")
            return

        # 2. 创建 Discord Thread
        try:
            channel: discord.abc.GuildChannel | None = interaction.channel  # type: ignore[assignment]
            if channel is None or not hasattr(channel, "create_thread"):
                await interaction.followup.send(
                    content="❌ 无法在当前频道创建子区", ephemeral=True
                )
                return

            thread_name: str = f"{thread_emoji} {prompt[:80]}"
            thread: discord.Thread = await channel.create_thread(  # type: ignore[union-attr]
                name=thread_name,
                auto_archive_duration=1440,  # 24 小时自动归档
                type=discord.ChannelType.private_thread,
            )

        except discord.Forbidden:
            logger.error("Bot 没有创建 Thread 的权限")
            await interaction.followup.send(
                content="❌ Bot 没有创建子区的权限,请检查权限设置"
            )
            return
        except Exception as e:
            logger.opt(exception=True).error(f"创建 Thread 失败: {e}")
            await interaction.followup.send(content=f"❌ 创建子区失败: {e}")
            return

        # 3. 存储会话映射 (包含 allowed_tools 供续接使用)
        session_info = SessionInfo(
            session_id=session_id,
            session_type=session_type,
            creator_id=str(interaction.user.id),
            allowed_tools=allowed_tools,
        )
        self._sessions[thread.id] = session_info

        logger.info(
            f"已创建 Thread 会话: thread={thread.id}, "
            f"session={session_id[:12]}..., type={session_type.value}"
        )

        # 4. 在 Thread 中发送首次 AI 响应
        await self._send_long_message(thread, response)

        # 5. 在原频道通知用户
        type_label: str = "对话" if session_type == SessionType.ASK else "编码"
        await interaction.followup.send(
            content=(
                f"✅ 已创建{type_label}会话: {thread.mention}\n"
                f"后续消息直接在子区中发送即可,无需使用命令。"
            )
        )

    async def _send_long_message(
        self,
        channel: discord.abc.Messageable,
        content: str,
    ) -> None:
        """发送可能超长的消息,按需拆分为多条

        Discord 单条消息上限 2000 字符,此方法按换行符拆分长消息。

        Args:
            channel: 目标频道/Thread
            content: 要发送的文本内容
        """
        if not content.strip():
            await channel.send("_(空响应)_")
            return

        # 短消息直接发送
        if len(content) <= _SAFE_MAX_LENGTH:
            await channel.send(content)
            return

        # 长消息按换行符拆分
        chunks: list[str] = []
        remaining: str = content

        while remaining:
            if len(remaining) <= _SAFE_MAX_LENGTH:
                chunks.append(remaining)
                break

            # 尝试在换行符处拆分
            split_at: int = remaining.rfind("\n", 0, _SAFE_MAX_LENGTH)
            if split_at <= 0:
                # 没有合适的换行符,强制截断
                split_at = _SAFE_MAX_LENGTH

            chunks.append(remaining[:split_at])
            remaining = remaining[split_at:].lstrip("\n")

        for chunk in chunks:
            await channel.send(chunk)


async def setup(bot: commands.Bot) -> None:
    """加载 Cog

    Args:
        bot: Discord Bot 实例
    """
    await bot.add_cog(AssistantCommands(bot))
