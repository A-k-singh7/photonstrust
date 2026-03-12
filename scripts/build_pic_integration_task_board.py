#!/usr/bin/env python3
"""Build per-owner integration task board from PIC external data manifest."""

from __future__ import annotations

import argparse
import csv
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
from typing import Any


DEFAULT_MANIFEST = Path("results/pic_readiness/handoff/pic_required_external_data_manifest_2026-03-03.json")
DEFAULT_OUTPUT_JSON = Path("results/pic_readiness/handoff/pic_integration_task_board_2026-03-03.json")
DEFAULT_OUTPUT_CSV = Path("results/pic_readiness/handoff/pic_integration_task_board_2026-03-03.csv")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build PIC per-owner integration task board")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST, help="External-data manifest JSON")
    parser.add_argument(
        "--output-json",
        type=Path,
        default=DEFAULT_OUTPUT_JSON,
        help="Output task board JSON path",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=DEFAULT_OUTPUT_CSV,
        help="Output task board CSV path",
    )
    parser.add_argument(
        "--default-status",
        default="ready",
        help="Default status for generated tasks (example: ready, in_progress, blocked)",
    )
    parser.add_argument(
        "--start-date",
        default=None,
        help="Target schedule start date (UTC) in YYYY-MM-DD format; defaults to current UTC date.",
    )
    parser.add_argument(
        "--target-step-days",
        type=int,
        default=2,
        help="Spacing in days between tasks inside the same area lane.",
    )
    return parser.parse_args()


def _resolve(path: Path, *, cwd: Path) -> Path:
    if path.is_absolute():
        return path.resolve()
    return (cwd / path).resolve()


def _load_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _as_str_list(value: Any) -> list[str]:
    items = _as_list(value)
    return [str(item) for item in items if isinstance(item, str)]


def _as_int(value: Any, *, fallback: int) -> int:
    if isinstance(value, (int, float, str)):
        try:
            return int(value)
        except Exception:
            return int(fallback)
    return int(fallback)


def _parse_start_date(value: str | None) -> date:
    if value is None or str(value).strip() == "":
        return datetime.now(timezone.utc).date()
    return date.fromisoformat(str(value).strip())


def _task_id(execution_order: int, requirement_id: str, *, fallback_index: int) -> str:
    suffix = requirement_id if requirement_id else f"ROW{fallback_index:02d}"
    return f"TASK-{execution_order:02d}-{suffix}"


def _expected_path_exists(expected_path: str, *, cwd: Path) -> bool:
    normalized = str(expected_path or "").strip()
    if not normalized:
        return False
    candidate = Path(normalized)
    if not candidate.is_absolute():
        candidate = (cwd / candidate)
    return candidate.exists()


def _apply_schedule_and_blockers(
    *,
    tasks: list[dict[str, Any]],
    cwd: Path,
    start_date: date,
    target_step_days: int,
) -> tuple[list[dict[str, Any]], int]:
    lane_step = max(1, int(target_step_days))
    lane_offsets: dict[str, int] = {}
    last_task_by_area: dict[str, str] = {}
    blocked_count = 0

    for task in tasks:
        area = str(task.get("area") or "General")
        lane_index = lane_offsets.get(area, 0)
        target_date = start_date + timedelta(days=lane_index * lane_step)
        lane_offsets[area] = lane_index + 1

        task_id = str(task.get("task_id") or "")
        dependency_blocker_task_id = last_task_by_area.get(area)
        expected_path = str(task.get("expected_path") or "")
        path_exists = _expected_path_exists(expected_path, cwd=cwd)

        blocker_details: list[str] = []
        blocker_codes: list[str] = []
        if dependency_blocker_task_id:
            blocker_codes.append("dependency")
            blocker_details.append(f"blocked_by_task:{dependency_blocker_task_id}")
        if not path_exists:
            blocker_codes.append("missing_expected_path")
            blocker_details.append(f"missing_expected_path:{expected_path}")

        if not blocker_codes:
            blocker_summary = "clear"
        else:
            blocker_summary = "+".join(blocker_codes)
            blocked_count += 1

        task["target_date_utc"] = target_date.isoformat()
        task["dependency_blocker_task_id"] = dependency_blocker_task_id
        task["expected_path_exists"] = bool(path_exists)
        task["blocker_summary"] = blocker_summary
        task["blocker_codes"] = blocker_codes
        task["blocker_details"] = blocker_details

        if task_id:
            last_task_by_area[area] = task_id

    return tasks, blocked_count


