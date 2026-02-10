"""Claude Code Bot 能力

提供 Claude Code CLI 的调用能力,支持单次指令和会话管理。
这是 bots 能力层的核心模块,不依赖任何平台 SDK。
"""

import asyncio
import json
from pathlib import Path

from loguru import logger


class ClaudeCodeService:
    """Claude Code CLI 调用服务

    支持两种模式:
    1. 单次指令 (execute_instruction) — 无状态调用
    2. 会话模式 (start_session / continue_session) — 带 session_id 的持久会话
    """

    def __init__(self, working_dir: Path | None = None) -> None:
        """初始化服务

        Args:
            working_dir: 工作目录,默认为用户主目录
        """
        self.working_dir: Path = working_dir or Path.home()

    # ------------------------------------------------------------------ #
    #  会话模式: start_session / continue_session
    # ------------------------------------------------------------------ #

    async def start_session(
        self,
        instruction: str,
        allowed_tools: list[str] | None = None,
        timeout: int = 300,
    ) -> tuple[str, str]:
        """启动一个新的 Claude Code 会话

        使用 ``claude -p "..." --output-format json`` 获取 session_id。

        Args:
            instruction: 初始指令
            allowed_tools: 允许自动执行的工具列表 (如 ["Bash", "Read", "Edit"])
            timeout: 超时时间 (秒)

        Returns:
            (session_id, response_text) — 会话 ID 和首次响应文本

        Raises:
            RuntimeError: 当 CLI 执行失败或无法解析 session_id 时
        """
        cmd: list[str] = [
            "claude",
            "-p",
            instruction,
            "--output-format",
            "json",
        ]

        if allowed_tools:
            cmd.extend(["--allowedTools", ",".join(allowed_tools)])

        logger.info(f"启动 Claude Code 会话: {instruction[:100]}...")
        session_id, result = await self._run_json_command(cmd, timeout=timeout)
        logger.info(f"会话已启动, session_id={session_id}")
        return session_id, result

    async def continue_session(
        self,
        session_id: str,
        message: str,
        allowed_tools: list[str] | None = None,
        timeout: int = 300,
    ) -> str:
        """在已有会话中继续对话

        使用 ``claude -r <session_id> -p "..." --output-format json``。
        必须传入与 start_session 相同的 allowed_tools,否则 Claude Code
        可能弹出权限提示导致 headless 模式卡住。

        Args:
            session_id: 要继续的会话 ID
            message: 用户消息
            allowed_tools: 允许自动执行的工具列表 (应与 start_session 一致)
            timeout: 超时时间 (秒)

        Returns:
            AI 响应文本

        Raises:
            RuntimeError: 当 CLI 执行失败时
        """
        cmd: list[str] = [
            "claude",
            "-r",
            session_id,
            "-p",
            message,
            "--output-format",
            "json",
        ]

        if allowed_tools:
            cmd.extend(["--allowedTools", ",".join(allowed_tools)])

        logger.info(
            f"继续会话 {session_id[:12]}...: {message[:80]}..."
        )
        _, result = await self._run_json_command(cmd, timeout=timeout)
        return result

    # ------------------------------------------------------------------ #
    #  单次指令模式 (保留兼容)
    # ------------------------------------------------------------------ #

    async def execute_instruction(
        self,
        instruction: str,
        timeout: int = 300,
    ) -> tuple[bool, str]:
        """执行单次 Claude Code 指令 (无会话状态)

        Args:
            instruction: 要执行的指令
            timeout: 超时时间 (秒)

        Returns:
            (成功标志, 输出内容或错误信息)
        """
        try:
            logger.info(f"执行 Claude Code 指令: {instruction[:100]}...")

            cmd: list[str] = ["claude", "-p", instruction]

            process: asyncio.subprocess.Process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.working_dir),
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                error_msg: str = f"⏱️ 执行超时({timeout}秒)"
                logger.warning(error_msg)
                return False, error_msg

            stdout_text: str = stdout.decode("utf-8", errors="replace")
            stderr_text: str = stderr.decode("utf-8", errors="replace")

            if process.returncode == 0:
                logger.info("Claude Code 执行成功")
                return True, stdout_text or "✅ 执行完成(无输出)"
            else:
                error_msg = f"❌ 执行失败(退出码: {process.returncode})\n{stderr_text}"
                logger.error(error_msg)
                return False, error_msg

        except FileNotFoundError:
            error_msg = "❌ 未找到 claude 命令,请确认已安装 Claude Code CLI"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"❌ 执行异常: {type(e).__name__}: {str(e)}"
            logger.opt(exception=True).error(error_msg)
            return False, error_msg

    # ------------------------------------------------------------------ #
    #  工具方法
    # ------------------------------------------------------------------ #

    async def check_available(self) -> bool:
        """检查 Claude Code CLI 是否可用

        Returns:
            是否可用
        """
        try:
            process: asyncio.subprocess.Process = await asyncio.create_subprocess_exec(
                "claude",
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await process.communicate()
            return process.returncode == 0
        except FileNotFoundError:
            return False
        except Exception as e:
            logger.error(f"检查 Claude Code CLI 可用性失败: {e}")
            return False

    async def _run_json_command(
        self,
        cmd: list[str],
        timeout: int = 300,
    ) -> tuple[str, str]:
        """执行 Claude Code CLI 命令并解析 JSON 输出

        Args:
            cmd: 完整的命令参数列表
            timeout: 超时时间 (秒)

        Returns:
            (session_id, result_text)

        Raises:
            RuntimeError: 执行失败或 JSON 解析失败时
        """
        try:
            process: asyncio.subprocess.Process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.working_dir),
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                raise RuntimeError(f"⏱️ 执行超时({timeout}秒)")

            stdout_text: str = stdout.decode("utf-8", errors="replace")
            stderr_text: str = stderr.decode("utf-8", errors="replace")

            if process.returncode != 0:
                raise RuntimeError(
                    f"CLI 执行失败 (退出码: {process.returncode})\n{stderr_text}"
                )

            # 解析 JSON 输出
            # claude --output-format json 返回一个事件数组:
            # [
            #   {"type": "system", "subtype": "init", "session_id": "...", ...},
            #   {"type": "assistant", "message": {...}, ...},
            #   {"type": "result", "result": "...", "session_id": "...", ...}
            # ]
            try:
                raw_output: dict | list = json.loads(stdout_text)
            except json.JSONDecodeError as e:
                raise RuntimeError(
                    f"无法解析 JSON 输出: {e}\n原始输出: {stdout_text[:500]}"
                ) from e

            session_id, result = self._extract_session_data(raw_output)

            if not session_id:
                raise RuntimeError(
                    f"JSON 输出中未包含 session_id, 输出结构: "
                    f"{type(raw_output).__name__}"
                )

            return session_id, result

        except FileNotFoundError:
            raise RuntimeError("未找到 claude 命令,请确认已安装 Claude Code CLI")
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"执行异常: {type(e).__name__}: {e}") from e

    @staticmethod
    def _extract_session_data(raw_output: dict | list) -> tuple[str, str]:
        """从 Claude Code JSON 输出中提取 session_id 和 result

        Claude Code ``--output-format json`` 返回一个事件数组 (list),
        每个元素是一个事件 dict。需要从中提取:
        - session_id: 通常在 type="system" subtype="init" 或 type="result" 的事件中
        - result: 在 type="result" 事件的 "result" 字段中

        也兼容直接返回单个 dict 的情况。

        Args:
            raw_output: 解析后的 JSON 输出 (dict 或 list)

        Returns:
            (session_id, result_text)
        """
        # 单个 dict 的情况 (兼容)
        if isinstance(raw_output, dict):
            return (
                raw_output.get("session_id", ""),
                raw_output.get("result", ""),
            )

        # 事件数组的情况
        if not isinstance(raw_output, list):
            return "", ""

        session_id: str = ""
        result: str = ""

        for event in raw_output:
            if not isinstance(event, dict):
                continue

            # 从任意包含 session_id 的事件中提取
            if not session_id and event.get("session_id"):
                session_id = event["session_id"]

            # 从 type="result" 事件中提取最终结果
            if event.get("type") == "result" and event.get("result"):
                result = event["result"]
                # result 事件也包含 session_id
                if not session_id and event.get("session_id"):
                    session_id = event["session_id"]

        # 如果没有 result 事件,尝试从 assistant 消息中拼接文本
        if not result:
            text_parts: list[str] = []
            for event in raw_output:
                if not isinstance(event, dict):
                    continue
                if event.get("type") == "assistant":
                    msg: dict | str = event.get("message", "")
                    if isinstance(msg, dict):
                        # message.content 可能是 list[{type: "text", text: "..."}]
                        content = msg.get("content", "")
                        if isinstance(content, list):
                            for block in content:
                                if isinstance(block, dict) and block.get("text"):
                                    text_parts.append(block["text"])
                        elif isinstance(content, str):
                            text_parts.append(content)
                    elif isinstance(msg, str):
                        text_parts.append(msg)
            result = "\n".join(text_parts)

        return session_id, result
