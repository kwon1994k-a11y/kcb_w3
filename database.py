import base64
from datetime import datetime
import time

import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

DEFAULT_SPREADSHEET_NAME = "\uacbd\ub9c8&\uacbd\ub95c&\uacbd\uc815_\ubd84\uc11d\ud45c"
DEFAULT_SPREADSHEET_ID = "1-nj7R15nseCyksW8Y2idTUlrkrQwJIlD0D-74Q5oO7o"
KEIRIN_PATTERN_HEADERS = ["no", "a1", "a2", "a3", "a4", "a5", "n1", "n2", "n3"]


def get_secret_value(key, default=None):
    try:
        return st.secrets[key]
    except KeyError:
        return default

def get_client():
    """
    Streamlit secrets.toml 또는 Streamlit Cloud Secrets에 등록한
    Google 서비스 계정 정보로 Google Sheets에 접속합니다.
    """
    service_account_info = dict(st.secrets["gcp_service_account"])
    # private_key를 Base64 디코딩합니다.
    service_account_info["private_key"] = base64.b64decode(
        service_account_info["private_key"]
    )
    credentials = Credentials.from_service_account_info(
        service_account_info,
        scopes=SCOPES
    )
    return gspread.authorize(credentials)


def get_spreadsheet():
    """
    Open the configured Google Spreadsheet. Prefer spreadsheet_id because it is
    stable even when the spreadsheet name changes or Streamlit secrets omit name.
    """
    client = get_client()
    spreadsheet_id = get_secret_value("spreadsheet_id", DEFAULT_SPREADSHEET_ID)
    spreadsheet_name = get_secret_value("spreadsheet_name", DEFAULT_SPREADSHEET_NAME)

    if spreadsheet_id:
        return client.open_by_key(spreadsheet_id)

    return client.open(spreadsheet_name)
def get_or_create_worksheet(spreadsheet, title, headers):
    """
    지정한 워크시트가 없으면 자동 생성하고 헤더를 입력합니다.
    """
    try:
        ws = spreadsheet.worksheet(title)
    except gspread.WorksheetNotFound:
        try:
            ws = spreadsheet.add_worksheet(title=title, rows=1000, cols=len(headers))
            ws.append_row(headers)
        except gspread.exceptions.APIError as e:
            # Concurrent Streamlit reruns can attempt to create the same sheet.
            if "already" not in str(e).lower() or "sheet" not in str(e).lower():
                raise
            for _ in range(3):
                try:
                    ws = spreadsheet.worksheet(title)
                    break
                except gspread.WorksheetNotFound:
                    time.sleep(0.5)
            else:
                raise

    values = ws.get_all_values()
    if not values:
        ws.append_row(headers)

    return ws


def init_db():
    """
    Google Sheets 안에 필요한 시트를 자동 생성합니다.
    """
    spreadsheet = get_spreadsheet()

    get_or_create_worksheet(
        spreadsheet,
        "posts",
        ["id", "category", "title", "content", "created_at"]
    )

    get_or_create_worksheet(
        spreadsheet,
        "images",
        ["id", "category", "filename", "base64_data", "created_at"]
    )

    get_or_create_worksheet(
        spreadsheet,
        "excel_data",
        ["id", "category", "title", "json_data", "created_at"]
    )

    get_or_create_worksheet(
        spreadsheet,
        "keirin_pattern_db",
        KEIRIN_PATTERN_HEADERS
    )


def _next_id(ws):
    records = ws.get_all_records()
    if not records:
        return 1

    ids = []
    for row in records:
        try:
            ids.append(int(row.get("id", 0)))
        except Exception:
            pass

    return max(ids) + 1 if ids else 1


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def save_post(category: str, title: str, content: str):
    spreadsheet = get_spreadsheet()
    ws = spreadsheet.worksheet("posts")
    row_id = _next_id(ws)

    ws.append_row([
        row_id,
        category,
        title,
        content,
        _now()
    ])


def save_image(category: str, filename: str, data: bytes):
    spreadsheet = get_spreadsheet()
    ws = spreadsheet.worksheet("images")
    row_id = _next_id(ws)

    base64_data = base64.b64encode(data).decode("utf-8")

    ws.append_row([
        row_id,
        category,
        filename,
        base64_data,
        _now()
    ])


def save_excel(category: str, title: str, df: pd.DataFrame):
    spreadsheet = get_spreadsheet()
    ws = spreadsheet.worksheet("excel_data")
    row_id = _next_id(ws)

    json_data = df.to_json(force_ascii=False)

    ws.append_row([
        row_id,
        category,
        title,
        json_data,
        _now()
    ])


def save_keirin_pattern_db(df: pd.DataFrame):
    missing = [col for col in KEIRIN_PATTERN_HEADERS if col not in df.columns]
    if missing:
        raise ValueError(f"db 시트에 필요한 열이 없습니다: {missing}")

    clean = df[KEIRIN_PATTERN_HEADERS].dropna(subset=KEIRIN_PATTERN_HEADERS[1:]).copy()
    for col in KEIRIN_PATTERN_HEADERS:
        clean[col] = pd.to_numeric(clean[col], errors="coerce")
    clean = clean.dropna(subset=KEIRIN_PATTERN_HEADERS)
    clean = clean.astype(int)

    spreadsheet = get_spreadsheet()
    ws = get_or_create_worksheet(spreadsheet, "keirin_pattern_db", KEIRIN_PATTERN_HEADERS)
    values = [KEIRIN_PATTERN_HEADERS] + clean.values.tolist()
    ws.clear()
    ws.update(values, value_input_option="RAW")
    return len(clean)


@st.cache_data(ttl=300)
def load_keirin_pattern_db() -> pd.DataFrame:
    spreadsheet = get_spreadsheet()
    ws = get_or_create_worksheet(spreadsheet, "keirin_pattern_db", KEIRIN_PATTERN_HEADERS)
    records = ws.get_all_records()
    df = pd.DataFrame(records)
    if df.empty:
        return pd.DataFrame(columns=KEIRIN_PATTERN_HEADERS)
    return df[KEIRIN_PATTERN_HEADERS].copy()


def load_posts(category: str) -> pd.DataFrame:
    spreadsheet = get_spreadsheet()
    ws = spreadsheet.worksheet("posts")
    records = ws.get_all_records()

    df = pd.DataFrame(records)
    if df.empty:
        return df

    df = df[df["category"] == category]
    return df.sort_values("created_at", ascending=False)


def load_images(category: str) -> pd.DataFrame:
    spreadsheet = get_spreadsheet()
    ws = spreadsheet.worksheet("images")
    records = ws.get_all_records()

    df = pd.DataFrame(records)
    if df.empty:
        return df

    df = df[df["category"] == category]
    return df.sort_values("created_at", ascending=False)


def load_excel_data(category: str) -> pd.DataFrame:
    spreadsheet = get_spreadsheet()
    ws = spreadsheet.worksheet("excel_data")
    records = ws.get_all_records()

    df = pd.DataFrame(records)
    if df.empty:
        return df

    df = df[df["category"] == category]
    return df.sort_values("created_at", ascending=False)


def base64_to_bytes(base64_text: str) -> bytes:
    return base64.b64decode(base64_text)

