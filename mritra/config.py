"""Single loader for everything under configs/."""

from __future__ import annotations

import hashlib
from functools import cache
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = REPO_ROOT / "configs"


@cache
def load_config(name: str = "experiment") -> dict[str, Any]:
    """Load `configs/<name>.yaml` as a dict (cached; treat the result as read-only)."""
    with (CONFIG_DIR / f"{name}.yaml").open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def config_sha256(name: str = "experiment") -> str:
    """SHA-256 of the raw config file, recorded alongside every result."""
    return hashlib.sha256((CONFIG_DIR / f"{name}.yaml").read_bytes()).hexdigest()


def repo_path(relative: str | Path) -> Path:
    """Resolve a path from config (relative to the repo root)."""
    return REPO_ROOT / relative
