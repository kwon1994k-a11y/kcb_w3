import pandas as pd
import streamlit as st

from database import get_or_create_worksheet, get_spreadsheet


KBOAT_PATTERN_HEADERS = ["no", "a1", "a2", "a3", "a4", "a5", "n1", "n2", "n3"]


def save_kboat_pattern_db(df: pd.DataFrame):
    missing = [col for col in KBOAT_PATTERN_HEADERS if col not in df.columns]
    if missing:
        raise ValueError(f"db 시트에 필요한 열이 없습니다: {missing}")

    clean = df[KBOAT_PATTERN_HEADERS].dropna(subset=KBOAT_PATTERN_HEADERS[1:]).copy()
    for col in KBOAT_PATTERN_HEADERS:
        clean[col] = pd.to_numeric(clean[col], errors="coerce")
    clean = clean.dropna(subset=KBOAT_PATTERN_HEADERS)
    clean = clean.astype(int)

    spreadsheet = get_spreadsheet()
    ws = get_or_create_worksheet(spreadsheet, "kboat_pattern_db", KBOAT_PATTERN_HEADERS)
    values = [KBOAT_PATTERN_HEADERS] + clean.values.tolist()
    ws.clear()
    ws.update(values, value_input_option="RAW")
    return len(clean)


@st.cache_data(ttl=300)
def load_kboat_pattern_db() -> pd.DataFrame:
    spreadsheet = get_spreadsheet()
    ws = get_or_create_worksheet(spreadsheet, "kboat_pattern_db", KBOAT_PATTERN_HEADERS)
    records = ws.get_all_records()
    df = pd.DataFrame(records)
    if df.empty:
        return pd.DataFrame(columns=KBOAT_PATTERN_HEADERS)
    return df[KBOAT_PATTERN_HEADERS].copy()
