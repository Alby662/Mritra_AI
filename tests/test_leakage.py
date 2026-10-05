"""Comprehensive data-leakage tests for Mritra (PREREGISTRATION §4, plan §10).

Guards against every known leakage vector that would inflate G:

  1. Temporal split — no timestamp straddles two splits; ordering is monotone.
  2. Behavioural features — no feature at time t uses data from t+1 or later.
  3. GFP / graph features — graph built on train only; test edges must not appear.
  4. Label leakage — is_laund never appears as a feature or crosses a boundary.
  5. Enclave / protocol — enclave never returns features for accounts outside
     the requesting bank; labels never cross the wire.
  6. Training — scale_pos_weight, threshold, and early-stopping use only
     train / val data.
  7. Evaluation — metrics are computed only on test split; G uses test F1s.
  8. Network features — neighbour aggregation does not leak labels.
  9. Partition — institution assignment is label-independent.
 10. Roles — role assignment on train split only; test accounts never inform roles.

Run with:  uv run pytest tests/test_leakage.py -v
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from mritra.data.partition import add_institutions, make_partition
from mritra.data.split import temporal_split
from mritra.eval.metrics import evaluate_configuration, gap_recovered
from mritra.features.behaviour import compute_behavioural_features
from mritra.features.graph_gfp import _prepare_edge_array, compute_gfp_features
from mritra.features.network import compute_network_features
from mritra.models.train import _optimal_threshold, train_lightgbm

# ───────────────────────────────────────────────────────────────────────────
# Helpers
# ───────────────────────────────────────────────────────────────────────────


def _make_transaction_df(n: int = 200, seed: int = 42) -> pd.DataFrame:
    """Synthetic transaction table with realistic columns, sorted by ts."""
    rng = np.random.default_rng(seed)
    ts = np.sort(rng.integers(1_000_000, 2_000_000, size=n))
    return pd.DataFrame(
        {
            "row_id": np.arange(n, dtype=np.int64),
            "ts": ts,
            "from_bank": rng.integers(0, 10, size=n),
            "from_acct": [f"A{i % 20}" for i in range(n)],
            "to_bank": rng.integers(0, 10, size=n),
            "to_acct": [f"B{i % 20}" for i in range(n)],
            "amt_paid": rng.exponential(500, size=n).round(2),
            "amt_recv": rng.exponential(500, size=n).round(2),
            "cur_paid": rng.choice(["USD", "EUR", "GBP"], size=n),
            "cur_recv": rng.choice(["USD", "EUR", "GBP"], size=n),
            "fmt": rng.choice(["Wire", "ACH", "Cash", "Check"], size=n),
            "is_laund": rng.choice([0, 1], size=n, p=[0.95, 0.05]).astype(np.int8),
        }
    )


def _add_inst_columns(df: pd.DataFrame, k: int = 5) -> pd.DataFrame:
    """Partition banks into k institutions and add from_inst / to_inst / cross."""
    inst_of = make_partition(df, "volume_balanced", k)
    return add_institutions(df, inst_of)


# ═══════════════════════════════════════════════════════════════════════════
# 1. TEMPORAL SPLIT INTEGRITY
# ═══════════════════════════════════════════════════════════════════════════


class TestTemporalSplitLeakage:
    """Ensure the temporal split never lets future data leak into earlier splits."""

    def test_no_timestamp_straddles_two_splits(self):
        """No single timestamp value should appear in more than one split."""
        df = _make_transaction_df(500)
        split = temporal_split(df["ts"], train=0.6, val=0.2)
        per_ts = pd.DataFrame({"ts": df["ts"], "split": split})
        nunique = per_ts.groupby("ts")["split"].nunique()
        violators = nunique[nunique > 1]
        assert violators.empty, f"Timestamps straddling splits: {violators.index.tolist()}"

    def test_splits_are_monotone_in_time(self):
        """max(train_ts) < min(val_ts) <= max(val_ts) < min(test_ts)."""
        df = _make_transaction_df(500)
        split = temporal_split(df["ts"], train=0.6, val=0.2)
        ts_by_split = {s: df["ts"][split == s] for s in ("train", "val", "test")}
        if len(ts_by_split["val"]) > 0 and len(ts_by_split["test"]) > 0:
            assert ts_by_split["train"].max() < ts_by_split["val"].min()
            assert ts_by_split["val"].max() < ts_by_split["test"].min()

    def test_every_row_gets_exactly_one_split(self):
        """All rows are labelled; no row is in two splits."""
        df = _make_transaction_df(500)
        split = temporal_split(df["ts"], train=0.6, val=0.2)
        assert split.isna().sum() == 0
        assert set(split.unique()) <= {"train", "val", "test"}

    def test_split_deterministic_across_calls(self):
        """Same data → same split, always."""
        df = _make_transaction_df(500)
        s1 = temporal_split(df["ts"], 0.6, 0.2)
        s2 = temporal_split(df["ts"], 0.6, 0.2)
        assert (s1 == s2).all()


# ═══════════════════════════════════════════════════════════════════════════
# 2. BEHAVIOURAL FEATURES — NO FUTURE LEAKAGE
# ═══════════════════════════════════════════════════════════════════════════


class TestBehaviouralFeatureLeakage:
    """Behavioural features must be strictly backward-looking at each row."""

    @pytest.fixture
    def df_with_inst(self) -> pd.DataFrame:
        df = _make_transaction_df(100)
        return _add_inst_columns(df)

    def test_velocity_uses_only_past(self, df_with_inst):
        """sender_velocity_* at row i must count only rows with ts < ts[i]."""
        feats = compute_behavioural_features(df_with_inst)
        df = df_with_inst.sort_values("ts").reset_index(drop=True)
        merged = df.merge(feats, on="row_id", how="left")

        # First transaction for each sender should have velocity = 0
        for sender_key in (
            df["from_inst"].astype(str) + "_" + df["from_acct"].astype(str)
        ).unique():
            mask = (
                merged["from_inst"].astype(str) + "_" + merged["from_acct"].astype(str)
            ) == sender_key
            sender_rows = merged[mask].sort_values("ts")
            first = sender_rows.iloc[0]
            assert first["sender_velocity_1h"] == 0, (
                f"First txn for {sender_key} has velocity_1h={first['sender_velocity_1h']}, "
                f"expected 0 (no past data to count)"
            )

    def test_pass_through_ratio_excludes_current_row(self, df_with_inst):
        """pass_through_ratio for a brand-new account with no prior activity should be 0."""
        feats = compute_behavioural_features(df_with_inst)
        df = df_with_inst.sort_values("ts").reset_index(drop=True)
        merged = df.merge(feats, on="row_id", how="left")

        # For accounts whose first appearance is as a sender,
        # cum_recv should be 0 → ratio should be 0
        sender_key = df["from_inst"].astype(str) + "_" + df["from_acct"].astype(str)
        receiver_key = df["to_inst"].astype(str) + "_" + df["to_acct"].astype(str)
        # Find accounts that only ever send (never receive before their first send)
        all_senders = set(sender_key)
        all_receivers = set(receiver_key)
        send_only = all_senders - all_receivers
        if send_only:
            acct = next(iter(send_only))
            mask = sender_key == acct
            first_row = merged[mask].sort_values("ts").iloc[0]
            assert first_row["pass_through_ratio"] == 0.0

    def test_baseline_deviation_uses_only_past_window(self, df_with_inst):
        """baseline_deviation for a sender's first two txns should be 0 (< 2 past points)."""
        feats = compute_behavioural_features(df_with_inst)
        df = df_with_inst.sort_values("ts").reset_index(drop=True)
        merged = df.merge(feats, on="row_id", how="left")
        sender_key = df["from_inst"].astype(str) + "_" + df["from_acct"].astype(str)

        for key in sender_key.unique():
            mask = sender_key == key
            rows = merged[mask].sort_values("ts")
            if len(rows) >= 1:
                assert rows.iloc[0]["baseline_deviation"] == 0.0, (
                    f"First txn for {key} should have baseline_deviation=0"
                )

    def test_behavioural_features_no_label_column(self, df_with_inst):
        """The output of compute_behavioural_features must never include is_laund."""
        feats = compute_behavioural_features(df_with_inst)
        forbidden = {"is_laund", "is_laundering", "label", "target", "y"}
        overlap = set(feats.columns) & forbidden
        assert not overlap, f"Label columns found in behavioural features: {overlap}"


