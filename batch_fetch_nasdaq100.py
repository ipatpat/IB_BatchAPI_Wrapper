#!/usr/bin/env python3
"""
NASDAQ 100 股票数据批量获取工具 - 面向对象版本

基于SOLID原则的优雅面向对象架构实现
支持多种数据获取模式的统一管理
"""

import os
import time
import pandas as pd
import argparse
from datetime import datetime
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod
from dataclasses import dataclass

from src.data_fetcher import DataFetcherFacade, BarSizeConfig
from src.logger_config import get_logger

# 获取logger
logger = get_logger("nasdaq_batch")


# ================================
# 1. 数据传输对象 (DTO)
# ================================

@dataclass
class BatchConfig:
    """批量处理配置"""
    mode: str
    start_date: str
    bar_size: Optional[str] = None  # 使用None，由系统自动设置默认值
    max_count: Optional[int] = None
    start_from: Optional[int] = None
    output_dir: str = "data"
    
    def __post_init__(self):
        """初始化后处理，确保bar_size有效"""
        if self.bar_size is None:
            self.bar_size = BarSizeConfig.get_default()


@dataclass
class ProcessResult:
    """处理结果"""
    success_count: int
    failed_count: int
    total_count: int
    success_symbols: List[str]
    failed_symbols: List[str]
    total_elapsed: float
    
    @property
    def success_rate(self) -> float:
        return (self.success_count / self.total_count * 100) if self.total_count > 0 else 0


# ================================
# 2. 抽象接口
# ================================

class IDataProcessor(ABC):
    """数据处理器接口"""
    
    @abstractmethod
    def process_symbols(self, symbols: List[str], config: BatchConfig) -> ProcessResult:
        """处理符号列表"""
        pass


class ISymbolLoader(ABC):
    """符号加载器接口"""
    
    @abstractmethod
    def load_symbols(self) -> List[str]:
        """加载符号列表"""
        pass


class IResultFormatter(ABC):
    """结果格式化器接口"""
    
    @abstractmethod
    def format_summary(self, result: ProcessResult, mode: str) -> None:
        """格式化并输出摘要"""
        pass


# ================================
# 3. 具体实现类
# ================================

class NASDAQ100Loader(ISymbolLoader):
    """NASDAQ 100 符号加载器"""
    
    def __init__(self, file_path: str = "index/nasdaq100.txt"):
        self.file_path = file_path
    
    def load_symbols(self) -> List[str]:
        """加载NASDAQ 100股票代码"""
        try:
            # 读取文件，第一列是股票代码
            df = pd.read_csv(self.file_path, sep='\t', header=None, names=['symbol', 'start_date', 'end_date'])
            symbols = df['symbol'].str.strip().tolist()
            logger.info(f"成功加载 {len(symbols)} 个 NASDAQ 100 股票信息")
            return symbols
        except FileNotFoundError:
            logger.error(f"未找到文件: {self.file_path}")
            return []
        except Exception as e:
            logger.error(f"加载NASDAQ 100数据失败: {e}")
            return []


class CustomListLoader(ISymbolLoader):
    """自定义列表加载器"""
    
    def __init__(self, symbols: List[str]):
        self.symbols = self._clean_symbols(symbols)
    
    def _clean_symbols(self, symbols: List[str]) -> List[str]:
        """清理股票符号"""
        cleaned = []
        for symbol in symbols:
            # 移除 $ 符号并转换为大写
            clean_symbol = symbol.replace('$', '').strip().upper()
            if clean_symbol and clean_symbol not in cleaned:
                cleaned.append(clean_symbol)
        
        logger.info(f"🧹 清理符号列表: 原始 {len(symbols)} 个，清理后 {len(cleaned)} 个")
        if len(cleaned) != len(symbols):
            removed = len(symbols) - len(cleaned)
            logger.info(f"🗑️  移除重复/无效符号: {removed} 个")
        
        return cleaned
    
    def load_symbols(self) -> List[str]:
        """返回自定义符号列表"""
        return self.symbols


