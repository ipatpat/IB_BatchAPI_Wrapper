#!/usr/bin/env python3
"""
NASDAQ股票数据获取项目的专业日志配置

功能特性:
- 彩色控制台输出
- 自动文件分割（按级别和大小）
- 失败情况单独记录
- 项目特定的便利方法
- 性能监控支持
"""

import logging
import logging.handlers
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import traceback


class ColoredFormatter(logging.Formatter):
    """彩色控制台日志格式化器"""
    
    COLORS = {
        'DEBUG': '\033[36m',     # 青色
        'INFO': '\033[32m',      # 绿色  
        'WARNING': '\033[33m',   # 黄色
        'ERROR': '\033[31m',     # 红色
        'CRITICAL': '\033[35m',  # 紫色
    }
    RESET = '\033[0m'
    
    def format(self, record):
        # 保存原始levelname
        original_levelname = record.levelname
        
        # 添加颜色（仅在控制台输出时）
        if hasattr(self, '_console_output') and self._console_output:
            if record.levelname in self.COLORS:
                record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.RESET}"
        
        formatted = super().format(record)
        
        # 恢复原始levelname
        record.levelname = original_levelname
        
        return formatted


class NASDAQLogger:
    """NASDAQ项目专用Logger类"""
    
    def __init__(self, name: str, level: int = logging.INFO, log_dir: str = "logs"):
        self.name = name
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # 创建logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # 避免重复添加handlers
        if not self.logger.handlers:
            self._setup_handlers()
        
        # 添加便利方法
        self._add_basic_methods()
        
        # 初始化统计信息
        self._init_stats()
    
    def _setup_handlers(self):
        """设置各种日志处理器"""
        
        # 1. 控制台Handler - 彩色输出
        console_handler = self._create_console_handler()
        self.logger.addHandler(console_handler)
        
        # 2. 主日志文件Handler - 记录所有INFO及以上
        main_handler = self._create_main_file_handler()
        self.logger.addHandler(main_handler)
        
        # 3. 调试日志Handler - 记录所有DEBUG级别
        debug_handler = self._create_debug_file_handler()
        self.logger.addHandler(debug_handler)
        
        # 4. 错误日志Handler - 只记录ERROR和CRITICAL
        error_handler = self._create_error_file_handler()
        self.logger.addHandler(error_handler)
        
        # 5. 失败情况专用Handler - 记录所有失败相关的日志
        failure_handler = self._create_failure_file_handler()
        self.logger.addHandler(failure_handler)
    
    def _create_console_handler(self):
        """创建彩色控制台处理器"""
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        
        formatter = ColoredFormatter(
            '%(asctime)s | %(name)s | %(levelname)-8s | %(message)s',
            datefmt='%H:%M:%S'
        )
        formatter._console_output = True  # 标记为控制台输出
        handler.setFormatter(formatter)
        return handler
    
    def _create_main_file_handler(self):
        """创建主日志文件处理器"""
        handler = logging.handlers.RotatingFileHandler(
            self.log_dir / f"{self.name}_main.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        handler.setLevel(logging.INFO)
        
        formatter = logging.Formatter(
            '%(asctime)s | %(name)s | %(levelname)-8s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        return handler
    
    def _create_debug_file_handler(self):
        """创建调试文件处理器"""
        handler = logging.handlers.RotatingFileHandler(
            self.log_dir / f"{self.name}_debug.log",
            maxBytes=20*1024*1024,  # 20MB
            backupCount=3,
            encoding='utf-8'
        )
        handler.setLevel(logging.DEBUG)
        
        formatter = logging.Formatter(
            '%(asctime)s | %(name)s | %(levelname)-8s | %(pathname)s:%(lineno)d | %(funcName)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        return handler
    
    def _create_error_file_handler(self):
        """创建错误专用文件处理器"""
        handler = logging.handlers.RotatingFileHandler(
            self.log_dir / f"{self.name}_error.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=10,
            encoding='utf-8'
        )
        handler.setLevel(logging.ERROR)
        
        formatter = logging.Formatter(
            '%(asctime)s | %(name)s | %(levelname)-8s | %(pathname)s:%(lineno)d | %(funcName)s\n'
            'MESSAGE: %(message)s\n'
            'TRACEBACK: %(exc_text)s\n'
            '{"separator": "="*80}\n',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        return handler
    
    def _create_failure_file_handler(self):
        """创建失败情况专用文件处理器"""
        handler = logging.handlers.RotatingFileHandler(
            self.log_dir / f"{self.name}_failures.log",
            maxBytes=5*1024*1024,  # 5MB
            backupCount=20,  # 保留更多失败记录
            encoding='utf-8'
        )
        
        # 创建自定义过滤器，只记录包含失败关键词的日志
        class FailureFilter(logging.Filter):
            def filter(self, record):
                failure_keywords = ['失败', '错误', 'failed', 'error', 'exception', '❌', '💥']
                message = record.getMessage().lower()
                return any(keyword in message for keyword in failure_keywords)
        
        handler.addFilter(FailureFilter())
        handler.setLevel(logging.WARNING)
        
        formatter = logging.Formatter(
            '%(asctime)s | FAILURE | %(name)s | %(levelname)-8s\n'
            'LOCATION: %(pathname)s:%(lineno)d | %(funcName)s\n'
            'MESSAGE: %(message)s\n'
            'EXTRA_INFO: %(exc_text)s\n'
            '{"failure_separator": "="*100}\n',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        return handler
    
    def _add_basic_methods(self):
        """添加基础日志方法"""
        self.debug = self.logger.debug
        self.info = self.logger.info
        self.warning = self.logger.warning
        self.error = self.logger.error
        self.critical = self.logger.critical
        self.exception = self.logger.exception
    
    def _init_stats(self):
        """初始化统计信息"""
        self._stats = {
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'start_time': datetime.now()
        }
    
    # ============================================================================
    # 项目特定的便利方法
    # ============================================================================
    
    def stock_start(self, symbol: str, start_date: str, additional_info: str = ""):
        """记录股票数据获取开始"""
        self._stats['total_operations'] += 1
        extra = f" - {additional_info}" if additional_info else ""
        self.info(f"🔄 开始获取 {symbol} 历史数据 (从 {start_date}){extra}")
    
    def stock_success(self, symbol: str, data_points: int, elapsed: float, 
                     start_date: str = "", end_date: str = ""):
        """记录股票数据获取成功"""
        self._stats['successful_operations'] += 1
        date_range = f" ({start_date} 到 {end_date})" if start_date and end_date else ""
        self.info(f"✅ {symbol}: 成功获取 {data_points:,} 条数据{date_range} - 耗时 {elapsed:.1f}秒")
    
    def stock_failure(self, symbol: str, error: str, error_code: str = "", 
                     additional_context: Dict[str, Any] = None):
        """记录股票数据获取失败 - 会被记录到失败专用日志"""
        self._stats['failed_operations'] += 1
        
        # 构建详细的失败信息
        failure_info = {
            'symbol': symbol,
            'error': error,
            'error_code': error_code,
            'timestamp': datetime.now().isoformat(),
            'context': additional_context or {}
        }
        
        # 基础错误日志
        error_msg = f"❌ {symbol}: 获取失败"
        if error_code:
            error_msg += f" (错误代码: {error_code})"
        error_msg += f" - {error}"
        
        self.error(error_msg, extra={'failure_info': failure_info})
        
        # 如果有额外上下文，记录到debug
        if additional_context:
            self.debug(f"失败上下文 {symbol}: {additional_context}")
    
    def connection_event(self, event_type: str, details: str = "", success: bool = True):
        """记录连接事件"""
        if success:
            if event_type == "connect":
                self.info(f"🔗 IBKR连接成功 {details}")
            elif event_type == "disconnect":
                self.info(f"🔌 IBKR正常断开 {details}")
            else:
                self.info(f"📡 连接事件: {event_type} {details}")
        else:
            self.error(f"💥 连接失败: {event_type} - {details}")
    
    def api_call(self, method: str, params: Dict[str, Any], success: bool = True, 
                error_msg: str = ""):
        """记录API调用"""
        if success:
            self.debug(f"🔧 API调用成功: {method}({params})")
        else:
            self.error(f"💥 API调用失败: {method}({params}) - {error_msg}")
    
    def batch_start(self, total_symbols: int, mode: str = ""):
        """记录批量处理开始"""
        mode_info = f" ({mode})" if mode else ""
        self.info(f"🚀 开始批量处理{mode_info}: 共 {total_symbols} 只股票")
        self._stats['batch_start_time'] = datetime.now()
    
    def batch_progress(self, current: int, total: int, symbol: str = ""):
        """记录批量处理进度"""
        progress = current / total * 100 if total > 0 else 0
        symbol_info = f" - 当前: {symbol}" if symbol else ""
        self.info(f"📊 批量进度: {current}/{total} ({progress:.1f}%){symbol_info}")
    
    def batch_summary(self, total: int, success: int, elapsed: float, 
                     data_points: int = 0, file_size_mb: float = 0):
        """记录批量处理摘要"""
        failed = total - success
        success_rate = success / total * 100 if total > 0 else 0
        
        summary = [
            f"📊 批量处理完成:",
            f"   ✅ 成功: {success}/{total} ({success_rate:.1f}%)",
            f"   ❌ 失败: {failed}/{total} ({100-success_rate:.1f}%)",
            f"   ⏱️ 总耗时: {elapsed/60:.1f}分钟"
        ]
        
        if data_points > 0:
            summary.append(f"   📈 总数据量: {data_points:,} 条")
        if file_size_mb > 0:
            summary.append(f"   💾 文件大小: {file_size_mb:.1f} MB")
        
        self.info("\n".join(summary))
        
        # 如果失败率过高，记录警告
        if success_rate < 80:
            self.warning(f"⚠️ 失败率较高 ({100-success_rate:.1f}%)，请检查logs/{self.name}_failures.log")
    
    def performance_metric(self, operation: str, value: float, unit: str = "秒"):
        """记录性能指标"""
        self.debug(f"📈 性能指标: {operation} = {value:.2f} {unit}")
    
    def data_quality_issue(self, symbol: str, issue: str, severity: str = "warning"):
        """记录数据质量问题"""
        if severity == "error":
            self.error(f"🔍 数据质量错误 {symbol}: {issue}")
        else:
            self.warning(f"🔍 数据质量警告 {symbol}: {issue}")
    
    def system_resource(self, resource_type: str, usage: str):
        """记录系统资源使用情况"""
        self.debug(f"💻 系统资源 {resource_type}: {usage}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取运行统计信息"""
        current_time = datetime.now()
        total_runtime = (current_time - self._stats['start_time']).total_seconds()
        
        stats = self._stats.copy()
        stats.update({
            'total_runtime_seconds': total_runtime,
            'total_runtime_minutes': total_runtime / 60,
            'success_rate': (stats['successful_operations'] / stats['total_operations'] * 100) 
                           if stats['total_operations'] > 0 else 0,
            'current_time': current_time.isoformat()
        })
        return stats
    
    def log_final_stats(self):
        """记录最终统计信息"""
        stats = self.get_stats()
        self.info(f"📊 最终统计: 总操作 {stats['total_operations']}, "
                 f"成功 {stats['successful_operations']}, "
                 f"失败 {stats['failed_operations']}, "
                 f"成功率 {stats['success_rate']:.1f}%, "
                 f"总耗时 {stats['total_runtime_minutes']:.1f}分钟")


# ============================================================================
# 全局Logger管理
# ============================================================================

_loggers: Dict[str, NASDAQLogger] = {}

def get_logger(name: str = 'nasdaq_fetcher', level: int = logging.INFO, 
               log_dir: str = "logs") -> NASDAQLogger:
    """
    获取或创建logger实例
    
    Args:
        name: logger名称
        level: 日志级别
        log_dir: 日志目录
    
    Returns:
        NASDAQLogger实例
    """
    logger_key = f"{name}_{log_dir}"
    if logger_key not in _loggers:
        _loggers[logger_key] = NASDAQLogger(name, level, log_dir)
    return _loggers[logger_key]


def setup_project_logging(debug_mode: bool = False) -> NASDAQLogger:
    """
    设置整个项目的日志配置
    
    Args:
        debug_mode: 是否启用调试模式
    
    Returns:
        配置好的主logger
    """
    level = logging.DEBUG if debug_mode else logging.INFO
    
    # 创建主logger
    main_logger = get_logger('nasdaq_fetcher', level)
    
    # 配置第三方库的日志级别
    logging.getLogger('ibapi').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    
    # 创建欢迎信息
    main_logger.info("="*80)
    main_logger.info("🚀 NASDAQ股票数据获取系统启动")
    main_logger.info(f"📁 日志目录: logs/")
    main_logger.info(f"🔧 调试模式: {'开启' if debug_mode else '关闭'}")
    main_logger.info("="*80)
    
    return main_logger


# ============================================================================
# 便利函数
# ============================================================================

def log_exception(logger: NASDAQLogger, message: str = "发生未处理的异常"):
    """记录异常的便利函数"""
    logger.exception(f"💥 {message}")
    
    # 获取详细的异常信息
    exc_info = sys.exc_info()
    if exc_info[0] is not None:
        tb_lines = traceback.format_exception(*exc_info)
        logger.debug(f"详细异常堆栈:\n{''.join(tb_lines)}") 