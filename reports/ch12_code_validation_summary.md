# Chapter 12 검증 요약

- Execution Gate 결정: DO_NOT_EXECUTE
- 사람 최종 판단: BLOCK
- execution_approved: False
- 최종 신뢰 판단: 사용 보류

## 신뢰할 수 있는 범위
- 필수 컬럼 4개 테이블 PASS, PK 결측·중복 없음
- line_total = quantity × unit_price 일치, merge 행 수 유지

## 아직 신뢰할 수 없는 부분
- FK 위반(customer_id 9991·9992, 빠진 상품 번호)
- category·날짜 결측으로 카테고리/월별 총합이 원본과 다름
- 정적 스캔 BLOCKED(네트워크·외부 명령·eval·키 노출·원본 덮어쓰기)
