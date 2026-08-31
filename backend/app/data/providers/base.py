from abc import ABC,abstractmethod
class MarketDataProvider(ABC):
    @abstractmethod
    def get_daily_prices(self,ticker,start,end=None): ...
