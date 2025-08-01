# TUSHARE_DATA - NASDAQ 100 股票和指数数据获取工具

这是一个基于 Interactive Brokers (IBKR) TWS API 的股票和指数历史数据获取工具，专门优化用于批量获取 NASDAQ 100 股票后复权数据和各种市场指数。
数据支持导入**Qlib与RD-AGENT**进行量化研究。

## 核心功能

- **批量股票数据获取**: 一次性获取 NASDAQ 100 全部股票复权历史数据
- **指数数据支持**: 专门的指数获取模式，支持 NDX、SPX、VIX 等主要指数
- **智能证券识别（有限支持）**: 自动识别股票和指数，使用合适的合约配置
- **失败重试机制**: 专门的失败股票重新获取功能
- **详细日志记录**: 完整的操作日志和失败记录
- **CSV 文件输出**: 标准化的数据格式，便于后续分析

## 主要问题 （TO FIX）
1. 获取高频数据时，Time Period过长会导致IBKR假死。
2. 端口硬编码4002。

## 快速开始

### 环境要求

1. Python 3.13+
2. IB Gateway
3. 有效的 IBKR 账户和市场数据权限
4. IB中设置内存为4096MB以上

### 安装依赖

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv --version
uv sync
source .venv/bin/activate
```

### 基本使用

#### 1. 测试模式（推荐新手）
```bash
python batch_fetch_nasdaq100.py --test
```
- 获取 6 只代表性股票的数据
- 快速验证环境配置

#### 2. 完整模式
```bash
python batch_fetch_nasdaq100.py --full --bar-size "1 day"
```
- 获取全部 NASDAQ 100 股票数据
- 约需 60-90 分钟

#### 3. 指数模式
```bash
# 获取单个指数
python batch_fetch_nasdaq100.py --index NDX

# 获取多个指数
python batch_fetch_nasdaq100.py --index NDX SPX VIX --start-date 2020-01-01

# 支持的主要指数
python batch_fetch_nasdaq100.py --index NDX SPX VIX RUT DJI
```

#### 4. 失败股票重试
```bash
python batch_fetch_nasdaq100.py --list AAPL MSFT GOOGL --start-date 2015-01-01
```

## 支持的指数类型

| 指数代码 | 名称 | 交易所 | 说明 |
|---------|------|--------|------|
| NDX | NASDAQ 100 指数 | NASDAQ | 纳斯达克100指数 |
| SPX | S&P 500 指数 | CBOE | 标普500指数 |
| VIX | 恐慌指数 | CBOE | 市场波动率指数 |
| RUT | 罗素2000指数 | RUSSELL | 小盘股指数 |
| DJI | 道琼斯工业指数 | NYSE | 道琼斯30指数 |

## 项目结构

```
TUSHARE_DATA/
├── src/                          # 核心模块
│   ├── ibkr_fetcher.py          # IBKR API 接口封装
│   └── logger_config.py         # 日志系统配置
├── data/                         # 数据输出目录
│   ├── [股票代码].csv           # 股票数据文件
│   ├── indices/                 # 指数数据目录
│   │   └── [指数代码].csv       # 指数数据文件
│   └── custom_list /           # 列表模式获取数据
├── logs/                         # 日志文件
├── index/                        # 索引文件
│   └── nasdaq100.txt            # NASDAQ 100 股票列表
├── batch_fetch_nasdaq100.py     # 主程序
└── requirements.txt              # 依赖列表
```

## 命令行参数详解

### 基本参数
```bash
# 四种运行模式（互斥）
--test                           # 测试模式（默认）
--full                           # 完整模式  
--list SYMBOL1 SYMBOL2   # 失败股票列表模式
--index INDEX1 INDEX2           # 指数模式

# 通用参数
--start-date YYYY-MM-DD         # 开始日期（默认: 2008-01-01）
--max-count N                   # 最大处理数量（仅标准模式）
--start-from N                  # 开始位置（仅标准模式）
--bar-size timeframe            # K线周期（默认: 1 day）
```

### 使用示例
```bash
# 获取从2020年开始的测试数据
python batch_fetch_nasdaq100.py --test --start-date 2020-01-01

# 获取前10只股票
python batch_fetch_nasdaq100.py --full --max-count 10

# 指数组合获取
python batch_fetch_nasdaq100.py --index NDX SPX --start-date 2022-01-01

# 处理特定失败股票
python batch_fetch_nasdaq100.py --failed-list AAPL MSFT GOOGL TSLA
```

## API 参考

### 核心函数

#### `get_stock_data(symbol, start_date, sec_type=None)`
获取单个证券的历史数据

**参数:**
- `symbol`: 证券代码 (如 'AAPL', 'NDX')
- `start_date`: 开始日期 ('YYYY-MM-DD' 或 'YYYYMMDD')
- `sec_type`: 证券类型 ('STK'=股票, 'IND'=指数), None=自动检测

**返回:** pandas.DataFrame

#### `fetch_indices(index_list, start_date, output_dir)`
专门获取指数数据

**参数:**
- `index_list`: 指数代码列表
- `start_date`: 开始日期
- `output_dir`: 输出目录（默认: data/indices）

#### `fetch_list_stocks(stock_list, start_date, save_to_csv, output_dir)`
获取股票列表数据

**参数:**
- `stock_list`: 股票代码列表
- `start_date`: 开始日期
- `save_to_csv`: 是否保存文件
- `output_dir`: 输出目录

## 输出格式

### CSV 文件结构
```csv
date,open,high,low,close,volume
2024-01-02,185.81,187.07,182.54,184.29,532792
2024-01-03,182.95,184.53,182.1,182.91,373129
```

### 文件命名规则
- 股票文件: `data/AAPL.csv`
- 指数文件: `data/indices/NDX.csv` 
- 单独获取: `data/failed_stocks/AAPL.csv`


## 故障排除

### 常见问题

1. **连接失败**
   ```
   错误: 无法建立连接
   解决: 确保 TWS/IB Gateway 正在运行，端口7496可用
   ```

2. **证券定义未找到**
   ```
   错误: 未找到该请求的证券定义
   解决: 检查股票代码是否正确，或该证券是否需要特定的市场数据权限
   ```

3. **指数数据获取失败**
   ```
   错误: 指数合约创建失败
   解决: 某些指数可能需要特定的市场数据订阅
   ```

### 日志查看
```bash
# 查看最新日志
tail -f logs/nasdaq_*.log

# 查看失败记录
cat logs/nasdaq_failures_*.log
```


## 更新日志

### v0.1.0
- 新增指数获取模式 (`--index`)
- NASDAQ 100 股票数据获取
- 失败股票重试机制
- 完整日志系统
- CSV 文件输出
