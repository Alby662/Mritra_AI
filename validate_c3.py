# ruff: noqa: E501
from pathlib import Path

import pandas as pd

from mritra.config import load_config
from mritra.data.partition import add_institutions, make_partition
from mritra.features.network import NETWORK_SUMMARY_DIM
from mritra.features.views import feature_view


def main():
    cfg = load_config()
    k = cfg["institutions"]["k"]

    # Load base df just to get feature_view
    df = pd.read_parquet(cfg["paths"]["parquet"] + "/trans.parquet")
    df = df[df["split"].isin(["train", "val", "test"])].copy()
    part_cfg = cfg["partitions"]["P1"]
    inst_of = make_partition(df, part_cfg["method"], k, seed=part_cfg.get("seed"))
    df = add_institutions(df, inst_of)

    run_dir = list(sorted(Path("results/runs").glob("*")))[-1]

    for bank_id in range(k):
        expected_view = feature_view(
            "C3", df, bank_id=bank_id, network_summary_dim=NETWORK_SUMMARY_DIM
        )
        expected_cols = sorted(expected_view.feature_columns)

        path = run_dir / f"features/C3/bank_{bank_id}.parquet"
        print(f"Validating {path}...")

        try:
            actual_df = pd.read_parquet(path)
        except Exception as e:
            print(f"FAILED to read {path}: {e}")
            continue

        print(f"Bank {bank_id}: Successfully read {len(actual_df)} rows")

        actual_cols = sorted(list(actual_df.columns))

        if actual_cols == expected_cols:
            print(
                f"Bank {bank_id}: Schema exactly matches feature_view('C3') ({len(actual_cols)} columns)"
            )
        else:
            print(f"Bank {bank_id}: SCHEMA MISMATCH!")
            missing = set(expected_cols) - set(actual_cols)
            extra = set(actual_cols) - set(expected_cols)
            print(f"  Missing from parquet: {missing}")
            print(f"  Extra in parquet: {extra}")


if __name__ == "__main__":
    main()
# noqa: E501
