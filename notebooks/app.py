"""Chapter 10 주문 취소 예측 대시보드 (Streamlit, 파일 하나로 실행)

실행:  streamlit run notebooks/app.py
- 처음 실행할 때 모델이 없으면 한 번 학습해서 파일로 저장한다. (data/raw 필요)
- 이후에는 저장된 모델 파일을 불러와서 예측만 한다. (서빙)
"""
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import streamlit as st
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent                     # notebooks -> 저장소 루트
RAW = PROJECT_ROOT / "data" / "raw"
ARTIFACT_DIR = HERE / "ch10_artifacts"
MODEL_PATH = ARTIFACT_DIR / "cancel_model.joblib"
META_PATH = ARTIFACT_DIR / "model_meta.json"
DAY_NAMES = ["월", "화", "수", "목", "금", "토", "일"]

# ----------------------------------------------------------- 모델 만들기 (없을 때만 한 번)
NUMERIC = ["item_count", "total_quantity", "order_amount", "order_month_num", "order_dayofweek", "age"]
CATEGORICAL = ["payment_method", "gender", "city"]
FEATURES = NUMERIC + CATEGORICAL


def load_model_data():
    orders = pd.read_csv(RAW / "orders.csv", encoding="utf-8-sig")
    items = pd.read_csv(RAW / "order_items.csv", encoding="utf-8-sig")
    customers = pd.read_csv(RAW / "customers.csv", encoding="utf-8-sig")

    df = orders[orders["order_status"].isin(["completed", "cancelled"])].copy()
    df["is_cancelled"] = df["order_status"].map({"completed": 0, "cancelled": 1})
    items["line_total"] = items["quantity"] * items["unit_price"]
    feat = (items.groupby("order_id")
            .agg(item_count=("order_item_id", "count"),
                 total_quantity=("quantity", "sum"),
                 order_amount=("line_total", "sum"))
            .reset_index())
    df = df.merge(feat, on="order_id", validate="one_to_one")
    df = df.merge(customers[["customer_id", "gender", "age", "city"]], on="customer_id", validate="many_to_one")
    df["order_date"] = pd.to_datetime(df["order_date"])
    df["order_month_num"] = df["order_date"].dt.month
    df["order_dayofweek"] = df["order_date"].dt.dayofweek
    return df


