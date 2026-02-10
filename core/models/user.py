"""用户模型"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class User:
    """统一用户模型"""

    id: str
    name: str
    platform: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None

    # 原始平台对象
    raw_user: Optional[object] = None
