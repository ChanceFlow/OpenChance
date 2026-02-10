# core/services/ - 通用服务

提供与平台无关的通用业务服务。

## 模块

| 文件 | 类 | 说明 |
|------|-----|------|
| `message_handler.py` | `MessageHandler` | 处理非命令文本消息的通用逻辑 |

## 说明

- Slash Command 的业务逻辑在 `apps/` 层的 Cogs 中实现
- 本目录仅存放跨平台通用的服务逻辑
- Bot 能力相关的服务 (如 Claude Code) 在 `bots/` 层
