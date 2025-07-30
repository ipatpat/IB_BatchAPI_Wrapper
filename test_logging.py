#!/usr/bin/env python3
"""
测试新的轻量级Logging系统
演示时间戳文件名和失败记录功能
"""

import time
from src.logger_config import get_logger, create_new_logger

def test_basic_logging():
    """测试基础logging功能"""
    print("🧪 测试基础Logging功能")
    print("-" * 50)
    
    logger = get_logger("test_basic")
    
    # 基础日志级别
    logger.debug("这是调试信息")
    logger.info("这是普通信息")
    logger.warning("这是警告信息")
    logger.error("这是错误信息")
    
    print("✅ 基础日志测试完成\n")

def test_stock_specific_logging():
    """测试股票特定的日志方法"""
    print("🧪 测试股票特定Logging方法")
    print("-" * 50)
    
    logger = get_logger("test_stock")
    
    # 模拟股票数据获取流程
    symbols = ["AAPL", "MSFT", "INVALID_SYMBOL"]
    
    for symbol in symbols:
        logger.stock_start(symbol, "2020-01-01")
        
        # 模拟处理时间
        time.sleep(0.5)
        
        if symbol == "INVALID_SYMBOL":
            # 模拟失败情况
            try:
                raise ValueError("Invalid stock symbol")
            except Exception as e:
                logger.stock_failure(symbol, "股票代码无效", e)
        else:
            # 模拟成功情况
            data_points = 1000 + len(symbol) * 100
            logger.stock_success(symbol, data_points, 0.5)
            logger.data_summary(symbol, "2020-01-01", "2025-01-01", data_points, 156.7)
    
    print("✅ 股票特定日志测试完成\n")

def test_batch_logging():
    """测试批量处理日志"""
    print("🧪 测试批量处理Logging")
    print("-" * 50)
    
    logger = get_logger("test_batch")
    
    symbols = ["AAPL", "MSFT", "GOOGL", "TSLA", "FAIL_STOCK"]
    total = len(symbols)
    success = 0
    failed = 0
    
    logger.batch_start(total, "测试模式")
    
    start_time = time.time()
    
    for i, symbol in enumerate(symbols, 1):
        logger.batch_progress(i, total, symbol)
        
        # 模拟处理
        time.sleep(0.2)
        
        if symbol == "FAIL_STOCK":
            logger.stock_failure(symbol, "模拟失败测试")
            failed += 1
        else:
            logger.stock_success(symbol, 1200, 0.2)
            success += 1
    
    elapsed = time.time() - start_time
    logger.batch_summary(total, success, failed, elapsed)
    
    print("✅ 批量处理日志测试完成\n")

def test_connection_and_api_logging():
    """测试连接和API日志"""
    print("🧪 测试连接和API Logging")
    print("-" * 50)
    
    logger = get_logger("test_api")
    
    # 模拟连接过程
    logger.system_info("开始连接IBKR TWS")
    time.sleep(0.3)
    
    # 模拟连接失败
    logger.connection_failure("127.0.0.1", 7496, "连接超时")
    
    # 模拟API调用失败
    logger.api_failure("reqHistoricalData", 321, "End date not supported with adjusted last")
    
    print("✅ 连接和API日志测试完成\n")

def test_multiple_loggers():
    """测试多个logger实例"""
    print("🧪 测试多个Logger实例")
    print("-" * 50)
    
    # 创建新的logger实例（不同的时间戳）
    logger1 = create_new_logger("session_1")
    time.sleep(1)  # 确保时间戳不同
    logger2 = create_new_logger("session_2")
    
    logger1.info("这是第一个session的日志")
    logger2.info("这是第二个session的日志")
    
    logger1.stock_failure("TEST1", "Session 1 中的失败")
    logger2.stock_failure("TEST2", "Session 2 中的失败")
    
    print("✅ 多个Logger实例测试完成\n")

def show_log_files():
    """显示生成的日志文件"""
    print("📁 生成的日志文件:")
    print("-" * 50)
    
    import os
    from pathlib import Path
    
    log_dir = Path("logs")
    if log_dir.exists():
        log_files = list(log_dir.glob("*.log"))
        log_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        for log_file in log_files:
            size = log_file.stat().st_size
            print(f"📄 {log_file.name} ({size} bytes)")
        
        print(f"\n📊 共生成 {len(log_files)} 个日志文件")
        
        # 显示最新的失败日志内容（如果存在）
        failure_logs = [f for f in log_files if "failures" in f.name]
        if failure_logs:
            latest_failure_log = failure_logs[0]
            print(f"\n❌ 最新失败日志内容 ({latest_failure_log.name}):")
            print("-" * 50)
            with open(latest_failure_log, 'r', encoding='utf-8') as f:
                content = f.read()
                if content.strip():
                    print(content)
                else:
                    print("(空文件)")
    else:
        print("❌ logs目录不存在")

if __name__ == "__main__":
    print("🚀 轻量级Logging系统测试")
    print("=" * 60)
    
    # 运行所有测试
    test_basic_logging()
    test_stock_specific_logging()
    test_batch_logging()
    test_connection_and_api_logging()
    test_multiple_loggers()
    
    # 显示生成的文件
    show_log_files()
    
    print("\n🎉 所有测试完成!")
    print("💡 提示: 查看 logs/ 目录中的日志文件以了解详细输出") 