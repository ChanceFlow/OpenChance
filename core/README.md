# core/ - 公用逻辑层

项目的公用逻辑库,**不依赖 bots 或 apps 层**。

## 设计理念

`core/` 是最稳定的一层,提供所有层共用的模型、服务、配置和工具。
任何代码都可以安全地依赖 `core/`,而 `core/` 不会反向依赖其他层。

## 文件结构

```
core/
├── __init__.py
├── models/             # 数据模型
│   ├── message.py      #   统一消息模型 (Message, MessageType)
│   ├── session.py      #   会话模型 (SessionInfo, SessionType)
│   ├── platform.py     #   平台枚举 (Platform)
│   └── user.py         #   用户模型 (User)
├── services/           # 通用服务
│   └── message_handler.py  # 非命令消息处理
├── config/             # 配置管理
│   └── settings.py     #   Settings (从环境变量加载)
└── utils/              # 工具函数
    └── logger.py       #   loguru 日志配置
```

## 子模块

| 子模块 | 职责 |
|--------|------|
| `models/` | 跨平台统一数据模型 |
| `services/` | 通用业务服务 |
| `config/` | 应用配置管理 |
| `utils/` | 工具函数 (日志等) |