def _build_tasks_from_plan(
    *,
    integration_plan: list[dict[str, Any]],
    default_status: str,
) -> list[dict[str, Any]]:
    ordered_plan = sorted(
        integration_plan,
        key=lambda row: (_as_int(row.get("execution_order"), fallback=9999), str(row.get("requirement_id") or "")),
    )

    tasks: list[dict[str, Any]] = []
    for idx, row in enumerate(ordered_plan, start=1):
        execution_order = _as_int(row.get("execution_order"), fallback=idx)
        requirement_id = str(row.get("requirement_id") or "")
        owner_role = str(row.get("owner_role") or "TBD")

        ranked_sources = [
            source_row for source_row in _as_list(row.get("ranked_sources")) if isinstance(source_row, dict)
        ]
        ranked_source_ids = [
            str(source_row.get("source_id") or "")
            for source_row in ranked_sources
            if str(source_row.get("source_id") or "")
        ]
        ranked_repositories = [
            str(source_row.get("repository") or "")
            for source_row in ranked_sources
            if str(source_row.get("repository") or "")
        ]

        primary_source_id = str(row.get("primary_source_id") or "")
        if not primary_source_id and ranked_source_ids:
            primary_source_id = ranked_source_ids[0]

        tasks.append(
            {
                "task_id": _task_id(execution_order, requirement_id, fallback_index=idx),
                "execution_order": int(execution_order),
                "requirement_id": requirement_id,
                "area": str(row.get("area") or ""),
                "owner_role": owner_role,
                "status": str(default_status),
                "expected_path": str(row.get("expected_path") or ""),
                "definition_of_done": str(row.get("definition_of_done") or ""),
                "primary_source_id": primary_source_id or None,
                "ranked_source_ids": ranked_source_ids,
                "ranked_repositories": ranked_repositories,
            }
        )

    return tasks


def _build_tasks_from_requirements(
    *,
    requirements: list[dict[str, Any]],
    requirement_to_source_ids: dict[str, list[str]],
    source_repository_by_id: dict[str, str],
    default_status: str,
) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for idx, requirement in enumerate(requirements, start=1):
        requirement_id = str(requirement.get("id") or "")
        source_ids = _as_str_list(requirement.get("recommended_source_ids"))
        if not source_ids and requirement_id:
            source_ids = requirement_to_source_ids.get(requirement_id, [])

        primary_source_id = str(requirement.get("primary_source_id") or "")
        if not primary_source_id and source_ids:
            primary_source_id = source_ids[0]

        tasks.append(
            {
                "task_id": _task_id(idx, requirement_id, fallback_index=idx),
                "execution_order": int(idx),
                "requirement_id": requirement_id,
                "area": str(requirement.get("area") or ""),
                "owner_role": "TBD",
                "status": str(default_status),
                "expected_path": str(requirement.get("expected_path") or ""),
                "definition_of_done": str(requirement.get("description") or ""),
                "primary_source_id": primary_source_id or None,
                "ranked_source_ids": source_ids,
                "ranked_repositories": [
                    source_repository_by_id[source_id]
                    for source_id in source_ids
                    if source_id in source_repository_by_id
                ],
            }
        )

    return tasks


