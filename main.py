"""OpenChance 通用入口

此文件作为通用入口,默认启动 Discord 应用
建议直接运行具体应用: python apps/oc-discord/main.py
"""
import asyncio
import sys
from pathlib import Path

from loguru import logger

# 提示用户使用具体应用
logger.info("=" * 60)
logger.info("OpenChance 机器人")
logger.info("=" * 60)
logger.info("建议直接运行具体应用:")
logger.info("  Discord:  python apps/oc-discord/main.py")
logger.info("或使用启动脚本:")
logger.info("  ./run_discord.sh")
logger.info("当前将启动 Discord 应用...")

# 导入 Discord 应用的 main
sys.path.insert(0, str(Path(__file__).parent))
from apps.oc_discord.main import main as discord_main


if __name__ == "__main__":
    try:
        asyncio.run(discord_main())
    except KeyboardInterrupt:
        logger.info("程序已终止")
