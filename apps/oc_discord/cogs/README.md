# apps/oc_discord/cogs/ - Discord 业务功能

Discord Slash Commands 和事件监听的业务逻辑实现。

## 模块

| 文件 | Cog 类 | 说明 |
|------|--------|------|
| `basic.py` | `BasicCommands` | 基础命令 (`/ping`, `/info`, `/serverinfo`, `/help`) |
| `assistant.py` | `AssistantCommands` | AI 助理 (`/ask`, `/code`, `/sessions`, Thread 对话) |
| `admin.py` | `AdminCommands` | 管理命令 (`/admin reload\|load\|unload\|cogs\|shutdown`) |

## AI 助理工作流

1. 用户执行 `/ask` 或 `/code`
2. 调用 `bots.ClaudeCodeService.start_session()` 获取 session_id
3. 创建私密 Discord Thread
4. 用户在 Thread 中发消息 -> `on_message` 监听
5. 调用 `bots.ClaudeCodeService.continue_session()` 持续对话

## 创建新 Cog

```python
import discord
from discord import app_commands
from discord.ext import commands


class MyFeature(commands.Cog):
    """功能描述"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="mycommand", description="命令描述")
    async def my_command(self, interaction: discord.Interaction) -> None:
        """命令描述"""
        await interaction.response.send_message("Hello!")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MyFeature(bot))
```

## 自动加载

`cogs/` 下所有 `.py` 文件 (除 `_` 开头的) 在启动时自动加载。

## 热重载

```
/admin reload <cog_name>
```
