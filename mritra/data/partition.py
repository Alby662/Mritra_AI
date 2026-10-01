"""Assign dataset bank IDs to K simulated institutions (PREREGISTRATION §4)."""

from __future__ import annotations

import numpy as np
import pandas as pd


def bank_volumes(df: pd.DataFrame) -> pd.Series:
    """Total transaction count per bank, counting sender and receiver appearances."""
    return pd.concat([df["from_bank"], df["to_bank"]]).value_counts()


def partition_volume_balanced(volumes: pd.Series, k: int) -> dict[int, int]:
    """P1: banks by volume desc (ties: bank ID asc) go to the lightest institution.

    Ties between institutions go to the lowest index.
    """
    order = sorted(volumes.items(), key=lambda kv: (-kv[1], kv[0]))
    load = np.zeros(k, dtype=np.int64)
    inst_of: dict[int, int] = {}
    for bank, n in order:
        i = int(load.argmin())  # argmin returns the first (lowest) index on ties
        inst_of[int(bank)] = i
        load[i] += n
    return inst_of


def partition_random(banks: list[int], k: int, seed: int) -> dict[int, int]:
    """P2: uniform random institution per bank, drawn over bank IDs sorted ascending."""
    ordered = sorted(int(b) for b in banks)
    draws = np.random.default_rng(seed).integers(0, k, size=len(ordered))
    return dict(zip(ordered, (int(d) for d in draws), strict=True))


def make_partition(
    df: pd.DataFrame, method: str, k: int, seed: int | None = None
) -> dict[int, int]:
    """Build a bank -> institution map using a method name from configs/experiment.yaml."""
    volumes = bank_volumes(df)
    if method == "volume_balanced":
        return partition_volume_balanced(volumes, k)
    if method == "random":
        if seed is None:
            raise ValueError("random partition needs a seed")
        return partition_random(list(volumes.index), k, seed)
    raise ValueError(f"Unknown partition method: {method}")


def add_institutions(df: pd.DataFrame, inst_of: dict[int, int]) -> pd.DataFrame:
    """Return a copy with from_inst, to_inst and cross (sender inst != receiver inst)."""
    out = df.copy()
    out["from_inst"] = out["from_bank"].map(inst_of).astype("int8")
    out["to_inst"] = out["to_bank"].map(inst_of).astype("int8")
    out["cross"] = out["from_inst"] != out["to_inst"]
    return out