class StockDataProcessor(IDataProcessor):
    """股票数据处理器"""
    
    def __init__(self, data_fetcher: DataFetcherFacade):
        self.data_fetcher = data_fetcher
    
    def process_symbols(self, symbols: List[str], config: BatchConfig) -> ProcessResult:
        """处理股票符号列表"""
        total_count = len(symbols)
        success_symbols = []
        failed_symbols = []
        
        # 确保输出目录存在
        os.makedirs(config.output_dir, exist_ok=True)
        
        logger.info(f"📊 开始批量处理: {total_count} 个股票")
        start_time = time.time()
        
        for i, symbol in enumerate(symbols, 1):
            logger.info(f"📊 处理进度: {i}/{total_count} - {symbol}")
            
            try:
                result = self._process_single_symbol(symbol, config, i)
                if result['success']:
                    success_symbols.append(symbol)
                    self._log_success(symbol, result)
                else:
                    failed_symbols.append(symbol)
                    logger.warning(f"❌ {symbol}: {result.get('error', '未知错误')}")
                    
            except Exception as e:
                failed_symbols.append(symbol)
                logger.error(f"❌ {symbol}: 处理异常 - {str(e)}")
            
            # 处理间隔
            if i < total_count:
                logger.info("⏱️  等待 3 秒...")
                time.sleep(3)
        
        total_elapsed = time.time() - start_time
        
        return ProcessResult(
            success_count=len(success_symbols),
            failed_count=len(failed_symbols),
            total_count=total_count,
            success_symbols=success_symbols,
            failed_symbols=failed_symbols,
            total_elapsed=total_elapsed
        )
    
    def _process_single_symbol(self, symbol: str, config: BatchConfig, client_id_offset: int) -> Dict[str, Any]:
        """处理单个股票符号"""
        stock_start_time = time.time()
        
        # 获取股票数据
        df = self.data_fetcher.fetch_stock_data(
            symbol, 
            config.start_date,
            bar_size=config.bar_size,  # 使用配置中的时间框架
            client_id=client_id_offset
        )
        
        stock_end_time = time.time()
        elapsed = stock_end_time - stock_start_time
        
        if not df.empty:
            # 保存到CSV
            csv_path = os.path.join(config.output_dir, f"{symbol}.csv")
            df.to_csv(csv_path)
            
            # 计算收益率
            total_return = 0
            if len(df) > 1:
                first_price = df['close'].iloc[0]
                last_price = df['close'].iloc[-1]
                total_return = (last_price - first_price) / first_price * 100
            
            return {
                'success': True,
                'symbol': symbol,
                'records': len(df),
                'start_date': df.index.min(),
                'end_date': df.index.max(),
                'time_taken': elapsed,
                'file_size_kb': os.path.getsize(csv_path) / 1024,
                'total_return': total_return,
                'csv_path': csv_path
            }
        else:
            return {'success': False, 'symbol': symbol, 'error': '无数据'}
    
    def _log_success(self, symbol: str, result: Dict[str, Any]) -> None:
        """记录成功结果"""
        logger.info(f"✅ {symbol} (股票): 成功保存 {result['records']} 条数据")
        logger.info(f"   📅 {result['start_date'].strftime('%Y-%m-%d')} 到 {result['end_date'].strftime('%Y-%m-%d')}")
        logger.info(f"   📈 总收益: {result['total_return']:+.1f}%")
        logger.info(f"   ⏱️  用时: {result['time_taken']:.1f}秒")


