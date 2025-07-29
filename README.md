# NASDAQ 100 股票数据获取工具

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![IBKR](https://img.shields.io/badge/IBKR-TWS%20API-green.svg)](https://interactivebrokers.github.io/tws-api/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

一个基于Interactive Brokers TWS API的专业股票历史数据获取工具，支持批量下载NASDAQ 100成分股的历史价格数据。

## 🚀 功能特性

### 核心功能
- 🔄 **稳定的数据获取**：自动处理IBKR API限制，确保数据完整性
- 📊 **批量处理**：支持一次性获取多只股票的历史数据
- 🎯 **智能筛选**：支持灵活的日期范围和数据过滤
- 💾 **自动保存**：将数据自动保存为CSV格式，便于后续分析
- 🔧 **命令行界面**：支持多种运行模式和参数配置

### 高级特性
- ⚡ **单次API调用**：优化的算法减少API调用次数，提高效率
- 🛡️ **错误处理**：完善的异常处理和重试机制
- 📈 **数据质量**：自动去重、排序和数据验证
- 🧪 **测试模式**：内置测试模式，快速验证功能
- 📋 **详细报告**：提供完整的执行统计和结果摘要

## 📁 项目结构

```
TUSHARE_DATA/
├── README.md                          # 项目文档
├── requirements.txt                   # Python依赖
├── pyproject.toml                     # 项目配置
├── main.py                           # 核心数据获取模块
├── batch_fetch_nasdaq100.csv.py       # 批量获取脚本（命令行版）
├── test_nasdaq_fetch.py              # 测试脚本
├── index/
│   └── nasdaq100.txt                 # NASDAQ 100成分股列表
└── data/                             # 输出目录（自动创建）
    ├── AAPL_data.csv
    ├── MSFT_data.csv
    └── ...
```

## 🛠️ 安装指南

### 环境要求
- Python 3.8+
- Interactive Brokers TWS 或 IB Gateway
- 有效的IBKR账户

### 快速安装

1. **克隆项目**
```bash
git clone <repository-url>
cd TUSHARE_DATA
```

2. **创建虚拟环境**
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或
.venv\Scripts\activate     # Windows
```

3. **安装依赖**
```bash
pip install -r requirements.txt
```

4. **启动TWS/Gateway**
   - 启动Interactive Brokers TWS客户端或IB Gateway
   - 确保API连接已启用（端口7496用于TWS，7497用于Gateway）
   - 在API设置中启用"Enable ActiveX and Socket Clients"

## 📖 使用指南

### 快速开始

#### 1. 测试模式（推荐首次使用）
```bash
# 获取6只代表性股票的历史数据
python batch_fetch_nasdaq100.py --test
```

#### 2. 完整模式
```bash
# 获取全部387只NASDAQ 100股票数据
python batch_fetch_nasdaq100.csv.py --full
```

### 命令行参数详解

```bash
# 查看所有可用参数
python batch_fetch_nasdaq100.csv.py --help

# 基本用法
python batch_fetch_nasdaq100.csv.py [选项]

选项:
  --test                    测试模式：只处理前6只股票
  --full                    完整模式：处理全部387只股票
  --start-date START_DATE   开始日期 (默认: 2008-01-01)
  --max-count MAX_COUNT     最大处理股票数量
  --start-from START_FROM   从第几个股票开始处理（续传功能）
```

### 使用示例

```bash
# 1. 默认测试模式
python batch_fetch_nasdaq100.csv.py

# 2. 处理特定数量的股票
python batch_fetch_nasdaq100.csv.py --max-count 20

# 3. 从特定位置开始（续传）
python batch_fetch_nasdaq100.csv.py --start-from 50 --max-count 30

# 4. 自定义开始日期
python batch_fetch_nasdaq100.csv.py --test --start-date 2015-01-01

# 5. 获取最近5年数据
python batch_fetch_nasdaq100.csv.py --full --start-date 2020-01-01
```

## 🔧 API参考

### 核心函数

#### `get_stock_data(symbol, start_date, host="127.0.0.1", port=7496, client_id=0)`

获取单只股票的历史数据。

**参数：**
- `symbol` (str): 股票代码，如 "AAPL"
- `start_date` (str): 开始日期，支持格式：
  - "YYYY-MM-DD" (如 "2020-01-01")
  - "YYYYMMDD" (如 "20200101")
- `host` (str): TWS/Gateway主机地址
- `port` (int): 连接端口
- `client_id` (int): 客户端ID

**返回：**
- `pandas.DataFrame`: 包含以下列的历史数据
  - `date` (index): 交易日期
  - `open`: 开盘价
  - `high`: 最高价
  - `low`: 最低价
  - `close`: 收盘价（复权后）
  - `volume`: 成交量

**示例：**
```python
from main import get_stock_data

# 获取苹果公司从2020年开始的历史数据
df = get_stock_data("AAPL", "2020-01-01")
print(f"获取到 {len(df)} 条数据")
print(df.head())
```

#### `get_multiple_stocks_data(symbols, start_date, host="127.0.0.1", port=7496)`

批量获取多只股票的历史数据。

**参数：**
- `symbols` (list): 股票代码列表
- `start_date` (str): 开始日期
- `host` (str): TWS/Gateway主机地址
- `port` (int): 连接端口

**返回：**
- `dict`: 以股票代码为键，DataFrame为值的字典

**示例：**
```python
from main import get_multiple_stocks_data

symbols = ["AAPL", "MSFT", "GOOGL"]
data_dict = get_multiple_stocks_data(symbols, "2020-01-01")

for symbol, df in data_dict.items():
    print(f"{symbol}: {len(df)} 条数据")
```

## 📊 输出格式

### CSV文件结构
每个股票的数据保存为单独的CSV文件，格式如下：

```csv
date,open,high,low,close,volume
2020-01-02,74.06,75.15,73.80,75.09,135480400
2020-01-03,74.29,75.14,74.13,74.36,146322800
...
```

### 执行报告示例
```
======================================================================
📊 NASDAQ 100 数据获取完成 - 测试模式
======================================================================
✅ 成功: 6 / 6
❌ 失败: 0 / 6
📈 成功率: 100.0%
⏱️  总耗时: 0.9 分钟

📈 数据统计:
   🔢 总数据条数: 24,789
   💾 总文件大小: 1025.6 KB
   ⚡ 平均处理速度: 447 条/秒
   📊 平均收益率: +9754.9%

📄 生成的文件:
   AAPL_data.csv - 4,420 条数据
   MSFT_data.csv - 4,420 条数据
   GOOGL_data.csv - 4,420 条数据
   TSLA_data.csv - 3,793 条数据
   NVDA_data.csv - 4,420 条数据
   META_data.csv - 3,316 条数据
```

## 🔍 数据质量说明

### 数据特性
- **价格类型**：使用ADJUSTED_LAST，已考虑股票分割和分红
- **时间范围**：支持最长30年历史数据
- **数据完整性**：自动处理缺失交易日和异常数据
- **去重处理**：自动移除重复记录，保留最新数据

### 支持的股票
- 所有NASDAQ 100成分股（当前387只）
- 自动从`index/nasdaq100.txt`加载最新列表
- 支持已退市股票的历史数据获取

## ⚠️ 注意事项

### API限制
- 建议在非交易时间运行以避免影响实时数据
- 连续请求间隔建议3秒以上
- 单次请求最长支持30年数据

### 常见错误处理
- **连接错误**：确保TWS/Gateway正在运行且API已启用
- **权限错误**：检查IBKR账户是否有数据订阅权限
- **超时错误**：网络不稳定时会自动重试

### 性能优化建议
- 测试模式验证配置后再运行完整模式
- 使用`--max-count`参数分批处理大量股票
- 定期清理`data/`目录中的旧文件

## 🤝 贡献指南

欢迎提交问题和改进建议！

### 开发环境设置
```bash
# 安装开发依赖
pip install -r requirements.txt

# 运行测试
python test_nasdaq_fetch.py
```

## 📄 许可证

本项目采用MIT许可证。详见 [LICENSE](LICENSE) 文件。

## 🆘 支持

如遇到问题，请：
1. 检查TWS/Gateway连接状态
2. 查看错误日志中的详细信息
3. 确认IBKR账户权限和数据订阅
4. 提交Issue并附上详细的错误信息

---

**⭐ 如果这个项目对你有帮助，请给个Star！** 