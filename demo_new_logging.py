#!/usr/bin/env python3
"""
演示新的轻量级Logging系统
运行此脚本可以看到时间戳文件名和失败记录的效果
"""

import time
from src.logger_config import get_logger

def demo_stock_fetching():
    """演示股票数据获取的日志记录"""
    
    # 获取logger
    logger = get_logger("nasdaq_demo")
    
    print("🚀 演示NASDAQ股票数据获取的日志记录")
    print("=" * 50)
    
    # 模拟获取几只股票的数据
    symbols = ["AAPL", "MSFT", "INVALID_STOCK", "GOOGL"]
    success_count = 0
    failed_count = 0
    start_time = time.time()
    
    logger.batch_start(len(symbols), "演示模式")
    
    for i, symbol in enumerate(symbols, 1):
        logger.batch_progress(i, len(symbols), symbol)
        logger.stock_start(symbol, "2020-01-01")
        
        # 模拟数据获取过程
        time.sleep(0.8)
        
        if symbol == "INVALID_STOCK":
            # 模拟失败情况
            try:
                raise ValueError("Invalid stock symbol provided")
            except Exception as e:
                logger.stock_failure(symbol, "股票代码无效", e)
                failed_count += 1
        else:
            # 模拟成功情况
            data_points = 1000 + i * 200
            logger.stock_success(symbol, data_points, 0.8)
            logger.data_summary(symbol, "2020-01-01", "2025-01-29", data_points, 125.5 + i * 20)
            success_count += 1
    
    # 记录批量处理摘要
    elapsed = time.time() - start_time
    logger.batch_summary(len(symbols), success_count, failed_count, elapsed)
    
    # 模拟一些系统事件
    logger.system_info("演示连接和API错误")
    logger.connection_failure("127.0.0.1", 7496, "模拟连接超时")
    logger.api_failure("reqHistoricalData", 321, "End date not supported with adjusted last")
    
    print("\n✅ 演示完成!")
    print("📁 请检查 logs/ 目录中生成的日志文件:")
    print("   - nasdaq_YYYYMMDD_HHMMSS.log (主日志)")
    print("   - nasdaq_failures_YYYYMMDD_HHMMSS.log (失败专用日志)")

if __name__ == "__main__":
    demo_stock_fetching() 