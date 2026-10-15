import json
import os
from datetime import date, timedelta, datetime
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

load_dotenv(BASE_DIR / ".env")

client_id = os.getenv("NAVER_CLIENT_ID")
client_secret = os.getenv("NAVER_CLIENT_SECRET")

if not client_id or not client_secret:
    raise RuntimeError("NAVER API Key가 설정되지 않았습니다.")

url = "https://naverapihub.apigw.ntruss.com/search-trend/v1/search"

end_date = date.today()
start_date = end_date - timedelta(days=365)

payload = {
    "startDate": start_date.isoformat(),
    "endDate": end_date.isoformat(),
    "timeUnit": "month",
    "keywordGroups": [
        {"groupName": "여행", "keywords": ["여행"]},
        {"groupName": "축제", "keywords": ["축제"]},
        {"groupName": "캠핑", "keywords": ["캠핑"]},
        {"groupName": "맛집", "keywords": ["맛집"]},
    ],
}

headers = {
    "X-NCP-APIGW-API-KEY-ID": client_id,
    "X-NCP-APIGW-API-KEY": client_secret,
    "Content-Type": "application/json",
}

response = requests.post(url, headers=headers, json=payload, timeout=30)

if response.status_code != 200:
    raise RuntimeError(
        f"NAVER API 실패: HTTP {response.status_code} {response.text[:300]}"
    )

data = response.json()

if "results" not in data:
    raise RuntimeError("NAVER 응답에 results가 없습니다.")

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
raw_path = RAW_DIR / f"naver_trend_{timestamp}.json"
with raw_path.open("w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

rows = []
for result in data["results"]:
    keyword = result.get("title")
    for point in result.get("data", []):
        rows.append({
            "period": point.get("period"),
            "keyword": keyword,
            "ratio": point.get("ratio"),
        })

df = pd.DataFrame(rows)

if df.empty:
    raise RuntimeError("NAVER 결과가 비어 있습니다.")

df["period"] = pd.to_datetime(df["period"], errors="coerce")
df["ratio"] = pd.to_numeric(df["ratio"], errors="coerce")

if df["period"].isna().any():
    raise RuntimeError("period 날짜 변환 실패 값이 있습니다.")
if df["ratio"].isna().any():
    raise RuntimeError("ratio 숫자 변환 실패 값이 있습니다.")

output_path = PROCESSED_DIR / "naver_trend.csv"
df.to_csv(output_path, index=False, encoding="utf-8-sig")

print("[PASS] NAVER Trend API")
print("rows:", len(df))
print("period:", df["period"].min().date(), "~", df["period"].max().date())
print("keywords:", sorted(df["keyword"].unique().tolist()))
print("saved:", output_path)
