from functools import lru_cache
from pathlib import Path
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_ASSET_UNIVERSE=["SPY","QQQ","IWM","DIA","XLF","XLE","XLK","XLV","XLY","XLP","XLI","XLU","XLB","XLRE","EFA","EEM","VEA","VWO","TLT","IEF","SHY","LQD","HYG","TIP","GLD","SLV","DBC","VNQ","MTUM","QUAL","VLUE","USMV","VIG"]

class Settings(BaseSettings):
    app_env:str="development"
    api_host:str="0.0.0.0"
    api_port:int=8000
    cors_allowed_origins:str="http://localhost:3000"
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
    @model_validator(mode="after")
    def validate_production_settings(self):
        if self.app_env.lower()=="production" and "*" in self.allowed_origins:
            raise ValueError("Wildcard CORS origins are not allowed in production")
        return self
    @property
    def allowed_origins(self): return [origin.strip().rstrip("/") for origin in self.cors_allowed_origins.split(",") if origin.strip()]
    @property
    def local_data_path(self): return Path(self.local_data_root).resolve()

@lru_cache
def get_settings(): return Settings()
