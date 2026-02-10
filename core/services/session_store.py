"""会话持久化存储

基于 JSON 文件的 Thread → SessionInfo 映射存储。
Bot 重启后可从文件恢复会话映射,配合 AI Bot 服务实现会话重连。
"""

import json
from pathlib import Path
from typing import Any, Iterator

from loguru import logger

from core.models.session import SessionInfo


class SessionStore:
    """JSON 文件持久化的会话存储

    同时维护内存字典和磁盘文件,保证两者一致。
    所有写操作 (put / remove / clear) 会自动刷盘。

    典型用法::

        store = SessionStore(Path("data/sessions.json"))
        store.load()  # 启动时从文件恢复

        store.put(thread_id, session_info)   # 创建/更新
        session = store.get(thread_id)       # 查询
        store.remove(thread_id)              # 删除
    """

    def __init__(self, store_path: Path) -> None:
        """初始化会话存储

        Args:
            store_path: JSON 持久化文件路径
        """
        self._path: Path = store_path
        self._sessions: dict[int, SessionInfo] = {}

    # ------------------------------------------------------------------ #
    #  生命周期
    # ------------------------------------------------------------------ #

    def load(self) -> int:
        """从文件加载会话到内存

        如果文件不存在或格式错误,会以空状态启动并记录警告。

        Returns:
            成功加载的会话数量
        """
        if not self._path.exists():
            logger.info(f"会话存储文件不存在,以空状态启动: {self._path}")
            return 0

        try:
            raw: str = self._path.read_text(encoding="utf-8")
            data: dict[str, Any] = json.loads(raw)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"读取会话存储文件失败,以空状态启动: {e}")
            return 0

        loaded: int = 0
        for thread_id_str, session_data in data.items():
            try:
                thread_id: int = int(thread_id_str)
                session: SessionInfo = SessionInfo.from_dict(session_data)
                self._sessions[thread_id] = session
                loaded += 1
            except (ValueError, KeyError, TypeError) as e:
                logger.warning(
                    f"跳过无效会话记录 thread_id={thread_id_str}: {e}"
                )

        logger.info(f"从文件恢复了 {loaded} 个会话映射")
        return loaded

    # ------------------------------------------------------------------ #
    #  CRUD
    # ------------------------------------------------------------------ #

    def get(self, thread_id: int) -> SessionInfo | None:
        """查询指定 Thread 的会话

        Args:
            thread_id: Discord Thread ID

        Returns:
            SessionInfo 或 None
        """
        return self._sessions.get(thread_id)

    def put(self, thread_id: int, session: SessionInfo) -> None:
        """创建或更新会话映射 (自动刷盘)

        Args:
            thread_id: Discord Thread ID
            session: 会话信息
        """
        self._sessions[thread_id] = session
        self._flush()

    def remove(self, thread_id: int) -> SessionInfo | None:
        """删除会话映射 (自动刷盘)

        Args:
            thread_id: Discord Thread ID

        Returns:
            被删除的 SessionInfo 或 None
        """
        session: SessionInfo | None = self._sessions.pop(thread_id, None)
        if session is not None:
            self._flush()
        return session

    def clear(self) -> None:
        """清空所有会话 (自动刷盘)"""
        self._sessions.clear()
        self._flush()

    def update_session_id(self, thread_id: int, new_session_id: str) -> None:
        """更新指定 Thread 的 session_id (重连后更新,自动刷盘)

        Args:
            thread_id: Discord Thread ID
            new_session_id: 新的 AI Bot session ID
        """
        session: SessionInfo | None = self._sessions.get(thread_id)
        if session is not None:
            session.session_id = new_session_id
            self._flush()

    # ------------------------------------------------------------------ #
    #  查询
    # ------------------------------------------------------------------ #

    def __len__(self) -> int:
        return len(self._sessions)

    def __bool__(self) -> bool:
        return bool(self._sessions)

    def __contains__(self, thread_id: int) -> bool:
        return thread_id in self._sessions

    def __iter__(self) -> Iterator[int]:
        return iter(self._sessions)

    def values(self) -> Iterator[SessionInfo]:
        """遍历所有会话"""
        yield from self._sessions.values()

    def items(self) -> Iterator[tuple[int, SessionInfo]]:
        """遍历所有 (thread_id, session) 对"""
        yield from self._sessions.items()

    # ------------------------------------------------------------------ #
    #  内部方法
    # ------------------------------------------------------------------ #

    def _flush(self) -> None:
        """将内存状态序列化写入 JSON 文件"""
        data: dict[str, Any] = {
            str(tid): session.to_dict()
            for tid, session in self._sessions.items()
        }

        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as e:
            logger.error(f"写入会话存储文件失败: {e}")
