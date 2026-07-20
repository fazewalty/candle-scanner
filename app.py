from pathlib import Path

import pandas as pd
import streamlit as st


CURRENT_RESULTS_FILE = Path("current_scan.csv")
HISTORY_FILE = Path("scan_history.csv")

CANDLE_ORDER = ["1", "2 Up", "2 Down", "3"]


def normalize_signal_column(data: pd.DataFrame) -> pd.DataFrame:
    data = data.copy()

    data["Signal"] = (
        data["Signal"]
        .astype(str)
        .str.strip()
        .str.lower()
        .isin({"true", "1", "yes"})
    )

    return data


st.set_page_config(
    page_title="1-2-3 Candle Scanner",
    layout="wide",
)

st.title("1–2–3 Candle Scanner")
st.caption("Completed daily candles only")

if not CURRENT_RESULTS_FILE.exists():
    st.warning(
        "No scan results exist yet. Run the GitHub Actions "
        "workflow before using the dashboard."
    )
    st.stop()


latest = pd.read_csv(CURRENT_RESULTS_FILE)
latest = normalize_signal_column(latest)
latest = latest.sort_values("Symbol")

signal_count = int(latest["Signal"].sum())
inside_count = int((latest["Candle"] == "1").sum())
outside_count = int((latest["Candle"] == "3").sum())

metric1, metric2, metric3, metric4 = st.columns(4)

metric1.metric("Symbols", len(latest))
metric2.metric("Signals", signal_count)
metric3.metric("Inside Bars", inside_count)
metric4.metric("Outside Bars", outside_count)

st.divider()

filter1, filter2 = st.columns(2)

with filter1:
    selected_types = st.multiselect(
        "Candle types",
        options=CANDLE_ORDER,
        default=CANDLE_ORDER,
    )

with filter2:
    signals_only = st.toggle("Show signals only")

filtered = latest[latest["Candle"].isin(selected_types)]

if signals_only:
    filtered = filtered[filtered["Signal"]]

st.subheader("Current scan")

display_columns = [
    "Symbol",
    "CandleDate",
    "Candle",
    "Signal",
    "PreviousHigh",
    "PreviousLow",
    "CurrentHigh",
    "CurrentLow",
]

st.dataframe(
    filtered[display_columns],
    hide_index=True,
    use_container_width=True,
)

st.subheader("Current candle distribution")

type_counts = (
    latest["Candle"]
    .value_counts()
    .reindex(CANDLE_ORDER, fill_value=0)
    .rename("Count")
)

st.bar_chart(type_counts)

if HISTORY_FILE.exists():
    history = pd.read_csv(HISTORY_FILE)
    history = normalize_signal_column(history)
    history["CandleDate"] = pd.to_datetime(history["CandleDate"])

    st.subheader("Signals by date")

    signals_by_date = (
        history.groupby("CandleDate")["Signal"]
        .sum()
        .astype(int)
        .rename("Signals")
    )

    st.line_chart(signals_by_date)

    available_symbols = sorted(history["Symbol"].unique())

    selected_symbol = st.selectbox(
        "Recent candle sequence",
        options=available_symbols,
    )

    sequence = (
        history[history["Symbol"] == selected_symbol]
        .sort_values("CandleDate")
        .tail(20)
    )

    st.dataframe(
        sequence[
            [
                "CandleDate",
                "Candle",
                "Signal",
                "CurrentHigh",
                "CurrentLow",
            ]
        ],
        hide_index=True,
        use_container_width=True,
    )