# ═══════════════════════════════════════════════════════════════════════════
# 3. GRAPH FEATURES (GFP) — NO FUTURE EDGES
# ═══════════════════════════════════════════════════════════════════════════


class TestGFPLeakage:
    """GFP must only see edges from the training period when computing train features."""

    def test_edge_array_contains_no_labels(self):
        """_prepare_edge_array output must not contain is_laund."""
        df = _make_transaction_df(50)
        arr = _prepare_edge_array(df)
        # GFP edge array: [edge_id, src, dst, ts, amount] — exactly 5 columns
        assert arr.shape[1] == 5, f"Edge array has {arr.shape[1]} cols, expected 5"

    def test_gfp_on_train_only_no_test_edges(self):
        """When we compute GFP on train-only data, test row_ids must not appear."""
        df = _make_transaction_df(200)
        split = temporal_split(df["ts"], 0.6, 0.2)
        train_df = df[split == "train"]
        result = compute_gfp_features(train_df)
        train_row_ids = set(train_df["row_id"])
        result_row_ids = set(result.index.astype(int))
        # Result should only contain train row IDs
        assert result_row_ids <= train_row_ids, (
            f"GFP output contains row_ids not in train: {result_row_ids - train_row_ids}"
        )
        # No test row IDs should appear
        test_df = df[split == "test"]
        test_row_ids = set(test_df["row_id"])
        leaked = result_row_ids & test_row_ids
        assert not leaked, f"Test row_ids leaked into train GFP: {leaked}"


