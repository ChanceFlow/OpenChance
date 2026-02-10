# OpenChance 架构总结

## 核心设计理念

### 三层分离架构

```
┌─────────────────────────────────────────────────────┐
│  Apps Layer (前端接入层)                              │
│  - 平台客户端封装(Discord, Telegram 等)               │
│  - 业务逻辑实现(Cogs, Commands)                      │
│  - 消息格式转换                                       │
│  - 适配器(连接 bots 和 core)                          │
└─────────────┬──────────────┬────────────────────────┘
              │              │
        调用 bots      调用 core
              │              │
    ┌─────────▼───────┐  ┌──▼──────────────────┐
    │  Bots Layer     │  │  Core Layer         │
    │  (Bot 能力层)    │  │  (公用逻辑)          │
    │                 │  │                     │
    │  - ClaudeCode   │  │  - Models           │
    │    Service      │  │  - Services         │
    │  - (未来更多    │  │  - Config           │
    │    Bot 能力)    │  │  - Utils            │
    │                 │  │                     │
    │  不依赖任何     │  │                     │
    │  平台 SDK       │  │                     │
    └─────────────────┘  └─────────────────────┘
                             ↑
                    不依赖 bots 或 apps
```

## 层次职责

### Core Layer (核心层)
**定位**: 公用逻辑库

**包含**:
- `models/` - 数据模型(Message, Platform, Session 等)
- `services/` - 通用服务(MessageHandler 等)
- `config/` - 配置管理(Settings)
- `utils/` - 工具函数(logger 等)

**特点**:
- 纯粹的公用逻辑
- 不依赖任何平台 SDK
- 可被 bots 和 apps 调用

### Bots Layer (Bot 能力层)
**定位**: Bot 的核心能力,不依赖任何平台 SDK

**包含**:
- `claude_code.py` - Claude Code CLI 调用能力(会话管理、指令执行)
- (未来) 更多 Bot 能力模块

**特点**:
- 定义 Bot "能做什么"(能力抽象)
- 不依赖 Discord / Telegram 等平台 SDK
- 纯粹的能力封装(如调用 Claude Code CLI)
- 可被任何 apps 层调用

### Apps Layer (前端接入层)
**定位**: 平台接入 + 业务逻辑

**包含**:
- `oc_discord/` - Discord 应用
  - `client.py` - Discord SDK 客户端封装
  - `adapter.py` - 应用适配器(连接 client、bots、core)
  - `cogs/` - Discord 业务功能(Slash Commands、Thread 管理等)
  - `main.py` - 应用入口

**特点**:
- 封装平台 SDK(如 discord.py)
- 实现消息转换(平台格式 -> 统一 Message)
- 实现业务逻辑(如 Thread 中的 AI 对话)
- 连接 bots 能力和 core 服务

## 依赖关系

```
Apps Layer
├─> 调用 Bots Layer (Bot 能力)
└─> 调用 Core Layer (公用服务)

Bots Layer
└─> 不依赖任何平台 SDK,纯能力抽象

Core Layer
└─> 独立存在,不依赖其他层
```

## 典型文件示例

### Core Layer 文件

```python
# core/services/message_handler.py
class MessageHandler:
    """公用消息处理服务"""
    async def handle_message(self, message: Message) -> str:
        # 处理消息的通用逻辑
        pass
```

### Bots Layer 文件

```python
# bots/claude_code.py
class ClaudeCodeService:
    """Claude Code CLI 调用能力 (不依赖任何平台)"""
    async def start_session(self, instruction: str) -> tuple[str, str]:
        # 启动 Claude Code 会话
        pass

    async def continue_session(self, session_id: str, message: str) -> str:
        # 继续会话
        pass
```

### Apps Layer 文件

```python
# apps/oc_discord/client.py
class DiscordClient:
    """Discord 平台客户端封装"""
    def __init__(self, token: str):
        self.bot = commands.Bot(...)

# apps/oc_discord/adapter.py
class OCDiscordAdapter:
    """Discord 应用适配器"""
    def __init__(self, settings):
        self.discord_client = DiscordClient(...)  # 平台接入
        self.message_handler = MessageHandler(...)  # core 服务

# apps/oc_discord/cogs/assistant.py
class AssistantCommands(commands.Cog):
    """业务逻辑: 使用 bots 层的 ClaudeCodeService 能力"""
    def __init__(self, bot):
        self.claude_service = ClaudeCodeService(...)  # bots 能力
```

## 扩展新平台的步骤

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
    def __init__(self, settings):
        self.tg_client = TelegramClient(...)
        self.message_handler = MessageHandler(...)  # 复用 core 服务
```

### 3. 创建业务逻辑

```python
# apps/oc_telegram/handlers/assistant.py
class AssistantHandler:
    def __init__(self):
        self.claude_service = ClaudeCodeService(...)  # 复用 bots 能力
```

### 4. 创建应用入口

```python
# apps/oc_telegram/main.py
async def main():
    adapter = OCTelegramAdapter(settings)
    await adapter.start()
```

## 优势

### 1. 清晰的职责分离
- Core: 公用逻辑
- Bots: Bot 能力抽象(不依赖平台)
- Apps: 平台接入 + 业务逻辑

### 2. 高度可复用
- ClaudeCodeService 可被 Discord / Telegram / CLI 等任何前端使用
- MessageHandler 可被所有平台使用
- Models 定义一次,到处使用

### 3. 易于测试
- Bots 层不依赖平台 SDK,可直接单元测试
- Core 层完全独立,可直接单元测试
- Apps 层可 mock bots 和 core

### 4. 低耦合
- Core 不依赖任何层,最稳定
- Bots 不依赖平台 SDK,很稳定
- Apps 依赖两者 + 平台 SDK,变更隔离在应用内

## 关键设计决策

### Bots 层 = Bot 能力,不是平台封装
**原因**: Bots 层定义"Bot 能做什么"(如调用 Claude Code),而不是"Bot 用什么平台"。平台相关的 SDK 封装放在 Apps 层。

### Apps 层 = 前端接入 + 业务
**原因**: 每个平台的 SDK 封装、业务逻辑、消息格式都不同,统一放在 Apps 层管理。

### Core 层不包含 Bot 类
**原因**: Bot 能力与平台强相关,不是公用逻辑。

## 文件清单

```
OpenChance/
├── core/                          # 公用逻辑
│   ├── models/
│   │   ├── message.py            # Message 模型
│   │   ├── session.py            # Session 模型
│   │   ├── platform.py           # Platform 枚举
│   │   └── user.py               # User 模型
│   ├── services/
│   │   └── message_handler.py    # 消息处理服务
│   ├── config/
│   │   └── settings.py           # 配置
│   └── utils/
│       └── logger.py             # 日志
│
├── bots/                          # Bot 能力层 (不依赖平台 SDK)
│   └── claude_code.py            # Claude Code CLI 能力
│
└── apps/                          # 前端接入层
    └── oc_discord/               # Discord 应用
        ├── client.py             # Discord SDK 客户端
        ├── adapter.py            # 应用适配器
        ├── cogs/                 # 业务功能 (Slash Commands)
        │   ├── assistant.py      # AI 助理命令
        │   ├── basic.py          # 基础命令
        │   └── admin.py          # 管理命令
        └── main.py               # 入口
```

## 总结

这个架构的核心思想是:**能力与平台分离**

- **Core**: "我提供公用工具,谁都可以用"
- **Bots**: "我定义 Bot 能做什么,不关心用什么平台"
- **Apps**: "我接入具体平台,实现具体业务"
