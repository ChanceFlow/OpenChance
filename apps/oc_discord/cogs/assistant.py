"""AI 助理命令 Cog

提供 Slash Commands: /ask, /code, /claude-status, /sessions
/ask 和 /code 会创建 Discord Thread,后续消息在 Thread 内自动续接会话。

底层使用 Claude Agent SDK 管理会话,支持流式输出:
- 创建 Thread 时首条消息会 @对话人
- AI 响应通过编辑消息实现逐步显示 (类似打字机效果)
- 会话映射持久化到 JSON 文件,重启后通过 --resume 继承完整对话上下文
"""

import time
from collections.abc import AsyncGenerator
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands
from loguru import logger

from bots.claude_agent import ClaudeAgentService
from core.models.session import BotType, SessionInfo, SessionType
from core.services.session_store import SessionStore

# ------------------------------------------------------------------ #
#  常量
# ------------------------------------------------------------------ #

# Discord 单条消息字符上限
_DISCORD_MAX_LENGTH: int = 2000
# 安全余量 (为 markdown 格式 / cursor 预留)
_SAFE_MAX_LENGTH: int = 1900

# 流式输出配置
_STREAM_EDIT_INTERVAL: float = 1.5  # 编辑消息的最小间隔 (秒)
_STREAM_CURSOR: str = " ▌"  # 流式输出中的闪烁光标

# Claude Agent SDK 预授权工具列表
_CODE_ALLOWED_TOOLS: list[str] = [
    "Bash", "Read", "Edit", "Write", "MultiEdit",
]
_ASK_ALLOWED_TOOLS: list[str] = [
    "Bash", "Read",
]

# 持久化文件路径 (项目根目录/data/sessions.json)
_PROJECT_ROOT: Path = Path(__file__).parent.parent.parent.parent
_SESSION_STORE_PATH: Path = _PROJECT_ROOT / "data" / "sessions.json"


