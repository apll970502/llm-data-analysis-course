import json
import os
from datetime import date, datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / "data" / "raw"
CONFIG_PATH = BASE_DIR / "config" / "tourism_params.json"
RAW_DIR.mkdir(parents=True, exist_ok=True)

load_dotenv(BASE_DIR / ".env")

service_key = os.getenv("TOURISM_SERVICE_KEY")
stay_url = os.getenv("TOURISM_STAY_URL")
consumption_url = os.getenv("TOURISM_CONSUMPTION_URL")

if not service_key:
    raise RuntimeError("TOURISM_SERVICE_KEY가 없습니다.")
if not stay_url or not consumption_url:
    raise RuntimeError("관광 API URL이 설정되지 않았습니다.")

with CONFIG_PATH.open("r", encoding="utf-8") as f:
    config = json.load(f)


def call_api(name, url, params):
    request_params = dict(params)
    request_params["serviceKey"] = service_key

    response = requests.get(url, params=request_params, timeout=30)

    if response.status_code != 200:
        raise RuntimeError(f"{name} API 실패: HTTP {response.status_code}")

    try:
        data = response.json()
    except ValueError as e:
        raise RuntimeError(f"{name} 응답이 JSON이 아닙니다.") from e

    if not data:
        raise RuntimeError(f"{name} 응답이 비어 있습니다.")

    header = data.get("response", {}).get("header", {})
    if header.get("resultCode") != "0000":
        raise RuntimeError(f"{name} API 오류: {header}")

    return data


def total_count(data):
    return int(data["response"]["body"].get("totalCount") or 0)


def month_candidates(n=6):
    """직전 달부터 거슬러 올라가는 YYYYMM 후보 (최신월은 데이터가 비어 있을 수 있음)."""
    y, m = date.today().year, date.today().month
    out = []
    for _ in range(n):
        m -= 1
        if m == 0:
            y, m = y - 1, 12
        out.append(f"{y}{m:02d}")
    return out


stay_params = dict(config["stay"]["params"])
consumption_params = dict(config["consumption"]["params"])

stay_data = None
if stay_params.get("baseYm") == "auto":
    for ym in month_candidates():
        stay_params["baseYm"] = ym
        data = call_api("stay", stay_url, stay_params)
        if total_count(data) > 0:
            stay_data = data
            break
    if stay_data is None:
        raise RuntimeError("최근 6개월 중 관광 데이터가 있는 기준월을 찾지 못했습니다.")
    consumption_params["baseYm"] = stay_params["baseYm"]
else:
    stay_data = call_api("stay", stay_url, stay_params)

consumption_data = call_api("consumption", consumption_url, consumption_params)

if total_count(stay_data) == 0:
    raise RuntimeError("stay 데이터가 0건입니다.")
if total_count(consumption_data) == 0:
    raise RuntimeError(
        f"consumption 데이터가 0건입니다. baseYm={consumption_params['baseYm']}"
    )

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
stay_path = RAW_DIR / f"tourism_stay_{timestamp}.json"
consumption_path = RAW_DIR / f"tourism_consumption_{timestamp}.json"

with stay_path.open("w", encoding="utf-8") as f:
    json.dump(stay_data, f, ensure_ascii=False, indent=2)
with consumption_path.open("w", encoding="utf-8") as f:
    json.dump(consumption_data, f, ensure_ascii=False, indent=2)

print("[PASS] Tourism API")
print("baseYm:", stay_params["baseYm"])
print("stay rows:", total_count(stay_data), "saved:", stay_path)
print("consumption rows:", total_count(consumption_data), "saved:", consumption_path)
