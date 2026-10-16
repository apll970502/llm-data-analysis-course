import json
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
CONFIG_PATH = BASE_DIR / "config" / "tourism_params.json"

failures = []


def check(ok, message):
    print(("PASS" if ok else "FAIL"), message)
    if not ok:
        failures.append(message)


def latest_raw(prefix):
    files = sorted(RAW_DIR.glob(f"{prefix}_*.json"))
    if not files:
        raise RuntimeError(f"{prefix} Raw 파일이 없습니다.")
    return files[-1]


# ---------- NAVER ----------
print("== NAVER ==")
naver = pd.read_csv(PROCESSED_DIR / "naver_trend.csv")
naver["period"] = pd.to_datetime(naver["period"], errors="coerce")

check(len(naver) > 0, f"행 수 > 0 ({len(naver)})")
check(naver["keyword"].notna().all(), "keyword 결측 없음")
check(naver["period"].notna().all(), "period 결측 없음")
check(naver["ratio"].notna().all(), "ratio 결측 없음")
check(
    naver["ratio"].between(0, 100).all(),
    f"ratio 범위 0~100 ({naver['ratio'].min():.2f} ~ {naver['ratio'].max():.2f})",
)
check(not naver.duplicated(["period", "keyword"]).any(), "period x keyword 중복 없음")
check(
    naver.groupby("keyword").size().nunique() == 1,
    "키워드별 행 수 동일",
)
print("최신 period:", naver["period"].max().date())

# ---------- Tourism ----------
print("== TOURISM ==")
with CONFIG_PATH.open("r", encoding="utf-8") as f:
    fields = json.load(f)["fields"]

for prefix, value_col in [
    ("tourism_stay", fields["stay"]),
    ("tourism_consumption", fields["consumption"]),
]:
    raw_file = latest_raw(prefix)
    with raw_file.open("r", encoding="utf-8") as f:
        node = json.load(f)
    for key in fields["item_path"]:
        node = node[key]
    df = pd.DataFrame(node if isinstance(node, list) else [node])

    print("--", prefix, raw_file.name)
    check(len(df) > 0, f"응답 데이터 존재 ({len(df)})")
    check(
        fields["region"] in df.columns and df[fields["region"]].notna().all(),
        "지역 key 존재",
    )
    check(
        fields["date"] in df.columns and df[fields["date"]].nunique() == 1,
        f"기준 시점 단일 ({df[fields['date']].unique().tolist()})",
    )
    values = pd.to_numeric(df[value_col], errors="coerce")
    check(values.notna().all(), f"{value_col} 숫자 변환 ({values.min()} ~ {values.max()})")
    check(not df["signguCd"].duplicated().any(), "signguCd 중복 없음")

if failures:
    raise RuntimeError(f"데이터 검증 FAIL {len(failures)}건: " + "; ".join(failures))

print("[PASS] Validate data")
