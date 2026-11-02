"""FastAPI application factory and shared request handling."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from inventory_api.config import Settings
from inventory_api.database import initialize_database
from inventory_api.models import ErrorResponse, ItemCreate, ItemResponse, ItemUpdate
from inventory_api.repository import (
    DuplicateItemError,
    ItemNotFoundError,
    create_item,
    delete_item,
    get_item,
    list_items,
    list_low_stock_items,
    update_item,
)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create an isolated application configured for the supplied local inventory."""
    app_settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
        initialize_database(app_settings.database_path)
        yield

    app = FastAPI(title="Home Inventory API", version="1.0.0", lifespan=lifespan)
    app.state.settings = app_settings

    @app.exception_handler(HTTPException)
    async def http_error(_: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        return JSONResponse(status_code=exc.status_code, content={"detail": detail})

    @app.exception_handler(RequestValidationError)
    async def request_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        messages = [
            f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
            for error in exc.errors()
        ]
        return JSONResponse(status_code=400, content={"detail": "; ".join(messages)})

    def error_response(description: str) -> dict[str, object]:
        return {"model": ErrorResponse, "description": description}

    def item_response(item: dict[str, object]) -> dict[str, object]:
        return {**item, "currency": app_settings.currency}

    @app.post(
        "/items",
        response_model=ItemResponse,
        status_code=status.HTTP_201_CREATED,
        name="create_item",
        responses={
            201: {
                "description": "Item created",
                "headers": {
                    "Location": {
                        "schema": {"type": "string"},
                        "description": "URL of the created item",
                    }
                },
            },
            400: error_response("Invalid item input"),
            409: error_response("Item identifier is already in use"),
        },
    )
    def create_inventory_item(
        item: ItemCreate, request: Request, response: Response
    ) -> dict[str, object]:
        try:
            created = create_item(app_settings.database_path, item.model_dump())
        except DuplicateItemError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Item identifier '{exc}' already exists",
            ) from exc
        response.headers["Location"] = str(request.url_for("get_item", item_id=str(created["id"])))
        return item_response(created)

    @app.get("/items/low-stock", response_model=list[ItemResponse], name="list_low_stock_items")
    def get_low_stock_items() -> list[dict[str, object]]:
        items = list_low_stock_items(
            app_settings.database_path,
            app_settings.low_stock_threshold,
        )
        return [item_response(item) for item in items]

    @app.get(
        "/items",
        response_model=list[ItemResponse],
        name="list_items",
        responses={400: error_response("Invalid query parameter")},
    )
    def get_items(
        category: str | None = None,
        sort_by: str | None = None,
        order: str = Query(default="asc"),
    ) -> list[dict[str, object]]:
        if sort_by is not None and sort_by not in {"quantity", "unit_price", "expiry_date"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="sort_by must be quantity, unit_price, or expiry_date",
            )
        if order not in {"asc", "desc"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="order must be asc or desc",
            )
        items = list_items(
            app_settings.database_path,
            category=category,
            sort_by=sort_by,
            order=order,
        )
        return [item_response(item) for item in items]

    @app.get(
        "/items/{item_id}",
        response_model=ItemResponse,
        name="get_item",
        responses={404: error_response("Item identifier is not present")},
    )
    def get_inventory_item(item_id: str) -> dict[str, object]:
        try:
            item = get_item(app_settings.database_path, item_id)
        except ItemNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Item '{item_id}' was not found",
            ) from exc
        return item_response(item)

    @app.put(
        "/items/{item_id}",
        response_model=ItemResponse,
        name="update_item",
        responses={
            400: error_response("Invalid item input"),
            404: error_response("Item identifier is not present"),
        },
    )
    def update_inventory_item(item_id: str, item: ItemUpdate) -> dict[str, object]:
        try:
            updated = update_item(
                app_settings.database_path,
                item_id,
                item.model_dump(),
            )
        except ItemNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Item '{item_id}' was not found",
            ) from exc
        return item_response(updated)

    @app.delete(
        "/items/{item_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        name="delete_item",
        responses={404: error_response("Item identifier is not present")},
    )
    def delete_inventory_item(item_id: str) -> None:
        try:
            delete_item(app_settings.database_path, item_id)
        except ItemNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Item '{item_id}' was not found",
            ) from exc

    def custom_openapi() -> dict[str, object]:
        if app.openapi_schema is not None:
            return app.openapi_schema
        schema = get_openapi(title=app.title, version=app.version, routes=app.routes)
        for path_item in schema["paths"].values():
            for operation in path_item.values():
                if isinstance(operation, dict):
                    operation.get("responses", {}).pop("422", None)
        app.openapi_schema = schema
        return schema

    app.openapi = custom_openapi
    return app


app = create_app()