class IndexDataProcessor(IDataProcessor):
    """指数数据处理器"""
    
    def __init__(self, data_fetcher: DataFetcherFacade):
        self.data_fetcher = data_fetcher
        # 预定义指数配置
        self.index_configs = {
            'NDX': ('NASDAQ 100 指数', 'NASDAQ'),
            'SPX': ('S&P 500 指数', 'CBOE'),
            'VIX': ('恐慌指数', 'CBOE'),
            'RUT': ('罗素2000指数', 'RUSSELL'),
            'DJI': ('道琼斯工业指数', 'NYSE')
        }
    
    def process_symbols(self, symbols: List[str], config: BatchConfig) -> ProcessResult:
        """处理指数符号列表"""
        total_count = len(symbols)
        success_symbols = []
        failed_symbols = []
        
        # 确保输出目录存在
        os.makedirs(config.output_dir, exist_ok=True)
        
        logger.info(f"🎯 开始获取指数数据: {total_count} 个指数")
        logger.info(f"🧹 处理指数列表: {symbols}")
        
        start_time = time.time()
        
        for i, symbol in enumerate(symbols, 1):
            logger.info(f"📊 进度 {i}/{total_count}: 正在处理 {symbol}")
            
            # 显示指数信息
            if symbol.upper() in self.index_configs:
                name, exchange = self.index_configs[symbol.upper()]
                logger.info(f"🎯 {symbol}: {name} (交易所: {exchange})")
            
            try:
                result = self._process_single_index(symbol, config, i)
                if result['success']:
                    success_symbols.append(symbol)
                    logger.info(f"✅ {symbol}: 指数数据获取成功")
                else:
                    failed_symbols.append(symbol)
                    logger.warning(f"❌ {symbol}: {result.get('error', '未知错误')}")
                    
            except Exception as e:
                failed_symbols.append(symbol)
                logger.error(f"❌ {symbol}: 处理异常 - {str(e)}")
        
        total_elapsed = time.time() - start_time
        
        return ProcessResult(
            success_count=len(success_symbols),
            failed_count=len(failed_symbols), 
            total_count=total_count,
            success_symbols=success_symbols,
            failed_symbols=failed_symbols,
            total_elapsed=total_elapsed
        )
    
    def _process_single_index(self, symbol: str, config: BatchConfig, client_id_offset: int) -> Dict[str, Any]:
        """处理单个指数符号"""
        stock_start_time = time.time()
        
        # 获取指数数据
        df = self.data_fetcher.fetch_index_data(
            symbol,
            config.start_date,
            bar_size=config.bar_size,  # 使用配置中的时间框架
            client_id=client_id_offset
        )
        
        stock_end_time = time.time()
        elapsed = stock_end_time - stock_start_time
        
        if not df.empty:
            # 保存到CSV
            csv_path = os.path.join(config.output_dir, f"{symbol}.csv")
            df.to_csv(csv_path)
            
            # 计算收益率
            total_return = 0
            if len(df) > 1:
                first_price = df['close'].iloc[0]
                last_price = df['close'].iloc[-1]
                total_return = (last_price - first_price) / first_price * 100
            
            return {
                'success': True,
                'symbol': symbol,
                'records': len(df),
                'start_date': df.index.min(),
                'end_date': df.index.max(),
                'time_taken': elapsed,
                'file_size_kb': os.path.getsize(csv_path) / 1024,
                'total_return': total_return,
                'csv_path': csv_path
            }
        else:
            return {'success': False, 'symbol': symbol, 'error': '无数据'}


