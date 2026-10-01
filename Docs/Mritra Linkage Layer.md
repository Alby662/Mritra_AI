Mritra · architecture draft · Oct 2026

# Mritra Linkage Layer

Cross-bank AML detection only works if every bank's record of the same business resolves to one node. This layer does that without raw customer names leaving any bank, and reuses most of the Amazon ML Challenge entity-resolution pipeline to do it.

## Why the graph needs it

A layering cycle that moves money A → B → C → A across three banks looks like three unrelated one-way transfers unless the system knows the endpoints are the same entities. Banks share no common customer ID, and most business names differ across systems through abbreviations, legal suffixes, transliteration and typos. Federated AML papers usually assume a shared ID and move on. Mritra's claim is that it resolves the entities first, under privacy constraints, and then runs detection on the resolved graph.

Dashed outlines are trust boundaries. Everything inside a bank's line runs on that bank's hardware; only the enclave sees encodings from more than one bank.

## What runs where

| Component | Runs at | From the AMLC pipeline | Status |
| --- | --- | --- | --- |
| `canon.py` | Each bank | Operator-inverting canonicalizer, Unicode-safe for Indic scripts | retrain dictionaries |
| `record_keys` | Each bank | N / A / G / D / X key families | reuse |
| Encode | Each bank | New: HMAC each key with a shared secret; Bloom-encode name and address n-grams | new |
| Block | Enclave | Streaming Pass A/B, DF-capped sparse matmul, proven at 10M records in 14 GB | reuse |
| Score | Enclave | LightGBM + isotonic; feature set depends on the protection mode below | adapt features |
| Cluster | Enclave | Replaces numpy exclusivity; one entity can hold accounts at every bank | redesign |
| Graph detection | Enclave or federated | None; this is the rest of Mritra | separate |

## Two ways to protect the records

Both keep raw data inside each bank's boundary in transit. They differ in what the linkage step can see and who you have to trust.

Mode A · cryptographic encoding

### Privacy-preserving record linkage

Banks send keyed-hash tokens and Bloom-filter encodings. The linkage node matches on token overlap and Bloom Dice similarity and never sees a name.

Trust

The math, plus the secrecy of the shared key

Accuracy

Lower. Features that need raw text, such as edit distance and token order, become Bloom approximations

Risk

Published frequency attacks can re-identify common names from Bloom filters. Salting, record-level encoding and balancing reduce that risk but do not remove it

Mode B · trusted execution · build this first

### Canonical records into a secure enclave

Banks encrypt canonical records to an attested LinuxONE Secure Execution guest. The existing pipeline runs inside it unchanged, with all 31 features.

Trust

IBM Z hardware attestation; the host operator cannot read guest memory

Accuracy

Same as the competition pipeline

Fit

It maps directly onto the Z Datathon stack, and nothing in the ER code has to change to run it

Build Mode B for the datathon. Treat Mode A as the research extension, and measure how much F-score is lost moving from B to A. That number is a result in itself.

## What has to change from the competition pipeline

Exclusivitydecide.py

The competition guaranteed each S2/S3 record was a copy of exactly one S1 record, so one-to-one assignment was correct. Across banks, one business can have accounts at every bank and duplicates within a bank. Replace exclusivity with clustering over scored pairs, such as thresholded connected components with a split check on oversized clusters.

Hard mergesthreshold → edges

Keep the calibrated match probability and write it into the graph as a weighted identity edge instead of merging nodes. Detection can then ask how confident a cross-bank cycle is, and an investigator can see which link it depends on.

MetricF0.5 → cost-weighted

F0.5 weighted precision because the competition said so. In AML a missed link hides a laundering path, and a false merge creates a false alert that a human reviews. Pick the operating point from those two costs, which likely favours recall more than F0.5 does.

Canonicalizerfitted to a generator

The canonicalizer undoes one synthetic generator's corruptions. Re-mine the dictionaries and retrain on real names; GLEIF's public LEI records are a candidate, since they carry real legal names and addresses across many countries. Check whether their alternate and transliterated name fields give usable labeled pairs.

Adversariesbenign noise → deliberate

Generator noise was accidental. Launderers choose names on purpose: shell companies that look almost alike, and related entities that look unrelated. Add an adversarial test set and report on it separately.

## Build order

1. ### Retrain ER on real names

   Re-mine the dictionaries and refit LightGBM on public registry data. Report F-score on real noise, not the competition number.
2. ### Simulate three banks

   The IBM AML transaction dataset has bank and account IDs but no customer names. Attach real registry entities to its accounts and apply different realistic noise per bank. Say plainly in the pitch that this name-to-account join is synthetic.
3. ### Stand up the enclave

   Run canonicalization at each simulated bank, ship encrypted canonical records into a Secure Execution guest, and run block, score and cluster there.
4. ### Wire global IDs into detection

   Rekey transactions by global entity ID with confidence-weighted identity edges, then run graph detection.
5. ### Add Mode A if time allows

   Swap the enclave input for keyed-hash and Bloom encodings and measure the accuracy cost.

## The result that sells it

Run the same detector three ways on the same transactions: each bank alone, all banks joined by exact name match, and all banks joined through the linkage layer. Report how many known cross-bank laundering patterns each one finds. If per-bank and exact-match detection miss cycles that the linked graph catches, that gap is Mritra's case in one chart.

## Open questions

- Who holds the shared encoding key, and how it rotates without re-encoding every bank's history.
- Whether corpus-wide IDF can be computed without exposing name frequencies, since frequency is what the Bloom attacks exploit.
- Scope for individuals. The pipeline is business-only, and personal names carry heavier obligations under India's DPDP Act.
- Whether the competition's data terms allow reusing its trained model. Retraining on public data avoids the question.