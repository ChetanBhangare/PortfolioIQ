import json
import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.analytics import router as analytics_router
from app.api.data import router as data_router
from app.api.health import router as health_router
from app.core.settings import get_settings


settings = get_settings()
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("portfolioiq.api")
app = FastAPI(title="PortfolioIQ API", version="0.3.1")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.middleware("http")
async def request_logging(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))[:128]
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(json.dumps({"event":"request_error","request_id":request_id,"method":request.method,"path":request.url.path,"error_category":"unhandled_exception"}))
        raise
    latency_ms = round((time.perf_counter() - started) * 1000, 2)
    logger.info(json.dumps({"event":"request_complete","request_id":request_id,"method":request.method,"path":request.url.path,"status_code":response.status_code,"latency_ms":latency_ms}))
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, error: Exception):
    return JSONResponse(status_code=500, content={"detail":"An internal service error occurred."})


app.include_router(health_router)
app.include_router(data_router)
app.include_router(analytics_router)


@app.get("/")
def root():
    return {"name":"PortfolioIQ","docs":"/docs"}
