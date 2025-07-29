#!/usr/bin/env python3
"""
批量获取 NASDAQ 100 股票历史数据 - 支持命令行参数

使用方法:
python batch_fetch_nasdaq100_v2.py --test     # 测试模式，只处理前6只股票
python batch_fetch_nasdaq100_v2.py --full     # 完整模式，处理全部387只股票
python batch_fetch_nasdaq100_v2.py            # 默认测试模式
"""

import pandas as pd
import os
import time
import argparse
from datetime import datetime
import logging
from src.ibkr_fetcher import get_stock_data

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='批量获取 NASDAQ 100 股票历史数据')
    
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--test', action='store_true', 
                      help='测试模式：只处理前6只股票')
    group.add_argument('--full', action='store_true', 
                      help='完整模式：处理全部387只股票')
    
    parser.add_argument('--start-date', default='2008-01-01',
                       help='开始日期 (默认: 2008-01-01)')
    parser.add_argument('--max-count', type=int,
                       help='最大处理股票数量（用于自定义测试）')
    parser.add_argument('--start-from', type=int, default=0,
                       help='从第几个股票开始处理（用于续传）')
    
    args = parser.parse_args()
    
    # 如果没有指定模式，默认为测试模式
    if not args.test and not args.full:
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

def fetch_and_save_stock_data(symbol, start_date, client_id_offset):
    """获取单个股票数据并保存到CSV"""
    try:
        logger.info(f"开始获取 {symbol} 历史数据...")
        
        stock_start_time = time.time()
        df = get_stock_data(symbol, start_date, client_id=client_id_offset)
        stock_end_time = time.time()
        elapsed = stock_end_time - stock_start_time
        
        if not df.empty:
            csv_path = os.path.join("data", f"{symbol}.csv")
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
                'total_return': total_return
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
        result = fetch_and_save_stock_data(symbol, start_date, client_id)
        
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
    """主函数"""
    args = parse_arguments()
    
    print("🚀 NASDAQ 100 股票数据批量获取工具")
    
    if args.test:
        print("🧪 运行模式: 测试模式")
    elif args.full:
        print("🏭 运行模式: 完整模式")
        
    print("请确保 TWS 或 IB Gateway 正在运行...")
    
    # 加载数据
    nasdaq_df = load_nasdaq100_data()
    if nasdaq_df.empty:
        logger.error("无法加载 NASDAQ 100 数据，程序退出")
        return
    
    print(f"\n📋 加载了 {len(nasdaq_df)} 只 NASDAQ 100 股票信息")
    
    # 如果是完整模式，给用户最后确认机会
    if args.full:
        print(f"\n⚠️  注意: 即将获取全部 {len(nasdaq_df)} 只股票的历史数据")
        print(f"预计耗时: {len(nasdaq_df) * 10 / 60:.0f} 分钟")
        
        confirm = input("确认继续？(y/N): ").strip().lower()
        if confirm not in ['y', 'yes']:
            print("👋 已取消操作")
            return
    
    # 执行批量获取
    results, total_elapsed = batch_fetch_stocks(
        nasdaq_df,
        test_mode=args.test,
        max_count=args.max_count,
        start_from=args.start_from,
        start_date=args.start_date
    )
    
    # 打印结果
    mode = "测试" if args.test else "完整"
    print_summary(results, total_elapsed, mode)
    
    if results['success']:
        print(f"\n💾 所有CSV文件已保存到 data/ 目录")

if __name__ == "__main__":
    main()
