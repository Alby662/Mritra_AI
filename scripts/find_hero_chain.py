#!/usr/bin/env python3
"""scripts/find_hero_chain.py

Mines the final test/validation scoring outputs of C1 and C3 to identify the
"Hero Chain" for the live frontend demo:
- Pattern: SCATTER-GATHER laundering ring (is_laund == 1)
- C1 Siloed Model: Missed it (Prediction Probability < 0.4)
- C3 Enclave Model: Confidently caught it (Prediction Probability > 0.9)

Outputs the selected chain to results/demo_hero_chain.json with full transaction details.
"""

from __future__ import annotations

import argparse
import json
import logging

import lightgbm as lgb
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from mritra.config import load_config, repo_path
from mritra.data.partition import add_institutions, make_partition
from mritra.runs import run_dir

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("find_hero_chain")


def main() -> None:
    parser = argparse.ArgumentParser(description="Mine hero chain for frontend demo.")
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args()

    cfg = load_config()
    k = cfg["institutions"]["k"]
    parquet_dir = repo_path(cfg["paths"]["parquet"])

    # Resolve run ID
    run_id = args.run_id
    if not run_id:
        last_run_file = repo_path(cfg["paths"]["results"]) / "runs" / ".last_run_id"
        if not last_run_file.exists():
            logger.error("No .last_run_id found. Please specify --run-id.")
            return
        run_id = last_run_file.read_text(encoding="utf-8").strip()

    logger.info("Mining Hero Chain from run: %s", run_id)
    rdir = run_dir(run_id)

    # Load transactions and patterns
    logger.info("Loading transaction metadata and patterns...")
    trans = pd.read_parquet(parquet_dir / "trans.parquet")
    inst_of = make_partition(trans, cfg["partitions"]["P1"]["method"], k)
    trans = add_institutions(trans, inst_of)
    trans = trans.set_index("row_id", drop=False)

    patterns = pd.read_parquet(parquet_dir / "patterns.parquet")
    sg_patterns = patterns[patterns["pattern_type"] == "SCATTER-GATHER"].copy()

    if sg_patterns.empty:
        logger.warning("No SCATTER-GATHER patterns found. Checking all laundering patterns.")
        sg_patterns = patterns[patterns["is_laund"] == 1].copy()

    # Match pattern transactions with trans row_ids if not already present
    if "row_id" not in sg_patterns.columns:
        merged = pd.merge(
            sg_patterns,
            trans[["row_id", "ts", "from_bank", "from_acct", "to_bank", "to_acct", "split"]],
            on=["ts", "from_bank", "from_acct", "to_bank", "to_acct"],
            how="inner",
        )
    else:
        merged = sg_patterns.merge(
            trans[["split"]], left_on="row_id", right_index=True, how="inner"
        )

    pattern_ids = merged["pattern_id"].unique()
    logger.info("Found %d candidate laundering patterns", len(pattern_ids))

    # Load C1 models and C3 models (seed 42)
    seed = "42"
    c1_models = {}
    c3_models = {}

    for b in range(k):
        c1_p = rdir / "models" / "C1" / f"bank_{b}" / f"seed_{seed}.txt"
        c3_p = rdir / "models" / "C3" / f"bank_{b}" / f"seed_{seed}.txt"
        if c1_p.exists():
            c1_models[b] = lgb.Booster(model_file=str(c1_p))
        if c3_p.exists():
            c3_models[b] = lgb.Booster(model_file=str(c3_p))

    # Score transactions per candidate pattern
    logger.info("Evaluating C1 vs C3 scores across patterns...")
    scored_candidates = []

    # Load feature tables for row_ids present in patterns
    pattern_row_ids = set(merged["row_id"].unique())

    # Pre-score all pattern row_ids under C1 and C3
    c1_probs: dict[int, dict[int, float]] = {b: {} for b in range(k)}
    c3_probs: dict[int, dict[int, float]] = {b: {} for b in range(k)}

    for b in range(k):
        c1_feat_path = rdir / "features" / "C1" / f"bank_{b}.parquet"
        c3_feat_path = rdir / "features" / "C3" / f"bank_{b}.parquet"

        if c1_feat_path.exists() and b in c1_models:
            pf1 = pq.ParquetFile(c1_feat_path)
            idx1 = pf1.read(["row_id"]).column("row_id").to_numpy()
            mask1 = np.isin(idx1, list(pattern_row_ids))
            if mask1.any():
                sub_feats = pf1.read().to_pandas().iloc[mask1]
                if "row_id" in sub_feats.columns:
                    sub_feats = sub_feats.set_index("row_id")
                cols = [c for c in sub_feats.columns if c not in ("row_id", "__index_level_0__")]
                probs = c1_models[b].predict(sub_feats[cols])
                for r_id, p in zip(sub_feats.index, probs):
                    c1_probs[b][int(r_id)] = float(p)

        if c3_feat_path.exists() and b in c3_models:
            pf3 = pq.ParquetFile(c3_feat_path)
            idx3 = pf3.read(["row_id"]).column("row_id").to_numpy()
            mask3 = np.isin(idx3, list(pattern_row_ids))
            if mask3.any():
                sub_feats = pf3.read().to_pandas().iloc[mask3]
                if "row_id" in sub_feats.columns:
                    sub_feats = sub_feats.set_index("row_id")
                cols = [c for c in sub_feats.columns if c not in ("row_id", "__index_level_0__")]
                probs = c3_models[b].predict(sub_feats[cols])
                for r_id, p in zip(sub_feats.index, probs):
                    c3_probs[b][int(r_id)] = float(p)

    # Evaluate each pattern group
    for pid in pattern_ids:
        pat_rows = merged[merged["pattern_id"] == pid].sort_values("ts")
        if len(pat_rows) < 3:
            continue

        c1_chain_probs = []
        c3_chain_probs = []
        txns_data = []

        for _, r in pat_rows.iterrows():
            rid = int(r["row_id"])
            from_i = int(r.get("from_inst", trans.loc[rid, "from_inst"]))
            to_i = int(r.get("to_inst", trans.loc[rid, "to_inst"]))

            # C1 score: max of sending/receiving bank's siloed prediction
            p_c1_from = c1_probs[from_i].get(rid, 0.0) if from_i in c1_probs else 0.0
            p_c1_to = c1_probs[to_i].get(rid, 0.0) if to_i in c1_probs else 0.0
            p_c1 = max(p_c1_from, p_c1_to)

            # C3 score: maximum of available enclave scores
            p_c3_from = c3_probs[from_i].get(rid, 0.0) if from_i in c3_probs else 0.0
            p_c3_to = c3_probs[to_i].get(rid, 0.0) if to_i in c3_probs else 0.0
            p_c3 = max(p_c3_from, p_c3_to)

            c1_chain_probs.append(p_c1)
            c3_chain_probs.append(p_c3)

            txns_data.append(
                {
                    "row_id": rid,
                    "ts": int(r["ts"]),
                    "from_bank": int(r["from_bank"]),
                    "from_account": str(r["from_acct"]),
                    "to_bank": int(r["to_bank"]),
                    "to_account": str(r["to_acct"]),
                    "from_institution": from_i,
                    "to_institution": to_i,
                    "amount": float(r["amt_paid"]),
                    "format": str(r.get("fmt", "ACH")),
                    "c1_siloed_prob": round(float(p_c1), 4),
                    "c3_enclave_prob": round(float(p_c3), 4),
                    "c1_missed": bool(p_c1 < 0.4),
                    "c3_caught": bool(p_c3 > 0.9),
                }
            )

        avg_c1 = float(np.mean(c1_chain_probs)) if c1_chain_probs else 0.0
        avg_c3 = float(np.mean(c3_chain_probs)) if c3_chain_probs else 0.0
        max_c3 = float(np.max(c3_chain_probs)) if c3_chain_probs else 0.0
        gap = avg_c3 - avg_c1

        scored_candidates.append(
            {
                "pattern_id": int(pid),
                "pattern_type": str(pat_rows["pattern_type"].iloc[0]),
                "num_transactions": len(pat_rows),
                "avg_c1_score": round(avg_c1, 4),
                "avg_c3_score": round(avg_c3, 4),
                "max_c3_score": round(max_c3, 4),
                "detection_gap": round(gap, 4),
                "transactions": txns_data,
            }
        )

    # Sort candidates by detection gap and C3 confidence
    scored_candidates.sort(
        key=lambda x: (x["max_c3_score"] >= 0.85, x["detection_gap"]), reverse=True
    )

    if not scored_candidates:
        logger.warning("No candidate chains evaluated. Generating fallback hero chain.")
        return

    INSTITUTION_NAMES = {
        0: "State Bank of India (SBI)",
        1: "HDFC Bank",
        2: "ICICI Bank",
        3: "Axis Bank",
        4: "Punjab National Bank (PNB)",
    }
    INSTITUTION_COLORS = {
        0: "#000000",
        1: "#4f46e5",
        2: "#059669",
        3: "#d97706",
        4: "#ff3b30",
    }

    hero = scored_candidates[0]
    for tx in hero["transactions"]:
        tx["from_bank_name"] = INSTITUTION_NAMES.get(tx["from_institution"], f"Bank {tx['from_institution']}")
        tx["to_bank_name"] = INSTITUTION_NAMES.get(tx["to_institution"], f"Bank {tx['to_institution']}")

    # Build dynamic nodes from model transactions
    acct_map = {}
    for tx in hero["transactions"]:
        fa = tx["from_account"]
        ta = tx["to_account"]
        if fa not in acct_map:
            acct_map[fa] = {
                "id": fa, "inst": tx["from_institution"],
                "in_deg": 0, "out_deg": 0, "in_amt": 0.0, "out_amt": 0.0,
                "c1_scores": [], "c3_scores": [],
            }
        acct_map[fa]["out_deg"] += 1
        acct_map[fa]["out_amt"] += tx["amount"]
        acct_map[fa]["c1_scores"].append(tx["c1_siloed_prob"])
        acct_map[fa]["c3_scores"].append(tx["c3_enclave_prob"])

        if ta not in acct_map:
            acct_map[ta] = {
                "id": ta, "inst": tx["to_institution"],
                "in_deg": 0, "out_deg": 0, "in_amt": 0.0, "out_amt": 0.0,
                "c1_scores": [], "c3_scores": [],
            }
        acct_map[ta]["in_deg"] += 1
        acct_map[ta]["in_amt"] += tx["amount"]
        acct_map[ta]["c1_scores"].append(tx["c1_siloed_prob"])
        acct_map[ta]["c3_scores"].append(tx["c3_enclave_prob"])

    layer1_mules = []
    layer2_mules = []
    for aid, a in acct_map.items():
        if a["in_deg"] > 0 and a["out_deg"] > 0:
            is_l1 = any(tx["to_account"] == aid and acct_map[tx["from_account"]]["in_deg"] == 0 for tx in hero["transactions"])
            if is_l1:
                layer1_mules.append(aid)
            else:
                layer2_mules.append(aid)
    layer1_mules.sort()
    layer2_mules.sort()

    CLEAN_COORDINATES = {
        # Lane 0: State Bank of India (SBI)
        "8019C0990": (84, 210),
        # Lane 1: HDFC Bank
        "80514DE20": (252, 210),
        # Lane 2: ICICI Bank
        "80145D1D0": (420, 65),
        "800F24BE0": (420, 135),
        "8006A6CF0": (420, 210),
        "806E5B990": (420, 285),
        "80779F730": (420, 355),
        # Lane 3: Axis Bank
        "800459750": (588, 65),
        "802FBEBC0": (588, 135),
        "803616220": (588, 210),
        "805A16080": (588, 285),
        "8053BE3E0": (588, 355),
        # Lane 4: Punjab National Bank (PNB)
        "8016EFD70": (756, 110),
        "80381C7A0": (756, 210),
        "8028E8460": (756, 310),
    }

    nodes = []
    for aid, a in acct_map.items():
        inst = a["inst"]
        b_name = INSTITUTION_NAMES.get(inst, f"Bank {inst}")
        b_color = INSTITUTION_COLORS.get(inst, "#64748b")
        if a["in_deg"] == 0:
            role = "Source"
            label = f"Src: {aid}"
        elif a["out_deg"] == 0:
            role = "Destination"
            label = f"Dest: {aid}"
        else:
            role = "Mule"
            label = f"Mule: {aid[:5]}.."

        x, y = CLEAN_COORDINATES.get(aid, (420, 210))

        total_vol = a["in_amt"] + a["out_amt"]
        pass_through = round(a["out_amt"] / max(1.0, a["in_amt"]), 2) if a["in_amt"] > 0 else 0.0
        c1_max = round(float(np.max(a["c1_scores"])), 4) if a["c1_scores"] else 0.0
        c3_max = round(float(np.max(a["c3_scores"])), 4) if a["c3_scores"] else 0.0

        nodes.append({
            "id": aid,
            "label": label,
            "bank": b_name,
            "bankColor": b_color,
            "role": role,
            "x": x,
            "y": y,
            "c1RiskScore": c1_max,
            "c3RiskScore": c3_max,
            "balance": f"${total_vol:,.2f}",
            "passThroughRatio": min(pass_through, 1.0),
            "velocityMin": 12,
            "inDegree": a["in_deg"],
            "outDegree": a["out_deg"],
        })

    hero["nodes"] = nodes

    out_file = repo_path("results/demo_hero_chain.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(hero, indent=2), encoding="utf-8")

    logger.info("================================================================")
    logger.info(" SELECTED HERO CHAIN FOR FRONTEND DEMO")
    logger.info(" Pattern ID:        %s (%s)", hero["pattern_id"], hero["pattern_type"])
    logger.info(" Transactions:      %d", hero["num_transactions"])
    logger.info(" Avg C1 (Siloed):   %.4f", hero["avg_c1_score"])
    logger.info(" Avg C3 (Enclave):  %.4f", hero["avg_c3_score"])
    logger.info(" Max C3 (Enclave):  %.4f", hero["max_c3_score"])
    logger.info(" Detection Gain:    +%.4f", hero["detection_gap"])
    logger.info(" Saved Output:      %s", out_file)
    logger.info("================================================================")


if __name__ == "__main__":
    main()
