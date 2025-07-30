#!/usr/bin/env python3
"""
轻量级Logging配置模块
- 日志文件以时间戳命名
- 失败情况单独记录
- 控制台输出 + 文件记录
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional


class TimestampLogger:
    """基于时间戳的轻量级Logger"""
    
    def __init__(self, name: str, level: int = logging.INFO):
        self.name = name
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)
        
        # 生成时间戳
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 创建logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # 清除现有handlers（避免重复）
        if self.logger.handlers:
            self.logger.handlers.clear()
        
        # 设置handlers
        self._setup_handlers(timestamp)
        
        # 添加便利方法
        self._add_methods()
    
    def _setup_handlers(self, timestamp: str):
        """设置日志处理器"""
        
        # 1. 控制台Handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # 2. 通用日志文件Handler
        general_file = self.log_dir / f"nasdaq_{timestamp}.log"
        file_handler = logging.FileHandler(general_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s | %(name)s | %(levelname)-8s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)
        
        # 3. 失败专用日志Handler
        failure_file = self.log_dir / f"nasdaq_failures_{timestamp}.log"
        self.failure_handler = logging.FileHandler(failure_file, encoding='utf-8')
        self.failure_handler.setLevel(logging.ERROR)
        failure_formatter = logging.Formatter(
            '%(asctime)s | FAILURE | %(message)s\n' + 
            '  位置: %(pathname)s:%(lineno)d\n' +
            '  函数: %(funcName)s\n' + 
            '-' * 80,
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.failure_handler.setFormatter(failure_formatter)
        self.logger.addHandler(self.failure_handler)
        
        # 记录启动信息
        self.logger.info(f"🚀 日志系统启动 - 主日志: {general_file.name}, 失败日志: {failure_file.name}")
    
    def _add_methods(self):
        """添加便利方法"""
        self.debug = self.logger.debug
        self.info = self.logger.info
        self.warning = self.logger.warning
        self.error = self.logger.error
        self.critical = self.logger.critical
    
    # 业务相关的日志方法
    def stock_start(self, symbol: str, start_date: str):
        """记录股票获取开始"""
        self.info(f"🔄 开始获取 {symbol} 历史数据 (从 {start_date})")
    
    def stock_success(self, symbol: str, data_points: int, elapsed: float = None):
        """记录股票获取成功"""
        time_info = f" - 耗时 {elapsed:.1f}秒" if elapsed else ""
        self.info(f"✅ {symbol}: 成功获取 {data_points:,} 条数据{time_info}")
    
    def stock_failure(self, symbol: str, error_msg: str, exception: Exception = None):
        """记录股票获取失败 - 会同时记录到失败专用日志"""
        failure_msg = f"❌ {symbol}: 获取失败 - {error_msg}"
        
        # 记录到主日志
        self.error(failure_msg)
        
        # 如果有异常，记录完整的异常信息到失败日志
        if exception:
            self.logger.exception(f"股票 {symbol} 获取失败详情: {error_msg}")
    
    def connection_failure(self, host: str, port: int, error_msg: str):
        """记录连接失败"""
        failure_msg = f"💥 IBKR连接失败 {host}:{port} - {error_msg}"
        self.error(failure_msg)
    
    def api_failure(self, api_call: str, error_code: int, error_msg: str):
        """记录API调用失败"""
        failure_msg = f"🚫 API调用失败: {api_call} - 错误码 {error_code}: {error_msg}"
        self.error(failure_msg)
    
    def batch_start(self, total_count: int, mode: str = ""):
        """记录批量处理开始"""
        mode_info = f" ({mode})" if mode else ""
        self.info(f"📊 开始批量处理{mode_info}: 共 {total_count} 只股票")
    
    def batch_progress(self, current: int, total: int, symbol: str):
        """记录批量处理进度"""
        progress = current / total * 100
        self.info(f"📈 进度 {current}/{total} ({progress:.1f}%) - 当前: {symbol}")
    
    def batch_summary(self, total: int, success: int, failed: int, elapsed: float):
        """记录批量处理摘要"""
        success_rate = success / total * 100 if total > 0 else 0
        self.info(f"📋 批量处理完成:")
        self.info(f"  ✅ 成功: {success}/{total} ({success_rate:.1f}%)")
        self.info(f"  ❌ 失败: {failed}/{total}")
        self.info(f"  ⏱️  总耗时: {elapsed/60:.1f} 分钟")
        
        if failed > 0:
            self.warning(f"⚠️  有 {failed} 只股票获取失败，详情请查看失败日志")
    
    def system_info(self, message: str):
        """记录系统信息"""
        self.info(f"🔧 {message}")
    
    def data_summary(self, symbol: str, start_date: str, end_date: str, 
                    total_records: int, file_size_kb: float):
        """记录数据摘要"""
        self.info(f"📄 {symbol} 数据摘要:")
        self.info(f"  📅 时间范围: {start_date} 到 {end_date}")
        self.info(f"  📊 数据条数: {total_records:,}")
        self.info(f"  💾 文件大小: {file_size_kb:.1f} KB")


# 全局logger实例
_logger_instance = None

def get_logger(name: str = "nasdaq_fetcher", level: int = logging.INFO) -> TimestampLogger:
    """获取logger实例（单例模式）"""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = TimestampLogger(name, level)
    return _logger_instance

def create_new_logger(name: str = "nasdaq_fetcher", level: int = logging.INFO) -> TimestampLogger:
    """创建新的logger实例（用于新的会话）"""
    return TimestampLogger(name, level) 