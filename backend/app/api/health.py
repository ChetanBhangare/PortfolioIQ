from fastapi import APIRouter
router=APIRouter(tags=["system"])
@router.get("/health")
def health(): return {"status":"ok","service":"portfolioiq-api","release":"R2.2-risk-contribution-stress"}
