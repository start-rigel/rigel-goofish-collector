from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import asdict
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.config import Config, load_config
from app.services.login_state_service import LoginStateService
from app.services.persistence_service import PersistenceService
from app.services.search_service import LoginRequiredError, RiskControlError, SearchService
from app.services.summary_service import summarize_prices


class LoginStateUpsertRequest(BaseModel):
    content: str
    file_name: Optional[str] = None


class RuntimePlanRequest(BaseModel):
    strategy: Optional[str] = None
    account_state_file: Optional[str] = None


class PromoteLoginStateRequest(BaseModel):
    file_name: str


class SearchRequest(BaseModel):
    keyword: str
    category: str = ""
    limit: int = 10
    strategy: Optional[str] = None
    account_state_file: Optional[str] = None
    persist: bool = False


class MarketSummaryRequest(BaseModel):
    keyword: str
    category: str = ""
    limit: int = 10
    strategy: Optional[str] = None
    account_state_file: Optional[str] = None
    persist: bool = False


class ValidateStateRequest(BaseModel):
    strategy: Optional[str] = None
    account_state_file: Optional[str] = None


def create_app(
    cfg: Optional[Config] = None,
    search_service: Optional[SearchService] = None,
    persistence_service: Optional[PersistenceService] = None,
) -> FastAPI:
    config = cfg or load_config()
    state_service = LoginStateService(config.state_dir, config.root_state_file)
    collector_service = search_service or SearchService(config, state_service)
    storage_service = persistence_service or (PersistenceService(config.postgres_dsn) if config.postgres_dsn else None)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        config.state_dir.mkdir(parents=True, exist_ok=True)
        yield

    app = FastAPI(title=config.service_name, lifespan=lifespan)

    @app.get("/healthz")
    async def healthz() -> dict:
        return {
            "status": "ok",
            "service": config.service_name,
            "mode": config.mode,
            "upstream_enabled": config.upstream_enabled,
            "persistence_enabled": storage_service is not None,
        }

    @app.get("/")
    async def index() -> dict:
        return {
            "service": config.service_name,
            "stage": "phase-1-adapter",
            "mode": config.mode,
            "routes": [
                "GET /healthz",
                "GET /api/v1/state-files",
                "POST /api/v1/login-state",
                "POST /api/v1/login-state/default",
                "DELETE /api/v1/login-state/{file_name}",
                "POST /api/v1/runtime-plan",
                "POST /api/v1/validate-state",
                "POST /api/v1/search",
                "POST /api/v1/market/summary",
            ],
            "todo": [
                "refine part-title filtering for Goofish used-market data",
                "persist canonical mappings after build-engine normalization is ready",
            ],
        }

    @app.get("/api/v1/state-files")
    async def list_state_files() -> dict:
        items = state_service.list_state_files()
        return {"count": len(items), "items": [asdict(item) for item in items]}

    @app.post("/api/v1/login-state")
    async def save_login_state(req: LoginStateUpsertRequest) -> dict:
        try:
            saved = state_service.save_state(req.content, req.file_name)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"message": "login state saved", "item": asdict(saved)}

    @app.post("/api/v1/login-state/default")
    async def promote_login_state(req: PromoteLoginStateRequest) -> dict:
        try:
            saved = state_service.promote_to_root(req.file_name)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"message": "default login state updated", "item": asdict(saved)}

    @app.delete("/api/v1/login-state/{file_name}")
    async def delete_login_state(file_name: str) -> dict:
        try:
            deleted = state_service.delete_state(file_name)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if not deleted:
            raise HTTPException(status_code=404, detail="state file not found")
        return {"message": "login state deleted", "file_name": file_name}

    @app.post("/api/v1/runtime-plan")
    async def runtime_plan(req: RuntimePlanRequest) -> dict:
        return state_service.resolve_runtime_plan(req.strategy, req.account_state_file)

    @app.post("/api/v1/validate-state")
    async def validate_state(req: ValidateStateRequest) -> dict:
        try:
            return await collector_service.validate_state(req.strategy, req.account_state_file)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except LoginRequiredError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        except RiskControlError as exc:
            raise HTTPException(status_code=429, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.post("/api/v1/search")
    async def search(req: SearchRequest) -> dict:
        try:
            result = await collector_service.search(req.keyword, req.category, req.limit, req.strategy, req.account_state_file)
            persist_result = _persist_if_requested(storage_service, req.persist, result, None)
            return _merge_persist_result(result, req.persist, persist_result)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except LoginRequiredError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        except RiskControlError as exc:
            raise HTTPException(status_code=429, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.post("/api/v1/market/summary")
    async def market_summary(req: MarketSummaryRequest) -> dict:
        try:
            search_result = await collector_service.search(req.keyword, req.category, req.limit, req.strategy, req.account_state_file)
            summary = summarize_prices(req.keyword, req.category, search_result.get("products", []))
            persist_result = _persist_if_requested(storage_service, req.persist, search_result, summary)
            response = {
                "keyword": req.keyword,
                "category": req.category,
                "state_file": search_result.get("state_file"),
                "products": search_result.get("products", []),
                "summary": summary,
            }
            response.update(_persist_metadata(req.persist, persist_result))
            return response
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except LoginRequiredError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        except RiskControlError as exc:
            raise HTTPException(status_code=429, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    return app


def _persist_if_requested(storage_service: Optional[PersistenceService], persist: bool, result: dict, summary: Optional[dict]):
    if not persist:
        return None
    if storage_service is None:
        raise ValueError("persistence requested but postgres dsn is not configured")
    return storage_service.persist_search_result(result, summary)


def _persist_metadata(persist: bool, persist_result) -> dict:
    payload = {"persisted": False, "persisted_count": 0}
    if persist and persist_result is not None:
        payload.update({"persisted": True, "persisted_count": persist_result.persisted_count, "job_id": persist_result.job_id})
    return payload


def _merge_persist_result(result: dict, persist: bool, persist_result) -> dict:
    payload = dict(result)
    payload.update(_persist_metadata(persist, persist_result))
    return payload


def run() -> None:
    cfg = load_config()
    uvicorn.run(create_app(cfg), host="0.0.0.0", port=cfg.http_port)
