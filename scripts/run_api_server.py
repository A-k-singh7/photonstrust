"""Run PhotonTrust FastAPI server (dev)."""

from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="Run PhotonTrust API server (FastAPI/uvicorn)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload (dev)")
    args = parser.parse_args()

    import uvicorn

    uvicorn.run(
        "photonstrust.api.server:app",
        host=str(args.host),
        port=int(args.port),
        reload=bool(args.reload),
    )


if __name__ == "__main__":
    main()

