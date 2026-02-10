# bots/ - Bot 能力层

定义 Bot 的核心能力,**不依赖任何平台 SDK**。

## 设计理念

`bots/` 层回答的问题是 "Bot 能做什么",而不是 "Bot 用什么平台"。
平台相关的 SDK 封装放在 `apps/` 层。

## 文件结构

```
bots/
├── __init__.py         # 导出 ClaudeCodeService
├── claude_code.py      # Claude Code CLI 调用能力
└── README.md
```

## 模块说明

### `claude_code.py` - ClaudeCodeService

提供 Claude Code CLI 的调用能力:

- **会话模式**: `start_session()` / `continue_session()` — 带 session_id 的持久对话
- **单次指令**: `execute_instruction()` — 无状态调用
- **可用性检查**: `check_available()` — 检测 CLI 是否已安装

```python
from bots import ClaudeCodeService

service = ClaudeCodeService(working_dir=Path.home())

# 启动会话
session_id, response = await service.start_session(
    instruction="帮我写一个 hello world",
    allowed_tools=["Bash", "Read", "Edit", "Write"],
)

# 继续会话
response = await service.continue_session(
    session_id=session_id,
    message="改成打印当前时间",
    allowed_tools=["Bash", "Read", "Edit", "Write"],
)
```

## 扩展新能力

在此目录下添加新的能力模块,确保:

1. 不 import 任何平台 SDK (discord, telegram 等)
2. 只封装 Bot 的抽象能力
3. 在 `__init__.py` 中导出
