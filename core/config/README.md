# core/config/ - 配置管理

应用配置的统一管理。

## 模块

| 文件 | 类 | 说明 |
|------|-----|------|
| `settings.py` | `Settings` | 从环境变量加载的应用配置 |

## 配置项

| 字段 | 环境变量 | 默认值 | 说明 |
|------|---------|--------|------|
| `discord_token` | `DISCORD_BOT_TOKEN` | (必填) | Discord Bot Token |
| `bot_owner_id` | `BOT_OWNER_ID` | `None` | Bot 所有者 ID |
| `assistant_name` | `ASSISTANT_NAME` | `OpenChance` | 助理名称 |
| `assistant_timezone` | `ASSISTANT_TIMEZONE` | `Asia/Shanghai` | 时区 |

## 使用

```python
from core.config import Settings

settings = Settings.from_env()
```
