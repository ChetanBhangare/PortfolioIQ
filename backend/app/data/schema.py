import pandas as pd

MARKET_PRICE_SCHEMA_VERSION="1.0"
PRICE_COLUMNS=["date","ticker","open","high","low","close","volume"]

def normalize_price_frame(df,ticker):
    if df.empty: return pd.DataFrame(columns=PRICE_COLUMNS)
    out=df.copy()
    out.columns=[str(c).lower().replace(" ","_") for c in out.columns]
    if "date" not in out.columns:
        out=out.reset_index(); out.columns=[str(c).lower().replace(" ","_") for c in out.columns]
    if "adj_close" in out.columns and "close" not in out.columns: out["close"]=out["adj_close"]
    keep=[c for c in ["date","open","high","low","close","volume"] if c in out.columns]
    out=out[keep].copy(); out["ticker"]=ticker.upper()
    for c in ["open","high","low","close","volume"]:
        if c not in out.columns: out[c]=pd.NA
    out["date"]=pd.to_datetime(out["date"],utc=True).dt.tz_convert(None)
    return out[PRICE_COLUMNS].sort_values("date").drop_duplicates(["ticker","date"],keep="last").reset_index(drop=True)