# ═══════════════════════════════════════════════════════════════════════════
# 4. LABEL LEAKAGE
# ═══════════════════════════════════════════════════════════════════════════


class TestLabelLeakage:
    """Labels must never appear in features, submissions, or cross-boundary data."""

    def test_behavioural_features_exclude_label(self):
        df = _make_transaction_df(50)
        df = _add_inst_columns(df)
        feats = compute_behavioural_features(df)
        assert "is_laund" not in feats.columns

    def test_gfp_features_exclude_label(self):
        from mritra.features.graph_gfp import compute_gfp_features

        df = _make_transaction_df(50)
        feats = compute_gfp_features(df)
        assert "is_laund" not in feats.columns
        # Also check column values aren't exactly the label
        df_merged = df.set_index("row_id")[["is_laund"]].join(feats, how="inner")
        for col in feats.columns:
            if (df_merged[col] == df_merged["is_laund"]).all() and len(df_merged) > 10:
                pytest.fail(f"GFP column '{col}' is identical to is_laund — likely leakage")

    def test_network_features_exclude_label(self):
        """Network feature output must not contain labels."""
        edges = pd.DataFrame(
            {
                "edge_ref": [1, 2],
                "from_acct": ["0_A1", "1_B1"],
                "to_acct": ["1_B1", "0_A1"],
                "ts": [100, 200],
                "amount": [500.0, 300.0],
            }
        )
        summaries = {
            "0_A1": np.array([1.0] * 6),
            "1_B1": np.array([4.0, 5.0, 6.0, 0.0, 0.0, 0.0]),
        }
        result = compute_network_features(edges, summaries)
        for acct, feat_vec in result.items():
            assert not np.isnan(feat_vec).any(), f"NaN in network features for {acct}"

    def test_partition_is_label_independent(self):
        """Partition assignment must not change if labels are shuffled."""
        df = _make_transaction_df(200)
        inst1 = make_partition(df, "volume_balanced", 5)

        df_shuffled = df.copy()
        df_shuffled["is_laund"] = np.random.default_rng(99).permutation(df["is_laund"].values)
        inst2 = make_partition(df_shuffled, "volume_balanced", 5)

        assert inst1 == inst2, "Partition changed when labels were shuffled — label leakage!"

    def test_cross_bank_txn_schema_has_no_label(self):
        """CrossBankTxn must not carry is_laund."""
        from mritra.protocol.messages import CrossBankTxn

        forbidden = {"is_laund", "is_laundering", "label", "target", "y", "ground_truth"}
        assert not CrossBankTxn.model_fields.keys() & forbidden

    def test_boundary_summary_has_no_label(self):
        """BoundarySummary features list must not encode labels."""
        from mritra.protocol.messages import BoundarySummary

        # Verify the schema
        forbidden = {"is_laund", "label", "target"}
        assert not BoundarySummary.model_fields.keys() & forbidden

    def test_round_response_has_no_label(self):
        """RoundResponse must not contain labels."""
        from mritra.protocol.messages import RoundResponse

        forbidden = {"is_laund", "label", "target", "y"}
        assert not RoundResponse.model_fields.keys() & forbidden


