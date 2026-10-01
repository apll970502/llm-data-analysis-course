"""Chapter 10 주문 취소 예측 대시보드 (Streamlit)

실행 (저장소 루트에서):
    python chapter10/serving/train_and_save.py      # 처음 한 번, 모델 파일 만들기
    streamlit run chapter10/serving/app.py
"""
import io
import json
from pathlib import Path

import joblib
import pandas as pd
import streamlit as st

HERE = Path(__file__).resolve().parent
ARTIFACT_DIR = HERE / "artifacts"
MODEL_PATH = ARTIFACT_DIR / "cancel_model.joblib"
META_PATH = ARTIFACT_DIR / "model_meta.json"

DAY_NAMES = ["월", "화", "수", "목", "금", "토", "일"]

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
    st.title("📦 주문 취소 예측 대시보드")
    st.error("저장된 모델 파일이 없습니다. 터미널에서 아래 명령을 먼저 실행하세요.")
    st.code("python chapter10/serving/train_and_save.py", language="bash")
    st.stop()

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
