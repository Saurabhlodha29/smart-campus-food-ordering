"""
FastAPI application factory.

Foundation stage: app boots, exception handlers registered, DB + lifespan wired.
No routers are mounted yet — those are added module-by-module per §22 migration order.
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.exceptions import ApiException, api_exception_handler, runtime_exception_handler


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Startup / shutdown lifecycle.

    On startup: seed roles + SuperAdmin (DataInitializer equivalent).
    This hook is intentionally idempotent — existence-check before every insert.
    The actual seeding logic will be added in the Auth module (migration step 2).
    """
    # TODO (Auth module): call seed_roles_and_superadmin() here
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
    # Routers are added here, one per migration module, after review sign-off.
    # DO NOT add routers here until the corresponding module is approved.

    return application


app = create_app()
