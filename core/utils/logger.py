"""日志配置 - 基于 loguru"""
import sys
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger

# 项目根目录下的 logs 文件夹
_LOG_DIR: Path = Path(__file__).resolve().parent.parent.parent / "logs"


def setup_logging(
    app_name: str = "app",
    level: str = "INFO",
    rotation: str = "10 MB",
    retention: str = "7 days",
) -> None:
    """配置 loguru 全局日志。

    移除默认 sink，添加控制台和文件 sink。
    每次启动都会在 ``logs/`` 下生成 ``{app_name}_{timestamp}.log``，
    避免多次启动日志混在一起。应在应用启动时调用一次。

    Args:
        app_name: 应用名称，用于日志文件名前缀，例如 ``"discord"``。
        level: 日志级别，默认 INFO。
        rotation: 单个日志文件轮转大小，默认 10 MB。
        retention: 日志文件保留时间，默认 7 天。
    """
    # 移除默认 sink，避免重复输出
    logger.remove()

    # 控制台 sink - 带颜色
    logger.add(
        sys.stderr,
        level=level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
        colorize=True,
    )

    # 文件 sink — 每次启动一个新文件: appname_20260210_153045.log
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp: str = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
    log_file: Path = _LOG_DIR / f"{app_name}_{timestamp}.log"

    logger.add(
        str(log_file),
        level="DEBUG",
        format=(
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
            "{level: <8} | "
            "{name}:{function}:{line} - "
            "{message}"
        ),
        rotation=rotation,
        retention=retention,
        encoding="utf-8",
        enqueue=True,  # 线程安全
    )

    logger.info("日志系统已初始化 (loguru) -> {}", log_file.name)


__all__ = ["setup_logging", "logger"]