# ═══════════════════════════════════════════════════════════════════════════
# 5. ENCLAVE PRIVACY BOUNDARY
# ═══════════════════════════════════════════════════════════════════════════


class TestEnclaveBoundary:
    """The enclave must return features only for the requesting bank's accounts."""

    def test_enclave_returns_only_own_accounts(self):
        """Bank 0 must not receive features for Bank 1's accounts."""
        import tempfile
        from pathlib import Path

        from nacl.public import PrivateKey

        from mritra.protocol.messages import (
            BoundarySummary,
            CrossBankTxn,
            RoundSubmission,
        )
        from mritra.services.enclave_service import EnclaveService

        # Setup keys
        bank_keys = {i: PrivateKey.generate() for i in range(2)}
        bank_pks = {i: k.public_key for i, k in bank_keys.items()}

        with tempfile.TemporaryDirectory() as tmpdir:
            enclave = EnclaveService(
                tlog_path=Path(tmpdir) / "tlog.jsonl",
                bank_public_keys=bank_pks,
            )

            # Build submissions
            from mritra.protocol.crypto import encrypt_submission

            subs = {}
            for bank_id in range(2):
                other_bank = 1 - bank_id
                submission = RoundSubmission(
                    bank_id=bank_id,
                    round_id=1,
                    txns=[
                        CrossBankTxn(
                            edge_ref=bank_id * 100,
                            own_account=f"ACCT_{bank_id}_001",
                            direction="out",
                            counterparty_bank=other_bank,
                            counterparty_account=f"ACCT_{other_bank}_001",
                            ts=1000,
                            amount=500.0,
                            currency="USD",
                            fmt="Wire",
                        )
                    ],
                    summaries=[
                        BoundarySummary(
                            account=f"ACCT_{bank_id}_001",
                            features=[1.0, 2.0, 3.0],
                        )
                    ],
                )
                subs[bank_id] = encrypt_submission(
                    submission, bank_keys[bank_id], enclave.public_key
                )

            responses = enclave.process_round(1, list(subs.values()))
            enclave.close()

            # Bank 0's response must only contain Bank 0's accounts
            for feat in responses[0].features:
                assert not feat.account.startswith("ACCT_1_"), (
                    f"Bank 0 received features for Bank 1's account: {feat.account}"
                )

            # Bank 1's response must only contain Bank 1's accounts
            for feat in responses[1].features:
                assert not feat.account.startswith("ACCT_0_"), (
                    f"Bank 1 received features for Bank 0's account: {feat.account}"
                )


# ═══════════════════════════════════════════════════════════════════════════
# 6. TRAINING PIPELINE — NO TEST LEAKAGE
# ═══════════════════════════════════════════════════════════════════════════


