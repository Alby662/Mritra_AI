# DECISIONS.md — decision log

One line per decision, newest at the bottom. Format: `YYYY-MM-DD · area · decision — reason (who)`. Never delete entries; supersede them with a new line that references the old one.

## Seeded from planning (30 Sep – 1 Oct 2026)

- 2026-09-30 · scope · Enter IBM Z Datathon 2026, track "AI Secured: Innovation Without Exposure" — direct fit for privacy-preserving collaborative detection (Rehan)
- 2026-09-30 · thesis · Federated learning alone is not the contribution: it shares model weights, not the missing cross-bank edges; cross-bank computation must happen at scoring time (Rehan)
- 2026-09-30 · architecture · Enclave does the cross-bank join (boundary exchange), not just model aggregation — gives the TEE a necessary role (Rehan)
- 2026-09-30 · positioning · Build on IBM's own work (AMLworld, Graph Feature Preprocessor, Multi-GNN) as baselines, not competitors (Rehan)
- 2026-10-01 · problem · Problem statement v2: name the dominant real case (mule networks moving fraud proceeds); outputs are accounts + role + path + amount; add lead time and innocent-customer protection; restitution, crypto analytics, cash/hawala out of scope (Rehan)
- 2026-10-01 · features · Account age is not a core signal (~60% of real mule accounts are >1 year old, RUSI); use behaviour change against the account's own baseline instead (Rehan)
- 2026-10-01 · latency · Half of mule money leaves within an hour → keep a fast local scoring path; enclave rounds are one simulated hour in the datathon (Rehan)
- 2026-10-01 · threat model · Bank staff/insiders included as adversaries (CBI Chakra-V, TD Bank evidence) (Rehan)
- 2026-10-01 · evaluation · Report coverage alongside accuracy metrics (TD Bank: 92% unmonitored) (Rehan)
- 2026-10-01 · evaluation · Single-bank bar is high (OCBC 89% yield); claim is incremental over a strong single-bank model, not over rules (Rehan)
- 2026-10-01 · naming · "Group-aware" is a published method (IEEE TKDE 2023) — cite, don't claim (Rehan)
- 2026-10-01 · data · AMLworld HI-Small primary; LI-Small optional replication only (Rehan)
- 2026-10-01 · partition · K = 5 institutions; P1 volume-balanced primary, P2 random robustness (Rehan)
- 2026-10-01 · split · Temporal 60/20/20, same convention as IBM Multi-GNN (Rehan)
- 2026-10-01 · model · LightGBM for all configurations; configurations differ only in features (Rehan)
- 2026-10-01 · crypto · Use NaCl `Box` (authenticated) instead of `SealedBox` (anonymous) so the enclave knows which bank sent a submission (PROTOCOL v0.1)
- 2026-10-01 · protocol · `edge_ref` = dataset row id, simulating the shared payment reference (UTR) both banks hold; basis for double-entry reconciliation (PROTOCOL v0.1)
- 2026-10-01 · honesty · If Secure Execution is unavailable, run a labelled simulated enclave; never claim attestation we do not have (Rehan)
- 2026-10-01 · naming · Working name "Mritra"; check how it reads in Hindi/Marathi (*mṛt* = dead) before public use — OPEN

## Log

<!-- add new decisions below this line -->
- 2026-10-01 · tooling · uv + pyproject.toml (lockfile `uv.lock`) instead of requirements.txt; deps added per module as it is built, not all up front (Claude, for Rehan)
- 2026-10-01 · data · Amounts stored as float64, not float32 — float32 loses cents above ~$170k, which breaks exact-amount reconciliation (Claude, for Rehan)
- 2026-10-01 · data · `row_id` = 0-based row position in the raw CSV, assigned before de-dup; it is the transaction identity and the protocol `edge_ref` (Claude, for Rehan)
- 2026-10-01 · partition · P2 draws `rng.integers(0, K)` over bank IDs sorted ascending, so the result is independent of load order (Claude, for Rehan)
- 2026-10-01 · split · Cut points are cumulative (floor(n·0.6), floor(n·0.8)); a split can shrink if a tied-timestamp run crosses its whole width (Claude, for Rehan)
- 2026-10-01 · data · Download only the three HI-Small files via Kaggle API, not the full dataset archive (Claude, for Rehan)
- 2026-10-01 · tooling · ruff excludes `Docs/` (ruff 0.16 reformats Python blocks inside Markdown) (Claude, for Rehan)
- 2026-10-01 · partition · P2 draw order formalised into PREREGISTRATION.md §4 itself (supersedes the DECISIONS-only entry above); implementation unchanged (Claude, for Rehan)
- 2026-10-01 · data · Removed the duplicate-row drop from load.py; it now only counts and logs exact duplicates. PREREGISTRATION.md §3 still says "drop exact duplicate rows" — unreconciled contradiction, flagged to Rehan, pending the real-data counts (Claude, for Rehan)
- 2026-10-01 · data · Supersedes the entry above: duplicate dropping is now `configs/experiment.yaml: data.drop_exact_duplicates`, default `true` (matches PREREGISTRATION.md §3). DuplicateStats is always computed before the flag is applied, so the counts are identical either way; `drop_exact_duplicates` is recorded in `data_stats.json` on every run (Rehan's correction — his "don't drop unless prereg says so" instruction was backwards, prereg already says to drop)
