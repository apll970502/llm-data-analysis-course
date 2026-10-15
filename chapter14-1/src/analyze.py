import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
REPORTS_DIR = BASE_DIR / "reports"
CONFIG_PATH = BASE_DIR / "config" / "tourism_params.json"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False


def latest_raw(prefix):
    files = sorted(RAW_DIR.glob(f"{prefix}_*.json"))
    if not files:
        raise RuntimeError(f"{prefix} Raw 파일이 없습니다.")
    return files[-1]


# ---------- NAVER ----------
naver = pd.read_csv(PROCESSED_DIR / "naver_trend.csv")
naver["period"] = pd.to_datetime(naver["period"])

if naver.empty:
    raise RuntimeError("NAVER 데이터가 비어 있습니다.")
if naver[["period", "keyword", "ratio"]].isna().any().any():
    raise RuntimeError("NAVER 데이터에 결측이 있습니다.")

# 진행 중인 달은 일부 일자만 반영된 불완전한 값이라 제외
current_month = pd.Timestamp.today().normalize().replace(day=1)
naver = naver[naver["period"] < current_month]
if naver.empty:
    raise RuntimeError("완전한 달의 NAVER 데이터가 없습니다.")

naver = naver.sort_values(["keyword", "period"])
latest_period = naver["period"].max()
latest = (
    naver.groupby("keyword").tail(1).sort_values("ratio", ascending=False)
)
previous = naver.groupby("keyword").nth(-2).set_index("keyword")["ratio"]

naver_rows = []
for _, row in latest.iterrows():
    prev = previous.get(row["keyword"])
    change = None if prev is None or pd.isna(prev) else row["ratio"] - prev
    naver_rows.append({
        "source": "NAVER",
        "item": row["keyword"],
        "period": row["period"].date().isoformat(),
        "value": round(float(row["ratio"]), 2),
        "change_vs_prev": None if change is None else round(float(change), 2),
    })

fig, ax = plt.subplots(figsize=(9, 5))
for keyword, group in naver.groupby("keyword"):
    ax.plot(group["period"], group["ratio"], marker="o", label=keyword)
ax.set_title("NAVER 검색 관심도 추이 (상대지수)")
ax.set_xlabel("기간")
ax.set_ylabel("상대 관심도")
ax.legend()
fig.tight_layout()
fig.savefig(REPORTS_DIR / "naver_trend.png", dpi=150)
plt.close(fig)

# ---------- Tourism ----------
with CONFIG_PATH.open("r", encoding="utf-8") as f:
    fields = json.load(f).get("fields", {})

region_f = fields.get("region")
date_f = fields.get("date")
stay_f = fields.get("stay")
cons_f = fields.get("consumption")
item_path = fields.get("item_path", [])

if not (region_f and stay_f and cons_f):
    raise RuntimeError(
        "config/tourism_params.json 의 fields(region, stay, consumption)를 "
        "Swagger 응답 기준으로 먼저 채워 주세요."
    )


def load_items(prefix):
    with latest_raw(prefix).open("r", encoding="utf-8") as f:
        node = json.load(f)
    for key in item_path:
        node = node[key]
    if isinstance(node, dict):
        node = [node]
    df = pd.DataFrame(node)
    # signguCd "0" 은 시도 전체 집계 행이라 구별 순위에서 제외
    if "signguCd" in df.columns:
        df = df[df["signguCd"].astype(str) != "0"]
    return df


stay_df = load_items("tourism_stay")
cons_df = load_items("tourism_consumption")

for name, df, col in [("stay", stay_df, stay_f), ("consumption", cons_df, cons_f)]:
    if df.empty:
        raise RuntimeError(f"{name} 데이터가 비어 있습니다.")
    for c in (region_f, col):
        if c not in df.columns:
            raise RuntimeError(f"{name} 데이터에 '{c}' 필드가 없습니다.")
    df[col] = pd.to_numeric(df[col], errors="coerce")
    if df[col].isna().all():
        raise RuntimeError(f"{name} '{col}' 값이 모두 숫자가 아닙니다.")

stay_top = stay_df.dropna(subset=[stay_f]).nlargest(10, stay_f)
cons_top = cons_df.dropna(subset=[cons_f]).nlargest(10, cons_f)

ref_date = ""
if date_f and date_f in cons_df.columns:
    ref_date = str(cons_df[date_f].iloc[0])

fig, ax = plt.subplots(figsize=(9, 5))
ax.barh(cons_top[region_f].astype(str)[::-1], cons_top[cons_f][::-1])
ax.set_title("지역별 관광 소비 강도 상위 10")
ax.set_xlabel("소비 강도")
fig.tight_layout()
fig.savefig(REPORTS_DIR / "tourism_consumption_top10.png", dpi=150)
plt.close(fig)

tour_rows = []
for rank, (_, r) in enumerate(stay_top.iterrows(), 1):
    tour_rows.append({
        "source": "관광 체류 강도(서울 구별)",
        "item": str(r[region_f]),
        "period": ref_date,
        "value": float(r[stay_f]),
        "change_vs_prev": None,
    })
for rank, (_, r) in enumerate(cons_top.iterrows(), 1):
    tour_rows.append({
        "source": "관광 소비 강도(서울 구별)",
        "item": str(r[region_f]),
        "period": ref_date,
        "value": float(r[cons_f]),
        "change_vs_prev": None,
    })

summary = pd.DataFrame(naver_rows + tour_rows)
summary.to_csv(
    REPORTS_DIR / "analysis_summary.csv", index=False, encoding="utf-8-sig"
)

print("[PASS] Analyze")
print("naver latest period:", latest_period.date())
print("naver top keyword:", latest.iloc[0]["keyword"])
print("stay top:", stay_top[region_f].astype(str).tolist()[:3])
print("consumption top:", cons_top[region_f].astype(str).tolist()[:3])
print("saved:", REPORTS_DIR / "analysis_summary.csv")
