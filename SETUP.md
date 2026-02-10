# OpenChance 安装配置指南 (使用 uv)

## 1. 创建 Discord Bot

### 步骤 1: 访问 Discord Developer Portal
1. 访问 https://discord.com/developers/applications
2. 点击 "New Application"
3. 输入应用名称(如 "OpenChance")

### 步骤 2: 配置 Bot
1. 进入 "Bot" 页面
2. 点击 "Add Bot"
3. 点击 "Reset Token" 获取 Bot Token(保存好,只显示一次!)

### 步骤 3: 启用 Intents
在 "Bot" 页面的 "Privileged Gateway Intents" 中启用:
- ✅ `PRESENCE INTENT`
- ✅ `SERVER MEMBERS INTENT`
- ✅ `MESSAGE CONTENT INTENT`

### 步骤 4: 生成邀请链接
1. 进入 "OAuth2" > "URL Generator"
2. 勾选 Scopes:
   - ✅ `bot`
   - ✅ `applications.commands`
3. 勾选 Bot Permissions:
   - ✅ `Send Messages`
   - ✅ `Send Messages in Threads`
   - ✅ `Embed Links`
   - ✅ `Attach Files`
   - ✅ `Read Message History`
   - ✅ `Use Slash Commands`
4. 复制生成的 URL,在浏览器中打开并选择服务器

## 2. 配置环境变量

创建 `.env` 文件:
```bash
cp .env.example .env
```

编辑 `.env`,填入你的配置:
```ini
# Discord Bot Token(从 Developer Portal 获取)
DISCORD_BOT_TOKEN=你的_bot_token

# 你的 Discord 用户 ID(右键你的头像 > 复制用户 ID)
BOT_OWNER_ID=你的_discord_用户id

# 助理配置
ASSISTANT_NAME=OpenChance
ASSISTANT_TIMEZONE=Asia/Shanghai

# Claude Code 配置
CLAUDE_CODE_WORKING_DIR=~
CLAUDE_CODE_TIMEOUT=300
```

### 如何获取你的 Discord 用户 ID:
1. 在 Discord 中启用开发者模式: 设置 > 高级 > 开发者模式
2. 右键点击你的头像
3. 选择 "复制用户 ID"

## 3. 安装 uv 和依赖

### 安装 uv (如果还没有)

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# 或使用 pip
pip install uv

# 或使用 Homebrew (macOS)
brew install uv
```

### 安装项目依赖

```bash
# 使用 uv (推荐) - 会自动创建虚拟环境
uv sync

# 或使用 pip
pip install -e .
```

`uv sync` 会自动:
- 创建 `.venv` 虚拟环境
- 安装 `pyproject.toml` 中的所有依赖
- 锁定依赖版本到 `uv.lock`

## 4. 安装 Claude Code CLI(可选)

如果需要使用 `/claudecode` 功能:

```bash
npm install -g @anthropic-ai/claude-code
```

## 5. 运行机器人

### 方式 1: 使用启动脚本 (推荐)

```bash
./run_discord.sh
```

### 方式 2: 使用 uv 运行

```bash
uv run python apps/oc-discord/main.py
```

### 方式 3: 手动激活虚拟环境

```bash
# 激活虚拟环境
source .venv/bin/activate  # Linux/macOS
# 或
.venv\Scripts\activate      # Windows

# 运行应用
python apps/oc-discord/main.py
```

### 成功启动的标志:
```
2026-02-10 13:30:00 - openchance - INFO - 配置加载成功
2026-02-10 13:30:01 - openchance - INFO - 正在加载 OpenChance...
2026-02-10 13:30:01 - openchance - INFO - 所有功能模块加载完成
2026-02-10 13:30:02 - openchance - INFO - 正在同步斜杠命令...
2026-02-10 13:30:03 - openchance - INFO - 斜杠命令同步完成
2026-02-10 13:30:03 - openchance - INFO - ✓ OpenChance#1234 已上线!
```

## 6. 测试命令

在 Discord 中输入 `/` 查看所有可用命令:
- `/ping` - 测试连接
- `/help` - 查看帮助
- `/ccstatus` - 检查 Claude Code CLI 状态
- `/claudecode <指令>` - 执行 Claude Code 指令

## 常见问题

### Q: 斜杠命令不显示?
A: 斜杠命令同步可能需要 1-5 分钟,请耐心等待

### Q: Claude Code CLI 不可用?
A: 确认已安装: `npm install -g @anthropic-ai/claude-code`

### Q: Bot 无法读取消息?
A: 检查 Developer Portal 中是否启用了 "MESSAGE CONTENT INTENT"

## uv 常用命令

```bash
# 安装依赖(根据 pyproject.toml 和 uv.lock)
uv sync

# 添加新依赖
uv add package-name

# 添加开发依赖
uv add --dev package-name

# 移除依赖
uv remove package-name

# 更新所有依赖
uv sync --upgrade

# 更新特定依赖
uv add --upgrade package-name

# 运行命令(无需激活虚拟环境)
uv run python script.py
uv run pytest

# 查看依赖树
uv tree

# 锁定依赖但不安装
uv lock
```

## 开发建议

### 使用 ruff 格式化代码

```bash
# 安装 ruff
uv add --dev ruff

# 格式化代码
uv run ruff format .

# 检查代码
uv run ruff check .

# 自动修复
uv run ruff check --fix .
```

### 代码类型检查

```bash
# 安装 mypy
uv add --dev mypy

# 类型检查
uv run mypy core/ bots/ apps/
```

## 生产部署

### 使用 systemd (Linux)

创建服务文件 `/etc/systemd/system/openchance-discord.service`:

```ini
[Unit]
Description=OpenChance Discord Bot
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/OpenChance
Environment="PATH=/path/to/OpenChance/.venv/bin"
ExecStart=/path/to/OpenChance/.venv/bin/python apps/oc-discord/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动服务:

```bash
sudo systemctl daemon-reload
sudo systemctl enable openchance-discord
sudo systemctl start openchance-discord
sudo systemctl status openchance-discord
```

查看日志:

```bash
# 实时日志
sudo journalctl -u openchance-discord -f

# 应用日志
tail -f logs/discord.log
```

## 后续扩展

可以添加的功能:
- 提醒功能(定时任务)
- 笔记管理
- 文件上传/下载
- 多项目管理
- 指令历史记录

## 更多文档

- [架构设计](ARCHITECTURE.md) - 了解项目架构
- [架构总结](ARCHITECTURE_SUMMARY.md) - 架构核心理念
- [项目总结](SUMMARY.md) - 项目概览
- [Discord 应用文档](apps/oc-discord/README.md) - Discord 应用详细说明
