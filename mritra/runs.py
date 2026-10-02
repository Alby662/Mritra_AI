"""Run directories and manifests under results/runs/<run_id>/.

A run manifest records what produced a run's outputs: config hash, snapml version,
partition, seeds, and the feature column list per configuration -- so a run's numbers can
always be traced back to exactly what generated them (CLAUDE.md rule 9: "no hand-typed
numbers").
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mritra.config import repo_path


def new_run_id() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def run_dir(run_id: str) -> Path:
    d = repo_path("results") / "runs" / run_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def manifest_path(run_id: str) -> Path:
    return run_dir(run_id) / "manifest.json"


def write_manifest(run_id: str, updates: dict[str, Any]) -> None:
    """Merge ``updates`` into the run's manifest.json (creating it if needed)."""
    path = manifest_path(run_id)
    manifest = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    manifest.update(updates)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")


def read_manifest(run_id: str) -> dict[str, Any]:
    path = manifest_path(run_id)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def snapml_version() -> str:
    import importlib.metadata

    return importlib.metadata.version("snapml")