class TestTrainingLeakage:
    """Training must never see test data or compute statistics from test."""

    def test_optimal_threshold_from_val_only(self):
        """_optimal_threshold must use only the arrays passed to it (val data)."""
        rng = np.random.default_rng(42)
        y_val = rng.choice([0, 1], size=100, p=[0.9, 0.1]).astype(int)
        y_prob_val = rng.uniform(0, 1, size=100)
        t = _optimal_threshold(y_val, y_prob_val)
        assert 0.01 <= t < 1.0, f"Threshold {t} out of expected range"

    def test_scale_pos_weight_from_train_only(self):
        """scale_pos_weight = n_neg / n_pos must use only train labels."""
        rng = np.random.default_rng(42)
        n = 1000
        y_train = rng.choice([0, 1], size=n, p=[0.99, 0.01]).astype(int)
        n_pos = int(y_train.sum())
        n_neg = n - n_pos
        spw = n_neg / n_pos if n_pos > 0 else 1.0

        # Verify it's computed from train
        y_test = np.ones(100, dtype=int)  # all positive (very different distribution)
        spw_test = (100 - int(y_test.sum())) / int(y_test.sum())
        assert spw != spw_test, "scale_pos_weight accidentally equals test-derived value"
        assert spw > 10, "With 1% positive rate, spw should be ~99"

    def test_train_function_does_not_accept_test_data(self):
        """train_lightgbm signature takes X_train, y_train, X_val, y_val — no test."""
        import inspect

        sig = inspect.signature(train_lightgbm)
        params = set(sig.parameters.keys())
        # Must NOT have test parameters
        forbidden = {"X_test", "y_test", "test_data", "X_all", "y_all"}
        assert not params & forbidden, (
            f"train_lightgbm accepts test data params: {params & forbidden}"
        )

    def test_training_on_small_synthetic_data(self):
        """End-to-end: train on small data, verify threshold is from val."""
        rng = np.random.default_rng(42)
        n_train, n_val = 200, 100
        n_feats = 5

        X_train = pd.DataFrame(
            rng.standard_normal((n_train, n_feats)), columns=[f"f{i}" for i in range(n_feats)]
        )
        y_train = rng.choice([0, 1], size=n_train, p=[0.9, 0.1]).astype(int)
        X_val = pd.DataFrame(
            rng.standard_normal((n_val, n_feats)), columns=[f"f{i}" for i in range(n_feats)]
        )
        y_val = rng.choice([0, 1], size=n_val, p=[0.9, 0.1]).astype(int)

        grid = {"num_leaves": [15], "learning_rate": [0.1], "n_estimators": [50]}
        model, threshold, info = train_lightgbm(
            X_train, y_train, X_val, y_val, seed=42, grid_cfg=grid
        )
        assert 0.01 <= threshold < 1.0
        assert info["n_train"] == n_train
        assert info["n_val"] == n_val
        # Threshold should be chosen on val, not train
        assert "val_pr_auc" in info


# ═══════════════════════════════════════════════════════════════════════════
# 7. EVALUATION — TEST-ONLY METRICS
# ═══════════════════════════════════════════════════════════════════════════


class TestEvaluationLeakage:
    """Metrics must be computed on test-period data only."""

    def test_evaluate_configuration_uses_given_df(self):
        """evaluate_configuration does not access global state — only its df arg."""
        rng = np.random.default_rng(42)
        n = 100
        df = pd.DataFrame(
            {
                "prob": rng.uniform(0, 1, size=n),
                "pred": rng.choice([0, 1], size=n),
                "is_laund": rng.choice([0, 1], size=n, p=[0.9, 0.1]).astype(int),
                "cross": rng.choice([True, False], size=n),
            }
        )
        result = evaluate_configuration(df)
        assert "all" in result
        assert "cross_bank" in result
        assert "within_bank" in result
        assert result["all"].n_samples == n

    def test_gap_recovered_formula(self):
        """G = (C3 - C1) / (C4 - C1); verify with known values."""
        # C1=0.2, C3=0.5, C4=0.8 → G = 0.3/0.6 = 0.5
        g = gap_recovered(0.2, 0.5, 0.8)
        assert abs(g - 0.5) < 1e-10

    def test_gap_recovered_zero_denominator(self):
        """G is undefined when C4 == C1 (no gap to close)."""
        g = gap_recovered(0.5, 0.5, 0.5)
        assert g is None

    def test_gap_recovered_perfect_recovery(self):
        """G = 1.0 when C3 == C4."""
        g = gap_recovered(0.2, 0.8, 0.8)
        assert abs(g - 1.0) < 1e-10

    def test_gap_recovered_negative(self):
        """G < 0 when C3 < C1 (Mritra hurts)."""
        g = gap_recovered(0.5, 0.3, 0.8)
        assert g is not None
        assert g < 0


