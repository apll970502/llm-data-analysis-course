[분석 목적]
(예: 완료 주문의 카테고리별 매출 집계)

[데이터 구조]  ← 고객 원본 행은 붙이지 않고 컬럼 이름과 타입만
- order_items: order_item_id, order_id, product_id, quantity, unit_price, line_total
- orders: order_id, customer_id, order_date, order_status

[오류를 재현하는 최소 코드]  ← 전체 코드가 아니라 문제 부분만
(여기에 붙이기. 문자열 안의 URL·키가 없는지 다시 확인)

[오류 메시지]  ← 사용자 이름·절대 경로 제거 후
(여기에 붙이기)

[Evidence]
- 행 수: / 미매칭 수: / 총합 차이:

[공유하지 않는 것]
고객 원본 행, API Key, Token, DB password, 내부 URL, 개인 사용자 경로, 전체 환경변수
