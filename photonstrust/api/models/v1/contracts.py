"""Typed API v1 request/response contracts."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class V1ErrorModel(BaseModel):
    code: str
    detail: str
    request_id: str
    retryable: bool


class V1ErrorEnvelope(BaseModel):
    error: V1ErrorModel


class V1RunSummary(BaseModel):
    run_id: str
    run_type: str
    generated_at: str
    output_dir: str
    project_id: str = "default"
    input_hash: str | None = None
    protocol_selected: str | None = None
    source_job_id: str | None = None
    compile_cache_key: str | None = None
    multifidelity_present: bool = False


class V1RunsListResponse(BaseModel):
    generated_at: str
    runs_root: str
    project_id: str | None = None
    runs: list[V1RunSummary]
    provenance: dict[str, Any]
    request_id: str


class V1RunManifest(BaseModel):
    model_config = ConfigDict(extra="allow")

    schema_version: str
    run_id: str
    run_type: str
    generated_at: str
    output_dir: str
    input: dict[str, Any] = Field(default_factory=dict)
    outputs_summary: dict[str, Any] = Field(default_factory=dict)
    artifacts: dict[str, Any] = Field(default_factory=dict)
    provenance: dict[str, Any] = Field(default_factory=dict)


class V1RunGetResponse(BaseModel):
    request_id: str
    run: V1RunManifest


class V1QkdRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    graph: dict[str, Any]
    execution_mode: str = "preview"
    include_cache_stats: bool = False
    include_qasm: bool = True
    project_id: str = "default"
    pdk: dict[str, Any] | None = None
    pdk_manifest: dict[str, Any] | None = None
    source_job_id: str | None = None


class V1QkdRunResponse(BaseModel):
    request_id: str
    run_id: str
    output_dir: str
    graph_hash: str
    compiled_config: dict[str, Any]
    compile_cache: dict[str, Any]
    results: dict[str, Any]
    artifact_relpaths: dict[str, Any]
    manifest_path: str