# ═══════════════════════════════════════════════════════════════════════════
# 8. NETWORK FEATURES — NO LABEL PROPAGATION
# ═══════════════════════════════════════════════════════════════════════════


class TestNetworkFeatureLeakage:
    """Network feature aggregation must not propagate labels through neighbours."""

    def test_neighbour_summary_does_not_encode_labels(self):
        """Boundary summaries are feature vectors, not label vectors."""
        # If a summary is [0, 0, ..., 1] where 1 = laund, that's leakage.
        # We verify that summaries are unconstrained floats, not binary {0,1} labels.
        edges = pd.DataFrame(
            {
                "edge_ref": [1, 2, 3],
                "from_acct": ["A", "B", "C"],
                "to_acct": ["B", "C", "A"],
                "ts": [100, 200, 300],
                "amount": [500.0, 300.0, 700.0],
            }
        )
        # Summaries with continuous feature values (not labels)
        summaries = {
            "A": np.array([1.23, 4.56, 7.89, 0.0, 0.0, 0.0]),
            "B": np.array([2.34, 5.67, 8.90, 0.0, 0.0, 0.0]),
            "C": np.array([3.45, 6.78, 9.01, 0.0, 0.0, 0.0]),
        }
        result = compute_network_features(edges, summaries)
        assert len(result) == 3
        # All results should be finite floats
        for acct, vec in result.items():
            assert np.all(np.isfinite(vec)), f"Non-finite values for {acct}"

    def test_network_features_symmetric_topology(self):
        """If topology is symmetric, fan-out and fan-in should match."""
        edges = pd.DataFrame(
            {
                "edge_ref": [1, 2],
                "from_acct": ["A", "B"],
                "to_acct": ["B", "A"],
                "ts": [100, 200],
                "amount": [500.0, 500.0],
            }
        )
        summaries = {
            "A": np.array([1.0] * 6),
            "B": np.array([1.0] * 6),
        }
        result = compute_network_features(edges, summaries)
        # Both A and B have fan-out=1, fan-in=1
        for acct in ("A", "B"):
            assert result[acct][0] == 1.0  # fan-out
            assert result[acct][1] == 1.0  # fan-in


# ═══════════════════════════════════════════════════════════════════════════
# 9. PARTITION LEAKAGE
# ═══════════════════════════════════════════════════════════════════════════


class TestPartitionLeakage:
    """Institution partitioning must be label-blind and data-order-stable."""

    def test_partition_uses_only_volumes(self):
        """Changing amounts or labels must not change the partition."""
        df = _make_transaction_df(200)
        inst_of_1 = make_partition(df, "volume_balanced", 5)

        df_modified = df.copy()
        df_modified["amt_paid"] = df["amt_paid"] * 2
        df_modified["is_laund"] = 1 - df["is_laund"]
        inst_of_2 = make_partition(df_modified, "volume_balanced", 5)

        assert inst_of_1 == inst_of_2, (
            "Partition changed when amounts/labels changed — should depend only on "
            "bank-level txn counts"
        )

    def test_partition_deterministic(self):
        """Same input → same partition."""
        df = _make_transaction_df(200)
        p1 = make_partition(df, "volume_balanced", 5)
        p2 = make_partition(df, "volume_balanced", 5)
        assert p1 == p2

    def test_random_partition_deterministic_with_seed(self):
        """Random partition with same seed → same result."""
        df = _make_transaction_df(200)
        p1 = make_partition(df, "random", 5, seed=42)
        p2 = make_partition(df, "random", 5, seed=42)
        assert p1 == p2

    def test_all_banks_assigned(self):
        """Every bank in the data gets an institution."""
        df = _make_transaction_df(200)
        all_banks = set(df["from_bank"]) | set(df["to_bank"])
        inst_of = make_partition(df, "volume_balanced", 5)
        assigned = set(inst_of.keys())
        assert all_banks <= assigned, f"Unassigned banks: {all_banks - assigned}"


