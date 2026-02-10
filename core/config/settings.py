"""应用配置设置"""
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class Settings:
    """应用配置"""

    # Discord 配置
    discord_token: str
    bot_owner_id: Optional[int] = None

    # 助理配置
    assistant_name: str = "OpenChance"
    assistant_timezone: str = "Asia/Shanghai"

    # 项目路径
    project_root: Path = Path(__file__).parent.parent.parent

    @classmethod
    def from_env(cls) -> "Settings":
        """从环境变量加载配置"""
        token = os.getenv("DISCORD_BOT_TOKEN")
        if not token:
            raise ValueError("DISCORD_BOT_TOKEN 环境变量未设置")

        owner_id_str = os.getenv("BOT_OWNER_ID")
        owner_id = int(owner_id_str) if owner_id_str else None

        return cls(
            discord_token=token,
            bot_owner_id=owner_id,
            assistant_name=os.getenv("ASSISTANT_NAME", "OpenChance"),
            assistant_timezone=os.getenv("ASSISTANT_TIMEZONE", "Asia/Shanghai"),
        )
