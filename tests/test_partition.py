from __future__ import annotations

import pandas as pd

from mritra.data.partition import (
    add_institutions,
    bank_volumes,
    partition_random,
    partition_volume_balanced,
)

ARBITRARY_BANKS = [17, 3, 290, 8, 1001, 42, 56, 7, 123, 99, 2, 500]


def test_volume_balanced_hand_computed() -> None:
    # volumes: 1->10, 2->7, 3->7, 4->3, 5->2 ; k=2
    # order (desc, ties by id): 1(10), 2(7), 3(7), 4(3), 5(2)
    # 1->0 [10,0]; 2->1 [10,7]; 3->1 [10,14]; 4->0 [13,14]; 5->0 [15,14]
    vols = pd.Series({3: 7, 1: 10, 5: 2, 2: 7, 4: 3})
    assert partition_volume_balanced(vols, 2) == {1: 0, 2: 1, 3: 1, 4: 0, 5: 0}


def test_volume_balanced_ties_go_to_lowest_institution() -> None:
    vols = pd.Series({1: 5, 2: 5, 3: 5})
    assert partition_volume_balanced(vols, 3) == {1: 0, 2: 1, 3: 2}


def test_random_partition_is_deterministic_and_order_independent() -> None:
    a = partition_random([30, 10, 20], k=5, seed=42)
    b = partition_random([10, 20, 30], k=5, seed=42)
    assert a == b
    assert set(a.values()) <= set(range(5))


def test_volume_balanced_covers_every_bank_exactly_once() -> None:
    vols = pd.Series({b: (i + 1) * 7 for i, b in enumerate(ARBITRARY_BANKS)})
    mapping = partition_volume_balanced(vols, k=5)
    assert sorted(mapping) == sorted(ARBITRARY_BANKS)
    assert set(mapping.values()) <= set(range(5))
    assert len(mapping) == len(ARBITRARY_BANKS)


def test_volume_balanced_is_deterministic_across_runs() -> None:
    vols = pd.Series({b: (i + 1) * 7 for i, b in enumerate(ARBITRARY_BANKS)})
    first = partition_volume_balanced(vols, k=5)
    for _ in range(5):
        assert partition_volume_balanced(vols, k=5) == first


def test_random_partition_covers_every_bank_exactly_once() -> None:
    mapping = partition_random(ARBITRARY_BANKS, k=5, seed=42)
    assert sorted(mapping) == sorted(ARBITRARY_BANKS)
    assert set(mapping.values()) <= set(range(5))
    assert len(mapping) == len(ARBITRARY_BANKS)


def test_bank_volumes_counts_both_ends() -> None:
    df = pd.DataFrame({"from_bank": [1, 1, 2], "to_bank": [2, 1, 3]})
    assert bank_volumes(df).to_dict() == {1: 3, 2: 2, 3: 1}


def test_add_institutions_marks_cross() -> None:
    df = pd.DataFrame({"from_bank": [1, 1, 2], "to_bank": [1, 2, 2]})
    out = add_institutions(df, {1: 0, 2: 1})
    assert out["cross"].tolist() == [False, True, False]


def test_add_institutions_no_nan_when_bank_only_receives() -> None:
    # bank 2 never appears as from_bank, only as to_bank
    df = pd.DataFrame({"from_bank": [1, 1], "to_bank": [2, 2]})
    out = add_institutions(df, {1: 0, 2: 1})
    assert out["from_inst"].isna().sum() == 0
    assert out["to_inst"].isna().sum() == 0
    assert out["to_inst"].tolist() == [1, 1]
    assert out["cross"].tolist() == [True, True]


def test_every_institution_non_empty_P1(k: int = 5) -> None:
    vols = pd.Series({b: (i + 1) * 7 for i, b in enumerate(ARBITRARY_BANKS)})
    mapping = partition_volume_balanced(vols, k)
    assert set(mapping.values()) == set(range(k))  # every institution gets >= 1 bank


def test_every_institution_non_empty_P2(k: int = 5) -> None:
    mapping = partition_random(ARBITRARY_BANKS, k, seed=42)
    assert set(mapping.values()) == set(range(k))  # every institution gets >= 1 bank


def test_P1_load_ratio_is_reported() -> None:
    """Max/min institution load ratio for P1 on the test fixture — reported, not asserted
    against a target: PREREGISTRATION.md does not set a balance requirement."""
    vols = pd.Series({b: (i + 1) * 7 for i, b in enumerate(ARBITRARY_BANKS)})
    mapping = partition_volume_balanced(vols, k=5)
    loads = vols.groupby(vols.index.map(mapping)).sum()
    ratio = loads.max() / loads.min()
    print(f"\nP1 institution loads: {loads.to_dict()}  max/min ratio: {ratio:.3f}")
    assert ratio >= 1.0  # trivially true; the number itself is the point, not a bound
