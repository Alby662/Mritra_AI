"""Network features returned by the enclave (plan §7.1 item 3 / §8.2 step 4).

These are the cross-bank neighbourhood features that the enclave computes on
the boundary graph and returns to each bank for its own accounts only.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def compute_network_features(
    boundary_edges: pd.DataFrame,
    boundary_summaries: dict[str, np.ndarray],
    precision: int = 4,
) -> dict[str, np.ndarray]:
    """Compute network features on the boundary graph.

    Parameters
    ----------
    boundary_edges : DataFrame
        Reconciled cross-bank transactions.  Columns: edge_ref, from_acct,
        to_acct, ts, amount.
    boundary_summaries : dict
        Mapping of ``acct_key`` -> feature vector (locally computed GFP +
        behavioural features) from each bank.
    precision : int
        Rounding precision for output features (output minimisation, §9.2).

    Returns
    -------
    dict mapping ``acct_key`` to the network feature vector.
    """
    if boundary_edges.empty:
        return {}

    # Build adjacency from boundary edges
    out_edges: dict[str, list[str]] = {}
    in_edges: dict[str, list[str]] = {}
    out_amounts: dict[str, list[float]] = {}
    in_amounts: dict[str, list[float]] = {}

    for _, row in boundary_edges.iterrows():
        src = str(row["from_acct"])
        dst = str(row["to_acct"])
        amt = float(row["amount"])

        out_edges.setdefault(src, []).append(dst)
        in_edges.setdefault(dst, []).append(src)
        out_amounts.setdefault(src, []).append(amt)
        in_amounts.setdefault(dst, []).append(amt)

    all_accounts = set(out_edges.keys()) | set(in_edges.keys())
    result: dict[str, np.ndarray] = {}

    for acct in all_accounts:
        feats: list[float] = []

        # Cross-bank fan-out / fan-in
        n_out = len(out_edges.get(acct, []))
        n_in = len(in_edges.get(acct, []))
        feats.extend([float(n_out), float(n_in)])

        # Cross-bank amount out / in
        amt_out = sum(out_amounts.get(acct, []))
        amt_in = sum(in_amounts.get(acct, []))
        feats.extend([amt_out, amt_in])

        # Pass-through ratio (cross-bank only)
        pt_ratio = amt_out / amt_in if amt_in > 0 else 0.0
        feats.append(pt_ratio)

        # 1-hop neighbour summary aggregation (mean, max, sum)
        neighbours = set(out_edges.get(acct, [])) | set(in_edges.get(acct, []))
        neighbour_vecs = [boundary_summaries[n] for n in neighbours if n in boundary_summaries]
        if neighbour_vecs:
            stack = np.stack(neighbour_vecs)
            feats.extend(np.mean(stack, axis=0).tolist())
            feats.extend(np.max(stack, axis=0).tolist())
            feats.extend(np.sum(stack, axis=0).tolist())
        else:
            # No neighbour summaries — zero-fill
            dim = len(next(iter(boundary_summaries.values()))) if boundary_summaries else 0
            feats.extend([0.0] * (dim * 3))

        result[acct] = np.round(np.array(feats, dtype=np.float64), precision)

    logger.info("Computed network features for %d boundary accounts", len(result))
    return result
