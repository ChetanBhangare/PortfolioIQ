import numpy as np
import pandas as pd

from app.analytics import AnalyticsError
from app.analytics.returns import wealth_index


def drawdown_series(returns: pd.Series) -> pd.DataFrame:
    if returns.empty:
        raise AnalyticsError("At least one return is required")
    wealth = wealth_index(returns)
    running_peak = wealth.cummax().clip(lower=1.0)
    drawdown = wealth / running_peak - 1.0
    return pd.DataFrame({"wealth_index": wealth, "running_peak": running_peak, "drawdown": drawdown})


def maximum_drawdown_details(returns: pd.Series):
    frame = drawdown_series(returns)
    trough = frame["drawdown"].idxmin()
    maximum = float(frame.loc[trough, "drawdown"])
    prior = frame.loc[:trough, "drawdown"]
    peak_dates = prior.index[np.isclose(prior.to_numpy(), 0.0)]
    start = peak_dates[-1] if len(peak_dates) else frame.index[0]
    after = frame.loc[trough:, "drawdown"]
    recovery_dates = after.index[after >= -1e-12]
    recovery = recovery_dates[0] if len(recovery_dates) else None
    return {
        "maximum_drawdown": maximum,
        "start_date": start.date().isoformat(),
        "trough_date": trough.date().isoformat(),
        "recovery_date": recovery.date().isoformat() if recovery is not None else None,
        "drawdown_duration_days": int((trough - start).days),
        "recovery_duration_days": int((recovery - trough).days) if recovery is not None else None,
    }
