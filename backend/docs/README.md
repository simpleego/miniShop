# 구매하기 기능 실습 가이드

> 대상 : 상품 목록 / 상세 / 검색 API 까지 완성한 상태
> 사용 기술 : FastAPI + PyMySQL + MariaDB (백엔드), React + Vite (프론트)
> 사용 테이블 : `products`, `orders`, `order_items`, `users` (이미 [sql/01_test_schema.sql](../sql/01_test_schema.sql) 에 있음)

---

## 실습 순서

| 순서 | 문서 | 내용 | 구분 |
|---|---|---|---|
| 0 | [00_purchase_overview.md](00_purchase_overview.md) | 구현 범위, API 설계, 처리 흐름 | 필수 |
| 1 | [01_purchase_prepare.md](01_purchase_prepare.md) | 기존 코드 정리(404), 주문 라우터 파일 만들기 | 필수 |
| 2 | [02_purchase_order_api.md](02_purchase_order_api.md) | **단일 상품 구매 API + 트랜잭션** | 필수 |
| 3 | [03_purchase_concurrency.md](03_purchase_concurrency.md) | 동시 구매 문제와 조건부 UPDATE | 권장 |
| 4 | [04_purchase_order_query.md](04_purchase_order_query.md) | 주문 목록 / 주문 상세 조회 (JOIN) | 권장 |
| 5 | [05_purchase_frontend.md](05_purchase_frontend.md) | React 구매 버튼, 수량 선택, 재고 갱신 | 필수 |
| 6 | [06_purchase_advanced.md](06_purchase_advanced.md) | 장바구니 다건 주문, 주문 취소 | 심화 과제 |

> 시간이 부족하면 **0 → 1 → 2 → 5** 만 진행해도 "구매하기" 가 화면까지 동작한다.

---

## 완성 후 파일 구조

```
backend/
├── app/
│   ├── main.py          ← (수정) 주문 라우터 등록, 상세 조회 404 수정
│   ├── product01.py     (기존) 상품 검색
│   └── order01.py       ← (신규) 주문 API
└── docs/                ← 이 실습 문서

frontend/
├── vite.config.js       ← (수정) /orders 프록시 추가
└── src/
    ├── api/orders.js    ← (신규) 주문 API 호출 함수
    ├── components/ProductCard.jsx  ← (수정) 수량 선택 + 구매 버튼
    └── pages/ProductList.jsx       ← (수정) 구매 처리, 재고 갱신
```

---

## 이번 실습에서 꼭 가져가야 할 4가지

1. **가격은 서버가 계산한다** — 클라이언트가 보낸 금액은 믿지 않는다.
2. **트랜잭션** — 주문 저장과 재고 차감은 "전부 성공" 아니면 "전부 취소".
3. **동시성** — 두 사람이 마지막 1개를 동시에 사도 한 명만 성공해야 한다.
4. **상태코드로 실패 이유를 알려준다** — 404(없음), 409(재고 부족), 422(입력 오류), 500(서버 오류).

## 관련 문서

- 장바구니 단계와 주문 단계의 재고 처리 차이 : [frontend/docs/cart_process.md](../../frontend/docs/cart_process.md)
- 상품 검색 SQL : [product_querys.md](../product_querys.md)
