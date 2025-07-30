#!/usr/bin/env python3
"""
批量获取 NASDAQ 100 股票历史数据 - 简化架构

支持三种模式:
1. 测试模式: python batch_fetch_nasdaq100.py --test     (默认，处理6只代表性股票)
2. 完整模式: python batch_fetch_nasdaq100.py --full     (处理全部NASDAQ 100股票)
3. 列表模式: python batch_fetch_nasdaq100.py --failed-list AAPL MSFT GOOGL  (处理指定股票列表)

其他参数:
--start-date: 开始日期，默认2008-01-01
--max-count: 最大处理数量 (仅标准模式)
--start-from: 开始位置 (仅标准模式)
"""

import pandas as pd
import os
import time
import argparse
from datetime import datetime
from src.ibkr_fetcher import get_stock_data
from src.logger_config import get_logger


# 获取轻量级logger
logger = get_logger("nasdaq_batch")

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='批量获取 NASDAQ 100 股票历史数据')
    
    # 主要模式选择
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--test', action='store_true', 
                      help='测试模式：只处理前6只股票')
    group.add_argument('--full', action='store_true', 
                      help='完整模式：处理全部股票')
    group.add_argument('--failed-list', type=str, nargs='+',
                      help='失败股票列表模式：处理指定的股票代码')
    
    # 通用参数
    parser.add_argument('--start-date', default='2008-01-01',
                       help='开始日期 (默认: 2008-01-01)')
    parser.add_argument('--max-count', type=int,
                       help='最大处理股票数量（仅标准模式有效）')
    parser.add_argument('--start-from', type=int, default=0,
                       help='从第几个股票开始处理（仅标准模式有效）')
    
    args = parser.parse_args()
    
    # 如果没有指定任何模式，默认为测试模式
    if not args.test and not args.full and not args.failed_list:
        args.test = True
        
    return args

def load_nasdaq100_data(file_path="index/nasdaq100.txt"):
    """加载 NASDAQ 100 数据文件"""
    try:
        df = pd.read_csv(file_path, sep='\t', header=None, names=['symbol', 'entry_date', 'exit_date'])
        df['entry_date'] = pd.to_datetime(df['entry_date'])
        df['exit_date'] = pd.to_datetime(df['exit_date'])
        logger.info(f"成功加载 {len(df)} 个 NASDAQ 100 股票信息")
        return df
    except Exception as e:
        logger.error(f"加载 NASDAQ 100 数据失败: {str(e)}")
        return pd.DataFrame()

def create_data_directory():
    """创建data目录（如果不存在）"""
    if not os.path.exists('data'):
        os.makedirs('data')
        logger.info("创建 data 目录")

def fetch_and_save_stock_data(symbol, start_date, client_id_offset, output_dir="data"):
    """获取单个股票数据并保存到CSV"""
    try:
        logger.info(f"开始获取 {symbol} 历史数据...")
        
        stock_start_time = time.time()
        df = get_stock_data(symbol, start_date, client_id=client_id_offset)
        stock_end_time = time.time()
        elapsed = stock_end_time - stock_start_time
        
        if not df.empty:
            # 确保输出目录存在
            if output_dir != "data":
                os.makedirs(output_dir, exist_ok=True)
            
            # 统一使用 {symbol}.csv 格式
            csv_path = os.path.join(output_dir, f"{symbol}.csv")
            df.to_csv(csv_path)
            
            # 计算收益率
            total_return = 0
            if len(df) > 1:
                first_price = df['close'].iloc[0]
                last_price = df['close'].iloc[-1]
                total_return = (last_price - first_price) / first_price * 100
            
            logger.info(f"✅ {symbol}: 成功保存 {len(df)} 条数据")
            logger.info(f"   📅 {df.index.min().strftime('%Y-%m-%d')} 到 {df.index.max().strftime('%Y-%m-%d')}")
            logger.info(f"   📈 总收益: {total_return:+.1f}%")
            logger.info(f"   ⏱️  用时: {elapsed:.1f}秒")
            
            return {
                'success': True,
                'symbol': symbol,
                'records': len(df),
                'start_date': df.index.min(),
                'end_date': df.index.max(),
                'time_taken': elapsed,
                'file_size_kb': os.path.getsize(csv_path) / 1024,
                'total_return': total_return,
                'csv_path': csv_path,
                'df': df  # 返回DataFrame供不保存文件时使用
            }
        else:
            logger.warning(f"❌ {symbol}: 未获取到数据")
            return {'success': False, 'symbol': symbol, 'error': '无数据'}
            
    except Exception as e:
        logger.error(f"❌ {symbol}: 获取数据失败 - {str(e)}")
        return {'success': False, 'symbol': symbol, 'error': str(e)}

