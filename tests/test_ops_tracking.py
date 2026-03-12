from __future__ import annotations

import json
from pathlib import Path

import pytest

from photonstrust.ops.tracking import start_tracking_session


def test_tracking_local_json_logs_payload_and_artifact(tmp_path: Path) -> None:
    output_dir = tmp_path / "tracking"
    artifact_source = tmp_path / "note.txt"
    artifact_source.write_text("deterministic artifact\n", encoding="utf-8")

    session = start_tracking_session(mode="local_json", output_dir=output_dir, run_id="day90_ws3")
    session.log_params({"alpha": 1.0, "seed": 7})
    session.log_metrics({"score": 0.91}, step=3)
    rel_artifact_path = session.log_artifact(artifact_source)
    session.finalize()

    run_json_path = output_dir / "day90_ws3" / "run.json"
    assert run_json_path.exists()

    payload = json.loads(run_json_path.read_text(encoding="utf-8"))
    assert payload["kind"] == "photonstrust.tracking.local_json_run"
    assert payload["run_id"] == "day90_ws3"
    assert payload["mode"] == "local_json"
    assert payload["status"] == "finished"
    assert payload["params"] == {"alpha": 1.0, "seed": 7}
    assert payload["metrics"] == [{"key": "score", "step": 3, "value": 0.91}]
    assert payload["artifacts"] == [{"name": "note.txt", "path": "artifacts/note.txt"}]
    assert rel_artifact_path == "artifacts/note.txt"

    copied_artifact = output_dir / "day90_ws3" / "artifacts" / "note.txt"
    assert copied_artifact.read_text(encoding="utf-8") == "deterministic artifact\n"


def test_tracking_mlflow_mode_raises_when_dependency_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _missing_mlflow(name: str):
        if name == "mlflow":
            raise ImportError("mlflow missing for test")
        return __import__(name)

    monkeypatch.setattr("photonstrust.ops.tracking.importlib.import_module", _missing_mlflow)

    with pytest.raises(RuntimeError, match="mlflow is required"):
        start_tracking_session(mode="mlflow", output_dir=tmp_path)