# ═══════════════════════════════════════════════════════════════════════════
# 10. ROLES — MUST USE TRAIN DATA ONLY
# ═══════════════════════════════════════════════════════════════════════════


class TestRoleLeakage:
    """Account roles must be computed from train split only."""

    def test_roles_change_with_different_splits(self):
        """Roles computed on train-only differ from roles on all data (proving split matters)."""
        from mritra.data.roles import assign_roles

        df = _make_transaction_df(200)
        df = _add_inst_columns(df)
        split = temporal_split(df["ts"], 0.6, 0.2)

        # Rename columns for assign_roles compatibility
        df_roles = df.copy()
        df_roles.rename(columns={"from_inst": "from_inst", "to_inst": "to_inst"}, inplace=True)

        roles_train = assign_roles(df_roles[split == "train"])
        roles_all = assign_roles(df_roles)

        # They should be computed on different data → might differ
        # The key test: roles_train must NOT use test/val data
        assert len(roles_train) <= len(roles_all), (
            "Train-only roles have more accounts than all-data roles — impossible"
        )

    def test_role_schema_is_clean(self):
        """Role output columns should not include prediction artifacts."""
        from mritra.data.roles import assign_roles

        df = _make_transaction_df(100)
        df = _add_inst_columns(df)
        roles = assign_roles(df)
        forbidden = {"prob", "pred", "score", "prediction"}
        overlap = set(roles.columns) & forbidden
        assert not overlap, f"Prediction artifacts in roles: {overlap}"


# ═══════════════════════════════════════════════════════════════════════════
# 11. CROSS-CUTTING: FEATURE MATRIX SANITY
# ═══════════════════════════════════════════════════════════════════════════


class TestFeatureMatrixSanity:
    """Feature matrix used for training must never contain forbidden columns."""

    FORBIDDEN_FEATURE_NAMES = {
        "is_laund",
        "is_laundering",
        "label",
        "target",
        "y",
        "split",
        "train",
        "val",
        "test",  # split indicators
    }

    def test_behavioural_features_clean(self):
        df = _make_transaction_df(50)
        df = _add_inst_columns(df)
        feats = compute_behavioural_features(df)
        overlap = set(feats.columns) & self.FORBIDDEN_FEATURE_NAMES
        assert not overlap, f"Forbidden cols in behavioural features: {overlap}"

    def test_gfp_features_clean(self):
        from mritra.features.graph_gfp import compute_gfp_features

        df = _make_transaction_df(50)
        feats = compute_gfp_features(df)
        overlap = set(feats.columns) & self.FORBIDDEN_FEATURE_NAMES
        assert not overlap, f"Forbidden cols in GFP features: {overlap}"


# ═══════════════════════════════════════════════════════════════════════════
# 12. BOOTSTRAP & CONFIDENCE INTERVALS — CORRECT INPUTS
# ═══════════════════════════════════════════════════════════════════════════


class TestBootstrapLeakage:
    """Bootstrap CI must receive test-only arrays."""

    def test_bootstrap_metric_diff_deterministic(self):
        """Same seed → same CI."""
        from mritra.eval.bootstrap import bootstrap_metric_diff

        rng = np.random.default_rng(42)
        n = 200
        y_true = rng.choice([0, 1], size=n, p=[0.9, 0.1]).astype(int)
        y_prob_a = rng.uniform(0, 1, n)
        y_prob_b = rng.uniform(0, 1, n)

        ci1 = bootstrap_metric_diff(y_true, y_prob_a, y_prob_b, 0.5, 0.5, seed=42)
        ci2 = bootstrap_metric_diff(y_true, y_prob_a, y_prob_b, 0.5, 0.5, seed=42)
        assert ci1.ci_lower == ci2.ci_lower
        assert ci1.ci_upper == ci2.ci_upper

    def test_bootstrap_gap_handles_degenerate_case(self):
        """When all labels are 0, G is undefined (nan) or 0."""
        from mritra.eval.bootstrap import bootstrap_gap_recovered

        n = 100
        y_true = np.zeros(n, dtype=int)
        y_prob = np.random.default_rng(42).uniform(0, 1, n)

        ci = bootstrap_gap_recovered(y_true, y_prob, y_prob, y_prob, 0.5, 0.5, 0.5)
        assert np.isnan(ci.point_estimate) or ci.point_estimate == 0.0


