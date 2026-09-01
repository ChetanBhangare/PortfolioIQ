from fastapi import APIRouter
router=APIRouter(tags=["system"])
@router.get("/health")
def health(): return {"status":"ok","service":"portfolioiq-api","version":"0.3.1","release":"R2.5-production-deployment-hardening"}
@router.get("/ready")
def ready(): return {"status":"ready","service":"portfolioiq-api","version":"0.3.1"}
