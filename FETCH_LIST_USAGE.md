# fetch_list_stocks 函数使用说明

## 概述

我已经在 `batch_fetch_nasdaq100.py` 中添加了一个新的 `fetch_list_stocks` 函数，专门用于处理失败股票列表或任何自定义股票列表。

**重要改进**: 现在 `fetch_list_stocks` 函数复用了现有的 `fetch_and_save_stock_data` 函数，避免了代码重复，确保了一致性。

## 函数签名

```python
def fetch_list_stocks(stock_list, start_date="2008-01-01", save_to_csv=True, output_dir="data"):
    """
    获取股票列表的历史数据
    
    参数:
    stock_list: 股票代码列表 (如 ['AAPL', 'MSFT', 'GOOGL'])
    start_date: 开始日期 (默认: 2008-01-01)
    save_to_csv: 是否保存为CSV文件 (默认: True)
    output_dir: 输出目录 (默认: data)
    
    返回:
    dict: 包含成功和失败信息的结果字典
    """
```

## 使用方法

### 1. 基本使用

```python
from batch_fetch_nasdaq100 import fetch_list_stocks

# 你的失败股票列表
failed_stocks = [
    'ANSS', 'LIN', 'MNST', 'SPLK', '$SGEN$', 'SGEN', 'ATVI', 'FISV',
    # ... 更多股票
]

# 获取数据
results = fetch_list_stocks(failed_stocks)
```

### 2. 自定义参数

```python
# 指定开始日期和输出目录
results = fetch_list_stocks(
    stock_list=['ANSS', 'LIN', 'MNST'], 
    start_date='2015-01-01',
    output_dir='data/failed_stocks'
)
```

### 3. 只获取数据，不保存文件

```python
results = fetch_list_stocks(
    stock_list=['TSLA', 'NVDA'], 
    save_to_csv=False
)

# 从结果中获取DataFrame
if 'TSLA' in results['success']:
    tesla_df = results['success']['TSLA']
    print(f"TSLA数据: {len(tesla_df)} 条")
```

### 4. 处理结果

```python
results = fetch_list_stocks(['AAPL', 'MSFT', 'GOOGL'])

# 检查成功获取的股票
print(f"成功获取 {len(results['success'])} 只股票:")
for symbol, df in results['success'].items():
    print(f"  {symbol}: {len(df)} 条数据")
    print(f"    价格范围: ${df['close'].min():.2f} - ${df['close'].max():.2f}")

# 检查失败的股票
if results['failed']:
    print(f"失败股票: {results['failed']}")

# 查看详细信息
if results.get('details'):
    for detail in results['details']:
        if detail['success']:
            print(f"{detail['symbol']}: {detail['records']} 条数据, "
                  f"文件: {detail['csv_path']}")
```

## 功能特点

✨ **代码复用**: 
- 复用现有的 `fetch_and_save_stock_data` 函数
- 确保所有模式使用相同的数据获取逻辑
- 统一的错误处理和日志记录

🧹 **自动清理**: 
- 去除重复股票
- 跳过空值和无效代码
- 自动跳过退市股票（$包围的代码）

📊 **详细日志**: 
- 处理进度显示
- 成功/失败统计
- 详细的错误信息

💾 **灵活保存**:
- 可选择是否保存CSV文件
- 自定义输出目录
- 统一的文件命名格式: `{symbol}.csv`

🔄 **错误处理**:
- 自动跳过失败股票
- 不影响其他股票处理
- 详细的失败原因记录

## 直接使用示例

### 处理你的失败股票列表

```python
# 导入函数
from batch_fetch_nasdaq100 import fetch_list_stocks

# 你的完整失败列表
failed_stocks = [
    'ANSS', 'LIN', 'MNST', 'SPLK', '$SGEN$', 'SGEN', 'ATVI', 'FISV', 
    'SPLK', 'XLNX', 'CERN', 'MXIM', 'ALXN', 'CTXS', 'WLTW', 'MYL', 
    # ... 所有失败股票
]

# 方法1: 测试少量股票
test_results = fetch_list_stocks(
    stock_list=failed_stocks[:5],
    start_date='2015-01-01'
)

# 方法2: 处理所有失败股票
all_results = fetch_list_stocks(
    stock_list=failed_stocks,
    start_date='2008-01-01',
    output_dir='data/failed_stocks_retry'
)

# 方法3: 只获取特定股票
specific_stocks = ['ANSS', 'LIN', 'MNST']
results = fetch_list_stocks(specific_stocks)
```

## 注意事项

⚠️ **重要提醒**:
1. 确保 TWS 或 IB Gateway 正在运行
2. 失败股票可能因为退市、代码变更等原因无法获取
3. 建议先用少量股票测试
4. 每只股票之间有3秒延迟，避免API限制

## 与原有功能的区别

| 功能 | batch_fetch_nasdaq100.py | fetch_list_stocks |
|------|-------------------------|-------------------|
| 数据源 | nasdaq100.txt 文件 | 直接传入列表 |
| 参数 | 命令行参数 | 函数参数 |
| 使用方式 | 脚本执行 | 函数调用 |
| 灵活性 | 固定流程 | 高度自定义 |
| 文件命名 | `{symbol}.csv` | `{symbol}.csv` |
| 代码复用 | 独立实现 | 复用核心函数 |

## 架构优势

🏗️ **简化架构**:
- 单一数据获取函数 (`fetch_and_save_stock_data`)
- 所有模式复用相同逻辑
- 减少代码重复和维护成本
- 确保行为一致性

这样你就可以直接调用函数来处理失败股票列表了！ 