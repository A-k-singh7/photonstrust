"""Authentication and project-scope helpers for the local API surface."""

from __future__ import annotations

import os
from typing import Any

from fastapi import HTTPException, Request


_AUTH_MODES = {"off", "header"}
_ROLE_SET = {"viewer", "runner", "approver", "admin"}


def auth_mode() -> str:
    mode = str(os.environ.get("PHOTONTRUST_API_AUTH_MODE", "off") or "off").strip().lower() or "off"
    if mode not in _AUTH_MODES:
        return "off"
    return mode


def auth_context(request: Request) -> dict[str, Any]:
    mode = auth_mode()
    if mode == "off":
        return {
            "mode": "off",
            "actor": "anonymous",
            "roles": set(_ROLE_SET),
            "projects": {"*"},
        }

    expected_token = str(os.environ.get("PHOTONTRUST_API_DEV_TOKEN", "") or "").strip()
    if expected_token:
        got_token = str(request.headers.get("x-photonstrust-dev-token", "") or "").strip()
        if got_token != expected_token:
            raise HTTPException(status_code=401, detail="invalid or missing dev token")

    actor = str(request.headers.get("x-photonstrust-actor", "") or "").strip()
    if not actor:
        raise HTTPException(status_code=401, detail="missing x-photonstrust-actor header")

    raw_roles = str(request.headers.get("x-photonstrust-roles", "") or "").strip()
    roles = {item.strip().lower() for item in raw_roles.split(",") if item.strip()}
    if not roles:
        raise HTTPException(status_code=401, detail="missing x-photonstrust-roles header")
    if not roles.intersection(_ROLE_SET):
        raise HTTPException(status_code=401, detail="no supported roles in x-photonstrust-roles")

    raw_projects = str(request.headers.get("x-photonstrust-projects", "") or "").strip()
    projects = {item.strip().lower() for item in raw_projects.split(",") if item.strip()}
    if not projects:
        projects = {"*"}

    return {
        "mode": mode,
        "actor": actor,
        "roles": roles,
        "projects": projects,
    }


def require_roles(request: Request, *required_roles: str) -> dict[str, Any]:
    ctx = auth_context(request)
    if "admin" in ctx["roles"]:
        return ctx

    required = {str(role).strip().lower() for role in required_roles if str(role).strip()}
    if not required:
        return ctx
    if not ctx["roles"].intersection(required):
        raise HTTPException(status_code=403, detail="insufficient role for endpoint")
    return ctx


def enforce_project_scope_or_403(ctx: dict[str, Any], project_id: str | None) -> None:
    pid = str(project_id or "default").strip().lower() or "default"
    projects = ctx.get("projects") if isinstance(ctx.get("projects"), set) else {"*"}
    if "*" in projects:
        return
    if pid not in projects:
        raise HTTPException(status_code=403, detail="project scope denied")
