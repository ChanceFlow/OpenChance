# core/utils/ - 工具函数

项目通用的工具函数集合。

## 模块

| 文件 | 函数/对象 | 说明 |
|------|----------|------|
| `logger.py` | `setup_logging()` | loguru 日志初始化,支持控制台 + 文件输出 |

## 日志配置

```python
from core.utils import setup_logging

setup_logging(
    log_file=Path("logs/discord.log"),
    level="INFO",
    rotation="10 MB",
    retention="7 days",
)
```

- 控制台: 带颜色输出,INFO 级别
- 文件: DEBUG 级别,自动轮转,UTF-8 编码,线程安全