class AssistantCommands(commands.Cog):
    """AI 助理命令组

    /ask 和 /code 会创建独立的 Discord Thread,
    每个 Thread 对应一个 Claude Agent SDK 持久会话 (ClaudeSDKClient)。
    用户在 Thread 内发送普通消息即可继续对话,无需再使用命令。
    AI 响应通过流式输出逐步显示在 Discord 中。

    会话映射通过 SessionStore 持久化到磁盘,
    重启后通过 Claude CLI 的 --resume 参数继承完整对话上下文。
    """

    def __init__(self, bot: commands.Bot) -> None:
        """初始化 AI 助理命令 Cog

        Args:
            bot: Discord Bot 实例
        """
        self.bot = bot
        self.claude_service = ClaudeAgentService(working_dir=Path.home())

        # 持久化会话存储 (Thread ID → SessionInfo)
        self._store: SessionStore = SessionStore(store_path=_SESSION_STORE_PATH)

    # ------------------------------------------------------------------ #
    #  事件监听
    # ------------------------------------------------------------------ #

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """当 Cog 加载完成时:恢复持久化会话 + 检查 Claude Agent SDK 可用性"""
        # 1. 从磁盘恢复会话映射
        loaded: int = self._store.load()
        if loaded > 0:
            # 统计有 cli_session_id 的数量
            resumable: int = sum(
                1 for s in self._store.values() if s.cli_session_id
            )
            logger.info(
                f"✅ 已恢复 {loaded} 个持久化会话映射 "
                f"(其中 {resumable} 个可通过 --resume 继承上下文)"
            )

        # 2. 检查 Claude Agent SDK 可用性
        is_available: bool = await self.claude_service.check_available()
        if is_available:
            logger.info("✅ Claude Agent SDK 可用")
        else:
            logger.warning("⚠️ Claude Agent SDK 不可用,/ask 和 /code 将无法使用")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """监听 Thread 内的用户消息,自动续接 Claude Agent 会话 (流式)

        如果底层 AI 连接已失效 (例如 Bot 重启),
        会通过 --resume 恢复上下文或创建新会话。

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
        session: SessionInfo | None = self._store.get(thread.id)
        if session is None:
            return

        # 忽略空消息
        if not message.content.strip():
            return

        logger.info(
            f"Thread {thread.id} 收到消息 (session={session.session_id[:12]}...): "
            f"{message.content[:80]}..."
        )

        # 检查底层 AI 连接是否存活,不存活则重建
        if not self.claude_service.has_session(session.session_id):
            logger.info(
                f"Thread {thread.id} 的 AI 连接已失效,正在重建 "
                f"(bot_type={session.bot_type.value}, "
                f"cli_session={'有' if session.cli_session_id else '无'})..."
            )
            await self._reconnect_and_respond(
                thread=thread,
                session=session,
                message_text=message.content,
            )
            return

        # 流式续接会话
        try:
            stream: AsyncGenerator[str, None] = (
                await self.claude_service.continue_session_stream(
                    session_id=session.session_id,
                    message=message.content,
                )
            )
            await self._stream_to_discord(
                channel=thread,
                stream=stream,
            )

            # 流结束后更新 CLI session ID
            self._save_cli_session_id(thread.id, session.session_id)

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
            bot_type=BotType.CLAUDE_AGENT,
            thread_emoji="💬",
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
            bot_type=BotType.CLAUDE_AGENT,
            thread_emoji="🤖",
        )

    @app_commands.command(name="claude-status", description="检查 Claude Agent SDK 状态")
    async def check_claude(self, interaction: discord.Interaction) -> None:
        """检查 Claude Agent SDK 状态

        Args:
            interaction: 交互对象
        """
        is_available: bool = await self.claude_service.check_available()

        if is_available:
            sdk_sessions: int = self.claude_service.active_session_count
            stored_sessions: int = len(self._store)
            embed = discord.Embed(
                title="✅ Claude Agent SDK 状态",
                description=(
                    "Claude Agent SDK 已就绪\n"
                    f"活跃 AI 连接数: {sdk_sessions}\n"
                    f"持久化会话数: {stored_sessions}"
                ),
                color=discord.Color.green(),
            )
        else:
            embed = discord.Embed(
                title="❌ Claude Agent SDK 状态",
                description=(
                    "Claude Agent SDK 不可用\n\n"
                    "请确认已安装依赖:\n"
                    "```bash\n"
                    "pip install claude-agent-sdk\n"
                    "npm install -g @anthropic-ai/claude-code\n"
                    "```\n"
                    "Agent SDK 底层依赖 Claude Code CLI (`claude` 命令)"
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
        if not self._store:
            await interaction.response.send_message(
                "📭 当前没有活跃的 AI 会话", ephemeral=True
            )
            return

        lines: list[str] = []
        for thread_id, session in self._store.items():
            thread: discord.Thread | None = self.bot.get_channel(thread_id)  # type: ignore[assignment]
            thread_name: str = thread.mention if thread else f"(已删除: {thread_id})"
            type_icon: str = "💬" if session.session_type == SessionType.ASK else "🤖"
            # 显示连接状态
            connected: bool = self.claude_service.has_session(session.session_id)
            if connected:
                status_icon: str = "🟢"
            elif session.cli_session_id:
                status_icon = "🟡"  # 可 resume
            else:
                status_icon = "🔴"  # 无上下文
            lines.append(
                f"{type_icon} {thread_name} — "
                f"`{session.bot_type.value}` "
                f"{status_icon} "
                f"by <@{session.creator_id}>"
            )

        embed = discord.Embed(
            title=f"📋 活跃 AI 会话 ({len(self._store)})",
            description="\n".join(lines) + "\n\n🟢 已连接 🟡 可恢复 🔴 无上下文",
            color=discord.Color.blue(),
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ------------------------------------------------------------------ #
    #  内部方法 — Thread + Session 创建
    # ------------------------------------------------------------------ #

    async def _start_thread_session(
        self,
        interaction: discord.Interaction,
        prompt: str,
        session_type: SessionType,
        bot_type: BotType,
        thread_emoji: str,
    ) -> None:
        """通用的 Thread + Session 创建流程 (流式输出)

        流程:
        1. defer 交互
        2. 启动 Claude Agent SDK 流式会话 (连接 + 发送指令)
        3. 创建 Discord Thread
        4. 在 Thread 中流式输出首次响应 (带 @用户 提及)
        5. 持久化会话映射 (含 CLI session ID)
        6. 在原频道通知用户

        Args:
            interaction: Discord 交互对象
            prompt: 用户输入的指令/问题
            session_type: 会话类型 (ASK / CODE)
            bot_type: Bot 类型
            thread_emoji: Thread 名称前缀 emoji
        """
        await interaction.response.defer(thinking=True)

        # 1. 启动 Claude Agent SDK 流式会话
        try:
            allowed_tools: list[str] = (
                _CODE_ALLOWED_TOOLS if session_type == SessionType.CODE
                else _ASK_ALLOWED_TOOLS
            )

            session_id, stream = await self.claude_service.start_session_stream(
                instruction=prompt,
                allowed_tools=allowed_tools,
            )

        except Exception as e:
            logger.opt(exception=True).error(f"启动 Claude Agent 会话失败: {e}")
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

        # 3. 持久化会话映射 (cli_session_id 流结束后更新)
        session_info = SessionInfo(
            session_id=session_id,
            session_type=session_type,
            bot_type=bot_type,
            creator_id=str(interaction.user.id),
            allowed_tools=allowed_tools,
        )
        self._store.put(thread.id, session_info)

        logger.info(
            f"已创建 Thread 会话: thread={thread.id}, "
            f"session={session_id[:12]}..., type={session_type.value}, "
            f"bot={bot_type.value}"
        )

        # 4. 在 Thread 中流式输出首次响应 (带 @用户 提及)
        mention_prefix: str = f"<@{interaction.user.id}>\n"
        await self._stream_to_discord(
            channel=thread,
            stream=stream,
            mention_prefix=mention_prefix,
        )

        # 5. 流结束后保存 CLI session ID (用于重启后 --resume)
        self._save_cli_session_id(thread.id, session_id)

        # 6. 在原频道通知用户 (interaction followup 可能因超时失效)
        type_label: str = "对话" if session_type == SessionType.ASK else "编码"
        try:
            await interaction.followup.send(
                content=(
                    f"✅ 已创建{type_label}会话: {thread.mention}\n"
                    f"后续消息直接在子区中发送即可,无需使用命令。"
                )
            )
        except discord.NotFound:
            # interaction token 已过期,改为在 Thread 中通知
            logger.warning("interaction followup 已过期,改为在 Thread 中通知")
        except discord.HTTPException as e:
            logger.warning(f"发送 followup 失败: {e}")

    # ------------------------------------------------------------------ #
    #  内部方法 — 重连 (支持 --resume 继承上下文)
    # ------------------------------------------------------------------ #

    async def _reconnect_and_respond(
        self,
        thread: discord.Thread,
        session: SessionInfo,
        message_text: str,
    ) -> None:
        """为已失效的会话重建 AI 连接并响应当前消息

        优先使用 CLI session ID 通过 --resume 恢复完整对话上下文,
        如果没有 cli_session_id 则创建全新会话 (无历史上下文)。

        Args:
            thread: Discord Thread
            session: 持久化的会话信息 (内部 session_id 已过期)
            message_text: 用户当前消息内容
        """
        try:
            if session.cli_session_id:
                # 有 CLI session ID → 通过 --resume 继承上下文
                logger.info(
                    f"Thread {thread.id}: 使用 --resume 恢复上下文 "
                    f"(cli_session={session.cli_session_id[:12]}...)"
                )
                new_session_id, stream = await self.claude_service.resume_session_stream(
                    cli_session_id=session.cli_session_id,
                    instruction=message_text,
                    allowed_tools=session.allowed_tools,
                )
            else:
                # 无 CLI session ID → 创建全新会话
                logger.warning(
                    f"Thread {thread.id}: 无 cli_session_id,创建新会话 (无历史上下文)"
                )
                new_session_id, stream = await self.claude_service.start_session_stream(
                    instruction=message_text,
                    allowed_tools=session.allowed_tools,
                )

        except Exception as e:
            logger.opt(exception=True).error(
                f"Thread {thread.id} 重建 AI 连接失败: {e}"
            )
            # 如果 resume 失败,降级为新建会话
            if session.cli_session_id:
                logger.warning(
                    f"Thread {thread.id}: --resume 失败,降级为新建会话"
                )
                try:
                    new_session_id, stream = await self.claude_service.start_session_stream(
                        instruction=message_text,
                        allowed_tools=session.allowed_tools,
                    )
                except Exception as e2:
                    logger.opt(exception=True).error(
                        f"Thread {thread.id} 新建会话也失败: {e2}"
                    )
                    await thread.send(f"❌ 重建 AI 连接失败: {e2}")
                    return
            else:
                await thread.send(f"❌ 重建 AI 连接失败: {e}")
                return

        # 更新持久化存储中的 session_id
        self._store.update_session_id(thread.id, new_session_id)

        logger.info(
            f"Thread {thread.id} AI 连接已重建: "
            f"new_session={new_session_id[:12]}..., "
            f"bot={session.bot_type.value}"
        )

        # 流式输出
        await self._stream_to_discord(
            channel=thread,
            stream=stream,
        )

        # 流结束后保存新的 CLI session ID
        self._save_cli_session_id(thread.id, new_session_id)

    # ------------------------------------------------------------------ #
    #  内部方法 — CLI session ID 持久化
    # ------------------------------------------------------------------ #

    def _save_cli_session_id(self, thread_id: int, session_id: str) -> None:
        """从 ClaudeAgentService 获取 CLI session ID 并持久化到 SessionStore

        在每次流式响应结束后调用。CLI session ID 来自 ResultMessage,
        是 Claude CLI 级别的会话标识,用于 --resume 恢复上下文。

        Args:
            thread_id: Discord Thread ID
            session_id: 内部会话 ID (用于从 ClaudeAgentService 查询)
        """
        cli_sid: str | None = self.claude_service.get_cli_session_id(session_id)
        if cli_sid:
            session: SessionInfo | None = self._store.get(thread_id)
            if session is not None:
                session.cli_session_id = cli_sid
                self._store.put(thread_id, session)  # 刷盘
                logger.info(
                    f"Thread {thread_id}: 已保存 CLI session_id={cli_sid[:12]}..."
                )

    # ------------------------------------------------------------------ #
    #  内部方法 — 流式输出到 Discord
    # ------------------------------------------------------------------ #

    async def _stream_to_discord(
        self,
        channel: discord.abc.Messageable,
        stream: AsyncGenerator[str, None],
        mention_prefix: str = "",
    ) -> None:
        """将流式文本输出到 Discord,通过编辑消息实现逐步显示

        工作原理:
        1. 收到第一个文本片段时创建消息 (末尾带闪烁光标 "▌")
        2. 每隔 EDIT_INTERVAL 秒编辑消息以追加新内容
        3. 当消息长度接近 Discord 上限时,定型当前消息并创建新消息
        4. 流结束后移除光标

        Args:
            channel: 目标频道/Thread
            stream: 文本片段异步生成器
            mention_prefix: 消息前缀 (如 "<@user_id>\\n"),仅用于首条消息
        """
        buffer: str = mention_prefix  # 当前消息的文本缓冲
        current_msg: discord.Message | None = None
        last_edit: float = 0.0
        has_content: bool = False

        try:
            async for chunk in stream:
                if not chunk:
                    continue

                has_content = True
                buffer += chunk
                now: float = time.monotonic()

                # --- 消息溢出: 需要分割 ---
                while len(buffer) > _SAFE_MAX_LENGTH:
                    # 在换行符处找到安全的分割点
                    split_at: int = buffer.rfind("\n", 0, _SAFE_MAX_LENGTH)
                    if split_at <= 0:
                        split_at = _SAFE_MAX_LENGTH

                    finalized_text: str = buffer[:split_at]
                    buffer = buffer[split_at:].lstrip("\n")

                    # 定型当前消息 (移除光标)
                    if current_msg is not None:
                        try:
                            await current_msg.edit(content=finalized_text)
                        except discord.HTTPException:
                            pass
                    else:
                        await channel.send(finalized_text)

                    # 为剩余内容准备新消息
                    current_msg = None

                # --- 首条消息 / 定期刷新 ---
                if current_msg is None:
                    current_msg = await channel.send(buffer + _STREAM_CURSOR)
                    last_edit = now
                elif now - last_edit >= _STREAM_EDIT_INTERVAL:
                    try:
                        await current_msg.edit(content=buffer + _STREAM_CURSOR)
                    except discord.HTTPException:
                        pass
                    last_edit = now

        except Exception as e:
            logger.opt(exception=True).error(f"流式输出异常: {e}")
            error_suffix: str = f"\n\n❌ 流式输出中断: {e}"
            if current_msg is not None:
                try:
                    await current_msg.edit(content=buffer + error_suffix)
                except discord.HTTPException:
                    await channel.send(error_suffix)
            else:
                await channel.send(
                    mention_prefix + error_suffix if not has_content else error_suffix
                )
            return

        # --- 流结束: 移除光标,显示最终内容 ---
        if current_msg is not None:
            final_content: str = buffer if buffer.strip() else "_(空响应)_"
            try:
                await current_msg.edit(content=final_content)
            except discord.HTTPException:
                pass
        elif not has_content:
            empty_content: str = (
                f"{mention_prefix}_(空响应)_" if mention_prefix else "_(空响应)_"
            )
            await channel.send(empty_content)

    # ------------------------------------------------------------------ #
    #  内部方法 — 长消息拆分 (非流式备用)
    # ------------------------------------------------------------------ #

    @staticmethod
    async def _send_long_message(
        channel: discord.abc.Messageable,
        content: str,
    ) -> None:
        """发送可能超长的消息,按需拆分为多条

        Discord 单条消息上限 2000 字符,此方法按换行符拆分长消息。
        仅用于非流式场景 (如错误消息)。

        Args:
            channel: 目标频道/Thread
            content: 要发送的文本内容
        """
        if not content.strip():
            await channel.send("_(空响应)_")
            return

        if len(content) <= _SAFE_MAX_LENGTH:
            await channel.send(content)
            return

        chunks: list[str] = []
        remaining: str = content

        while remaining:
            if len(remaining) <= _SAFE_MAX_LENGTH:
                chunks.append(remaining)
                break

            split_at: int = remaining.rfind("\n", 0, _SAFE_MAX_LENGTH)
            if split_at <= 0:
                split_at = _SAFE_MAX_LENGTH

            chunks.append(remaining[:split_at])
            remaining = remaining[split_at:].lstrip("\n")

        for chunk in chunks:
            await channel.send(chunk)

    # ------------------------------------------------------------------ #
    #  生命周期
    # ------------------------------------------------------------------ #

    async def cog_unload(self) -> None:
        """Cog 卸载时关闭所有活跃 AI 连接 (会话映射保留在磁盘)"""
        logger.info("AssistantCommands Cog 正在卸载,关闭所有 AI 连接...")
        for session in self._store.values():
            await self.claude_service.close_session(session.session_id)
        # 注意: 不清空 store,重启后仍可恢复
        logger.info("所有 AI 连接已关闭 (会话映射已保留在磁盘)")


async def setup(bot: commands.Bot) -> None:
    """加载 Cog

    Args:
        bot: Discord Bot 实例
    """
    await bot.add_cog(AssistantCommands(bot))
