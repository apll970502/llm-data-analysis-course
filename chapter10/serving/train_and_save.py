"""Chapter 10 서빙용 모델 만들기: 모델을 한 번 학습해서 파일로 저장한다.

실행 (저장소 루트에서):  python chapter10/serving/train_and_save.py
만들어지는 파일: chapter10/serving/artifacts/cancel_model.joblib, model_meta.json
"""
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[1]          # chapter10/serving -> 저장소 루트
RAW = PROJECT_ROOT / "data" / "raw"
ARTIFACT_DIR = HERE / "artifacts"
ARTIFACT_DIR.mkdir(exist_ok=True)

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


def main():
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

    joblib.dump(model, ARTIFACT_DIR / "cancel_model.joblib")
    (ARTIFACT_DIR / "model_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print("모델 저장 완료: chapter10/serving/artifacts/cancel_model.joblib")
    print("메타 저장 완료: chapter10/serving/artifacts/model_meta.json")
    print("선택 threshold:", threshold)
    print("Final Test:", meta["test_metrics"]["Logistic Regression"])


if __name__ == "__main__":
    main()