def batch_fetch_stocks(nasdaq_df, test_mode=True, max_count=None, start_from=0, start_date="2008-01-01"):
    """批量获取股票数据"""
    
    create_data_directory()
    
    symbols = nasdaq_df['symbol'].tolist()
    
    # 确定处理的股票列表
    if test_mode:
        # 测试模式：选择代表性股票
        preferred_symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA', 'META']
        test_symbols = []
        
        for symbol in preferred_symbols:
            if symbol in symbols:
                test_symbols.append(symbol)
            if len(test_symbols) >= 6:
                break
        
        if len(test_symbols) < 6:
            # 如果代表性股票不够，补充文件中的前几个
            remaining_needed = 6 - len(test_symbols)
            for symbol in symbols:
                if symbol not in test_symbols:
                    test_symbols.append(symbol)
                    remaining_needed -= 1
                    if remaining_needed <= 0:
                        break
        
        symbols = test_symbols
        print(f"🧪 测试模式: 处理 {len(symbols)} 只代表性股票")
    else:
        # 完整模式或自定义数量
        if max_count:
            symbols = symbols[start_from:start_from + max_count]
        else:
            symbols = symbols[start_from:]
        print(f"🏭 {'完整' if not max_count else '自定义'}模式: 处理 {len(symbols)} 只股票")
    
    print(f"🎯 股票列表: {symbols}")
    print(f"📅 数据起始: {start_date}")
    print(f"💾 保存目录: data/")
    
    results = {'success': [], 'failed': [], 'details': []}
    start_time = time.time()
    
    for i, symbol in enumerate(symbols, 1):
        print(f"\n📊 处理进度: {i}/{len(symbols)} - {symbol}")
        
        client_id = 300 + i
        result = fetch_and_save_stock_data(symbol, start_date, client_id, "data")
        
        if result['success']:
            results['success'].append(symbol)
            results['details'].append(result)
        else:
            results['failed'].append(symbol)
        
        # 添加延迟
        if i < len(symbols):
            print("⏱️  等待 3 秒...")
            time.sleep(3)
    
    end_time = time.time()
    total_elapsed = end_time - start_time
    
    return results, total_elapsed

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
    
    logger.info(f"🚀 开始获取股票列表数据: {len(stock_list)} 只股票")
    
    # 清理股票代码列表
    cleaned_symbols = []
    skipped_count = 0
    
    for symbol in stock_list:
        if not symbol or symbol.strip() == "":
            continue
        # 跳过退市股票标记（$包围）
        if symbol.startswith('$') and symbol.endswith('$'):
            logger.warning(f"⏭️ 跳过已退市股票: {symbol}")
            skipped_count += 1
            continue
        # 清理并去重
        clean_symbol = symbol.strip().upper()
        if clean_symbol and clean_symbol not in cleaned_symbols:
            cleaned_symbols.append(clean_symbol)
    
    logger.info(f"🧹 清理后股票列表: {len(cleaned_symbols)} 只（跳过 {skipped_count} 只退市股票）")
    
    if not cleaned_symbols:
        logger.error("没有有效的股票代码可以处理")
        return {'success': {}, 'failed': [], 'details': []}
    
    # 创建输出目录
    if save_to_csv:
        create_data_directory()
        if output_dir != "data":
            os.makedirs(output_dir, exist_ok=True)
    
    # 初始化结果
    results = {
        'success': {},
        'failed': [],
        'details': []
    }
    
    start_time = time.time()
    
    # 处理每个股票
    for i, symbol in enumerate(cleaned_symbols, 1):
        logger.info(f"📊 进度 {i}/{len(cleaned_symbols)}: 正在处理 {symbol}")
        
        # 使用不同的client_id避免冲突
        client_id = 200 + i
        
        if save_to_csv:
            # 保存到文件模式
            result = fetch_and_save_stock_data(symbol, start_date, client_id, output_dir)
        else:
            # 仅获取数据模式，保存到临时位置但不作为最终输出
            temp_dir = "/tmp/stock_temp"
            os.makedirs(temp_dir, exist_ok=True)
            result = fetch_and_save_stock_data(symbol, start_date, client_id, temp_dir)
        
        if result['success']:
            # 根据模式处理结果
            if save_to_csv:
                results['success'][symbol] = result['df']  # 保存DataFrame
                results['details'].append({
                    'symbol': symbol,
                    'success': True,
                    'records': result['records'],
                    'start_date': result['start_date'].strftime('%Y-%m-%d'),
                    'end_date': result['end_date'].strftime('%Y-%m-%d'),
                    'file_size_kb': result['file_size_kb'],
                    'total_return': result['total_return'],
                    'csv_path': result['csv_path']
                })
            else:
                results['success'][symbol] = result['df']  # 只保存DataFrame
                logger.info(f"✅ {symbol}: 成功获取 {result['records']} 条数据（未保存文件）")
        else:
            results['failed'].append(symbol)
        
        # 股票间延迟，避免请求过于频繁
        if i < len(cleaned_symbols):
            time.sleep(3)
    
    # 计算总体统计
    elapsed_time = time.time() - start_time
    success_count = len(results['success'])
    failed_count = len(results['failed'])
    
    # 打印摘要
    print(f"\n{'='*60}")
    print(f"📊 股票列表获取完成")
    print(f"{'='*60}")
    print(f"✅ 成功: {success_count} 只")
    print(f"❌ 失败: {failed_count} 只")
    print(f"⏱️  总耗时: {elapsed_time/60:.1f} 分钟")
    
    if results['success']:
        total_records = sum(len(df) for df in results['success'].values())
        print(f"🔢 总数据条数: {total_records:,}")
        print(f"📁 成功股票: {list(results['success'].keys())}")
        
        if save_to_csv and results['details']:
            total_size = sum(detail.get('file_size_kb', 0) for detail in results['details'])
            print(f"💾 总文件大小: {total_size:.1f} KB")
    
    if results['failed']:
        print(f"❌ 失败股票: {results['failed']}")
    
    logger.info(f"📋 股票列表处理完成: 成功 {success_count}, 失败 {failed_count}")
    
    return results