class ConsoleResultFormatter(IResultFormatter):
    """控制台结果格式化器"""
    
    def format_summary(self, result: ProcessResult, mode: str) -> None:
        """格式化并输出结果摘要"""
        print("\n" + "=" * 70)
        
        if mode == "指数":
            print("📊 指数数据获取完成")
            print("=" * 60)
            print(f"✅ 成功: {result.success_count} 个")
            print(f"❌ 失败: {result.failed_count} 个")
            print(f"⏱️  总耗时: {result.total_elapsed / 60:.1f} 分钟")
            
            if result.success_symbols:
                total_records = sum(self._get_record_count(symbol) for symbol in result.success_symbols)
                total_size = sum(self._get_file_size(symbol) for symbol in result.success_symbols) 
                print(f"🔢 总数据条数: {total_records:,}")
                print(f"📁 成功指数: {result.success_symbols}")
                print(f"💾 总文件大小: {total_size:.1f} KB")
                print(f"📂 保存目录: data/indices/")
            
            logger.info(f"📋 指数处理完成: 成功 {result.success_count}, 失败 {result.failed_count}")
        else:
            print(f"📊 NASDAQ 100 数据获取完成 - {mode}模式")
            print("=" * 70)
            print(f"✅ 成功: {result.success_count} / {result.total_count}")
            print(f"❌ 失败: {result.failed_count} / {result.total_count}")
            print(f"📈 成功率: {result.success_rate:.1f}%")
            print(f"⏱️  总耗时: {result.total_elapsed / 60:.1f} 分钟")
            
            if result.success_symbols:
                # 计算统计信息
                self._print_data_statistics(result.success_symbols, result)
                self._print_file_list(result.success_symbols)
            
            if result.failed_symbols:
                print(f"\n❌ 失败的股票: {result.failed_symbols}")
    
    def _get_record_count(self, symbol: str) -> int:
        """获取记录数量"""
        try:
            csv_path = f"data/{symbol}.csv"
            if os.path.exists(csv_path):
                df = pd.read_csv(csv_path, index_col=0)
                return len(df)
        except:
            pass
        return 0
    
    def _get_file_size(self, symbol: str) -> float:
        """获取文件大小(KB)"""
        try:
            csv_path = f"data/{symbol}.csv" 
            if os.path.exists(csv_path):
                return os.path.getsize(csv_path) / 1024
        except:
            pass
        return 0
    
    def _print_data_statistics(self, symbols: List[str], result: ProcessResult) -> None:
        """打印数据统计信息"""
        total_records = 0
        total_size = 0
        total_return = 0
        valid_returns = 0
        
        for symbol in symbols:
            records = self._get_record_count(symbol)
            size = self._get_file_size(symbol)
            total_records += records
            total_size += size
            
            # 尝试计算收益率
            try:
                csv_path = f"data/{symbol}.csv"
                if os.path.exists(csv_path):
                    df = pd.read_csv(csv_path, index_col=0)
                    if len(df) > 1:
                        first_price = df['close'].iloc[0]
                        last_price = df['close'].iloc[-1]
                        symbol_return = (last_price - first_price) / first_price * 100
                        total_return += symbol_return
                        valid_returns += 1
            except:
                pass
        
        avg_return = total_return / valid_returns if valid_returns > 0 else 0
        avg_speed = total_records / result.total_elapsed if result.total_elapsed > 0 else 0
        
        print(f"\n📈 数据统计:")
        print(f"   🔢 总数据条数: {total_records:,}")
        print(f"   💾 总文件大小: {total_size:.1f} KB")
        print(f"   ⚡ 平均处理速度: {avg_speed:.0f} 条/秒")
        print(f"   📊 平均收益率: {avg_return:+.1f}%")
    
    def _print_file_list(self, symbols: List[str]) -> None:
        """打印文件列表"""
        print(f"\n📄 生成的文件:")
        for symbol in symbols:
            records = self._get_record_count(symbol)
            print(f"   {symbol}.csv - {records} 条数据")


# ================================
# 4. 主要业务类
# ================================

class BatchDataManager:
    """批量数据管理器 - 主要业务逻辑"""
    
    def __init__(self):
        self.data_fetcher = DataFetcherFacade()
        self.formatter = ConsoleResultFormatter()
    
    def process_nasdaq100(self, config: BatchConfig, test_mode: bool = False) -> ProcessResult:
        """处理NASDAQ 100数据"""
        loader = NASDAQ100Loader()
        symbols = loader.load_symbols()
        
        if not symbols:
            logger.error("无法加载 NASDAQ 100 数据")
            return ProcessResult(0, 0, 0, [], [], 0)
        
        # 测试模式处理
        if test_mode:
            test_symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA', 'META']
            symbols = test_symbols
            print(f"🧪 测试模式: 处理 {len(symbols)} 只代表性股票")
            print(f"🎯 股票列表: {symbols}")
        
        # 应用其他过滤条件
        if config.max_count:
            symbols = symbols[:config.max_count]
        if config.start_from:
            symbols = symbols[config.start_from-1:]
        
        print(f"📅 数据起始: {config.start_date}")
        print(f"⏰ 时间框架: {config.bar_size}")
        print(f"💾 保存目录: {config.output_dir}/")
        print()
        
        processor = StockDataProcessor(self.data_fetcher)
        return processor.process_symbols(symbols, config)
    
    def process_custom_list(self, symbols: List[str], config: BatchConfig) -> ProcessResult:
        """处理自定义符号列表"""
        loader = CustomListLoader(symbols)
        clean_symbols = loader.load_symbols()
        
        if not clean_symbols:
            logger.error("没有有效的股票符号")
            return ProcessResult(0, 0, 0, [], [], 0)
        
        # 更新输出目录
        config.output_dir = "data/custom_list"
        
        processor = StockDataProcessor(self.data_fetcher)
        return processor.process_symbols(clean_symbols, config)
    
    def process_indices(self, symbols: List[str], config: BatchConfig) -> ProcessResult:
        """处理指数列表"""
        loader = CustomListLoader(symbols)
        clean_symbols = loader.load_symbols()
        
        if not clean_symbols:
            logger.error("没有有效的指数符号")
            return ProcessResult(0, 0, 0, [], [], 0)
        
        # 更新输出目录
        config.output_dir = "data/indices"
        
        processor = IndexDataProcessor(self.data_fetcher)
        return processor.process_symbols(clean_symbols, config)


