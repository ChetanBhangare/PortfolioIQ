import json,logging
from fastapi import APIRouter,HTTPException
from app.core.settings import DEFAULT_ASSET_UNIVERSE,get_settings
from app.data.query import dataset_status,load_prices
from app.data.storage import get_storage
router=APIRouter(prefix="/api/data",tags=["data"])
logger=logging.getLogger("portfolioiq.data")
@router.get("/status")
def status():
    s=get_settings(); storage=get_storage(s); out=[]
    for t in DEFAULT_ASSET_UNIVERSE:
        try: out.append(dataset_status(t,storage))
        except Exception as error:
            logger.warning(json.dumps({"event":"dataset_status_error","ticker":t,"error_category":type(error).__name__}))
            out.append({"ticker":t,"available":False,"error":"Dataset status unavailable"})
    return {"storage_mode":s.storage_mode,"datasets":out}
@router.get("/prices/{ticker}")
def prices(ticker,limit:int=250):
    ticker=ticker.upper()
    if ticker not in DEFAULT_ASSET_UNIVERSE: raise HTTPException(404,"Ticker is not in configured universe")
    df=load_prices(ticker)
    if df.empty: raise HTTPException(404,"No stored data")
    df=df.tail(max(1,min(limit,5000))).copy(); df["date"]=df["date"].astype(str)
    return {"ticker":ticker,"rows":len(df),"data":df.to_dict(orient="records")}
