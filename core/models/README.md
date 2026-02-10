# core/models/ - 数据模型

跨平台统一数据模型,使用 `@dataclass` 定义。

## 模块

| 文件 | 类 | 说明 |
|------|-----|------|
| `message.py` | `Message`, `MessageType` | 统一消息模型,所有平台消息转换为此格式 |
| `session.py` | `SessionInfo`, `SessionType` | AI 会话信息,记录 session_id、类型、创建者等 |
| `platform.py` | `Platform` | 支持的平台枚举 (Discord, Telegram, Slack 等) |
| `user.py` | `User` | 统一用户模型 |

## 使用示例

```python
from core.models import Message, MessageType, SessionInfo, SessionType

# 创建消息
msg = Message(
    id="123",
    content="你好",
    type=MessageType.TEXT,
    user_id="456",
    user_name="chance",
    platform="discord",
)

# 创建会话信息
session = SessionInfo(
    session_id="abc-123",
    session_type=SessionType.CODE,
    creator_id="456",
    allowed_tools=["Bash", "Read", "Edit"],
)
```
