"""HTTP-layer helpers for request IDs and v1 error envelopes."""

from __future__ import annotations

import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from photonstrust.api.models.v1 import V1ErrorEnvelope


REQUEST_ID_HEADER = "x-request-id"


def request_id(request: Request) -> str:
    existing = getattr(request.state, "request_id", None)
    if isinstance(existing, str) and existing.strip():
        return existing.strip()
    rid = uuid.uuid4().hex
    request.state.request_id = rid
    return rid


def _is_v1_path(request: Request) -> bool:
    return str(request.url.path).startswith("/v1/")


def _v1_error_code(status_code: int) -> str:
    if int(status_code) == 400:
        return "invalid_request"
    if int(status_code) == 401:
        return "unauthorized"
    if int(status_code) == 403:
        return "forbidden"
    if int(status_code) == 404:
        return "not_found"
    if int(status_code) == 422:
        return "validation_error"
    return "http_error"


def _v1_error_response(*, request: Request, status_code: int, code: str, detail: str) -> JSONResponse:
    rid = request_id(request)
    payload = V1ErrorEnvelope.model_validate(
        {
            "error": {
                "code": str(code),
                "detail": str(detail),
                "request_id": rid,
                "retryable": int(status_code) in {429, 500, 502, 503, 504},
            }
        }
    )
    return JSONResponse(
        status_code=int(status_code),
        content=payload.model_dump(),
        headers={REQUEST_ID_HEADER: rid},
    )


def install_http_layer(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        incoming = str(request.headers.get(REQUEST_ID_HEADER, "") or "").strip()
        request.state.request_id = incoming or uuid.uuid4().hex
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id(request)
        return response

    @app.exception_handler(HTTPException)
    async def http_exception_handler_with_v1_envelope(request: Request, exc: HTTPException):
        if not _is_v1_path(request):
            return await http_exception_handler(request, exc)
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        return _v1_error_response(
            request=request,
            status_code=int(exc.status_code),
            code=_v1_error_code(int(exc.status_code)),
            detail=detail,
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_handler_with_v1_envelope(request: Request, exc: RequestValidationError):
        if not _is_v1_path(request):
            return await request_validation_exception_handler(request, exc)
        errors = exc.errors()
        first = errors[0] if isinstance(errors, list) and errors else {}
        detail = str(first.get("msg") or "request validation failed")
        return _v1_error_response(request=request, status_code=422, code="validation_error", detail=detail)
