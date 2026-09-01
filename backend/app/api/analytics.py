from fastapi import APIRouter, HTTPException

from app.analytics import AnalyticsError
from app.analytics.schemas import (
    PortfolioAnalyticsRequest,
    PortfolioAnalyticsResponse,
    PortfolioRiskRequest,
    PortfolioRiskResponse,
)
from app.analytics.risk_service import PortfolioRiskService
from app.analytics.service import PortfolioAnalyticsService

router = APIRouter(prefix="/api/analytics", tags=["analytics"])
service = PortfolioAnalyticsService()
risk_service = PortfolioRiskService(service)


@router.post("/portfolio", response_model=PortfolioAnalyticsResponse)
def analyze_portfolio(request: PortfolioAnalyticsRequest):
    try:
        return service.analyze(request)
    except AnalyticsError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/portfolio/risk", response_model=PortfolioRiskResponse)
def analyze_portfolio_risk(request: PortfolioRiskRequest):
    try:
        return risk_service.analyze(request)
    except AnalyticsError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
