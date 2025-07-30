from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.common import *
import threading
import time
import pandas as pd
from datetime import datetime, timedelta
from .logger_config import get_logger

# 获取轻量级logger
logger = get_logger("nasdaq_fetcher")

class StockDataFetcher(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.data_received = False
        self.data_count = 0
        self.historical_data = []
        self.error_occurred = False
        self.error_message = ""

    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
        # 这些是正常的连接信息，不是错误
        if errorCode in [2104, 2106, 2158, 2174]:
            logger.system_info(f"IBKR连接信息 {errorCode}: {errorString}")
        else:
            logger.api_failure("IBKR API", errorCode, errorString)
            self.error_message = f"错误 {errorCode}: {errorString}"
            if errorCode in [200, 162, 321, 10314]:  # 严重错误
                self.error_occurred = True
                self.data_received = True

    def historicalData(self, reqId: int, bar: BarData):
        logger.debug(f"日期: {bar.date}, 开盘: {bar.open}, 最高: {bar.high}, 最低: {bar.low}, 收盘: {bar.close}, 成交量: {bar.volume}")
        self.data_count += 1
        
        # 存储数据
        data_row = {
            'date': bar.date,
            'open': bar.open,
            'high': bar.high,
            'low': bar.low,
            'close': bar.close,
            'volume': bar.volume
        }
        self.historical_data.append(data_row)
        
    def historicalDataEnd(self, reqId: int, start: str, end: str):
        logger.info(f"历史数据接收完成! 共接收 {self.data_count} 条数据")
        self.data_received = True

def create_stock_contract(symbol):
    """创建股票合约"""
    contract = Contract()
    contract.symbol = symbol
    contract.secType = "STK"
    contract.exchange = "SMART"
    contract.currency = "USD"
    return contract



def get_stock_data(symbol, start_date=None, host="127.0.0.1", port=7496, client_id=0):
    """
    获取股票历史数据 - 简化版本
    
    参数:
    symbol: 股票代码 (如 'AAPL', 'MSFT')
    start_date: 开始日期 (字符串 'YYYYMMDD' 或 'YYYY-MM-DD')
    host: TWS 主机地址，默认 "127.0.0.1"
    port: TWS 端口，默认 7496
    client_id: 客户端ID，默认 0
    
    返回:
    pandas.DataFrame: 包含股票历史数据的 DataFrame
    """
    
    # 处理开始日期参数
    if start_date is None:
        # 默认获取3年数据
        raise ValueError("请提供开始日期")
    else:
        # 处理不同的日期格式
        if isinstance(start_date, str):
            if len(start_date) == 8 and start_date.isdigit():  # YYYYMMDD格式
                filter_start_date = datetime.strptime(start_date, '%Y%m%d')
            else:  # YYYY-MM-DD格式
                filter_start_date = datetime.strptime(start_date, '%Y-%m-%d')
        else:
            filter_start_date = start_date
        
        # 计算需要的年数，至少1年，IBKR支持最多30年历史数据
        years_needed = max(1, min(30, (datetime.now() - filter_start_date).days // 365 + 1))
        duration_str = f"{years_needed} Y"
        
        logger.debug(f"计算时间跨度: 从 {filter_start_date.strftime('%Y-%m-%d')} 到现在 = {(datetime.now() - filter_start_date).days} 天 = {years_needed} 年")
    
    # 使用新的日志方法
    logger.stock_start(symbol, filter_start_date.strftime('%Y-%m-%d'))
    logger.system_info(f"将请求 {duration_str} 的数据后进行筛选")
    
    # 创建客户端实例
    app = StockDataFetcher()
    
    try:
        # 连接到TWS
        logger.info("正在连接到IBKR TWS...")
        app.connect(host, port, client_id)
        
        # 在单独的线程中运行消息循环
        api_thread = threading.Thread(target=app.run, daemon=True)
        api_thread.start()
        
        # 等待连接建立
        time.sleep(3)
        
        if not app.isConnected():
            logger.connection_failure(host, port, "无法建立连接")
            return pd.DataFrame()
        
        # 创建股票合约
        contract = create_stock_contract(symbol)
        
        logger.info(f"请求数据: 持续时间={duration_str}")
        
        # 请求历史数据
        chart_options = []
        app.reqHistoricalData(
            reqId=1, 
            contract=contract, 
            endDateTime="",  # 空字符串使用最新数据
            durationStr=duration_str,
            barSizeSetting="1 day",
            whatToShow="ADJUSTED_LAST",
            useRTH=1,
            formatDate=1,
            keepUpToDate=False,
            chartOptions=chart_options
        )
        
        # 等待数据接收完成
        timeout = 60
        start_time = time.time()
        while not app.data_received and time.time() - start_time < timeout:
            time.sleep(0.5)
        
        if app.error_occurred:
            logger.stock_failure(symbol, app.error_message)
            return pd.DataFrame()
        
        if not app.data_received:
            logger.stock_failure(symbol, "获取数据超时")
            return pd.DataFrame()
        
        logger.system_info(f"成功获取 {len(app.historical_data)} 条原始数据")
        
        # 转换为 DataFrame
        if app.historical_data:
            df = pd.DataFrame(app.historical_data)
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date').drop_duplicates(subset=['date'], keep='last').reset_index(drop=True)
            df.set_index('date', inplace=True)
            
            # 按开始日期筛选数据
            df_filtered = df[df.index >= filter_start_date]
            
            # 计算时间跨度和文件信息
            start_date = df_filtered.index.min().strftime('%Y-%m-%d')
            end_date = df_filtered.index.max().strftime('%Y-%m-%d')
            
            logger.stock_success(symbol, len(df_filtered))
            logger.data_summary(symbol, start_date, end_date, len(df_filtered), 0)  # 文件大小稍后计算
            return df_filtered
        else:
            return pd.DataFrame()
            
    except Exception as e:
        logger.stock_failure(symbol, f"系统异常: {str(e)}", e)
        return pd.DataFrame()
    finally:
        # 断开连接
        if app.isConnected():
            app.disconnect()
            time.sleep(2)

def get_multiple_stocks_data(symbols, start_date=None, host="127.0.0.1", port=7496):
    """
    批量获取多个股票的历史数据
    
    参数:
    symbols: 股票代码列表 (如 ['AAPL', 'MSFT', 'GOOGL'])
    start_date: 开始日期（结束日期总是今天）
    host: TWS 主机地址
    port: TWS 端口
    
    返回:
    dict: 以股票代码为键，DataFrame 为值的字典
    """
    results = {}
    total_symbols = len(symbols)
    success_count = 0
    start_time = time.time()
    
    logger.batch_start(total_symbols, "多股票数据获取")
    
    for i, symbol in enumerate(symbols, 1):
        logger.batch_progress(i, total_symbols, symbol)
        
        try:
            df = get_stock_data(symbol, start_date, host, port)
            if not df.empty:
                results[symbol] = df
                success_count += 1
            else:
                logger.stock_failure(symbol, "返回空数据")
        except Exception as e:
            logger.stock_failure(symbol, f"批量获取异常: {str(e)}", e)
        
        # 在每个股票之间稍作延迟，避免请求过于频繁
        time.sleep(2)
    
    # 记录批量处理摘要
    elapsed_time = time.time() - start_time
    failed_count = total_symbols - success_count
    logger.batch_summary(total_symbols, success_count, failed_count, elapsed_time)
    
    return results


if __name__ == "__main__":
    print("请确保 TWS 或 IB Gateway 正在运行...")
    
    print("\n" + "="*50)
    print("测试1: 获取 AAPL数据")
    print("="*50)
    
    symbol = "AAPL"
    start_date = "2008-01-01"
    df = get_stock_data(symbol, start_date, client_id=5)
    
    if not df.empty:
        print(f"\n✅ {symbol} 数据获取成功!")
        print(f"数据形状: {df.shape}")
        print(f"日期范围: {df.index.min().strftime('%Y-%m-%d')} 到 {df.index.max().strftime('%Y-%m-%d')}")
        print(f"\n📊 {symbol} 数据预览:")
        print(df.head())
        print(f"\n📈 {symbol} 最新数据:")
        print(df.tail(3))
        
        # 保存数据
        df.to_csv(f"/data/{symbol}_data.csv")
    else:
        print(f"❌ {symbol} 数据获取失败")

    print("\n" + "="*50)
    print("测试完成!")
    print("="*50)
