import json
import logging

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

import app.api.analytics as analytics_api
import app.api.data as data_api
from app.core.settings import Settings
from app.main import app


def valid_payload():
    return {
        "portfolio_name":"Synthetic", "benchmark_ticker":"SPY",
        "holdings":[{"ticker":"SPY","weight":1.0}],
        "start_date":"2026-01-01", "end_date":"2026-01-31",
    }


def test_production_cors_rejects_wildcard_and_parses_origins():
    settings=Settings(_env_file=None,app_env="production",cors_allowed_origins="https://portfolioiq.vercel.app, http://localhost:3000/")
    assert settings.allowed_origins==["https://portfolioiq.vercel.app","http://localhost:3000"]
    with pytest.raises(ValidationError,match="Wildcard CORS"):
        Settings(_env_file=None,app_env="production",cors_allowed_origins="*")


def test_cors_allows_configured_origin_only():
    client=TestClient(app)
    allowed=client.options("/health",headers={"Origin":"http://localhost:3000","Access-Control-Request-Method":"GET"})
    rejected=client.options("/health",headers={"Origin":"https://untrusted.example","Access-Control-Request-Method":"GET"})
    assert allowed.status_code==200
    assert allowed.headers["access-control-allow-origin"]=="http://localhost:3000"
    assert "access-control-allow-origin" not in rejected.headers


def test_health_and_readiness_are_non_sensitive():
    client=TestClient(app)
    health=client.get("/health"); ready=client.get("/ready")
    assert health.status_code==ready.status_code==200
    assert health.json()=={"status":"ok","service":"portfolioiq-api","version":"0.3.1","release":"R2.5-production-deployment-hardening"}
    assert ready.json()=={"status":"ready","service":"portfolioiq-api","version":"0.3.1"}
    encoded=json.dumps([health.json(),ready.json()]).lower()
    assert "bucket" not in encoded and "arn" not in encoded and "credential" not in encoded


def test_internal_error_returns_safe_response_and_logs_category(monkeypatch,caplog):
    monkeypatch.setattr(analytics_api.service,"analyze",lambda request:(_ for _ in ()).throw(RuntimeError("private diagnostic")))
    with caplog.at_level(logging.ERROR):
        response=TestClient(app,raise_server_exceptions=False).post("/api/analytics/portfolio",json=valid_payload())
    assert response.status_code==500
    assert response.json()=={"detail":"An internal service error occurred."}
    assert "unhandled_exception" in caplog.text
    assert "private diagnostic" not in response.text


def test_request_log_contains_metadata_not_portfolio_payload(caplog):
    with caplog.at_level(logging.INFO):
        response=TestClient(app).post("/api/analytics/portfolio",json={**valid_payload(),"holdings":[{"ticker":"SPY","weight":.8}]})
    assert response.status_code==422
    assert "request_complete" in caplog.text and '"status_code": 422' in caplog.text
    assert "Synthetic" not in caplog.text


def test_data_status_does_not_expose_bucket_or_raw_storage_error(monkeypatch):
    monkeypatch.setattr(data_api,"get_storage",lambda settings:object())
    monkeypatch.setattr(data_api,"dataset_status",lambda ticker,storage:(_ for _ in ()).throw(RuntimeError("private bucket diagnostic")))
    response=TestClient(app).get("/api/data/status")
    assert response.status_code==200
    assert "bucket" not in response.json()
    assert "private bucket diagnostic" not in response.text
    assert all(row["error"]=="Dataset status unavailable" for row in response.json()["datasets"])
