from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.common import *
import threading
import time
import pandas as pd
from datetime import datetime, timedelta
import logging
import os
import sys

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.logger_config import get_logger, log_exception

# 使用新的logging系统
logger = get_logger('nasdaq_fetcher')

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
            logger.connection_event("info", f"代码{errorCode}: {errorString}")
        else:
            # 记录详细的错误信息到失败日志
            error_context = {
                'reqId': reqId,
                'errorCode': errorCode,
                'errorString': errorString,
                'advancedOrderRejectJson': advancedOrderRejectJson
            }
            logger.api_call("IBKR_API_ERROR", error_context, success=False, error_msg=errorString)
            
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
        logger.info(f"📊 历史数据接收完成! 共接收 {self.data_count} 条数据")
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
    
    # 记录开始时间用于计算总耗时
    start_time = time.time()
    
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
    
    # 记录开始获取股票数据
    logger.stock_start(symbol, filter_start_date.strftime('%Y-%m-%d'), f"请求{duration_str}数据")
    
    # 创建客户端实例
    app = StockDataFetcher()
    
    try:
        # 连接到TWS
        logger.connection_event("connect", f"尝试连接{host}:{port}")
        app.connect(host, port, client_id)
        
        # 在单独的线程中运行消息循环
        api_thread = threading.Thread(target=app.run, daemon=True)
        api_thread.start()
        
        # 等待连接建立
        time.sleep(3)
        
        if not app.isConnected():
            logger.connection_event("connect", f"连接{host}:{port}失败", success=False)
            return pd.DataFrame()
        
        logger.connection_event("connect", f"已连接{host}:{port}")
        
        # 创建股票合约
        contract = create_stock_contract(symbol)
        
        # 记录API调用
        api_params = {
            'symbol': symbol,
            'duration': duration_str,
            'barSize': '1 day',
            'whatToShow': 'ADJUSTED_LAST'
        }
        logger.api_call("reqHistoricalData", api_params)
        
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
            logger.stock_failure(symbol, app.error_message, additional_context={
                'host': host, 'port': port, 'client_id': client_id, 'duration': duration_str
            })
            return pd.DataFrame()
        
        if not app.data_received:
            logger.stock_failure(symbol, "获取数据超时", additional_context={
                'timeout': timeout, 'host': host, 'port': port
            })
            return pd.DataFrame()
        
        logger.debug(f"成功获取 {len(app.historical_data)} 条原始数据")
        
        # 转换为 DataFrame
        if app.historical_data:
            df = pd.DataFrame(app.historical_data)
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date').drop_duplicates(subset=['date'], keep='last').reset_index(drop=True)
            df.set_index('date', inplace=True)
            
            # 按开始日期筛选数据
            df_filtered = df[df.index >= filter_start_date]
            
            if len(df_filtered) > 0:
                # 计算处理时间
                end_time = time.time()
                elapsed = end_time - start_time
                
                # 记录成功
                logger.stock_success(
                    symbol, 
                    len(df_filtered), 
                    elapsed,
                    df_filtered.index.min().strftime('%Y-%m-%d'),
                    df_filtered.index.max().strftime('%Y-%m-%d')
                )
                return df_filtered
            else:
                logger.data_quality_issue(symbol, "筛选后无数据", "error")
                return pd.DataFrame()
        else:
            logger.data_quality_issue(symbol, "API返回空数据", "error")
            return pd.DataFrame()
            
    except Exception as e:
        # 使用专用的异常记录函数
        log_exception(logger, f"获取{symbol}数据时发生异常")
        logger.stock_failure(symbol, str(e), additional_context={
            'exception_type': type(e).__name__,
            'host': host, 'port': port
        })
        return pd.DataFrame()
    finally:
        # 断开连接
        if app.isConnected():
            logger.connection_event("disconnect", f"断开{host}:{port}")
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
    batch_start_time = time.time()
    
    # 记录批量处理开始
    logger.batch_start(len(symbols), "多股票数据获取")
    
    success_count = 0
    for i, symbol in enumerate(symbols, 1):
        logger.batch_progress(i, len(symbols), symbol)
        
        try:
            df = get_stock_data(symbol, start_date, host, port)
            if not df.empty:
                results[symbol] = df
                success_count += 1
                logger.debug(f"{symbol} 数据获取成功")
            else:
                logger.warning(f"{symbol} 数据获取失败 - 返回空DataFrame")
        except Exception as e:
            log_exception(logger, f"获取{symbol}数据时发生异常")
            logger.stock_failure(symbol, str(e), additional_context={
                'batch_processing': True,
                'position_in_batch': i,
                'total_in_batch': len(symbols)
            })
        
        # 在每个股票之间稍作延迟，避免请求过于频繁
        time.sleep(2)
    
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
