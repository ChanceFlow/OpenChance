# OpenChance

跨平台 AI 私人助理机器人,采用 **能力与平台分离** 的三层架构设计。

## 架构

```
Apps Layer (前端接入层)          Bots Layer (Bot 能力层)
  平台 SDK 封装                    不依赖任何平台 SDK
  业务逻辑 (Cogs)                  纯能力抽象
  消息格式转换                      (ClaudeCodeService 等)
       |                                |
       +------------ 调用 -------------+
       |                                |
       +-------- Core Layer (公用逻辑) --------+
                  Models / Services / Config / Utils
```

详细架构文档: [ARCHITECTURE_SUMMARY.md](ARCHITECTURE_SUMMARY.md)

## 项目结构

```
OpenChance/
├── bots/                  # Bot 能力层 (不依赖平台 SDK)
│   └── claude_code.py     #   Claude Code CLI 调用能力
│
├── apps/                  # 前端接入层
│   └── oc_discord/        #   Discord 应用
│       ├── client.py      #     Discord SDK 客户端
│       ├── adapter.py     #     应用适配器
│       ├── cogs/          #     业务功能 (Slash Commands)
│       └── main.py        #     应用入口
│
├── core/                  # 公用逻辑 (不依赖 bots 或 apps)
│   ├── models/            #   数据模型
│   ├── services/          #   通用服务
│   ├── config/            #   配置管理
│   └── utils/             #   工具函数
│
└── main.py                # 通用入口 (默认启动 Discord)
```

## 快速开始

### 前置要求

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) 包管理器
- Discord Bot Token
- (可选) Claude Code CLI

### 安装

```bash
git clone <repository-url>
cd OpenChance
uv sync
```

### 配置

```bash
cp .env.example .env
```

编辑 `.env`:

```ini
DISCORD_BOT_TOKEN=your_bot_token_here
BOT_OWNER_ID=your_discord_user_id
ASSISTANT_NAME=OpenChance
ASSISTANT_TIMEZONE=Asia/Shanghai
```

### Discord Bot 设置

1. 访问 [Discord Developer Portal](https://discord.com/developers/applications)
2. 创建应用,进入 Bot 页面获取 Token
3. 启用 Privileged Gateway Intents:
   - `MESSAGE CONTENT INTENT`
   - `SERVER MEMBERS INTENT`
4. OAuth2 > URL Generator,勾选 `bot` + `applications.commands`
5. Bot Permissions 勾选: Send Messages, Read Messages, Embed Links, Create Public/Private Threads, Send Messages in Threads
6. 用生成的 URL 邀请 Bot 到服务器

### 运行

```bash
# 推荐: 直接运行 Discord 应用
python apps/oc_discord/main.py

# 或使用启动脚本
./run_discord.sh

# 或通用入口
python main.py
```

## 可用命令 (Slash Commands)

| 命令 | 说明 |
|------|------|
| `/ping` | 检查延迟 |
| `/info` | 机器人信息 |
| `/serverinfo` | 服务器信息 |
| `/help` | 命令列表 |
| `/ask <question>` | 向 Claude 提问 (创建私密 Thread) |
| `/code <task>` | Claude 编码任务 (创建私密 Thread) |
| `/claude-status` | Claude Code CLI 状态 |
| `/sessions` | 活跃会话列表 |
| `/admin reload\|load\|unload <cog>` | 管理 Cog |
| `/admin cogs` | 列出已加载 Cog |
| `/admin shutdown` | 关闭机器人 |

## 技术栈

- **Python 3.13** + **uv**
- **discord.py 2.6+** (Application Commands)
- **Claude Code CLI** (AI 能力)
- **loguru** (日志)

## 许可证

MIT License