def print_summary(results, total_elapsed, mode):
    """打印处理结果摘要"""
    print(f"\n{'='*70}")
    print(f"📊 NASDAQ 100 数据获取完成 - {mode}模式")
    print(f"{'='*70}")
    
    total_stocks = len(results['success']) + len(results['failed'])
    success_rate = len(results['success']) / total_stocks * 100 if total_stocks > 0 else 0
    
    print(f"✅ 成功: {len(results['success'])} / {total_stocks}")
    print(f"❌ 失败: {len(results['failed'])} / {total_stocks}")
    print(f"📈 成功率: {success_rate:.1f}%")
    print(f"⏱️  总耗时: {total_elapsed/60:.1f} 分钟")
    
    if results['details']:
        total_records = sum(detail['records'] for detail in results['details'])
        total_size = sum(detail['file_size_kb'] for detail in results['details'])
        avg_return = sum(detail['total_return'] for detail in results['details']) / len(results['details'])
        
        print(f"\n📈 数据统计:")
        print(f"   🔢 总数据条数: {total_records:,}")
        print(f"   💾 总文件大小: {total_size:.1f} KB")
        print(f"   ⚡ 平均处理速度: {total_records/total_elapsed:.0f} 条/秒")
        print(f"   📊 平均收益率: {avg_return:+.1f}%")
        
        print(f"\n📄 生成的文件:")
        for detail in results['details']:
            print(f"   {detail['symbol']}.csv - {detail['records']:,} 条数据")
    
    if results['failed']:
        print(f"\n❌ 失败的股票: {results['failed']}")
        # 需要log下来
        

def main():
    """主函数 - 简化架构，根据参数直接执行"""
    args = parse_arguments()
    
    print("🚀 NASDAQ 100 股票数据批量获取工具")
    print("请确保 TWS 或 IB Gateway 正在运行...")
    
    # 根据参数类型直接执行相应功能
    if args.failed_list:
        # 失败股票列表模式
        print("🔄 运行模式: 失败股票重试模式")
        print(f"📋 处理股票: {len(args.failed_list)} 只")
        print(f"📅 开始日期: {args.start_date}")
        
        results = fetch_list_stocks(
            stock_list=args.failed_list,
            start_date=args.start_date,
            save_to_csv=True,
            output_dir="data/failed_stocks"
        )
        
        print(f"\n✅ 失败股票处理完成!")
        
    else:
        # 标准NASDAQ 100模式
        nasdaq_df = load_nasdaq100_data()
        if nasdaq_df.empty:
            logger.error("无法加载 NASDAQ 100 数据，程序退出")
            return
        
        if args.test:
            print("🧪 运行模式: 测试模式")
        elif args.full:
            print("🏭 运行模式: 完整模式")
            print(f"\n⚠️  注意: 即将获取全部 {len(nasdaq_df)} 只股票的历史数据")
            print(f"预计耗时: {len(nasdaq_df) * 10 / 60:.0f} 分钟")
            
            confirm = input("确认继续？(y/N): ").strip().lower()
            if confirm not in ['y', 'yes']:
                print("👋 已取消操作")
                return
        
        print(f"📋 数据源: {len(nasdaq_df)} 只 NASDAQ 100 股票")
        
        results, total_elapsed = batch_fetch_stocks(
            nasdaq_df,
            test_mode=args.test,
            max_count=args.max_count,
            start_from=args.start_from,
            start_date=args.start_date
        )
        
        # 打印标准摘要
        mode = "测试" if args.test else "完整"
        print_summary(results, total_elapsed, mode)
        
        if results['success']:
            print(f"\n💾 所有CSV文件已保存到 data/ 目录")

if __name__ == "__main__":
    main()
