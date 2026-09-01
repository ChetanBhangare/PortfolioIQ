from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.health import router as health_router
from app.api.data import router as data_router
from app.api.analytics import router as analytics_router
from app.core.settings import get_settings
s=get_settings(); app=FastAPI(title="PortfolioIQ API",version="0.2.1")
app.add_middleware(CORSMiddleware,allow_origins=[s.frontend_origin],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
app.include_router(health_router); app.include_router(data_router); app.include_router(analytics_router)
@app.get("/")
def root(): return {"name":"PortfolioIQ","docs":"/docs"}
