"""FastAPI app entrypoint."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .database import init_db
from .routers import accounts, auth, logs, runs, targets, stats
from .routers import settings as settings_router
from .services import scheduler
from .services.pw_login import ensure_chromium_installed

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    # Install Playwright Chromium in a background thread so the server starts
    # immediately and the health-check probe gets a 200 without waiting for
    # the ~2-minute Chromium download that happens on a fresh production VM.
    import asyncio
    asyncio.get_event_loop().run_in_executor(None, ensure_chromium_installed)
    scheduler.start_scheduler()
    yield
    scheduler.stop_scheduler()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router)
    app.include_router(accounts.router)
    app.include_router(targets.router)
    app.include_router(runs.router)
    app.include_router(logs.router)
    app.include_router(settings_router.router)
    app.include_router(stats.router)

    @app.get("/api/health", tags=["health"])
    def health() -> dict:
        return {"status": "ok", "app": settings.app_name}

    return app


app = create_app()
