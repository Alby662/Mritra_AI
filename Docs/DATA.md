# DATA.md — dataset card

> **Status:** Template v0.1 · 1 Oct 2026 · Owner: role B (data)
> Fill every `TBD` from `make data` and `make h1` output. Numbers here must be copied from generated files in `results/`, never typed from memory.

## 1. Source

| Field | Value |
|---|---|
| Name | IBM Transactions for Anti-Money Laundering (AMLworld) |
| Location | Kaggle `ealtman2019/ibm-transactions-for-anti-money-laundering-aml` |
| Paper | Altman et al., *Realistic Synthetic Financial Transactions for Anti-Money Laundering Models*, NeurIPS 2023 Datasets & Benchmarks — https://arxiv.org/html/2306.16424v1 |
| Nature | Fully synthetic, agent-based simulation of a multi-bank financial world; complete laundering ground truth |
| Licence | TBD (copy from the Kaggle page; check redistribution terms before putting data in any public repo) |
| Downloaded on | TBD · by TBD · SHA-256 of each file recorded in `data/raw/CHECKSUMS` |

**Why this dataset:** it is the only public AML dataset that records the bank on **both ends** of every transaction, which is what makes a bank-partitioned (cross-institution) experiment possible.

## 2. Files used

| File | Content | Used for |
|---|---|---|
| `HI-Small_Trans.csv` | One row per transaction | Everything |
| `HI-Small_Patterns.txt` | Laundering attempts grouped by typology | Pattern-level metrics, cross-bank pattern share, lead time |
| `HI-Small_accounts.csv` | Account → bank / entity info | Sanity checks |
| `LI-Small_*` | Lower illicit ratio variant | Optional replication only |

## 3. Schema (verify on load and correct this table)

| Column (raw) | Renamed | Type | Notes |
|---|---|---|---|
| Timestamp | `ts` | int (unix s) | Parse to UTC; stable sort |
| From Bank | `from_bank` | category | Dataset bank ID |
| Account | `from_acct` | category | Unique within bank |
| To Bank | `to_bank` | category | |
| Account (2nd) | `to_acct` | category | pandas reads as `Account.1` |
| Amount Received | `amt_recv` | float32 | In receiving currency |
| Receiving Currency | `cur_recv` | category | |
| Amount Paid | `amt_paid` | float32 | In payment currency |
| Payment Currency | `cur_paid` | category | |
| Payment Format | `fmt` | category | Exact values listed in §5 |
| Is Laundering | `is_laund` | int8 | 1 = laundering; **label, never a feature** |

## 4. Summary statistics (from `results/h1.json` / `results/data_stats.json`)

| Statistic | HI-Small | Source file |
|---|---|---|
| Transactions (raw / after de-dup) | TBD / TBD | data_stats.json |
| Distinct banks | TBD | data_stats.json |
| Distinct accounts | TBD | data_stats.json |
| Laundering transactions (count, %) | TBD | data_stats.json |
| Laundering attempts in Patterns file | TBD | h1.json |
| Time span (first → last) | TBD | data_stats.json |
| Train / val / test rows and time ranges | TBD | data_stats.json |
| Laundering rate per split | TBD | data_stats.json |

## 5. Categorical values

| Field | Values (copy exactly) |
|---|---|
| Payment Format | TBD |
| **Exit formats** (per PREREGISTRATION §4) | TBD — the cash and bitcoin categories as spelled above |
| Currencies | TBD |

## 6. Currency conversion to USD

Amounts span several currencies. We convert to USD with a **fixed rate table built once, before experiments**:

1. From transactions where `cur_paid ≠ cur_recv`, compute the implied rate `amt_recv / amt_paid` per currency pair.
2. Take the median per pair; derive each currency's rate to USD.
3. Save to `data/fx_rates.json`; record the table below.

| Currency | USD per unit | Pairs used |
|---|---|---|
| TBD | TBD | TBD |

## 7. Partitions and H1 results

| Metric | P1 (volume-balanced) | P2 (random, seed 42) |
|---|---|---|
| Transactions per institution (min / max) | TBD | TBD |
| Cross-bank share, all transactions | TBD | TBD |
| Cross-bank share, laundering transactions | TBD | TBD |
| **Cross-bank share, laundering patterns** | TBD | TBD |
| Cross-bank pattern share by typology (fan-in, fan-out, cycle, scatter-gather, gather-scatter, stack, bipartite, random) | TBD | TBD |

**H1 gate:** pattern share ≥ ~15% under P1 → proceed. Otherwise see PREREGISTRATION §7.

## 8. Derived labels (proxies)

| Label | Definition | Count | Caveat |
|---|---|---|---|
| Mule | Receives and sends laundering | TBD | Proxy; real mules include unwitting account holders |
| Source | Sends laundering, receives none | TBD | In synthetic data, often the laundering origin, not a fraud victim |
| Innocent-looking recipient | Receives laundering, sends none, laundering < 10% of inflow | TBD | Proxy for downstream innocents; may include integration endpoints |

## 9. Known limitations

- **Synthetic:** behaviour, amounts and timing come from a simulator, not Indian banks or UPI.
- **Not India-specific:** no UPI, IMPS or NEFT semantics; payment formats are generic.
- **Pattern coverage:** not every laundering transaction belongs to a Patterns-file attempt (funds are also tracked through co-mingling); pattern-level metrics cover only listed attempts.
- **Bank partition is artificial:** real institutions differ in size, customer mix and geography; we test two partitions to check robustness.
- **Proxy roles** are defined from labels and flows, not ground-truth intent.
- **Transfer:** results may not hold on other simulators (AMLGentex, SAML-D) — tested post-datathon.

## 10. Data handling

- Raw and Parquet data are gitignored; never commit data.
- Check the licence before sharing processed data or a demo that embeds data.
- Keep a copy of the exact Kaggle files with checksums so results are reproducible.
