from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_ASSET_UNIVERSE=["SPY","QQQ","IWM","DIA","XLF","XLE","XLK","XLV","XLY","XLP","XLI","XLU","XLB","XLRE","EFA","EEM","VEA","VWO","TLT","IEF","SHY","LQD","HYG","TIP","GLD","SLV","DBC","VNQ","MTUM","QUAL","VLUE","USMV","VIG"]

class Settings(BaseSettings):
    app_env:str="development"
    api_host:str="0.0.0.0"
    api_port:int=8000
    frontend_origin:str="http://localhost:3000"
    storage_mode:str="local"
    local_data_root:str="../data"
    aws_profile:str=""
    aws_region:str="us-east-1"
    s3_bucket:str=""
    s3_prefix:str="portfolioiq"
    market_data_provider:str="yahoo"
    default_start_date:str="2016-01-01"
    fred_api_key:str=""
    model_config=SettingsConfigDict(env_file=("../.env",".env"), env_file_encoding="utf-8", extra="ignore")
    @property
    def local_data_path(self): return Path(self.local_data_root).resolve()

@lru_cache
def get_settings(): return Settings()
