"""Claude Agent SDK Bot 能力

基于 Claude Agent SDK (Python) 的 AI 能力服务。
提供会话管理 (含流式输出)、单次查询、可用性检查等功能。
不依赖任何平台 SDK。
"""

import asyncio
import uuid
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

from loguru import logger

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
    query,
)
from claude_agent_sdk.types import StreamEvent


class ClaudeAgentService:
    """Claude Agent SDK 调用服务

    基于 claude-agent-sdk Python SDK,支持:
    1. 流式会话 (start_session_stream / continue_session_stream) — 推荐
    2. 非流式会话 (start_session / continue_session) — 等待完整响应
    3. 单次查询 (execute_instruction) — 无状态一次性调用
    4. 会话恢复 (resume_session_stream) — 重启后用 CLI session ID 继承上下文
    """

    def __init__(
        self,
        working_dir: Path | None = None,
        system_prompt: str | None = None,
    ) -> None:
        """初始化服务

        Args:
            working_dir: 工作目录,默认为用户主目录
            system_prompt: 全局系统提示词,默认为 None (使用 Claude 默认)
        """
        self.working_dir: Path = working_dir or Path.home()
        self.system_prompt: str | None = system_prompt

        # session_id → ClaudeSDKClient 的内存映射
        self._clients: dict[str, ClaudeSDKClient] = {}

        # session_id → CLI session ID 的映射
        # 在 _stream_response 中从 ResultMessage 捕获,供调用方读取后持久化
        self._cli_session_ids: dict[str, str] = {}

    # ------------------------------------------------------------------ #
    #  流式会话 (推荐)
    # ------------------------------------------------------------------ #

    async def start_session_stream(
        self,
        instruction: str,
        allowed_tools: list[str] | None = None,
    ) -> tuple[str, AsyncGenerator[str, None]]:
        """启动一个新的 Claude Agent 会话 (流式输出)

        创建 ClaudeSDKClient,发送初始指令,返回会话 ID 和文本流。
        调用方通过 ``async for chunk in stream`` 消费文本片段。

        Args:
            instruction: 初始指令
            allowed_tools: 允许自动执行的工具列表 (如 ["Bash", "Read", "Edit"])

        Returns:
            (session_id, text_stream) — 会话 ID 和文本片段异步生成器

        Raises:
            RuntimeError: 连接或发送指令失败时
        """
        session_id: str = str(uuid.uuid4())

        options: ClaudeAgentOptions = self._build_options(
            allowed_tools=allowed_tools,
        )

        logger.info(f"启动 Claude Agent 流式会话: {instruction[:100]}...")

        client: ClaudeSDKClient = ClaudeSDKClient(options)
        try:
            await client.connect()
            await client.query(instruction)
        except Exception as e:
            await self._safe_disconnect(client)
            raise RuntimeError(
                f"会话启动失败: {type(e).__name__}: {e}"
            ) from e

        self._clients[session_id] = client
        logger.info(f"流式会话已启动, session_id={session_id[:12]}...")

        return session_id, self._stream_response(session_id, client)

    async def resume_session_stream(
        self,
        cli_session_id: str,
        instruction: str,
        allowed_tools: list[str] | None = None,
    ) -> tuple[str, AsyncGenerator[str, None]]:
        """通过 CLI session ID 恢复已有会话 (流式输出)

        使用 Claude CLI 的 ``--resume`` 参数继承完整对话历史。
        适用于 Bot 重启后恢复之前的对话上下文。

        Args:
            cli_session_id: Claude CLI session ID (来自之前的 ResultMessage.session_id)
            instruction: 要发送的指令/消息
            allowed_tools: 允许自动执行的工具列表

        Returns:
            (session_id, text_stream) — 新的内部会话 ID 和文本片段异步生成器

        Raises:
            RuntimeError: 恢复会话失败时
        """
        session_id: str = str(uuid.uuid4())

        options: ClaudeAgentOptions = self._build_options(
            allowed_tools=allowed_tools,
            resume=cli_session_id,
        )

        logger.info(
            f"恢复 Claude Agent 流式会话: cli_session={cli_session_id[:12]}..., "
            f"instruction={instruction[:80]}..."
        )

        client: ClaudeSDKClient = ClaudeSDKClient(options)
        try:
            await client.connect()
            await client.query(instruction)
        except Exception as e:
            await self._safe_disconnect(client)
            raise RuntimeError(
                f"会话恢复失败: {type(e).__name__}: {e}"
            ) from e

        self._clients[session_id] = client
        logger.info(
            f"流式会话已恢复, session_id={session_id[:12]}..., "
            f"cli_session={cli_session_id[:12]}..."
        )

        return session_id, self._stream_response(session_id, client)

    async def continue_session_stream(
        self,
        session_id: str,
        message: str,
    ) -> AsyncGenerator[str, None]:
        """在已有会话中继续对话 (流式输出)

        ClaudeSDKClient 自动维护上下文。

        Args:
            session_id: 会话 ID
            message: 用户消息

        Returns:
            文本片段异步生成器

        Raises:
            RuntimeError: 会话不存在或发送消息失败时
        """
        client: ClaudeSDKClient | None = self._clients.get(session_id)
        if client is None:
            raise RuntimeError(f"会话不存在: {session_id}")

        logger.info(
            f"继续流式会话 {session_id[:12]}...: {message[:80]}..."
        )

        try:
            await client.query(message)
        except Exception as e:
            raise RuntimeError(
                f"会话续接失败: {type(e).__name__}: {e}"
            ) from e

        return self._stream_response(session_id, client)

    # ------------------------------------------------------------------ #
    #  非流式会话 (等待完整响应)
    # ------------------------------------------------------------------ #

    async def start_session(
        self,
        instruction: str,
        allowed_tools: list[str] | None = None,
        timeout: int = 300,
    ) -> tuple[str, str]:
        """启动一个新的 Claude Agent 会话 (非流式)

        等待完整响应后一次性返回。

        Args:
            instruction: 初始指令
            allowed_tools: 允许自动执行的工具列表
            timeout: 超时时间 (秒)

        Returns:
            (session_id, response_text) — 会话 ID 和完整响应文本

        Raises:
            RuntimeError: 连接或查询失败时
        """
        session_id, stream = await self.start_session_stream(
            instruction=instruction,
            allowed_tools=allowed_tools,
        )

        try:
            response: str = await asyncio.wait_for(
                self._exhaust_stream(stream),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            await self.close_session(session_id)
            raise RuntimeError(f"⏱️ 会话启动超时({timeout}秒)")

        return session_id, response

    async def continue_session(
        self,
        session_id: str,
        message: str,
        allowed_tools: list[str] | None = None,
        timeout: int = 300,
    ) -> str:
        """在已有会话中继续对话 (非流式)

        等待完整响应后一次性返回。

        Args:
            session_id: 会话 ID
            message: 用户消息
            allowed_tools: (未使用) 保留接口兼容
            timeout: 超时时间 (秒)

        Returns:
            完整 AI 响应文本

        Raises:
            RuntimeError: 会话不存在或查询失败时
        """
        stream: AsyncGenerator[str, None] = await self.continue_session_stream(
            session_id=session_id,
            message=message,
        )

        try:
            response: str = await asyncio.wait_for(
                self._exhaust_stream(stream),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            raise RuntimeError(f"⏱️ 会话响应超时({timeout}秒)")

        return response

    # ------------------------------------------------------------------ #
    #  会话管理
    # ------------------------------------------------------------------ #

    async def close_session(self, session_id: str) -> None:
        """关闭指定会话并释放资源

        Args:
            session_id: 要关闭的会话 ID
        """
        client: ClaudeSDKClient | None = self._clients.pop(session_id, None)
        if client is not None:
            await self._safe_disconnect(client)
            logger.info(f"会话已关闭: {session_id[:12]}...")
        self._cli_session_ids.pop(session_id, None)

    async def close_all_sessions(self) -> None:
        """关闭所有活跃会话 (用于优雅停机)"""
        session_ids: list[str] = list(self._clients.keys())
        for sid in session_ids:
            await self.close_session(sid)
        logger.info(f"已关闭 {len(session_ids)} 个活跃会话")

    def get_cli_session_id(self, session_id: str) -> str | None:
        """获取指定会话的 CLI session ID

        CLI session ID 在流式响应结束后 (收到 ResultMessage 时) 被捕获。
        调用方可在流结束后读取并持久化。

        Args:
            session_id: 内部会话 ID

        Returns:
            CLI session ID,如果尚未收到 ResultMessage 则返回 None
        """
        return self._cli_session_ids.get(session_id)

    # ------------------------------------------------------------------ #
    #  单次查询模式 (无状态)
    # ------------------------------------------------------------------ #

    async def execute_instruction(
        self,
        instruction: str,
        allowed_tools: list[str] | None = None,
        timeout: int = 300,
    ) -> tuple[bool, str]:
        """执行单次 Claude Agent 指令 (无会话状态)

        使用 query() 函数,每次创建新会话,不保留上下文。

        Args:
            instruction: 要执行的指令
            allowed_tools: 允许自动执行的工具列表
            timeout: 超时时间 (秒)

        Returns:
            (成功标志, 输出内容或错误信息)
        """
        options: ClaudeAgentOptions = self._build_options(
            allowed_tools=allowed_tools,
        )

        logger.info(f"执行单次指令: {instruction[:100]}...")

        text_parts: list[str] = []

        try:

            async def _run_query() -> None:
                async for msg in query(prompt=instruction, options=options):
                    if isinstance(msg, AssistantMessage):
                        for block in msg.content:
                            if isinstance(block, TextBlock):
                                text_parts.append(block.text)

            await asyncio.wait_for(_run_query(), timeout=timeout)

            result: str = (
                "".join(text_parts) if text_parts
                else "✅ 执行完成(无输出)"
            )
            logger.info("单次指令执行成功")
            return True, result

        except asyncio.TimeoutError:
            error_msg: str = f"⏱️ 执行超时({timeout}秒)"
            logger.warning(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"❌ 执行异常: {type(e).__name__}: {e}"
            logger.opt(exception=True).error(error_msg)
            return False, error_msg

    # ------------------------------------------------------------------ #
    #  工具方法
    # ------------------------------------------------------------------ #

    async def check_available(self) -> bool:
        """检查 Claude Agent SDK 是否可用

        Agent SDK 底层依赖 Claude Code CLI,
        因此检查 CLI 是否已安装。

        Returns:
            是否可用
        """
        try:
            process: asyncio.subprocess.Process = (
                await asyncio.create_subprocess_exec(
                    "claude",
                    "--version",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
            )
            await process.communicate()
            return process.returncode == 0
        except FileNotFoundError:
            return False
        except Exception as e:
            logger.error(f"检查 Claude CLI 可用性失败: {e}")
            return False

    @property
    def active_session_count(self) -> int:
        """当前活跃会话数量"""
        return len(self._clients)

    def has_session(self, session_id: str) -> bool:
        """检查指定会话是否存在

        Args:
            session_id: 会话 ID

        Returns:
            会话是否存在
        """
        return session_id in self._clients

    # ------------------------------------------------------------------ #
    #  内部方法
    # ------------------------------------------------------------------ #

    def _build_options(
        self,
        allowed_tools: list[str] | None = None,
        resume: str | None = None,
    ) -> ClaudeAgentOptions:
        """构建 Claude Agent SDK 选项

        Args:
            allowed_tools: 允许的工具列表
            resume: CLI session ID,用于恢复已有会话

        Returns:
            配置好的 ClaudeAgentOptions 实例
        """
        kwargs: dict[str, Any] = {
            "permission_mode": "acceptEdits",
            "cwd": str(self.working_dir),
            "include_partial_messages": True,
        }

        if allowed_tools:
            kwargs["allowed_tools"] = allowed_tools

        if self.system_prompt:
            kwargs["system_prompt"] = self.system_prompt

        if resume:
            kwargs["resume"] = resume

        return ClaudeAgentOptions(**kwargs)

    async def _stream_response(
        self,
        session_id: str,
        client: ClaudeSDKClient,
    ) -> AsyncGenerator[str, None]:
        """从 ClaudeSDKClient 流式获取响应文本片段

        混合策略 (自动降级):
        1. 优先从 StreamEvent 的 text_delta 提取 token 级增量 (真正流式)
        2. 若 SDK 未产出 StreamEvent,降级从 AssistantMessage TextBlock 提取

        同时捕获 ResultMessage.session_id 存入 ``self._cli_session_ids``,
        供调用方在流结束后读取并持久化。

        Args:
            session_id: 内部会话 ID (用于存储 CLI session ID)
            client: SDK 客户端实例

        Yields:
            文本片段
        """
        # 跟踪是否已通过 StreamEvent 收到过文本 (当前 assistant turn)
        received_stream_text: bool = False
        # 已通过 StreamEvent 输出的文本总长度 (用于 partial message 去重)
        streamed_text_len: int = 0
        # 统计各消息类型数量 (用于诊断流式是否生效)
        stats: dict[str, int] = {"stream_event": 0, "text_yields": 0, "assistant_msg": 0, "other": 0}

        async for message in client.receive_response():
            msg_type: str = type(message).__name__

            if isinstance(message, StreamEvent):
                stats["stream_event"] += 1
                event: dict[str, Any] = message.event

                # 提取 delta (Claude CLI 的 StreamEvent 格式):
                # - 完整格式: {'type': 'content_block_delta', 'delta': {'type': 'text_delta', 'text': '...'}}
                # - CLI 简化格式: {'index': 0, 'delta': {'type': 'text_delta', 'text': '...'}}
                # 两种格式都兼容: 直接检查 delta.type == "text_delta"
                delta: dict[str, Any] = event.get("delta", {})
                if delta.get("type") == "text_delta":
                    text: str = delta.get("text", "")
                    if text:
                        received_stream_text = True
                        streamed_text_len += len(text)
                        stats["text_yields"] += 1
                        yield text

            elif isinstance(message, AssistantMessage):
                stats["assistant_msg"] += 1
                if received_stream_text:
                    # 文本已通过 StreamEvent 输出,跳过 AssistantMessage 避免重复
                    logger.debug(
                        "[stream] 跳过 AssistantMessage (已通过 StreamEvent 输出)"
                    )
                else:
                    # 降级路径: SDK 未产出可用的 text_delta StreamEvent
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            logger.warning(
                                f"[stream] ⚠️ 降级: 从 AssistantMessage TextBlock "
                                f"一次性提取 ({len(block.text)} 字符) — "
                                f"StreamEvent 中未找到 text_delta"
                            )
                            yield block.text
                # 重置标记: 下一轮 assistant turn 可能有新的 StreamEvent
                received_stream_text = False
                streamed_text_len = 0

            elif isinstance(message, ResultMessage):
                # 捕获 CLI session ID 供调用方持久化 (用于 --resume 恢复上下文)
                cli_sid: str | None = getattr(message, "session_id", None)
                if cli_sid:
                    self._cli_session_ids[session_id] = cli_sid
                    logger.info(
                        f"[stream] 捕获 CLI session_id: {cli_sid[:12]}... "
                        f"(内部 session={session_id[:12]}...)"
                    )

                if hasattr(message, "subtype") and message.subtype == "error":
                    logger.warning(f"Claude Agent 返回错误状态: {message}")

            else:
                stats["other"] += 1
                logger.debug(f"[stream] 未处理的消息类型: {msg_type}")

        # 响应结束后打印统计
        logger.info(
            f"[stream] 响应统计: "
            f"StreamEvent={stats['stream_event']}, "
            f"text_yields={stats['text_yields']}, "
            f"AssistantMessage={stats['assistant_msg']}, "
            f"other={stats['other']}"
        )

    @staticmethod
    async def _exhaust_stream(
        stream: AsyncGenerator[str, None],
    ) -> str:
        """消费整个流并拼接为完整字符串

        Args:
            stream: 文本片段异步生成器

        Returns:
            拼接后的完整文本
        """
        parts: list[str] = []
        async for chunk in stream:
            parts.append(chunk)
        return "".join(parts) if parts else "(空响应)"

    @staticmethod
    async def _safe_disconnect(client: ClaudeSDKClient) -> None:
        """安全断开客户端连接

        Args:
            client: SDK 客户端实例
        """
        try:
            await client.disconnect()
        except Exception as e:
            logger.warning(f"断开客户端连接时出错: {e}")