def _build_owner_summary(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    owner_map: dict[str, dict[str, Any]] = {}
    for task in tasks:
        owner_role = str(task.get("owner_role") or "TBD")
        entry = owner_map.setdefault(
            owner_role,
            {
                "owner_role": owner_role,
                "task_ids": [],
                "requirement_ids": [],
                "areas": [],
                "target_dates": [],
                "blocked_task_ids": [],
            },
        )
        entry["task_ids"].append(str(task.get("task_id") or ""))
        entry["requirement_ids"].append(str(task.get("requirement_id") or ""))
        area = str(task.get("area") or "")
        if area:
            entry["areas"].append(area)
        target_date = str(task.get("target_date_utc") or "")
        if target_date:
            entry["target_dates"].append(target_date)
        if str(task.get("blocker_summary") or "") != "clear":
            blocked_task_id = str(task.get("task_id") or "")
            if blocked_task_id:
                entry["blocked_task_ids"].append(blocked_task_id)

    owners: list[dict[str, Any]] = []
    for owner_role in sorted(owner_map):
        entry = owner_map[owner_role]
        task_ids = [task_id for task_id in entry["task_ids"] if task_id]
        requirement_ids = sorted({item for item in entry["requirement_ids"] if item})
        areas = sorted({item for item in entry["areas"] if item})
        target_dates = sorted({item for item in entry["target_dates"] if item})
        blocked_task_ids = [task_id for task_id in entry["blocked_task_ids"] if task_id]
        owners.append(
            {
                "owner_role": owner_role,
                "task_count": int(len(task_ids)),
                "task_ids": task_ids,
                "requirement_ids": requirement_ids,
                "areas": areas,
                "target_dates_utc": target_dates,
                "blocked_task_count": int(len(blocked_task_ids)),
                "blocked_task_ids": blocked_task_ids,
            }
        )
    return owners


def _write_csv(path: Path, *, tasks: list[dict[str, Any]]) -> None:
    fieldnames = [
        "execution_order",
        "task_id",
        "requirement_id",
        "area",
        "owner_role",
        "status",
        "expected_path",
        "primary_source_id",
        "ranked_source_ids",
        "ranked_repositories",
        "target_date_utc",
        "dependency_blocker_task_id",
        "expected_path_exists",
        "blocker_summary",
        "blocker_codes",
        "blocker_details",
        "definition_of_done",
    ]

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in tasks:
            writer.writerow(
                {
                    "execution_order": int(row.get("execution_order") or 0),
                    "task_id": str(row.get("task_id") or ""),
                    "requirement_id": str(row.get("requirement_id") or ""),
                    "area": str(row.get("area") or ""),
                    "owner_role": str(row.get("owner_role") or ""),
                    "status": str(row.get("status") or ""),
                    "expected_path": str(row.get("expected_path") or ""),
                    "primary_source_id": str(row.get("primary_source_id") or ""),
                    "ranked_source_ids": "|".join(_as_str_list(row.get("ranked_source_ids"))),
                    "ranked_repositories": "|".join(_as_str_list(row.get("ranked_repositories"))),
                    "target_date_utc": str(row.get("target_date_utc") or ""),
                    "dependency_blocker_task_id": str(row.get("dependency_blocker_task_id") or ""),
                    "expected_path_exists": str(bool(row.get("expected_path_exists") is True)).lower(),
                    "blocker_summary": str(row.get("blocker_summary") or ""),
                    "blocker_codes": "|".join(_as_str_list(row.get("blocker_codes"))),
                    "blocker_details": "|".join(_as_str_list(row.get("blocker_details"))),
                    "definition_of_done": str(row.get("definition_of_done") or ""),
                }
            )


def main() -> int:
    args = parse_args()
    cwd = Path.cwd()

    manifest_path = _resolve(args.manifest, cwd=cwd)
    output_json = _resolve(args.output_json, cwd=cwd)
    output_csv = _resolve(args.output_csv, cwd=cwd)

    manifest = _load_json_object(manifest_path)

    source_candidates = [
        row for row in _as_list(manifest.get("source_candidates")) if isinstance(row, dict)
    ]
    source_repository_by_id: dict[str, str] = {}
    for row in source_candidates:
        source_id = str(row.get("source_id") or "")
        if source_id:
            source_repository_by_id[source_id] = str(row.get("repository") or "")

    plan_rows = [
        row for row in _as_list(manifest.get("integration_plan")) if isinstance(row, dict)
    ]
    if plan_rows:
        tasks = _build_tasks_from_plan(integration_plan=plan_rows, default_status=str(args.default_status))
    else:
        requirements = [
            row for row in _as_list(manifest.get("requirements")) if isinstance(row, dict)
        ]
        requirement_to_source_ids_obj = _as_dict(manifest.get("requirement_to_source_ids"))
        requirement_to_source_ids: dict[str, list[str]] = {
            str(key): _as_str_list(value) for key, value in requirement_to_source_ids_obj.items()
        }
        tasks = _build_tasks_from_requirements(
            requirements=requirements,
            requirement_to_source_ids=requirement_to_source_ids,
            source_repository_by_id=source_repository_by_id,
            default_status=str(args.default_status),
        )

    tasks.sort(key=lambda row: (int(row.get("execution_order") or 0), str(row.get("task_id") or "")))

    start_date = _parse_start_date(args.start_date)
    tasks, blocked_task_count = _apply_schedule_and_blockers(
        tasks=tasks,
        cwd=cwd,
        start_date=start_date,
        target_step_days=int(args.target_step_days),
    )

    owners = _build_owner_summary(tasks)

    payload = {
        "schema_version": "0.1",
        "kind": "photonstrust.pic_integration_task_board",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "manifest": str(manifest_path),
            "manifest_kind": str(manifest.get("kind") or ""),
            "default_status": str(args.default_status),
            "start_date_utc": start_date.isoformat(),
            "target_step_days": int(max(1, args.target_step_days)),
        },
        "task_count": int(len(tasks)),
        "owner_count": int(len(owners)),
        "blocked_task_count": int(blocked_task_count),
        "tasks": tasks,
        "owners": owners,
    }

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    _write_csv(output_csv, tasks=tasks)

    print(
        json.dumps(
            {
                "task_board_json": str(output_json),
                "task_board_csv": str(output_csv),
                "task_count": int(len(tasks)),
                "owner_count": int(len(owners)),
                "blocked_task_count": int(blocked_task_count),
            },
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
