"""Mritra Dashboard — Streamlit demo app (plan §16).

Shows:
  1. Live chain graph with role/path/amount per account
  2. Results charts: G with interval, PR-AUC, lead time, innocent money
  3. Transparency log viewer with chain verification
  4. Reconciliation results
"""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

st.set_page_config(
    page_title="Mritra — Cross-Bank AML",
    page_icon="🛡️",
    layout="wide",
)

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.title("🛡️ Mritra — Privacy-Preserving Cross-Bank AML")
st.caption(
    "Enclave boundary simulated — production target: IBM Secure Execution on LinuxONE"
)

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

st.sidebar.header("Configuration")
results_files = sorted(RESULTS_DIR.glob("*.json")) if RESULTS_DIR.exists() else []
selected_file = st.sidebar.selectbox(
    "Results file",
    options=results_files,
    format_func=lambda p: p.name,
) if results_files else None

# ---------------------------------------------------------------------------
# Results Tab
# ---------------------------------------------------------------------------

tab_results, tab_chain, tab_log, tab_recon = st.tabs(
    ["📊 Results", "🔗 Chain Graph", "📋 Transparency Log", "🔍 Reconciliation"]
)

with tab_results:
    if selected_file:
        data = json.loads(selected_file.read_text())
        st.json(data)
    else:
        st.info("No results files found. Run `make eval` to generate results.")

    st.subheader("Gap Recovered (G)")
    st.markdown(
        """
        > G = (F1_C3 − F1_C1) / (F1_C4 − F1_C1)
        >
        > G = 0 → Mritra adds nothing over isolated banks.
        > G = 1 → Matches the all-seeing oracle model.
        """
    )

    # Placeholder for the bar chart — populated after make eval
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("C1 (Siloed)", "—", help="Status quo: each bank alone")
    with col2:
        st.metric("C3 (Mritra)", "—", help="Siloed + enclave network features")
    with col3:
        st.metric("C4 (Oracle)", "—", help="Full-graph upper bound")

# ---------------------------------------------------------------------------
# Chain Graph Tab
# ---------------------------------------------------------------------------

with tab_chain:
    st.subheader("Cross-Bank Laundering Chain")
    st.info(
        "Select a demo chain from the test period to visualise. "
        "Pick one where C1 misses and C3 catches."
    )
    # Placeholder for pyvis graph — populated during demo
    st.markdown("*Chain graph will render here during the live demo.*")

# ---------------------------------------------------------------------------
# Transparency Log Tab
# ---------------------------------------------------------------------------

with tab_log:
    st.subheader("Transparency Log")
    tlog_path = RESULTS_DIR / "tlog.db"
    demo_tlog_path = RESULTS_DIR / "demo_tlog.db"

    for db_name, db_path in [("Main", tlog_path), ("Demo", demo_tlog_path)]:
        if db_path.exists():
            from mritra.protocol.tlog import TransparencyLog, verify_chain

            tlog = TransparencyLog(db_path)
            entries = tlog.entries()
            tlog.close()

            st.write(f"**{db_name} log:** {len(entries)} entries")
            valid, broken = verify_chain(entries)
            if valid:
                st.success(f"✅ Chain intact — head: `{entries[-1].entry_hash[:16]}...`")
            else:
                st.error(f"❌ Chain broken at seq {broken}")

            if entries:
                import pandas as pd

                log_df = pd.DataFrame(
                    [
                        {
                            "seq": e.seq,
                            "requester": e.requester,
                            "query_type": e.query_type,
                            "entry_hash": e.entry_hash[:16] + "...",
                        }
                        for e in entries[-20:]
                    ]
                )
                st.dataframe(log_df, use_container_width=True)
        else:
            st.info(f"{db_name} log not found at {db_path}")

# ---------------------------------------------------------------------------
# Reconciliation Tab
# ---------------------------------------------------------------------------

with tab_recon:
    st.subheader("Reconciliation Results")
    recon_path = RESULTS_DIR / "reconciliation_injection.json"
    if recon_path.exists():
        recon_data = json.loads(recon_path.read_text())
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Injected Issues", recon_data.get("injected_issues", "—"))
        with col2:
            st.metric("Caught Issues", recon_data.get("caught_issues", "—"))
        with col3:
            rate = recon_data.get("catch_rate", 0)
            st.metric("Catch Rate", f"{rate:.1%}")

        st.json(recon_data)
    else:
        st.info("No reconciliation results. Run `scripts/inject_lying_bank.py`.")