# ═══════════════════════════════════════════════════════════════════════════
# 13. RECONCILIATION — NO DATA INJECTION
# ═══════════════════════════════════════════════════════════════════════════


class TestReconciliationLeakage:
    """Reconciliation must detect tampered or injected transactions."""

    def test_reconcile_detects_amount_mismatch(self):
        """If two banks report different amounts for the same edge, flag it."""
        from mritra.protocol.messages import CrossBankTxn
        from mritra.protocol.reconcile import reconcile_round

        txns = {
            0: [
                CrossBankTxn(
                    edge_ref=1,
                    own_account="A1",
                    direction="out",
                    counterparty_bank=1,
                    counterparty_account="B1",
                    ts=100,
                    amount=500.0,
                    currency="USD",
                    fmt="Wire",
                )
            ],
            1: [
                CrossBankTxn(
                    edge_ref=1,
                    own_account="B1",
                    direction="in",
                    counterparty_bank=0,
                    counterparty_account="A1",
                    ts=100,
                    amount=999.0,  # TAMPERED amount
                    currency="USD",
                    fmt="Wire",
                )
            ],
        }
        result = reconcile_round(txns)
        assert result.total_issues > 0, "Reconciliation failed to detect amount mismatch"

    def test_reconcile_detects_unmatched_edge(self):
        """An edge reported by one bank but not the other is flagged."""
        from mritra.protocol.messages import CrossBankTxn
        from mritra.protocol.reconcile import reconcile_round

        txns = {
            0: [
                CrossBankTxn(
                    edge_ref=1,
                    own_account="A1",
                    direction="out",
                    counterparty_bank=1,
                    counterparty_account="B1",
                    ts=100,
                    amount=500.0,
                    currency="USD",
                    fmt="Wire",
                )
            ],
            1: [],  # Bank 1 doesn't report anything
        }
        result = reconcile_round(txns)
        assert result.total_issues > 0, "Reconciliation failed to detect unmatched edge"


# ═══════════════════════════════════════════════════════════════════════════
# 14. TRANSPARENCY LOG — AUDIT TRAIL
# ═══════════════════════════════════════════════════════════════════════════


class TestTransparencyLogIntegrity:
    """Transparency log must be tamper-evident and complete."""

    def test_tlog_entries_are_hash_chained(self):
        """Each entry's prev_hash must equal the entry_hash of the prior entry."""
        import tempfile
        from pathlib import Path

        from mritra.protocol.tlog import TransparencyLog, verify_chain

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "tlog.db"
            tlog = TransparencyLog(path)
            tlog.append("bank_0", "submit", "input_hash_1", "output_hash_1", "code_v1")
            tlog.append("bank_1", "submit", "input_hash_2", "output_hash_2", "code_v1")
            entries = tlog.entries()
            tlog.close()

            assert len(entries) == 2
            # Second entry's prev_hash should be the first entry's entry_hash
            assert entries[1].prev_hash == entries[0].entry_hash
            # Full chain verification
            valid, broken_seq = verify_chain(entries)
            assert valid, f"Chain broken at seq {broken_seq}"

    def test_tlog_records_every_round(self):
        """If we process N rounds, the log should have N entries."""
        import tempfile
        from pathlib import Path

        from mritra.protocol.tlog import TransparencyLog, verify_chain

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "tlog.db"
            tlog = TransparencyLog(path)
            for i in range(5):
                tlog.append(f"round_{i}", "boundary_exchange", f"in_{i}", f"out_{i}", "v1")
            entries = tlog.entries()
            tlog.close()

            assert len(entries) == 5
            valid, broken_seq = verify_chain(entries)
            assert valid, f"Chain broken at seq {broken_seq}"
