from typing import Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.app.config import get_settings
from api.app.errors import install_error_handlers
from api.app.routers import auth, events, jobs, quotes, requests, rules, uploads, voice


def create_app() -> FastAPI:
    app = FastAPI(
        title="SuryaSetu API",
        version="0.1.0",
        description="PM Surya Ghar rooftop solar marketplace. Every number comes from `rules/`.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_settings().cors_origins,
        allow_methods=["*"],
        allow_headers=["Authorization", "Content-Type"],
    )
    install_error_handlers(app)
    for module in (auth, uploads, voice, requests, quotes, jobs, events, rules):
        app.include_router(module.router)

    @app.get("/health", tags=["health"])
    async def health() -> dict[Literal["status"], Literal["ok"]]:
        return {"status": "ok"}

    return app


app = create_app()
