# 轻量级Logging系统使用指南

## 🎯 功能特色

### ✨ 核心特性
- **时间戳文件名**: 每次运行生成唯一的日志文件 `nasdaq_YYYYMMDD_HHMMSS.log`
- **失败专用日志**: 单独记录失败情况到 `nasdaq_failures_YYYYMMDD_HHMMSS.log`
- **控制台+文件**: 同时输出到控制台和文件
- **业务特定方法**: 针对股票数据获取的专用日志方法
- **轻量级设计**: 简单易用，无需复杂配置

### 📁 日志文件结构
```
logs/
├── nasdaq_20250129_174530.log          # 主日志文件（所有级别）
├── nasdaq_failures_20250129_174530.log # 失败专用日志
├── nasdaq_20250129_180245.log          # 另一次运行的主日志
└── nasdaq_failures_20250129_180245.log # 另一次运行的失败日志
```

## 🚀 快速开始

### 1. 导入和初始化
```python
from src.logger_config import get_logger

# 获取logger实例（单例模式）
logger = get_logger("nasdaq_fetcher")
```

### 2. 基础日志方法
```python
logger.debug("调试信息")
logger.info("普通信息") 
logger.warning("警告信息")
logger.error("错误信息")
logger.critical("严重错误")
```

## 📊 业务特定方法

### 股票数据获取
```python
# 开始获取股票数据
logger.stock_start("AAPL", "2020-01-01")

# 获取成功
logger.stock_success("AAPL", 1250, 5.2)  # symbol, data_points, elapsed_time

# 获取失败（会自动记录到失败日志）
logger.stock_failure("AAPL", "连接超时")

# 获取失败（带异常信息）
try:
    # 你的代码
    pass
except Exception as e:
    logger.stock_failure("AAPL", "系统异常", e)
```

### 批量处理
```python
symbols = ["AAPL", "MSFT", "GOOGL"]

# 开始批量处理
logger.batch_start(len(symbols), "测试模式")

# 处理进度
for i, symbol in enumerate(symbols, 1):
    logger.batch_progress(i, len(symbols), symbol)
    # 你的处理逻辑...

# 批量处理摘要
logger.batch_summary(total=3, success=2, failed=1, elapsed=120.5)
```

### 连接和API
```python
# 连接失败
logger.connection_failure("127.0.0.1", 7496, "连接超时")

# API调用失败
logger.api_failure("reqHistoricalData", 321, "End date not supported")

# 系统信息
logger.system_info("开始连接IBKR TWS")
```

### 数据摘要
```python
logger.data_summary(
    symbol="AAPL",
    start_date="2020-01-01", 
    end_date="2025-01-01",
    total_records=1250,
    file_size_kb=156.7
)
```

## 🔧 高级用法

### 创建新的Logger实例
```python
from src.logger_config import create_new_logger

# 创建新的logger（新的时间戳）
logger = create_new_logger("session_2")
```

### 在现有代码中替换
```python
# 旧的方式 ❌
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 新的方式 ✅
from src.logger_config import get_logger
logger = get_logger("nasdaq_fetcher")
```

## 📝 日志输出示例

### 控制台输出
```
17:45:30 | INFO     | 🚀 日志系统启动 - 主日志: nasdaq_20250129_174530.log, 失败日志: nasdaq_failures_20250129_174530.log
17:45:31 | INFO     | 🔄 开始获取 AAPL 历史数据 (从 2020-01-01)
17:45:31 | INFO     | 🔧 将请求 5 Y 的数据后进行筛选
17:45:36 | INFO     | ✅ AAPL: 成功获取 1,250 条数据 - 耗时 5.2秒
17:45:37 | ERROR    | ❌ INVALID: 获取失败 - 股票代码无效
```

### 主日志文件 (nasdaq_20250129_174530.log)
```
2025-01-29 17:45:30 | nasdaq_fetcher | INFO     | get_logger:156 | 🚀 日志系统启动 - 主日志: nasdaq_20250129_174530.log, 失败日志: nasdaq_failures_20250129_174530.log
2025-01-29 17:45:31 | nasdaq_fetcher | INFO     | stock_start:87 | 🔄 开始获取 AAPL 历史数据 (从 2020-01-01)
2025-01-29 17:45:31 | nasdaq_fetcher | INFO     | system_info:126 | 🔧 将请求 5 Y 的数据后进行筛选
2025-01-29 17:45:36 | nasdaq_fetcher | INFO     | stock_success:92 | ✅ AAPL: 成功获取 1,250 条数据 - 耗时 5.2秒
2025-01-29 17:45:37 | nasdaq_fetcher | ERROR    | stock_failure:99 | ❌ INVALID: 获取失败 - 股票代码无效
```

### 失败日志文件 (nasdaq_failures_20250129_174530.log)
```
2025-01-29 17:45:37 | FAILURE | ❌ INVALID: 获取失败 - 股票代码无效
  位置: /path/to/your/script.py:45
  函数: get_stock_data
--------------------------------------------------------------------------------
2025-01-29 17:45:42 | FAILURE | 💥 IBKR连接失败 127.0.0.1:7496 - 连接超时
  位置: /path/to/your/script.py:108
  函数: connect_to_ibkr
--------------------------------------------------------------------------------
```

## 🎯 最佳实践

### 1. 在函数开始和结束时记录
```python
def get_stock_data(symbol, start_date):
    logger.stock_start(symbol, start_date)
    
    try:
        # 你的逻辑
        result = fetch_data()
        logger.stock_success(symbol, len(result), elapsed_time)
        return result
    except Exception as e:
        logger.stock_failure(symbol, str(e), e)
        raise
```

### 2. 批量处理中使用进度记录
```python
def batch_process(symbols):
    logger.batch_start(len(symbols))
    
    for i, symbol in enumerate(symbols, 1):
        logger.batch_progress(i, len(symbols), symbol)
        # 处理逻辑...
    
    logger.batch_summary(total, success, failed, elapsed)
```

### 3. 异常处理中记录详细信息
```python
try:
    risky_operation()
except ConnectionError as e:
    logger.connection_failure(host, port, str(e))
except APIError as e:
    logger.api_failure("operation_name", e.code, e.message)
except Exception as e:
    logger.stock_failure(symbol, f"未知错误: {str(e)}", e)
```

## 🔍 调试技巧

### 查看最新的失败日志
```bash
# 在logs目录中找到最新的failures文件
ls -la logs/*failures* | tail -1

# 查看失败日志内容
cat logs/nasdaq_failures_20250129_174530.log
```

### 过滤特定类型的日志
```bash
# 只看成功的股票获取
grep "✅.*成功获取" logs/nasdaq_20250129_174530.log

# 只看失败的情况
grep "❌.*失败" logs/nasdaq_20250129_174530.log

# 只看批量处理摘要
grep "📋 批量处理完成" logs/nasdaq_20250129_174530.log
```

## 🚀 升级现有代码

如果你的项目已经在使用标准的Python logging，可以这样无缝升级：

```python
# 只需要替换这两行：
# import logging
# logger = logging.getLogger(__name__)

# 改为：
from src.logger_config import get_logger
logger = get_logger("nasdaq_fetcher")

# 其他logger.info(), logger.error()等调用保持不变
# 但建议逐步替换为业务特定的方法，如：
# logger.info(f"开始获取 {symbol}") -> logger.stock_start(symbol, start_date)
# logger.error(f"{symbol} 失败") -> logger.stock_failure(symbol, error_msg)
```

这个轻量级的logging系统专为你的NASDAQ股票数据获取项目设计，既保持了简单性，又提供了强大的失败追踪和业务日志功能！🎉 