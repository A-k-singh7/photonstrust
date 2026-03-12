"""Small tracking abstraction for local JSON and MLflow backends."""

from __future__ import annotations

import importlib
import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def start_tracking_session(
    *,
    mode: str,
    output_dir: Path | str,
    run_id: str | None = None,
    tracking_uri: str | None = None,
) -> "TrackingSession":
    """Create a tracking session for the selected backend mode."""

    normalized_mode = str(mode).strip().lower()
    if normalized_mode == "local_json":
        backend = _LocalJsonBackend(
            output_dir=Path(output_dir).expanduser().resolve(),
            run_id=(run_id.strip() if isinstance(run_id, str) and run_id.strip() else None),
            tracking_uri=tracking_uri,
        )
        return TrackingSession(
            run_id=backend.run_id,
            mode=normalized_mode,
            tracking_uri=backend.tracking_uri,
            _backend=backend,
        )

    if normalized_mode == "mlflow":
        backend = _MlflowBackend(run_id=run_id, tracking_uri=tracking_uri)
        return TrackingSession(
            run_id=backend.run_id,
            mode=normalized_mode,
            tracking_uri=backend.tracking_uri,
            _backend=backend,
        )

    raise ValueError(f"Unsupported tracking mode: {mode}")


@dataclass
class TrackingSession:
    """Tracking session facade with a stable API across backends."""

    run_id: str
    mode: str
    tracking_uri: str | None
    _backend: Any = field(repr=False)

    def log_params(self, params: dict[str, Any]) -> None:
        self._backend.log_params(params)

    def log_metrics(self, metrics: dict[str, float], *, step: int | None = None) -> None:
        self._backend.log_metrics(metrics, step=step)

    def log_artifact(self, artifact_path: Path | str, *, name: str | None = None) -> str:
        return self._backend.log_artifact(artifact_path, name=name)

    def finalize(self, *, status: str = "finished") -> None:
        self._backend.finalize(status=status)


class _LocalJsonBackend:
    def __init__(self, *, output_dir: Path, run_id: str | None, tracking_uri: str | None) -> None:
        self._output_dir = output_dir
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self.run_id = run_id or _next_local_run_id(self._output_dir)
        self._run_dir = self._output_dir / self.run_id
        self._run_dir.mkdir(parents=True, exist_ok=True)
        self._artifact_dir = self._run_dir / "artifacts"
        self._artifact_dir.mkdir(parents=True, exist_ok=True)

        self.tracking_uri = tracking_uri or str(self._output_dir)
        self._params: dict[str, Any] = {}
        self._metrics: list[dict[str, Any]] = []
        self._artifacts: list[dict[str, str]] = []
        self._status = "running"
        self._write_snapshot()

    def log_params(self, params: dict[str, Any]) -> None:
        for key in sorted(params):
            self._params[str(key)] = params[key]
        self._write_snapshot()

    def log_metrics(self, metrics: dict[str, float], *, step: int | None = None) -> None:
        metric_step = int(step) if step is not None else 0
        for key in sorted(metrics):
            self._metrics.append(
                {
                    "key": str(key),
                    "value": float(metrics[key]),
                    "step": metric_step,
                }
            )
        self._metrics.sort(key=lambda row: (int(row["step"]), str(row["key"])))
        self._write_snapshot()

    def log_artifact(self, artifact_path: Path | str, *, name: str | None = None) -> str:
        source = Path(artifact_path).expanduser().resolve()
        if not source.exists():
            raise FileNotFoundError(f"Artifact path does not exist: {source}")
        artifact_name = str(name).strip() if isinstance(name, str) and name.strip() else source.name
        destination = self._artifact_dir / artifact_name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        relative = destination.relative_to(self._run_dir).as_posix()
        self._artifacts.append({"name": artifact_name, "path": relative})
        self._artifacts.sort(key=lambda row: (row["name"], row["path"]))
        self._write_snapshot()
        return relative

    def finalize(self, *, status: str = "finished") -> None:
        self._status = str(status)
        self._write_snapshot()

    def _write_snapshot(self) -> None:
        payload = {
            "schema_version": "0.1",
            "kind": "photonstrust.tracking.local_json_run",
            "run_id": self.run_id,
            "mode": "local_json",
            "tracking_uri": self.tracking_uri,
            "status": self._status,
            "params": dict(sorted(self._params.items(), key=lambda row: row[0])),
            "metrics": list(self._metrics),
            "artifacts": list(self._artifacts),
        }

        (self._run_dir / "run.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )


class _MlflowBackend:
    def __init__(self, *, run_id: str | None, tracking_uri: str | None) -> None:
        try:
            mlflow = importlib.import_module("mlflow")
        except Exception as exc:
            raise RuntimeError("mlflow is required. Install with `mlflow`.") from exc

        if tracking_uri:
            mlflow.set_tracking_uri(str(tracking_uri))

        run_name = str(run_id) if run_id is not None and str(run_id).strip() else None
        active_run = mlflow.start_run(run_name=run_name)
        self._mlflow = mlflow
        self.run_id = str(active_run.info.run_id)
        self.tracking_uri = str(mlflow.get_tracking_uri())

    def log_params(self, params: dict[str, Any]) -> None:
        normalized = {str(key): value for key, value in params.items()}
        self._mlflow.log_params(normalized)

    def log_metrics(self, metrics: dict[str, float], *, step: int | None = None) -> None:
        for key, value in metrics.items():
            if step is None:
                self._mlflow.log_metric(str(key), float(value))
            else:
                self._mlflow.log_metric(str(key), float(value), step=int(step))

    def log_artifact(self, artifact_path: Path | str, *, name: str | None = None) -> str:
        source = Path(artifact_path).expanduser().resolve()
        if not source.exists():
            raise FileNotFoundError(f"Artifact path does not exist: {source}")
        artifact_subdir = str(name) if isinstance(name, str) and name.strip() else None
        self._mlflow.log_artifact(str(source), artifact_path=artifact_subdir)
        return source.name

    def finalize(self, *, status: str = "finished") -> None:
        normalized = str(status).strip().upper() or "FINISHED"
        if normalized not in {"FINISHED", "FAILED", "KILLED"}:
            normalized = "FINISHED"
        self._mlflow.end_run(status=normalized)


def _next_local_run_id(output_dir: Path) -> str:
    max_index = 0
    for path in output_dir.iterdir():
        if not path.is_dir():
            continue
        name = path.name
        if not name.startswith("run_"):
            continue
        suffix = name[4:]
        if suffix.isdigit():
            max_index = max(max_index, int(suffix))
    return f"run_{max_index + 1:04d}"
