"""FastAPI application bootstrap for PhotonTrust."""

from __future__ import annotations

import os
from pathlib import Path

from importlib.metadata import PackageNotFoundError, version
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from photonstrust.api.http_layer import install_http_layer


def photonstrust_version() -> str | None:
    try:
        return version("photonstrust")
    except Exception as exc:
        if not isinstance(exc, PackageNotFoundError):
            return None
        try:
            root = Path(__file__).resolve().parents[2]
            pyproject = root / "pyproject.toml"
            if not pyproject.exists():
                return None
            for line in pyproject.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("version"):
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        return parts[1].strip().strip("\"'")
        except (OSError, UnicodeError):
            return None
    return None


def cors_allow_origins() -> list[str]:
    """Return allowed CORS origins.

    Configure with `PHOTONTRUST_API_CORS_ALLOW_ORIGINS` as a comma-separated list.
    Defaults are local-development origins only.
    """

    raw = str(os.environ.get("PHOTONTRUST_API_CORS_ALLOW_ORIGINS", "")).strip()
    if raw:
        origins = [item.strip() for item in raw.split(",") if item.strip()]
        if origins:
            return origins

    return [
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:4173",
        "http://localhost:5173",
        "http://127.0.0.1",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:4173",
        "http://127.0.0.1:5173",
    ]


def create_app() -> FastAPI:
    app = FastAPI(title="PhotonTrust API", version=photonstrust_version() or "0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_allow_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    install_http_layer(app)
    return app
