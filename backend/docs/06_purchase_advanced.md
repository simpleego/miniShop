# 6. 심화 과제 — 장바구니 주문, 주문 취소

> 0 ~ 5단계를 마친 사람을 위한 과제다. **정답 코드 없이 요구사항과 힌트만** 제공한다.
> 지금까지 배운 트랜잭션, 조건부 UPDATE, 상태코드를 스스로 조합해 본다.

---

## 과제 A. 장바구니 다건 주문

여러 상품을 한 번에 주문한다. 주문 1건(`orders`) 아래에 주문 상품(`order_items`)이 여러 개 생긴다.

### 요구사항

```http
POST /orders/cart
Content-Type: application/json

{
  "items": [
    { "product_id": 1, "quantity": 2 },
    { "product_id": 4, "quantity": 1 }
  ]
}
```

```json
// 201 Created
{
  "order_id": 20,
  "total_price": 4000,
  "status": "PAID",
  "items": [
    { "product_id": 1, "product_name": "콜라", "quantity": 2, "unit_price": 1500, "subtotal": 3000 },
    { "product_id": 4, "product_name": "생수", "quantity": 1, "unit_price": 1000, "subtotal": 1000 }
  ]
}
```

| 규칙 | 결과 |
|---|---|
| `items` 가 비어 있음 / 10종 초과 | 422 |
| 같은 `product_id` 가 두 번 나옴 | 422 (또는 수량을 합쳐서 처리 — 둘 중 하나를 정해서 구현) |
| 상품 중 **하나라도** 없음 | 404, **아무것도 주문되지 않아야 한다** |
| 상품 중 **하나라도** 재고 부족 | 409, **다른 상품의 재고도 줄면 안 된다** |

### 힌트

1. Pydantic 모델 안에 모델 목록을 넣을 수 있다.
   ```python
   class CartItem(BaseModel):
       product_id: int = Field(ge=1)
       quantity: int = Field(ge=1, le=10)

   class CartOrderIn(BaseModel):
       items: list[CartItem] = Field(min_length=1, max_length=10)
   ```
2. `orders` 의 `total_price` 는 모든 상품을 처리한 **뒤에** 알 수 있다.
   - 방법 ① 먼저 `total_price = 0` 으로 INSERT → 마지막에 UPDATE
   - 방법 ② 모든 상품을 먼저 조회/차감하며 합계 계산 → 그다음 `orders` INSERT
3. 반복문 안에서 `raise HTTPException(409)` 를 해도 `except` 에서 `rollback` 하므로 **앞에서 차감한 재고까지 모두 취소**된다. 이것이 트랜잭션의 힘이다.
4. (더 생각해 보기) 두 사람이 `[콜라, 생수]`, `[생수, 콜라]` 순서로 동시에 주문하면 서로 상대가 잠근 행을 기다리는 **교착 상태(Deadlock)** 가 생길 수 있다. `product_id` 순서로 **정렬한 뒤** 처리하면 예방할 수 있다.

### 확인 시나리오

```sql
-- 준비 : 콜라 재고 10, 생수 재고 0
UPDATE products SET stock = 10 WHERE id = 1;
UPDATE products SET stock = 0  WHERE id = 4;
```

`[콜라 2, 생수 1]` 주문 → **409**, 그리고 콜라 재고가 **10 그대로**인지 확인한다.

---

## 과제 B. 주문 취소

```http
POST /orders/{order_id}/cancel
```

> 상태를 바꾸는 동작이라 `DELETE` 가 아니라 `POST` 를 쓴다. 주문 기록은 지우지 않고 `status` 만 `CANCELLED` 로 바꾼다.
> (기록을 지우면 매출 통계, 고객 문의 대응을 할 수 없다)

### 요구사항

| 상황 | 결과 |
|---|---|
| 내 주문이고 `PAID` 상태 | 200, `status` → `CANCELLED`, **재고 복구** |
| 주문이 없거나 내 주문이 아님 | 404 |
| 이미 `CANCELLED` | 409 `이미 취소된 주문입니다.` |

### 힌트

1. 상태 변경도 **조건부 UPDATE** 로 하면 "취소 버튼 두 번 클릭" 에도 재고가 두 번 복구되지 않는다.
   ```sql
   UPDATE orders SET status = 'CANCELLED'
   WHERE id = %s AND user_id = %s AND status = 'PAID'
   ```
   `rowcount == 0` 이면 → 주문이 없는 건지(404) 이미 취소된 건지(409) 한 번 더 조회해서 구분한다.
2. 재고 복구는 주문 상품 수만큼 반복한다.
   ```sql
   SELECT product_id, quantity FROM order_items WHERE order_id = %s
   UPDATE products SET stock = stock + %s WHERE id = %s
   ```
3. 상태 변경과 재고 복구는 **하나의 트랜잭션**이어야 한다.
4. 테스트 DB 의 검색 API(`/search/products?sort=popular`)는 `CANCELLED` 주문을 판매량에서 뺀다.
   주문을 취소한 뒤 인기순 순위가 바뀌는지 확인해 보자.

### 확인 시나리오

1. 콜라 3개 구매 → 재고 확인 (예 : 10 → 7)
2. 그 주문 취소 → 200, 재고 7 → 10
3. 같은 주문 다시 취소 → 409, 재고 **10 그대로**
4. 3-2 의 동시성 스크립트를 응용해서 **같은 주문 취소를 10번 동시에** 보낸다 → 200 이 1개, 409 가 9개

---

## 과제 C. 프론트 주문 내역 화면 (선택)

- `GET /orders` 로 "내 주문 내역" 목록 화면을 만든다. (`콜라 외 1건 · 4,000원 · 결제완료`)
- 항목을 누르면 `GET /orders/{id}` 로 상세를 보여 준다.
- 상세 화면에 `PAID` 상태일 때만 [주문 취소] 버튼을 보여 준다.

---

## 다음에 배울 것

이 실습에서 일부러 단순하게 처리한 부분이다. 실제 서비스에서는 이렇게 바뀐다.

| 지금 | 실제 서비스 |
|---|---|
| `TEMP_USER_ID = 1` 고정 | 로그인(JWT, 세션)으로 얻은 사용자 id |
| 주문 = 바로 `PAID` | `PENDING`(결제 대기) → 결제사(PG) 승인 → `PAID` |
| 요청마다 DB 연결 생성 | 커넥션 풀(Connection Pool) |
| 버튼 비활성화로 중복 클릭 방지 | 서버에서도 막기 (멱등성 키 Idempotency-Key) |
