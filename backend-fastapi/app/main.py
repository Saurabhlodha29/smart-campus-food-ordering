"""
FastAPI application factory.

Foundation stage: app boots, exception handlers registered, DB + lifespan wired.
No routers are mounted yet — those are added module-by-module per §22 migration order.
"""
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import AsyncSessionLocal
from app.exceptions import ApiException, api_exception_handler, runtime_exception_handler

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup / shutdown lifecycle.

    On startup: seed roles + SuperAdmin (DataInitializer equivalent).
    This hook is intentionally idempotent — existence-check before every insert,
    so re-running on every boot is safe and produces zero duplicate rows.

    Must NOT crash the app if seeding fails against a live DB the app doesn't
    own (e.g. if migrations haven't been run yet). We log the failure and
    continue serving traffic — JWT validation still works, routes that depend
    on seeded roles will fail loudly on demand with a clean 500.
    """
    try:
        from app.services.seeding import seed_roles_and_superadmin

        async with AsyncSessionLocal() as db:
            await seed_roles_and_superadmin(db)
    except Exception:
        logger.exception("Seeding failed at startup — continuing (run alembic upgrade head)")
    yield
    # TODO (cleanup): dispose engine, close Redis pool


def create_app() -> FastAPI:
    application = FastAPI(
        title="Smart Campus Food Ordering",
        description="Pickup-only campus food ordering — FastAPI backend",
        version="0.1.0",
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    # Reproduces Spring's AllowedOriginPatterns("*") + allowCredentials(true).
    # Auth travels via Authorization header (not cookies), which is the only
    # reason wildcard origin + credentials is valid here — see spec §4.6.
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Exception handlers ─────────────────────────────────────────────────────
    application.add_exception_handler(ApiException, api_exception_handler)  # type: ignore[arg-type]
    application.add_exception_handler(Exception, runtime_exception_handler)

    # ── Routers ────────────────────────────────────────────────────────────────
    # Auth module router — /api/auth/* (all public per SecurityConfig §9 "public").
    from app.routers.auth import router as auth_router
    # Application module routers — /api/admin-applications/* + /api/outlet-applications/*
    # (per spec §9: public submit + SUPERADMIN/ADMIN review — see migration-notes/03-applications.md)
    from app.routers.admin_application import router as admin_app_router
    from app.routers.outlet_application import router as outlet_app_router

    application.include_router(auth_router)
    application.include_router(admin_app_router)
    application.include_router(outlet_app_router)

    return application


app = create_app()
