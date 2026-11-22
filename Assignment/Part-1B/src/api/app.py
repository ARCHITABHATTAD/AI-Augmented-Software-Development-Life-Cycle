from __future__ import annotations

import logging
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from src.api.routes import router
from src.config import Settings
from src.domain.triage import (
    EmptyCustomerMessage,
    InvalidCustomerMessage,
    TriageService,
)
from src.domain.validation import ProviderOutputError
from src.persistence.database import SQLiteRepository
from src.providers.base import ProviderUnavailable
from src.providers.configured_provider import ConfiguredProvider
from src.providers.mock_provider import MockProvider

LOGGER = logging.getLogger(__name__)


def create_app(
    settings: Settings | None = None,
    *,
    provider: Any | None = None,
    repository: SQLiteRepository | None = None,
) -> FastAPI:
    configured = settings or Settings.from_env()
    repo = repository or SQLiteRepository(
        configured.database_path, configured.reviewer_credentials
    )
    selected_provider = provider or _make_provider(configured)
    service = TriageService(selected_provider)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        try:
            repo.cleanup_expired()
        except sqlite3.Error:
            LOGGER.exception("Startup retention cleanup failed.")
        yield

    app = FastAPI(
        title="AI Customer Support Ticket Triage",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.state.settings = configured
    app.state.repository = repo
    app.state.triage_service = service
    static_directory = Path(__file__).with_name("static")
    app.mount(
        "/static",
        StaticFiles(directory=str(static_directory), html=False),
        name="static",
    )
    app.include_router(router)

    @app.exception_handler(EmptyCustomerMessage)
    async def empty_message_handler(
        _: Request, exc: EmptyCustomerMessage
    ) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(InvalidCustomerMessage)
    async def invalid_message_handler(
        _: Request, exc: InvalidCustomerMessage
    ) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(ProviderUnavailable)
    async def unavailable_provider_handler(
        _: Request, __: ProviderUnavailable
    ) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={"detail": "The triage provider is unavailable."},
        )

    @app.exception_handler(ProviderOutputError)
    async def invalid_provider_output_handler(
        _: Request, __: ProviderOutputError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={"detail": "The triage provider returned invalid output."},
        )

    @app.exception_handler(sqlite3.Error)
    async def persistence_error_handler(_: Request, __: sqlite3.Error) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={"detail": "The triage record store is unavailable."},
        )

    return app


def _make_provider(settings: Settings) -> Any:
    if settings.triage_provider == "mock":
        return MockProvider()
    if settings.triage_provider == "openai_compatible":
        return ConfiguredProvider(settings)
    raise ValueError("TRIAGE_PROVIDER must be mock or openai_compatible.")


