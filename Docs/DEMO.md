# DEMO.md — live demo runbook

> **Status:** v0.1 · 1 Oct 2026 · Owner: role E · Rehearse twice before submission
> Goal: the judges leave remembering one sentence and one chart.

**The sentence:** "Each bank alone misses the chain; one all-seeing model is illegal; Mritra recovers most of that gap without anyone sharing data."

## 1. Before the demo (T − 30 min)

- [ ] LinuxONE VM reachable; `make demo` services healthy (`/v1/health` on enclave and all 5 banks)
- [ ] Enclave `/v1/enclave/info` shows the correct attestation type; banner matches (real/simulated)
- [ ] Transparency log verified: `python scripts/verify_log.py` → OK
- [ ] Dashboard open on the projector, browser zoom 125%, notifications off
- [ ] Demo chain preloaded (IDs in §3); replay cursor set to the round before it
- [ ] Backup video open in a second tab, muted, at 0:00
- [ ] Results figures from `results/figures/` open in a third tab
- [ ] Laptop on power; phone hotspot ready if venue Wi-Fi fails

## 2. Script (5 minutes)

| Time | Screen | Say (key lines) | Do |
|---|---|---|---|
| 0:00–0:40 | Title slide | "A ₹547 crore network in Telangana moved victims' money through a web of mule accounts across banks, into USDT, to Cambodia. Half of mule money leaves within an hour. India refunds about 2% of what it freezes." | — |
| 0:40–1:30 | Dashboard · Bank view (toggle **Siloed**) | "Five banks, each seeing only its own accounts. Here's a scatter-gather chain crossing three banks — every bank rates it low risk." | Select Bank B1, show chain accounts ranked low |
| 1:30–2:30 | Toggle **Mritra** → Case view | "Each bank sends only encrypted cross-bank transfers and account summaries to the enclave on LinuxONE. Nothing internal leaves. The same chain now lights up — role, path and evidence, and only this bank's accounts." | Run round; open the case; point at "Data exposed" |
| 2:30–3:30 | Results page | "On the full test period: isolated banks score X, the illegal all-seeing model Y, Mritra Z — that's G = __ of the gap, with this interval, under two ways of splitting the banks." | Show chart; name the interval |
| 3:30–4:20 | Operator page | "You don't have to trust us. Every computation is in a hash chain. And if a bank lies —" | Click Verify → OK. Show reconciliation catching injected Bank B4 |
| 4:20–5:00 | Roadmap slide | "It complements RBI's DPIP and MuleHunter, and it outputs the amount per account that courts now require for liens. Runs on IBM Z today." | — |

## 3. The demo chain

Pick before the event from the **test period**: a cross-bank pattern (ideally scatter-gather or fan-in → fan-out) that C1 misses and C3 catches, spanning ≥ 3 institutions, ending in an exit transaction.

| Field | Value |
|---|---|
| Pattern ID / type | TBD |
| Institutions spanned | TBD |
| Accounts (per bank) | TBD |
| Round IDs involved | TBD |
| C1 max score / C3 max score / threshold | TBD |
| Exit transaction time; C3 first flag time | TBD |

Also choose a **backup chain** with the same properties in case the first misbehaves.

## 4. Failure playbook

| Failure | Recovery (≤ 20 s) |
|---|---|
| LinuxONE VM unreachable | Switch to laptop `make demo` (same containers); say "same code, running locally; LinuxONE logs are in the repo" |
| A bank service down | Round runs with remaining banks (`banks_included` shows it); say so and continue |
| Dashboard crashes | Switch to backup video at the matching timestamp |
| Round takes too long | Use the precomputed round (`replay_stream.py --precomputed`) |
| Question you can't answer | "Good question — here's what we measured; that part is future work" (see `JUDGE_QA.md`) |

## 5. Backup video

- 3 minutes, recorded with OBS at 1080p after Gate 3 (hour 19).
- Same script, voice-over, captions for key numbers.
- Stored in the repo release assets and on two laptops.

## 6. Rehearsal log

| # | Date/hour | Duration | What went wrong | Fixed? |
|---|---|---|---|---|
| 1 | | | | |
| 2 | | | | |
