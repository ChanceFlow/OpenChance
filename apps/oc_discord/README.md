# apps/oc_discord/ - Discord 应用

基于 Discord 平台的 OpenChance 应用,使用 Slash Commands 和 Thread AI 对话。

## 文件结构

```
apps/oc_discord/
├── client.py       # Discord SDK 客户端封装 (DiscordClient)
├── adapter.py      # 应用适配器 (OCDiscordAdapter)
├── main.py         # 应用入口
├── cogs/           # 业务功能模块
│   ├── basic.py    #   基础命令 (/ping, /info, /help 等)
│   ├── assistant.py#   AI 助理 (/ask, /code, Thread 对话)
│   └── admin.py    #   管理命令 (/admin reload 等)
└── README.md
```

## 模块说明

### `client.py` - DiscordClient

封装 discord.py SDK,提供:
- Gateway 连接和事件监听
- Application Commands 同步
- 全局错误处理
- Cog 自动加载

### `adapter.py` - OCDiscordAdapter

连接 DiscordClient、bots 能力和 core 服务:
- 消息格式转换 (Discord Message -> 统一 Message)
- 非命令消息分发到 MessageHandler

### `cogs/` - 业务功能

详见 [cogs/README.md](cogs/README.md)

## 运行

```bash
# 从项目根目录
python apps/oc_discord/main.py

# 或
./run_discord.sh
```

## 环境变量

```ini
DISCORD_BOT_TOKEN=your_token
BOT_OWNER_ID=your_user_id
ASSISTANT_NAME=OpenChance
ASSISTANT_TIMEZONE=Asia/Shanghai
```

## 所需 Discord 权限

### Privileged Gateway Intents
- MESSAGE CONTENT INTENT
- SERVER MEMBERS INTENT

### Bot Permissions
- Send Messages
- Read Messages / View Channels
- Embed Links
- Create Public Threads
- Create Private Threads
- Send Messages in Threads
