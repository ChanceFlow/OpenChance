"""Discord 应用端点入口

此应用专门用于 Discord 平台,包含 Discord 特定的命令、Cogs 和逻辑。
"""
import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

# 将项目根目录添加到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from apps.oc_discord.adapter import OCDiscordAdapter
from core.config import Settings
from core.utils import setup_logging


async def main() -> None:
    """Discord 应用主函数"""
    # 加载环境变量
    load_dotenv()

    # 设置日志 (loguru)
    log_dir = project_root / "logs"
    setup_logging(log_file=log_dir / "discord.log")

    # 加载配置
    try:
        settings = Settings.from_env()
        logger.info("配置加载成功")
    except ValueError as e:
        logger.error(f"配置加载失败: {e}")
        logger.error("请检查 .env 文件或环境变量设置")
        return

    # 创建 OC-Discord 适配器
    adapter = OCDiscordAdapter(settings)
    logger.info("OC-Discord 适配器初始化成功")

    # Cogs 路径
    cogs_path = Path(__file__).parent / "cogs"

    try:
        # 加载 Cogs
        async with adapter.get_discord_bot():
            await adapter.load_cogs(cogs_path)
            logger.info("Cogs 加载完成")

            # 启动机器人
            logger.info("正在启动 Discord 机器人...")
            await adapter.start()
    except KeyboardInterrupt:
        logger.info("收到中断信号,正在关闭...")
    except Exception as e:
        logger.opt(exception=True).error(f"机器人运行出错: {e}")
    finally:
        await adapter.stop()
        logger.info("Discord 机器人已停止")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("程序已终止")