def make_pipeline(estimator):
    prep = ColumnTransformer([
        ("num", Pipeline([("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler())]), NUMERIC),
        ("cat", Pipeline([("imputer", SimpleImputer(strategy="most_frequent")),
                          ("onehot", OneHotEncoder(handle_unknown="ignore"))]), CATEGORICAL),
    ])
    return Pipeline([("prep", prep), ("model", estimator)])


def metrics(y_true, y_pred):
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
    }


def train_and_save():
    df = load_model_data()
    X, y = df[FEATURES], df["is_cancelled"]

    # Train 60% / Validation 20% / Test 20% (노트북과 같은 분할)
    X_rest, X_test, y_rest, y_test = train_test_split(X, y, test_size=0.20, stratify=y, random_state=42)
    X_train, X_val, y_train, y_val = train_test_split(X_rest, y_rest, test_size=0.25, stratify=y_rest, random_state=42)

    model = make_pipeline(LogisticRegression(max_iter=1000, random_state=42))
    model.fit(X_train, y_train)                      # Train으로만 학습
    dummy = make_pipeline(DummyClassifier(strategy="most_frequent")).fit(X_train, y_train)

    # Validation에서 threshold 선택 (F1 -> Recall -> Precision 순)
    val_proba = model.predict_proba(X_val)[:, 1]
    curve = []
    for t in np.round(np.arange(0.10, 0.91, 0.05), 2):
        pred = (val_proba >= t).astype(int)
        m = metrics(y_val, pred)
        m.update({"threshold": float(t), "predicted_cancel": int(pred.sum())})
        curve.append(m)
    best = sorted(curve, key=lambda r: (r["f1"], r["recall"], r["precision"]), reverse=True)[0]
    threshold = best["threshold"]

    # Final Test는 고정한 모델과 threshold로 한 번만 평가
    test_pred = (model.predict_proba(X_test)[:, 1] >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_test, test_pred, labels=[0, 1]).ravel()

    meta = {
        "model_name": "Logistic Regression",
        "threshold": threshold,
        "numeric_features": NUMERIC,
        "categorical_features": CATEGORICAL,
        "feature_columns": FEATURES,
        "options": {c: sorted(df[c].dropna().unique().tolist()) for c in CATEGORICAL},
        "ranges": {c: [float(df[c].min()), float(df[c].max())]
                   for c in ["age", "order_amount", "item_count", "total_quantity"]},
        "class_counts": {"completed": int((y == 0).sum()), "cancelled": int((y == 1).sum())},
        "split_sizes": {"train": len(y_train), "validation": len(y_val), "test": len(y_test)},
        "validation_curve": curve,
        "test_metrics": {"Dummy": metrics(y_test, dummy.predict(X_test)),
                         "Logistic Regression": metrics(y_test, test_pred)},
        "confusion": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
    }

    ARTIFACT_DIR.mkdir(exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    META_PATH.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")





# ----------------------------------------------------------- 대시보드
st.set_page_config(page_title="주문 취소 예측 대시보드", page_icon="📦", layout="wide")


@st.cache_resource
def load_artifacts():
    model = joblib.load(MODEL_PATH)
    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    return model, meta


def predict(model, frame, threshold):
    """서빙 함수: 입력 표를 받아 취소 확률과 판단을 돌려준다."""
    proba = model.predict_proba(frame)[:, 1]
    out = frame.copy()
    out["cancel_probability"] = proba.round(3)
    out["prediction"] = ["취소 위험" if p >= threshold else "완료 예상" for p in proba]
    return out


# ---------------------------------------------------------------- 모델 파일 확인
if not (MODEL_PATH.exists() and META_PATH.exists()):
    if not (RAW / "orders.csv").exists():
        st.title("📦 주문 취소 예측 대시보드")
        st.error("학습용 데이터(data/raw)를 찾지 못했습니다. 저장소 안의 notebooks 폴더에서 실행하세요.")
        st.stop()
    with st.spinner("저장된 모델이 없어 처음 한 번 학습합니다 (몇 초 걸립니다)..."):
        train_and_save()

model, meta = load_artifacts()
features = meta["feature_columns"]
curve = pd.DataFrame(meta["validation_curve"]).set_index("threshold")

# ---------------------------------------------------------------- 사이드바
st.sidebar.header("⚙️ 판단 기준 (threshold)")
threshold = st.sidebar.slider(
    "취소 확률이 이 값 이상이면 '취소 위험'",
    min_value=0.10, max_value=0.90, value=float(meta["threshold"]), step=0.05,
)
st.sidebar.caption(f"Validation에서 고른 기본값: {meta['threshold']}")
if threshold in curve.index:
    row = curve.loc[threshold]
    st.sidebar.markdown("**이 기준의 Validation 성능**")
    st.sidebar.metric("Precision (취소라고 한 것 중 맞은 비율)", f"{row['precision']:.3f}")
    st.sidebar.metric("Recall (실제 취소 중 잡아낸 비율)", f"{row['recall']:.3f}")
    st.sidebar.metric("F1", f"{row['f1']:.3f}")
st.sidebar.caption("낮추면 취소를 더 많이 잡지만(Recall ↑) 잘못 의심도 늘어납니다(FP ↑).")

# ---------------------------------------------------------------- 본문
st.title("📦 주문 취소 예측 대시보드")
st.caption(f"모델: {meta['model_name']} (저장된 서빙 모델) · 예측 시점: 주문 생성 직후")
st.warning(
    "이 모델은 Final Test에서 실제 취소 중 약 31%만 잡았습니다. "
    "최종 판단은 **현재 사용 보류**이며, 이 화면의 결과는 **참고용**입니다."
)

tab_one, tab_batch, tab_perf = st.tabs(["🔎 주문 1건 예측", "📄 CSV 일괄 예측", "📊 모델 성능"])

# ---------------------------------------------------------------- 탭 1: 1건 예측
with tab_one:
    st.subheader("새 주문 정보를 입력하세요")
    rng = meta["ranges"]
    c1, c2, c3 = st.columns(3)
    with c1:
        order_amount = st.number_input("주문 금액(원)", min_value=0, value=850000, step=10000)
        item_count = st.number_input("주문 상품 종류 수", min_value=1, max_value=20, value=3)
        total_quantity = st.number_input("총 수량", min_value=1, max_value=100, value=7)
    with c2:
        month = st.selectbox("주문 월", list(range(1, 13)), index=6)
        day_label = st.selectbox("주문 요일", DAY_NAMES, index=0)
        payment = st.selectbox("결제수단", meta["options"]["payment_method"], index=2)
    with c3:
        age = st.slider("고객 나이", 10, 90, 33)
        gender = st.selectbox("성별", meta["options"]["gender"])
        city = st.selectbox("도시", meta["options"]["city"])

    if st.button("예측하기", type="primary"):
        one = pd.DataFrame([{
            "item_count": item_count, "total_quantity": total_quantity, "order_amount": order_amount,
            "order_month_num": month, "order_dayofweek": DAY_NAMES.index(day_label), "age": age,
            "payment_method": payment, "gender": gender, "city": city,
        }])[features]
        res = predict(model, one, threshold).iloc[0]
        prob = float(res["cancel_probability"])

        m1, m2, m3 = st.columns(3)
        m1.metric("취소 확률", f"{prob:.1%}")
        m2.metric("판단 기준", f"{threshold:.2f}")
        m3.metric("판단", res["prediction"])
        st.progress(min(prob, 1.0))
        if res["prediction"] == "취소 위험":
            st.error("취소 위험으로 판단했습니다. 확인 연락 등 대응 후보입니다.")
        else:
            st.success("완료 예상으로 판단했습니다. 다만 이 모델은 취소를 많이 놓치므로 안심할 수는 없습니다.")
        st.caption("확률은 학습 데이터(주문 248건)에서 배운 패턴이며, 취소의 원인을 설명하지는 않습니다.")

# ---------------------------------------------------------------- 탭 2: 일괄 예측
with tab_batch:
    st.subheader("여러 주문을 CSV로 한꺼번에 예측")
    st.markdown("필요한 컬럼: `" + "`, `".join(features) + "`")

    example = pd.DataFrame([
        [1, 1, 30000, 3, 2, 45, "card", "F", meta["options"]["city"][0]],
        [4, 12, 1800000, 11, 5, 28, "bank_transfer", "M", meta["options"]["city"][1]],
        [3, 7, 850000, 7, 0, 33, "kakao_pay", "F", meta["options"]["city"][2]],
    ], columns=features)
    st.download_button("예시 CSV 내려받기", example.to_csv(index=False).encode("utf-8-sig"),
                       file_name="example_orders.csv", mime="text/csv")

    uploaded = st.file_uploader("CSV 파일 올리기", type="csv")
    if uploaded is not None:
        try:
            data = pd.read_csv(uploaded, encoding="utf-8-sig")
        except Exception:
            st.error("CSV를 읽지 못했습니다. 파일 형식을 확인하세요.")
            st.stop()
        missing = [c for c in features if c not in data.columns]
        if missing:
            st.error("없는 컬럼이 있습니다: " + ", ".join(missing))
        else:
            result = predict(model, data[features], threshold)
            n_risk = int((result["prediction"] == "취소 위험").sum())
            k1, k2, k3 = st.columns(3)
            k1.metric("전체 주문", len(result))
            k2.metric("취소 위험", n_risk)
            k3.metric("취소 위험 비율", f"{n_risk / len(result):.1%}")
            unknown = [c for c in meta["categorical_features"]
                       if (~result[c].isin(meta["options"][c])).any()]
            if unknown:
                st.info("학습 때 없던 값이 있는 컬럼: " + ", ".join(unknown) + " (해당 값은 무시하고 예측합니다)")
            st.dataframe(result)
            st.download_button("결과 CSV 내려받기", result.to_csv(index=False).encode("utf-8-sig"),
                               file_name="cancel_predictions.csv", mime="text/csv")

# ---------------------------------------------------------------- 탭 3: 모델 성능
with tab_perf:
    st.subheader("Final Test 성능 (모델·threshold 고정 후 한 번만 평가)")
    tm = meta["test_metrics"]
    perf = pd.DataFrame(tm).T.rename(columns={
        "accuracy": "Accuracy", "precision": "Precision", "recall": "Recall", "f1": "F1"}).round(3)
    st.dataframe(perf)
    st.caption(f"Test {meta['split_sizes']['test']}건, 기준 threshold {meta['threshold']} 고정. "
               "슬라이더는 Test 결과를 바꾸지 않습니다.")

    left, right = st.columns(2)
    with left:
        st.markdown("**Confusion Matrix (Final Test)**")
        cm = meta["confusion"]
        st.dataframe(pd.DataFrame(
            [[cm["tn"], cm["fp"]], [cm["fn"], cm["tp"]]],
            index=["실제 완료", "실제 취소"], columns=["완료 예측", "취소 예측"]))
        st.caption("FP: 정상 주문을 잘못 의심 · FN: 취소를 놓침")
    with right:
        st.markdown("**클래스 분포 (학습에 쓴 주문)**")
        cc = meta["class_counts"]
        st.bar_chart(pd.DataFrame({"건수": [cc["completed"], cc["cancelled"]]},
                                  index=["completed", "cancelled"]))

    st.markdown("**Validation threshold별 Precision / Recall / F1**")
    st.line_chart(curve[["precision", "recall", "f1"]])
    st.caption("Random split 기반 교육용 결과이며, Test 50건(취소 13건)이라 결과가 불안정합니다.")
