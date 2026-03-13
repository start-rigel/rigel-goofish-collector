from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import asdict
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.config import Config, load_config
from app.services.login_state_service import LoginStateService


class LoginStateUpsertRequest(BaseModel):
    content: str
    file_name: Optional[str] = None


class RuntimePlanRequest(BaseModel):
    strategy: Optional[str] = None
    account_state_file: Optional[str] = None


def create_app(cfg: Optional[Config] = None) -> FastAPI:
    config = cfg or load_config()
    state_service = LoginStateService(config.state_dir, config.root_state_file)

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
                "DELETE /api/v1/login-state/{file_name}",
                "POST /api/v1/runtime-plan",
            ],
            "todo": [
                "wire vendored scraper into market summary search flow",
                "adapt ai-goofish-monitor listing extraction into part-focused market summaries",
            ],
        }

    @app.get("/api/v1/state-files")
    async def list_state_files() -> dict:
        return {"count": len(state_service.list_state_files()), "items": [asdict(item) for item in state_service.list_state_files()]}

    @app.post("/api/v1/login-state")
    async def save_login_state(req: LoginStateUpsertRequest) -> dict:
        try:
            saved = state_service.save_state(req.content, req.file_name)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"message": "login state saved", "item": asdict(saved)}

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

    return app


def run() -> None:
    cfg = load_config()
    uvicorn.run(create_app(cfg), host="0.0.0.0", port=cfg.http_port)
