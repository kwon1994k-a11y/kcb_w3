import numpy as np
import pandas as pd


A_COLS = ["a1", "a2", "a3", "a4", "a5"]
N_COLS = ["n1", "n2", "n3"]
REQUIRED_COLS = ["no"] + A_COLS + N_COLS


def _prepare_db(db: pd.DataFrame) -> pd.DataFrame:
    missing = [col for col in REQUIRED_COLS if col not in db.columns]
    if missing:
        raise ValueError(f"db 데이터에 필요한 열이 없습니다: {missing}")

    data = db[REQUIRED_COLS].copy()
    for col in REQUIRED_COLS:
        data[col] = pd.to_numeric(data[col], errors="coerce")
    data = data.dropna(subset=A_COLS + N_COLS)
    for col in A_COLS + N_COLS:
        data[col] = data[col].astype(int).astype(str)
    data["x_key"] = data[A_COLS].agg("|".join, axis=1)
    data["y_key"] = data[N_COLS].agg("=".join, axis=1)
    return data


def _rank_pattern(row: pd.Series) -> str:
    popularity = [row[col] for col in A_COLS]
    pattern = []
    for col in N_COLS:
        value = row[col]
        pattern.append(str(popularity.index(value)) if value in popularity else f"OUT:{value}")
    return "|".join(pattern)


def _translate_pattern(inputs: list[str], pattern: str) -> str:
    output = []
    for value in pattern.split("|"):
        if value.startswith("OUT:"):
            output.append(value.replace("OUT:", "", 1))
        else:
            output.append(inputs[int(value)])
    return "=".join(output)


def _top_result_rows(distribution: dict[str, float], limit: int = 3) -> pd.DataFrame:
    rows = sorted(distribution.items(), key=lambda item: (-item[1], item[0]))[:limit]
    return pd.DataFrame(rows, columns=["예측 조합", "확률"])


def predict_from_popularity(db: pd.DataFrame, a_values, neighbor_limit: int = 50) -> dict:
    data = _prepare_db(db)
    if data.empty:
        raise ValueError("저장된 db 데이터가 없습니다. 관리자 화면에서 db 엑셀을 먼저 등록하세요.")

    inputs = [str(int(value)) for value in a_values]
    if len(inputs) != 5 or len(set(inputs)) != 5:
        raise ValueError("a1~a5는 중복되지 않은 숫자 5개여야 합니다.")

    x_key = "|".join(inputs)
    exact = data[data["x_key"] == x_key]
    if not exact.empty:
        dist = exact["y_key"].value_counts(normalize=True).to_dict()
        return {
            "rows": _top_result_rows(dist),
            "method": "동일 조합 db 빈도",
            "match_count": int(len(exact)),
            "message": f"db에서 같은 인기순위 조합 {len(exact)}건을 찾았습니다.",
        }

    candidate_values = data[A_COLS].to_numpy()
    inputs_array = np.array(inputs)
    position_matches = (candidate_values == inputs_array).sum(axis=1)
    overlap_matches = np.array([len(set(candidate) & set(inputs)) for candidate in candidate_values])
    scores = (position_matches * 3) + overlap_matches
    top_index = np.argsort(-scores)[: min(neighbor_limit, len(data))]
    neighbors = data.iloc[top_index].copy()
    neighbors["pattern"] = neighbors.apply(_rank_pattern, axis=1)
    neighbors["weight"] = np.maximum(scores[top_index], 1) ** 3
    weighted = neighbors.groupby("pattern")["weight"].sum()
    translated = {}
    for pattern, weight in weighted.items():
        label = _translate_pattern(inputs, pattern)
        translated[label] = translated.get(label, 0.0) + float(weight)
    total = sum(translated.values())
    dist = {label: value / total for label, value in translated.items()}

    return {
        "rows": _top_result_rows(dist),
        "method": "유사 조합 패턴 빈도",
        "match_count": 0,
        "message": "동일한 조합이 없어 가장 비슷한 과거 패턴으로 계산했습니다.",
    }
