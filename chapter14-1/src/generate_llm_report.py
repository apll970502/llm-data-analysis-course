import json
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]
REPORTS_DIR = BASE_DIR / "reports"

load_dotenv(BASE_DIR / ".env")


def build_prompt(summary):
    return f"""
당신은 데이터 분석 보고서 작성 보조자입니다.
아래 값은 Python에서 계산하고 사람이 기본 검증을 완료한 결과입니다.

{json.dumps(summary, ensure_ascii=False, indent=2)}

데이터 설명:
- NAVER 값은 조회 기간 내 최대 검색량을 100으로 둔 상대지수이며, 전국 단위입니다.
- 진행 중인 달은 불완전하므로 NAVER 값은 직전 완전한 달 기준입니다.
- 관광 데이터는 서울특별시 25개 자치구만 포함하며, 전국 지역 비교가 아닙니다.
- 관광 체류 강도는 타권역 방문자 비중, 숙박 비중, 숙박일수별 방문자 수를 종합한 지수이며 숙박만을 뜻하지 않습니다.
- 관광 소비 강도는 외지인 소비액, 소비 비중, 방문량 대비 소비액을 종합한 지수입니다.
- 두 관광 지수는 100을 넘을 수 있고 항목 간 단위가 다르므로 서로 직접 비교하지 마세요.
- change_vs_prev는 전월 대비 지수 값의 차이(포인트)이며 백분율(%)이 아닙니다. %를 붙이지 마세요.
- change_vs_prev가 비어 있는 항목은 전월 대비 값이 계산되지 않은 것입니다.

다음 형식으로 한국어 보고서를 작성하세요.

1. 분석 기준일
2. 검색 관심도 주요 변화
3. 지역 관광 수요 주요 특징
4. 관찰 가능한 패턴
5. 현재 데이터로 말할 수 없는 것
6. 추가 확인이 필요한 사항

중요:
- 검색 관심도는 실제 검색 건수가 아닌 상대지수라고 명시하세요.
- 상관관계나 동시 변화만으로 인과관계를 단정하지 마세요.
- 입력에 없는 사실을 새로 만들지 마세요.
"""


def call_gemini(prompt, api_key, model):
    from google import genai

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(model=model, contents=prompt)
    return response.text


def call_openai(prompt, api_key, model):
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    response = client.responses.create(model=model, input=prompt)
    return response.output_text


def call_claude(prompt, api_key, model):
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=model,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


PROVIDERS = {
    "gemini": call_gemini,
    "openai": call_openai,
    "claude": call_claude,
}


def generate_report(summary):
    provider = os.getenv("LLM_PROVIDER", "").lower()
    api_key = os.getenv("LLM_API_KEY")
    model = os.getenv("LLM_MODEL")

    if provider not in PROVIDERS:
        raise RuntimeError("LLM_PROVIDER는 gemini / openai / claude 중 하나여야 합니다.")
    if not api_key or not model:
        raise RuntimeError("LLM_API_KEY 또는 LLM_MODEL이 설정되지 않았습니다.")

    text = PROVIDERS[provider](build_prompt(summary), api_key, model)
    if not text or not text.strip():
        raise RuntimeError("LLM 응답이 비어 있습니다.")

    output_path = REPORTS_DIR / "llm_summary.md"
    output_path.write_text(text, encoding="utf-8")
    return text


if __name__ == "__main__":
    df = pd.read_csv(REPORTS_DIR / "analysis_summary.csv")
    if df.empty:
        raise RuntimeError("analysis_summary.csv가 비어 있습니다.")
    summary = json.loads(df.to_json(orient="records", force_ascii=False))
    generate_report(summary)
    print("[PASS] LLM report:", REPORTS_DIR / "llm_summary.md")