# ================================
# 5. 命令行接口
# ================================

class CommandLineInterface:
    """命令行接口管理器"""
    
    def __init__(self):
        self.manager = BatchDataManager()
        self.formatter = ConsoleResultFormatter()
    
    def parse_arguments(self) -> argparse.Namespace:
        """解析命令行参数"""
        parser = argparse.ArgumentParser(
            description='NASDAQ 100 股票数据批量获取工具 - 面向对象版本',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
使用示例:
  python %(prog)s --test                          # 测试模式
  python %(prog)s --full                          # 完整模式  
  python %(prog)s --list AAPL MSFT GOOGL         # 自定义列表模式
  python %(prog)s --index NDX SPX VIX             # 指数模式
  python %(prog)s --test --start-date 2024-01-01  # 指定开始日期
  python %(prog)s --test --bar-size "1 hour"      # 获取小时数据
  python %(prog)s --list AAPL --bar-size "5 mins" # 获取5分钟数据

支持的时间框架:
  秒级: 30 secs
  分钟级: 1 min, 5 mins, 15 mins, 30 mins
  小时级: 1 hour, 2 hours, 4 hours  
  日级以上: 1 day (默认), 1 week, 1 month
            """)
        
        # 模式选择（互斥）
        group = parser.add_mutually_exclusive_group()
        group.add_argument('--test', action='store_true', 
                           help='测试模式: 只处理前6只股票')
        group.add_argument('--full', action='store_true', 
                           help='完整模式: 处理全部股票')
        group.add_argument('--list', type=str, nargs='+',
                           help='自定义列表模式: 处理指定的股票代码')
        group.add_argument('--index', type=str, nargs='+',
                           help='指数模式: 获取指定指数数据 (如 NDX SPX)')
        
        # 通用参数
        parser.add_argument('--start-date', type=str, default='2008-01-01',
                            help='开始日期 (格式: YYYY-MM-DD 或 YYYYMMDD)，默认: 2008-01-01')
        parser.add_argument('--bar-size', type=str, 
                            help=f'时间框架，默认: {BarSizeConfig.get_default()}。' +
                                 f'支持: {", ".join(sorted(BarSizeConfig.VALID_BAR_SIZES))}')
        parser.add_argument('--max-count', type=int,
                            help='最大处理数量 (仅标准模式)')
        parser.add_argument('--start-from', type=int,
                            help='开始位置 (仅标准模式)')
        
        return parser.parse_args()
    
    def _validate_bar_size(self, bar_size: Optional[str]) -> Optional[str]:
        """验证时间框架参数"""
        if bar_size is None:
            return None
            
        if not BarSizeConfig.validate(bar_size):
            print(f"⚠️  警告: 无效的时间框架 '{bar_size}'")
            print(f"📋 支持的时间框架: {', '.join(sorted(BarSizeConfig.VALID_BAR_SIZES))}")
            
            alternatives = BarSizeConfig.suggest_alternatives(bar_size)
            if alternatives:
                print(f"💡 建议替代: {', '.join(alternatives[:3])}")
            
            # 询问是否使用默认值
            default = BarSizeConfig.get_default()
            confirm = input(f"是否使用默认时间框架 '{default}'? (Y/n): ").strip().lower()
            if confirm in ['', 'y', 'yes']:
                return None  # 返回None，让系统使用默认值
            else:
                print("❌ 程序退出")
                exit(1)
        
        return bar_size
    
    def run(self) -> None:
        """运行主程序"""
        args = self.parse_arguments()
        
        print("🚀 NASDAQ 100 股票数据批量获取工具")
        print("请确保 TWS 或 IB Gateway 正在运行...")
        
        # 验证时间框架
        validated_bar_size = self._validate_bar_size(args.bar_size)
        
        # 创建配置
        config = BatchConfig(
            mode="",
            start_date=args.start_date,
            bar_size=validated_bar_size,  # 使用验证后的bar_size
            max_count=args.max_count,
            start_from=args.start_from
        )
        
        # 显示使用的时间框架
        if config.bar_size:
            from src.data_fetcher import BarSizeConfig
            category = BarSizeConfig.get_category(config.bar_size)
            print(f"⏰ 时间框架: {config.bar_size} (类别: {category})")
        
        try:
            # 根据模式分发处理
            if args.list:
                self._handle_list_mode(args.list, config)
            elif args.index:
                self._handle_index_mode(args.index, config)
            else:
                self._handle_nasdaq_mode(args, config)
                
        except KeyboardInterrupt:
            print("\n⚠️  用户中断操作")
        except Exception as e:
            logger.error(f"程序执行异常: {e}")
            print(f"❌ 程序执行失败: {e}")
    
    def _handle_list_mode(self, symbols: List[str], config: BatchConfig) -> None:
        """处理自定义列表模式"""
        print("🔄 运行模式: 自定义列表模式")
        print(f"📋 处理股票: {len(symbols)} 只")
        print(f"📅 开始日期: {config.start_date}")
        print(f"⏰ 时间框架: {config.bar_size}")
        
        result = self.manager.process_custom_list(symbols, config)
        self.formatter.format_summary(result, "自定义列表")
        
        if result.success_symbols:
            print(f"\n💾 所有CSV文件已保存到 data/custom_list/ 目录")
    
    def _handle_index_mode(self, symbols: List[str], config: BatchConfig) -> None:
        """处理指数模式"""
        print("🔄 运行模式: 指数数据获取模式")
        print(f"📋 处理指数: {len(symbols)} 个")
        print(f"📅 开始日期: {config.start_date}")
        print(f"⏰ 时间框架: {config.bar_size}")
        
        result = self.manager.process_indices(symbols, config)
        self.formatter.format_summary(result, "指数")
        
        if result.success_symbols:
            print(f"\n✅ 指数数据获取完成!")
    
    def _handle_nasdaq_mode(self, args: argparse.Namespace, config: BatchConfig) -> None:
        """处理NASDAQ标准模式"""
        if args.test:
            print("🧪 运行模式: 测试模式")
            config.mode = "测试"
        elif args.full:
            print("🏭 运行模式: 完整模式")
            config.mode = "完整"
            
            # 确认操作
            nasdaq_loader = NASDAQ100Loader()
            symbols = nasdaq_loader.load_symbols()
            if symbols:
                print(f"\n⚠️  注意: 即将获取全部 {len(symbols)} 只股票的历史数据")
                print(f"预计耗时: {len(symbols) * 10 / 60:.0f} 分钟")
                confirm = input("确认继续？(y/N): ").strip().lower()
                if confirm not in ['y', 'yes']:
                    print("👋 已取消操作")
                    return
        else:
            # 默认测试模式
            print("🧪 运行模式: 测试模式 (默认)")
            config.mode = "测试"
            args.test = True
        
        # 显示配置信息
        nasdaq_loader = NASDAQ100Loader()
        symbols = nasdaq_loader.load_symbols()
        if symbols:
            print(f"📋 数据源: {len(symbols)} 只 NASDAQ 100 股票")
        
        result = self.manager.process_nasdaq100(config, test_mode=args.test)
        self.formatter.format_summary(result, config.mode)
        
        if result.success_symbols:
            print(f"\n💾 所有CSV文件已保存到 data/ 目录")


# ================================
# 6. 程序入口
# ================================

def main():
    """主函数"""
    cli = CommandLineInterface()
    cli.run()


if __name__ == "__main__":
    main()
