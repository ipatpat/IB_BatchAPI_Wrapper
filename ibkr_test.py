from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.common import *
import threading
import time

class IBKRClient(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.data_received = False
        self.data_count = 0
        self.historical_data = []

    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
        print(f"错误 {errorCode}: {errorString}")

    def historicalData(self, reqId: int, bar: BarData):
        print(f"日期: {bar.date}, 开盘: {bar.open}, 最高: {bar.high}, 最低: {bar.low}, 收盘: {bar.close}, 成交量: {bar.volume}")
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
        print(f"历史数据接收完成! 共接收 {self.data_count} 条数据")
        self.data_received = True

def create_stock_contract(symbol):
    contract = Contract()
    contract.symbol = symbol
    contract.secType = "STK"
    contract.exchange = "SMART"
    contract.currency = "USD"
    return contract

def main():
    app = IBKRClient()
    
    # 连接到TWS
    print("正在连接到IBKR TWS...")
    app.connect("127.0.0.1", 7496, 0)
    
    # 在单独的线程中运行消息循环
    api_thread = threading.Thread(target=app.run, daemon=True)
    api_thread.start()
    
    # 等待连接建立
    time.sleep(2)
    
    if app.isConnected():
        print("连接成功!")
        
        # 创建股票合约
        contract = create_stock_contract("AAPL")
        
        # 获取复权数据的选项：
        # 1. 后复权 (Adjusted for splits and dividends) - 推荐用于分析
        print("正在请求AAPL复权数据...")
        chart_options = ["ADJUSTED"]  # 后复权数据
        
        # 如果要获取未复权数据，使用：
        # chart_options = []
        
        # 如果要获取前复权数据，使用：
        # chart_options = ["SPLIT_ADJUSTED"]  # 只复权分股，不复权分红
        
        app.reqHistoricalData(1, contract, "", "1 Y", "1 day", "TRADES", 1, 1, False, chart_options)
        
        # 等待数据接收完成
        while not app.data_received:
            time.sleep(0.5)
        
        print("数据获取完成!")
        print(f"获取到 {len(app.historical_data)} 条复权数据")
        
        # 显示最近几条数据
        if app.historical_data:
            print("\n最近5条数据:")
            for data in app.historical_data[-5:]:
                print(f"日期: {data['date']}, 收盘价: {data['close']}")
        
    else:
        print("连接失败!")
    
    # 断开连接
    if app.isConnected():
        app.disconnect()
        print("已断开连接")

if __name__ == "__main__":
    main()
