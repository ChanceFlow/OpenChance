"""日志配置 - 基于 loguru"""
import sys
from pathlib import Path

from loguru import logger


def setup_logging(
    log_file: Path | None = None,
    level: str = "INFO",
    rotation: str = "10 MB",
    retention: str = "7 days",
) -> None:
    """配置 loguru 全局日志

    移除默认 sink，添加控制台和可选的文件 sink。
    应在应用启动时调用一次。

    Args:
        log_file: 日志文件路径（可选）
        level: 日志级别，默认 INFO
        rotation: 日志文件轮转大小，默认 10 MB
        retention: 日志文件保留时间，默认 7 天
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

    # 文件 sink（如果指定了日志文件）
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
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

    logger.info("日志系统已初始化 (loguru)")


__all__ = ["setup_logging", "logger"]
