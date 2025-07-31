#!/usr/bin/env python3
"""
基于SOLID原则的优雅面向对象数据获取架构

设计原则：
1. Single Responsibility Principle (SRP) - 单一职责原则
2. Open/Closed Principle (OCP) - 开闭原则  
3. Liskov Substitution Principle (LSP) - 里氏替换原则
4. Interface Segregation Principle (ISP) - 接口隔离原则
5. Dependency Inversion Principle (DIP) - 依赖倒置原则
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Set
from datetime import datetime, timedelta
import pandas as pd
import threading
import time
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.common import BarData
from .logger_config import get_logger


# ================================
# 0. 时间框架配置管理 (SRP - 单一职责原则)
# ================================

class BarSizeConfig:
    """时间框架配置管理器"""
    
    # IBKR支持的标准时间框架
    VALID_BAR_SIZES: Set[str] = {
        # 秒级
        "30 secs",
        # 分钟级  
        "1 min", "2 mins", "3 mins", "5 mins", "10 mins", 
        "15 mins", "20 mins", "30 mins",
        # 小时级
        "1 hour", "2 hours", "3 hours", "4 hours", "8 hours",
        # 日级以上
        "1 day", "1 week", "1 month"
    }
    
    # 默认时间框架
    DEFAULT_BAR_SIZE: str = "1 day"
    
    # 时间框架分类
    CATEGORIES: Dict[str, List[str]] = {
        "ultra_high_freq": ["30 secs"],
        "high_freq": ["1 min", "2 mins", "3 mins", "5 mins"],
        "medium_freq": ["10 mins", "15 mins", "20 mins", "30 mins"],
        "hourly": ["1 hour", "2 hours", "3 hours", "4 hours", "8 hours"],
        "daily_plus": ["1 day", "1 week", "1 month"]
    }
    
    @classmethod
    def validate(cls, bar_size: str) -> bool:
        """验证时间框架是否有效"""
        return bar_size in cls.VALID_BAR_SIZES
    
    @classmethod
    def get_default(cls) -> str:
        """获取默认时间框架"""
        return cls.DEFAULT_BAR_SIZE
    
    @classmethod
    def get_category(cls, bar_size: str) -> Optional[str]:
        """获取时间框架分类"""
        for category, sizes in cls.CATEGORIES.items():
            if bar_size in sizes:
                return category
        return None
    
    @classmethod
    def get_recommended_timeout(cls, bar_size: str) -> int:
        """根据时间框架推荐超时时间"""
        category = cls.get_category(bar_size)
        timeout_map = {
            "ultra_high_freq": 120,  # 2分钟
            "high_freq": 90,         # 1.5分钟
            "medium_freq": 75,       # 1.25分钟
            "hourly": 60,           # 1分钟
            "daily_plus": 45        # 45秒
        }
        return timeout_map.get(category, 60)
    
    @classmethod
    def suggest_alternatives(cls, invalid_bar_size: str) -> List[str]:
        """为无效的时间框架推荐替代方案"""
        # 简单的建议逻辑
        if "sec" in invalid_bar_size.lower():
            return ["30 secs", "1 min"]
        elif "min" in invalid_bar_size.lower():
            return ["1 min", "5 mins", "15 mins", "30 mins"]
        elif "hour" in invalid_bar_size.lower():
            return ["1 hour", "2 hours", "4 hours"]
        else:
            return ["1 day", "1 week"]


class BarSizeValidator:
    """时间框架验证器"""
    
    def __init__(self, logger=None):
        self.logger = logger or get_logger()
    
    def validate_and_fix(self, bar_size: str) -> str:
        """验证并修复时间框架"""
        if not bar_size:
            self.logger.warning(f"⚠️  空的时间框架，使用默认值: {BarSizeConfig.get_default()}")
            return BarSizeConfig.get_default()
        
        # 标准化格式 (去除多余空格，统一大小写)
        normalized = self._normalize_bar_size(bar_size)
        
        if BarSizeConfig.validate(normalized):
            if normalized != bar_size:
                self.logger.info(f"🔧 时间框架已标准化: '{bar_size}' -> '{normalized}'")
            return normalized
        else:
            self.logger.warning(f"⚠️  无效的时间框架: '{bar_size}'")
            alternatives = BarSizeConfig.suggest_alternatives(bar_size)
            default = BarSizeConfig.get_default()
            self.logger.warning(f"🔄 建议使用: {alternatives[:3]}")
            self.logger.warning(f"🔄 使用默认值: {default}")
            return default
    
    def _normalize_bar_size(self, bar_size: str) -> str:
        """标准化时间框架格式"""
        # 去除多余空格并转换为标准格式
        parts = bar_size.strip().split()
        if len(parts) == 2:
            number, unit = parts
            
            # 标准化单位
            unit_map = {
                "sec": "secs", "second": "secs", "seconds": "secs",
                "min": "mins" if int(number) > 1 else "min", 
                "minute": "mins", "minutes": "mins",
                "hr": "hour", "hrs": "hours", "h": "hour"
            }
            
            normalized_unit = unit_map.get(unit.lower(), unit.lower())
            
            # 特殊处理：1 min 不加s
            if number == "1" and normalized_unit in ["mins"]:
                normalized_unit = "min"
            elif number != "1" and normalized_unit == "min":
                normalized_unit = "mins"
                
            return f"{number} {normalized_unit}"
        
        return bar_size


# ================================
# 1. 抽象接口 (ISP - 接口隔离原则)
# ================================

class IDataFetcher(ABC):
    """数据获取器接口"""
    
    @abstractmethod
    def fetch_data(self, symbol: str, start_date: str) -> pd.DataFrame:
        """获取数据的抽象方法"""
        pass


class IContractFactory(ABC):
    """合约工厂接口"""
    
    @abstractmethod
    def create_contract(self, symbol: str) -> Contract:
        """创建合约的抽象方法"""
        pass


class IExchangeStrategy(ABC):
    """交易所策略接口"""
    
    @abstractmethod
    def get_exchange_configs(self, symbol: str) -> List[tuple]:
        """获取交易所配置列表"""
        pass


class IDateProcessor(ABC):
    """日期处理器接口"""
    
    @abstractmethod
    def process_date_range(self, start_date: str) -> tuple:
        """处理日期范围"""
        pass


# ================================
# 2. 数据传输对象 (DTO)
# ================================

class SecurityConfig:
    """证券配置数据传输对象"""
    
    def __init__(self, symbol: str, sec_type: str, exchange: str, 
                 primary_exchange: Optional[str] = None, currency: str = "USD"):
        self.symbol = symbol
        self.sec_type = sec_type
        self.exchange = exchange
        self.primary_exchange = primary_exchange
        self.currency = currency


class FetchRequest:
    """获取请求数据传输对象"""
    
    def __init__(self, symbol: str, start_date: str, 
                 host: str = "127.0.0.1", port: int = 7496, client_id: int = 0):
        self.symbol = symbol
        self.start_date = start_date
        self.host = host
        self.port = port
        self.client_id = client_id


class FetchResult:
    """获取结果数据传输对象"""
    
    def __init__(self, success: bool, data: pd.DataFrame, 
                 symbol: str, error_message: str = ""):
        self.success = success
        self.data = data
        self.symbol = symbol
        self.error_message = error_message
        self.record_count = len(data) if not data.empty else 0


# ================================
# 3. 策略模式实现 (OCP - 开闭原则)
# ================================

class StockExchangeStrategy(IExchangeStrategy):
    """股票交易所策略"""
    
    def get_exchange_configs(self, symbol: str) -> List[tuple]:
        return [("SMART", "NASDAQ")]


class IndexExchangeStrategy(IExchangeStrategy):
    """指数交易所策略"""
    
    def get_exchange_configs(self, symbol: str) -> List[tuple]:
        symbol_upper = symbol.upper()
        
        # 基于测试结果优化的交易所顺序
        if symbol_upper == "NDX":
            return [("NASDAQ", None), ("SMART", None)]
        elif symbol_upper in ["SPX", "VIX"]:
            return [("CBOE", None), ("SMART", None)]
        elif symbol_upper in ["DJI"]:
            return [("NYSE", None), ("SMART", None)]
        else:
            return [
                ("SMART", None),
                ("NASDAQ", None),
                ("CBOE", None),
                ("NYSE", None),
                ("ISLAND", None)
            ]


# ================================
# 4. 工厂模式实现 (SRP - 单一职责原则)
# ================================

class StockContractFactory(IContractFactory):
    """股票合约工厂"""
    
    def create_contract(self, symbol: str) -> Contract:
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "STK"
        contract.exchange = "SMART"
        contract.primaryExchange = "NASDAQ"
        contract.currency = "USD"
        return contract


class IndexContractFactory(IContractFactory):
    """指数合约工厂"""
    
    def create_contract(self, symbol: str) -> Contract:
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "IND"
        contract.exchange = "SMART"  # 默认，会被策略覆盖
        contract.currency = "USD"
        return contract


class ConfigurableContractFactory(IContractFactory):
    """可配置合约工厂"""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
    
    def create_contract(self, symbol: str) -> Contract:
        contract = Contract()
        contract.symbol = symbol
        contract.secType = self.config.sec_type
        contract.exchange = self.config.exchange
        contract.currency = self.config.currency
        
        if self.config.primary_exchange:
            contract.primaryExchange = self.config.primary_exchange
            
        return contract


# ================================
# 5. 组件实现
# ================================

class DateProcessor(IDateProcessor):
    """日期处理器实现"""
    
    def process_date_range(self, start_date: str) -> tuple:
        """处理日期范围，返回 (过滤开始日期, 持续时间字符串)"""
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
        
        return filter_start_date, duration_str


class IBKRApiClient(EWrapper, EClient):
    """IBKR API客户端 - 封装底层API交互"""
    
    def __init__(self):
        EClient.__init__(self, self)
        self.data_received = False
        self.data_count = 0
        self.historical_data = []
        self.error_occurred = False
        self.error_message = ""
        self.logger = get_logger()
    
    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
        """错误处理"""
        if errorCode in [2104, 2106, 2158, 2174]:
            pass  # 正常连接信息
        else:
            self.logger.api_failure("IBKR API", errorCode, errorString)
            self.error_message = f"错误 {errorCode}: {errorString}"
            if errorCode in [200, 162, 321, 10314]:
                self.error_occurred = True
                self.data_received = True
    
    def historicalData(self, reqId: int, bar: BarData):
        """历史数据回调"""
        self.data_count += 1
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
        """历史数据结束回调"""
        self.logger.info(f"历史数据接收完成! 共接收 {self.data_count} 条数据")
        self.data_received = True


# ================================
# 6. 核心数据获取器 (DIP - 依赖倒置原则)
# ================================

class BaseFetcher(IDataFetcher):
    """基础数据获取器 - 模板方法模式"""
    
    def __init__(self, contract_factory: IContractFactory, 
                 exchange_strategy: IExchangeStrategy,
                 date_processor: IDateProcessor):
        self.contract_factory = contract_factory
        self.exchange_strategy = exchange_strategy
        self.date_processor = date_processor
        self.bar_size_validator = BarSizeValidator()
        self.logger = get_logger()
    
    def fetch_data(self, symbol: str, start_date: str, 
                   host: str = "127.0.0.1", port: int = 7496, 
                   client_id: int = 0, bar_size: Optional[str] = None) -> FetchResult:
        """获取数据的模板方法"""
        try:
            # 验证并标准化时间框架
            if bar_size is None:
                bar_size = BarSizeConfig.get_default()
            validated_bar_size = self.bar_size_validator.validate_and_fix(bar_size)
            
            # 处理日期
            filter_start_date, duration_str = self.date_processor.process_date_range(start_date)
            
            # 获取交易所配置并尝试
            exchange_configs = self.exchange_strategy.get_exchange_configs(symbol)
            
            for exchange, primary_exchange in exchange_configs:
                result = self._try_fetch_with_config(
                    symbol, exchange, primary_exchange, 
                    duration_str, filter_start_date, host, port, client_id, validated_bar_size
                )
                
                if result.success:
                    return result
            
            # 所有配置都失败
            error_msg = f"所有交易所配置都失败"
            self.logger.stock_failure(symbol, error_msg)
            return FetchResult(False, pd.DataFrame(), symbol, error_msg)
            
        except Exception as e:
            error_msg = f"获取数据异常: {str(e)}"
            self.logger.stock_failure(symbol, error_msg, e)
            return FetchResult(False, pd.DataFrame(), symbol, error_msg)
    
    def _try_fetch_with_config(self, symbol: str, exchange: str, 
                              primary_exchange: Optional[str], duration_str: str,
                              filter_start_date: datetime, host: str, port: int, 
                              client_id: int, validated_bar_size: str) -> FetchResult:
        """尝试使用特定配置获取数据"""
        client = IBKRApiClient()
        
        try:
            # 连接到TWS
            self.logger.info("正在连接到IBKR TWS...")
            client.connect(host, port, client_id)
            
            # 运行API
            api_thread = threading.Thread(target=client.run, daemon=True)
            api_thread.start()
            time.sleep(3)
            
            if not client.isConnected():
                return FetchResult(False, pd.DataFrame(), symbol, "无法建立连接")
            
            # 创建合约并更新交易所信息
            contract = self.contract_factory.create_contract(symbol)
            contract.exchange = exchange
            if primary_exchange:
                contract.primaryExchange = primary_exchange
            
            # 获取时间框架分类信息
            category = BarSizeConfig.get_category(validated_bar_size)
            recommended_timeout = BarSizeConfig.get_recommended_timeout(validated_bar_size)
            
            self.logger.system_info(f"创建合约: {symbol} ({contract.secType}) @ {exchange}")
            self.logger.system_info(f"时间框架: {validated_bar_size} (类别: {category})")
            
            # 请求历史数据
            client.reqHistoricalData(
                reqId=1,
                contract=contract,
                endDateTime="",
                durationStr=duration_str,
                barSizeSetting=validated_bar_size,  # 使用验证后的时间框架
                whatToShow="ADJUSTED_LAST",
                useRTH=1,
                formatDate=1,
                keepUpToDate=False,
                chartOptions=[]
            )
            
            # 使用推荐的超时时间
            start_time = time.time()
            while not client.data_received and time.time() - start_time < recommended_timeout:
                time.sleep(0.5)
            
            if client.error_occurred:
                return FetchResult(False, pd.DataFrame(), symbol, client.error_message)
            
            if not client.data_received:
                return FetchResult(False, pd.DataFrame(), symbol, f"获取数据超时 ({recommended_timeout}秒)")
            
            # 处理数据
            if client.historical_data:
                df = pd.DataFrame(client.historical_data)
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values('date').drop_duplicates(subset=['date'], keep='last').reset_index(drop=True)
                df.set_index('date', inplace=True)
                
                # 按开始日期筛选
                df_filtered = df[df.index >= filter_start_date]
                
                self.logger.stock_success(symbol, len(df_filtered))
                return FetchResult(True, df_filtered, symbol)
            else:
                return FetchResult(False, pd.DataFrame(), symbol, "无数据返回")
                
        except Exception as e:
            return FetchResult(False, pd.DataFrame(), symbol, f"获取异常: {str(e)}")
        finally:
            if client.isConnected():
                client.disconnect()
                time.sleep(2)


# ================================
# 7. 具体实现类 (LSP - 里氏替换原则)
# ================================

class StockDataFetcher(BaseFetcher):
    """股票数据获取器"""
    
    def __init__(self):
        super().__init__(
            contract_factory=StockContractFactory(),
            exchange_strategy=StockExchangeStrategy(),
            date_processor=DateProcessor()
        )
        self.logger.system_info("初始化股票数据获取器")


class IndexDataFetcher(BaseFetcher):
    """指数数据获取器"""
    
    def __init__(self):
        super().__init__(
            contract_factory=IndexContractFactory(),
            exchange_strategy=IndexExchangeStrategy(),
            date_processor=DateProcessor()
        )
        self.logger.system_info("初始化指数数据获取器")


# ================================
# 8. 外观模式 - 简化接口
# ================================

class DataFetcherFacade:
    """数据获取器外观类 - 提供简化的接口"""
    
    def __init__(self):
        self.stock_fetcher = StockDataFetcher()
        self.index_fetcher = IndexDataFetcher()
        self.logger = get_logger()
    
    def fetch_stock_data(self, symbol: str, start_date: str, bar_size: Optional[str] = None, **kwargs) -> pd.DataFrame:
        """获取股票数据 - 简化接口"""
        result = self.stock_fetcher.fetch_data(symbol, start_date, bar_size=bar_size, **kwargs)
        if result.success:
            return result.data
        else:
            self.logger.error(f"获取股票数据失败: {result.error_message}")
            return pd.DataFrame()
    
    def fetch_index_data(self, symbol: str, start_date: str, bar_size: Optional[str] = None, **kwargs) -> pd.DataFrame:
        """获取指数数据 - 简化接口"""
        result = self.index_fetcher.fetch_data(symbol, start_date, bar_size=bar_size, **kwargs)
        if result.success:
            return result.data
        else:
            self.logger.error(f"获取指数数据失败: {result.error_message}")
            return pd.DataFrame()
    
    def fetch_security_data(self, symbol: str, start_date: str, sec_type: Optional[str] = None, 
                           bar_size: Optional[str] = None, **kwargs) -> pd.DataFrame:
        """自动检测证券类型并获取数据"""
        if sec_type is None:
            # 自动检测逻辑
            index_symbols = ['NDX', 'SPX', 'RUT', 'VIX', 'DJI', 'IXIC', 'COMPX']
            if symbol.upper() in index_symbols or len(symbol) <= 3:
                sec_type = "IND"
            else:
                sec_type = "STK"
        
        if sec_type == "IND":
            return self.fetch_index_data(symbol, start_date, bar_size=bar_size, **kwargs)
        else:
            return self.fetch_stock_data(symbol, start_date, bar_size=bar_size, **kwargs)


# ================================
# 9. 向后兼容的函数接口
# ================================

# 暂无兼容性问题