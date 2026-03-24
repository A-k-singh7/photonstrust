"""Starlette middleware that auto-logs every API request to the audit trail."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from photonstrust.audit.log import AuditLog


class AuditMiddleware(BaseHTTPMiddleware):
    """Logs incoming HTTP requests to an :class:`AuditLog`."""

    def __init__(self, app, *, audit_log: AuditLog) -> None:  # type: ignore[override]
        super().__init__(app)
        self._audit_log = audit_log

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        actor = request.headers.get("X-PhotonTrust-User", "anonymous")
        try:
            response = await call_next(request)
        except Exception:
            raise
        else:
            try:
                self._audit_log.append(
                    actor=actor,
                    action="api_call",
                    resource_type=request.url.path,
                    resource_id=request.method,
                    details={"status_code": response.status_code},
                )
            except Exception:
                # Never break the request due to audit logging failures
                pass
            return response
