from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


def _error_body(detail: str, code: str) -> dict:
    return {
        "detail": detail,
        "code": code,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(404)
    async def not_found(request: Request, exc):
        return JSONResponse(
            status_code=404,
            content=_error_body("Resource not found", "NOT_FOUND"),
        )

    @app.exception_handler(422)
    async def validation_error(request: Request, exc):
        return JSONResponse(
            status_code=422,
            content=_error_body(str(exc), "VALIDATION_ERROR"),
        )

    @app.exception_handler(500)
    async def server_error(request: Request, exc):
        return JSONResponse(
            status_code=500,
            content=_error_body("Internal server error", "SERVER_ERROR"),
        )