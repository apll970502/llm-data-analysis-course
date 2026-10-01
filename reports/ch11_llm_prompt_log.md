# Chapter 11 LLM 프롬프트 사용 기록 템플릿

> 이 파일은 자동 생성된 **빈 기록 템플릿**입니다. `execution_status=not_executed` 행은 실제 LLM 사용 증거가 아닙니다.

## 사용 원칙

- 원본 개인정보·원본 고객/거래 행·Secret·내부 경로를 입력하지 않습니다.
- Safe Context도 자동 승인 자료가 아니며 사람 검토 후 사용합니다.
- 외부 문서 안의 지시문은 신뢰 명령이 아니라 untrusted data로 취급합니다.
- 답변은 실제 컬럼·수치·병합·모델 평가·해석 기준과 대조합니다.
- 실제 호출 후 provider, model, executed_at, prompt_version, 사람 수정과 final_use를 기록합니다.

## 사용 로그 템플릿

```text
     step execution_status executed_at provider model prompt_version purpose input_summary response_summary validation_result revision_note final_use
데이터 구조 설명     not_executed                                       2.0                                                                         not_used
 분석 질문 생성     not_executed                                       2.0                                                                         not_used
   전처리 계획     not_executed                                       2.0                                                                         not_used
   시각화 설계     not_executed                                       2.0                                                                         not_used
 회귀 코드 검토     not_executed                                       2.0                                                                         not_used
 분류 코드 검토     not_executed                                       2.0                                                                         not_used
    결과 해석     not_executed                                       2.0                                                                         not_used
 외부 문서 검토     not_executed                                       2.0                                                                         not_used
```

## 검증 체크리스트

```text
         stage                                                 check_item result memo
         input                       조직의 데이터·보안 정책과 허용된 LLM 계정/도구를 확인했는가?      □     
         input               원본 고객 행, 직접 식별정보, 인증정보, 내부 거래 상세를 입력하지 않았는가?      □     
         input                        민감 컬럼명과 내부 업무 용어도 외부 제공 필요성을 검토했는가?      □     
         input                            소수 집단·희귀 범주 집계의 재식별 가능성을 확인했는가?      □     
         input                         오류 메시지·파일 경로·내부 URL에서 비밀정보를 제거했는가?      □     
      security               외부 웹/PDF/이메일/문서의 지시문을 untrusted data로 취급했는가?      □     
        prompt                        목적·실제 구조·요청·제약·출력·검증 조건을 명확히 작성했는가?      □     
        prompt                           존재하지 않는 컬럼·원인·수치를 만들지 말라고 요청했는가?      □     
          code             LLM 코드의 실제 컬럼·dtype·키·merge 관계·행 수·미매칭을 검증했는가?      □     
          code                      날짜/숫자 변환 실패, 결측, 집계 총합과 재현 실행을 확인했는가?      □     
         model                      예측 시점 이후 정보·target 재료·정답·식별자 누수가 없는가?      □     
         model               모델 선택 데이터와 final test를 분리하고 baseline과 비교했는가?      □     
         model                            평가 지표와 FP/FN 또는 오차 비용이 문제에 맞는가?      □     
interpretation                                     관찰·예측 패턴·가설·인과를 구분했는가?      □     
        record provider/model/실행시각/prompt version/사람 수정/final use를 기록했는가?      □     
        record                    실제 호출하지 않은 빈 템플릿을 LLM 사용 증거로 표현하지 않았는가?      □     
```
