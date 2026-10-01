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
