import pandas as pd
import streamlit as st
from kiwipiepy import Kiwi
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.naive_bayes import MultinomialNB

DATA_PATH = "books_improved.csv"

st.set_page_config(
    page_title="베스트셀러 텍스트 분석 앱 (개선판)",
    layout="wide",
)


# ---------------------------------------------------------
# 형태소 분석 + 단어 필터링 (Chapter 07 실습 3, 4와 동일한 기준)
# ---------------------------------------------------------
@st.cache_resource
def load_kiwi():
    return Kiwi()


TARGET_TAGS = {"NNG", "NNP", "SL"}
STOPWORDS = {"에디션"}


def extract_tokens(text, kiwi):
    tokens = kiwi.tokenize(str(text))
    return " ".join(t.form for t in tokens if t.tag in TARGET_TAGS)


def filter_tokens(text):
    words = str(text).split()
    result = []
    for word in words:
        if len(word) < 2:
            continue
        if word.isdigit():
            continue
        if word in STOPWORDS:
            continue
        result.append(word)
    return " ".join(result)


def clean_title(text, kiwi):
    return filter_tokens(extract_tokens(text, kiwi))


# ---------------------------------------------------------
# 데이터 로딩
# ---------------------------------------------------------
@st.cache_data
def load_data():
    df = pd.read_csv(DATA_PATH, encoding="utf-8-sig")
    required_columns = ["상품명", "분야"]
    missing_columns = [
        col for col in required_columns
        if col not in df.columns
    ]
    if missing_columns:
        raise ValueError(
            f"필수 컬럼이 없습니다: {missing_columns}"
        )
    df["상품명"] = (
        df["상품명"]
        .fillna("")
        .astype(str)
        .str.strip()
    )
    df["분야"] = (
        df["분야"]
        .fillna("미분류")
        .astype(str)
        .str.strip()
    )
    df = df[df["상품명"] != ""].reset_index(drop=True)

    kiwi = load_kiwi()
    df["상품명_토큰"] = df["상품명"].apply(lambda t: extract_tokens(t, kiwi))
    df["상품명_정제"] = df["상품명_토큰"].apply(filter_tokens)
    return df


# ---------------------------------------------------------
# 분류 모델 (개선된 텍스트로 학습)
# ---------------------------------------------------------
@st.cache_resource
def train_classifier():
    df = load_data()
    train_df = df[df["분야"] != "미분류"].copy()
    if train_df["분야"].nunique() < 2:
        raise ValueError(
            "서로 다른 분야가 2개 이상 필요합니다."
        )
    vectorizer = TfidfVectorizer()
    X = vectorizer.fit_transform(train_df["상품명_정제"])
    y = train_df["분야"]
    model = MultinomialNB()
    model.fit(X, y)
    return vectorizer, model


# ---------------------------------------------------------
# 추천: 같은 분야 후보 + 개선된 텍스트 + similarity > 0
# ---------------------------------------------------------
def recommend_books(df, selected_index, top_n=5):
    selected_category = df.loc[selected_index, "분야"]
    candidate_df = df[df["분야"] == selected_category].copy()

    vectorizer = TfidfVectorizer()
    matrix = vectorizer.fit_transform(candidate_df["상품명_정제"])

    local_index = candidate_df.index.get_loc(selected_index)
    similarities = cosine_similarity(
        matrix[local_index], matrix
    ).ravel()
    candidate_df["similarity"] = similarities

    candidate_df = candidate_df[candidate_df.index != selected_index]
    candidate_df = candidate_df[candidate_df["similarity"] > 0]
    candidate_df = candidate_df.sort_values(
        "similarity", ascending=False
    ).head(top_n)

    display_columns = [
        col
        for col in ["상품명", "저자", "출판사", "분야"]
        if col in df.columns
    ]
    result = candidate_df[display_columns].copy()
    result["similarity"] = candidate_df["similarity"].round(4)
    return result.reset_index(drop=True)


# ---------------------------------------------------------
# 데이터 / 모델 준비
# ---------------------------------------------------------
try:
    df = load_data()
    kiwi = load_kiwi()
    classifier_vectorizer, classifier_model = train_classifier()
except (FileNotFoundError, ValueError) as error:
    st.error(str(error))
    st.stop()

st.title("교보문고 베스트셀러 텍스트 분석 앱 (개선판)")
st.write(
    "형태소 분석과 단어 필터링을 적용한 도서 분야 예측과 "
    "유사 도서 추천 기능을 실습합니다."
)

# 1. 도서 분야 예측
st.header("1. 도서 분야 예측")
user_title = st.text_input(
    "도서 제목을 입력하세요",
    placeholder="예: 처음 배우는 파이썬 데이터 분석",
)
if st.button("분야 예측"):
    clean = user_title.strip()
    if not clean:
        st.warning("도서 제목을 입력해 주세요.")
    else:
        # 형태소 분석 + 단어 필터링을 새 제목에도 동일하게 적용
        processed_title = clean_title(clean, kiwi)
        # 새 제목에는 fit_transform이 아니라 transform만 사용한다
        title_vector = classifier_vectorizer.transform([processed_title])
        predicted_category = classifier_model.predict(title_vector)[0]
        st.success(f"예상 분야: {predicted_category}")
        st.caption(f"전처리 결과: '{clean}' → '{processed_title}'")

st.divider()

# 2. 비슷한 도서 추천
st.header("2. 비슷한 도서 추천")


def format_book(index):
    title = df.loc[index, "상품명"]
    field = df.loc[index, "분야"]
    return f"{title} ({field})"


selected_index = st.selectbox(
    "기준 도서를 선택하세요",
    options=df.index.tolist(),
    format_func=format_book,
)
if st.button("비슷한 도서 5권 추천"):
    recommendations = recommend_books(df, selected_index, top_n=5)
    if recommendations.empty:
        st.info("현재 기준으로 유사도가 있는 추천 도서를 찾지 못했습니다.")
    else:
        st.dataframe(
            recommendations,
            width="stretch",
            hide_index=True,
        )

st.divider()
st.caption(
    "분류 결과는 형태소 분석·필터링을 거친 제목 텍스트 패턴을 이용한 예측이며 "
    "실제 서점의 공식 분류와 다를 수 있습니다."
)
st.caption(
    "추천은 같은 분야 안에서 유사도가 0보다 큰 도서만 보여줍니다. "
    "조건을 만족하는 도서가 없으면 추천 없음으로 안내합니다."
)
