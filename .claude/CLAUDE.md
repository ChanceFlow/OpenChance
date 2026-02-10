# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目简介

OpenChance 是一个跨平台的 AI 私人助理机器人项目,采用三层分离架构设计。

## 三层架构设计

**核心理念**: 能力与平台分离

```
Apps Layer (前端接入层)
  ├─> 调用 Bots Layer (Bot 能力)
  └─> 调用 Core Layer (公用服务)

Bots Layer (Bot 能力层)
  └─> 不依赖任何平台 SDK,纯能力抽象

Core Layer (公用逻辑)
  └─> 独立存在,不依赖其他层
```

### 层次职责

- **Core Layer** (`core/`): 公用逻辑库
  - 不依赖任何平台或 Bot
  - 包含: models, services, config, utils
  - 不包含任何 Bot 相关类

- **Bots Layer** (`bots/`): Bot 能力层
  - 定义 Bot 的核心能力(如 ClaudeCodeService)
  - **不依赖任何平台 SDK**(不 import discord / telegram 等)
  - 纯粹的能力封装

- **Apps Layer** (`apps/`): 前端接入 + 业务逻辑
  - 平台 SDK 客户端封装(如 `apps/oc_discord/client.py`)
  - 适配器连接 bots 和 core(如 `apps/oc_discord/adapter.py`)
  - 业务功能实现(如 `apps/oc_discord/cogs/`)
  - 消息转换(平台格式 -> 统一 Message 模型)

### 关键设计决策

1. **Bots 层 = 能力层** - 定义"Bot 能做什么",不关心"用什么平台"
2. **Apps 层 = 平台接入 + 业务** - 平台 SDK 封装和业务逻辑都在这里
3. **消息转换在 Apps 层** - 不同应用对同一平台可能有不同的转换需求
4. **Core 层不包含 Bot 类** - Bot 能力不是公用逻辑

## 常用命令

### 依赖管理
```bash
# 安装依赖
uv sync

# 添加新依赖
uv add <package-name>
```

### 运行应用
```bash
# Discord 应用
python apps/oc_discord/main.py

# 或使用启动脚本
./run_discord.sh
```

### 代码检查
```bash
# 语法检查
python -m py_compile <file.py>

# 批量检查
python -m py_compile core/**/*.py bots/**/*.py apps/**/*.py
```

## 开发规范

### 类型注解要求
- **所有函数必须有类型注解**,包括参数和返回值
- 禁止使用非类型化的容器类型作为函数参数
  - `def foo(data: dict)` -> `def foo(data: dict[str, int])`
  - `def foo(data: UserModel)` -> OK

### 结构化数据类型选择
- 处理外部数据: 使用 `Pydantic BaseModel`(运行时验证)
- 内部数据结构: 使用 `@dataclass`(标准库)
- 字典结构标注: 使用 `TypedDict`(保持 dict 形式)

### 代码风格
- 遵循 PEP 8 规范
- 行长度限制 79 字符
- 使用 ruff 进行格式化和 linting
- 所有公共函数和类必须有 docstring(简体中文)

## Discord 应用开发

### 创建新的 Cog

在 `apps/oc_discord/cogs/` 下创建新文件:

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

Cog 会自动加载,运行时可用 `/admin reload` 热重载。

### 管理员命令

- `/admin reload <cog>` - 重载 Cog
- `/admin load <cog>` - 加载 Cog
- `/admin unload <cog>` - 卸载 Cog
- `/admin cogs` - 列出所有 Cog
- `/admin shutdown` - 关闭机器人

## 添加新平台支持

### 1. 在 Apps 层创建平台客户端

```python
# apps/oc_telegram/client.py
class TelegramClient:
    """Telegram 平台客户端封装"""
    def __init__(self, token: str):
        # 封装 Telegram SDK
        pass
```

### 2. 创建适配器

```python
# apps/oc_telegram/adapter.py
class OCTelegramAdapter:
    def __init__(self, settings: Settings):
        self.tg_client = TelegramClient(...)
        self.message_handler = MessageHandler(...)  # 复用 core
```

### 3. 在业务层使用 bots 能力

```python
# apps/oc_telegram/handlers/assistant.py
from bots.claude_code import ClaudeCodeService  # 复用 bots 能力

class AssistantHandler:
    def __init__(self):
        self.claude_service = ClaudeCodeService(...)
```

## 环境配置

在项目根目录创建 `.env` 文件:

```ini
DISCORD_BOT_TOKEN=your_bot_token_here
BOT_OWNER_ID=your_discord_user_id
ASSISTANT_NAME=OpenChance
ASSISTANT_TIMEZONE=Asia/Shanghai
```

Discord Bot 需要启用以下 Intents:
- MESSAGE CONTENT INTENT
- SERVER MEMBERS INTENT

## 日志系统

- Discord 应用: `logs/discord.log`
- 使用 loguru 记录日志
- 所有关键操作必须记录日志

## 数据流示例

```
用户消息
  |
apps.oc_discord.client.DiscordClient (接收消息)
  |
apps.oc_discord.adapter.OCDiscordAdapter (转换为 Message 模型)
  |
core.services.MessageHandler (处理消息)
  |
返回响应
  |
apps.OCDiscordAdapter (发送回复)
  |
用户看到响应
```

### AI Thread 对话流

```
用户 /code 或 /ask
  |
apps.oc_discord.cogs.assistant (Slash Command)
  |
bots.ClaudeCodeService.start_session() (Bot 能力)
  |
创建 Discord Thread + 返回初始响应
  |
用户在 Thread 中发消息
  |
apps.oc_discord.cogs.assistant.on_message (监听)
  |
bots.ClaudeCodeService.continue_session() (Bot 能力)
  |
回复到 Thread
```

## 关键文件

- `core/models/message.py` - 统一消息模型
- `core/models/session.py` - 会话模型
- `core/services/message_handler.py` - 消息处理服务
- `bots/claude_code.py` - Claude Code CLI 能力 (Bot 能力层)
- `apps/oc_discord/client.py` - Discord 平台客户端
- `apps/oc_discord/adapter.py` - Discord 应用适配器
- `apps/oc_discord/cogs/` - Discord 业务功能模块

## 注意事项

### 工具调用限制
- Write/Edit 工具: 单次写入不能过大,否则会失败
- 解决方案: 拆分为多次小批量操作
- Bash 命令: 将大参数写入 `/tmp` 临时文件,然后通过文件路径引用

### Git 提交规范
- **所有 commit message 必须使用简体中文**
- 格式遵循 Conventional Commits: `feat(api): 添加用户认证功能`
- **禁止添加 Co-Authored-By 标识**

### 禁止事项
- 在任何地方署名 Anthropic、Claude、LLM 或 AI 相关标识
- 在生成内容中添加 emoji(除非用户明确要求)
- Core 层依赖 Bots 或 Apps 层
- Bots 层依赖任何平台 SDK
