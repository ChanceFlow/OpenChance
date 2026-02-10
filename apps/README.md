# apps/ - 前端接入层

各平台的应用实现,包含平台 SDK 封装、业务逻辑和消息转换。

## 设计理念

`apps/` 层负责:
- 封装平台 SDK (如 discord.py)
- 实现平台特定的业务逻辑 (如 Slash Commands, Thread 管理)
- 消息格式转换 (平台格式 -> 统一 Message 模型)
- 连接 `bots/` 能力和 `core/` 服务

## 当前应用

| 目录 | 平台 | 说明 |
|------|------|------|
| `oc_discord/` | Discord | Discord 应用 (Slash Commands + Thread AI 对话) |

## 扩展新平台

1. 创建 `apps/oc_<platform>/` 目录
2. 实现平台客户端 (`client.py`) 封装 SDK
3. 实现适配器 (`adapter.py`) 连接 bots + core
4. 实现业务逻辑
5. 创建入口 (`main.py`)

```
apps/
├── oc_discord/    # Discord 应用
├── oc_telegram/   # Telegram 应用 (计划中)
└── ...
```
