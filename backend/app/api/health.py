from fastapi import APIRouter
from app.core.version import APP_VERSION, RELEASE
router=APIRouter(tags=["system"])
@router.get("/health")
def health(): return {"status":"ok","service":"portfolioiq-api","version":APP_VERSION,"release":RELEASE}
@router.get("/ready")
def ready(): return {"status":"ready","service":"portfolioiq-api","version":APP_VERSION}
