from datetime import timedelta
import logging
import time
import pandas as pd
import yfinance as yf
from app.data.providers.base import MarketDataProvider
from app.data.schema import normalize_price_frame

log = logging.getLogger("portfolioiq.provider.yahoo")


class YahooFinanceProvider(MarketDataProvider):
    def __init__(self,max_attempts=3,backoff_seconds=1.0):
        self.max_attempts=max_attempts
        self.backoff_seconds=backoff_seconds

    def get_daily_prices(self,ticker,start,end=None):
        effective_end=(end+timedelta(days=1)) if end else None
        for attempt in range(1,self.max_attempts+1):
            try:
                frame=yf.download(ticker,start=start.isoformat(),end=effective_end.isoformat() if effective_end else None,auto_adjust=True,actions=False,progress=False,threads=False)
                break
            except Exception:
                if attempt==self.max_attempts:
                    log.exception("ticker=%s provider=yahoo failed after attempts=%s",ticker,attempt)
                    raise
                delay=self.backoff_seconds*(2**(attempt-1))
                log.warning("ticker=%s provider=yahoo attempt=%s/%s failed; retrying in %.1fs",ticker,attempt,self.max_attempts,delay)
                time.sleep(delay)
        if frame.empty: return pd.DataFrame()
        if isinstance(frame.columns,pd.MultiIndex): frame.columns=frame.columns.get_level_values(0)
        return normalize_price_frame(frame,ticker)
