# 4. 주문 목록 / 주문 상세 조회

> 목표 : `GET /orders`, `GET /orders/{order_id}` 를 만든다.
> 핵심 : **JOIN**, 집계 함수, 응답 데이터 모양 만들기(주문 + 주문 상품 목록)

---

## 4-1. 주문 목록 : `GET /orders`

### SQL 먼저

주문 목록 화면에는 "주문 번호, 날짜, 대표 상품 이름, 상품 종류 수, 총액, 상태" 를 보여 준다.

```sql
SELECT o.id          AS order_id,
       o.total_price,
       o.status,
       o.created_at,
       MIN(p.name)   AS first_product_name,   -- 대표 상품 이름
       COUNT(oi.id)  AS item_count            -- 주문에 들어간 상품 종류 수
FROM orders o
JOIN order_items oi ON oi.order_id = o.id
JOIN products    p  ON p.id = oi.product_id
WHERE o.user_id = 1
GROUP BY o.id, o.total_price, o.status, o.created_at
ORDER BY o.created_at DESC, o.id DESC
LIMIT 20;
```

| 포인트 | 설명 |
|---|---|
| `JOIN` 2번 | 주문 → 주문상품 → 상품 순서로 연결해서 상품 이름을 가져온다 |
| `GROUP BY o.id` | 주문 1건에 상품이 여러 개여도 **한 줄**로 만든다 |
| `MIN(p.name)` | 그룹 안에서 이름 하나를 고른다 (가나다순 첫 번째) |
| `WHERE o.user_id = 1` | **내 주문만** 보여 준다. 다른 사람 주문이 보이면 안 된다 |

> 화면에 "콜라 외 2건" 처럼 보여 주려면 `first_product_name` 과 `item_count - 1` 을 쓰면 된다.

### 코드 (`app/order01.py`)

```python
# -----------------------------------------------------------------------------
# 내 주문 목록 : GET /orders
# -----------------------------------------------------------------------------
@router.get("")
def list_orders():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT o.id AS order_id, o.total_price, o.status, o.created_at,
                       MIN(p.name) AS first_product_name,
                       COUNT(oi.id) AS item_count
                FROM orders o
                JOIN order_items oi ON oi.order_id = o.id
                JOIN products    p  ON p.id = oi.product_id
                WHERE o.user_id = %s
                GROUP BY o.id, o.total_price, o.status, o.created_at
                ORDER BY o.created_at DESC, o.id DESC
                LIMIT 20
                """,
                (TEMP_USER_ID,),
            )
            return cursor.fetchall()
    except Exception as e:
        logger.error("주문 목록 조회 실패: %s", e)
        raise HTTPException(status_code=500, detail="주문 목록 조회 에러")
    finally:
        conn.close()
```

---

## 4-2. 주문 상세 : `GET /orders/{order_id}`

### 응답 모양

주문 정보 1개 안에 주문 상품 **목록**이 들어 있는 모양으로 만든다.

```json
{
  "order_id": 17,
  "total_price": 4400,
  "status": "PAID",
  "created_at": "2026-11-13T14:20:00",
  "items": [
    { "product_id": 1, "product_name": "콜라",   "quantity": 2, "unit_price": 1500, "subtotal": 3000 },
    { "product_id": 2, "product_name": "사이다", "quantity": 1, "unit_price": 1400, "subtotal": 1400 }
  ]
}
```

SQL 한 번으로 이 모양을 만들기는 어려우므로 **SQL 2번**으로 나눈다.

1. 주문 1건 조회 → 없으면 404
2. 그 주문의 상품 목록 조회 → `items` 에 넣기

### 코드

```python
# -----------------------------------------------------------------------------
# 주문 상세 : GET /orders/{order_id}
# -----------------------------------------------------------------------------
@router.get("/{order_id}")
def get_order(order_id: int):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # ① 주문 1건 : 내 주문이 아니면 없는 것처럼 404
            cursor.execute(
                """
                SELECT id AS order_id, total_price, status, created_at
                FROM orders
                WHERE id = %s AND user_id = %s
                """,
                (order_id, TEMP_USER_ID),
            )
            order = cursor.fetchone()

            if order is None:
                raise HTTPException(status_code=404, detail="주문을 찾을 수 없습니다.")

            # ② 주문 상품 목록 : 가격은 products.price 가 아니라 구매 당시 가격(unit_price)
            cursor.execute(
                """
                SELECT oi.product_id, p.name AS product_name,
                       oi.quantity, oi.unit_price,
                       oi.quantity * oi.unit_price AS subtotal
                FROM order_items oi
                JOIN products p ON p.id = oi.product_id
                WHERE oi.order_id = %s
                ORDER BY oi.id
                """,
                (order_id,),
            )
            order["items"] = cursor.fetchall()
            return order

    except HTTPException:
        raise
    except Exception as e:
        logger.error("주문 상세 조회 실패 order_id=%s: %s", order_id, e)
        raise HTTPException(status_code=500, detail="주문 상세 조회 에러")
    finally:
        conn.close()
```

### 코드 읽기 포인트

| 코드 | 설명 |
|---|---|
| `AND user_id = %s` | 남의 주문 번호를 넣어도 볼 수 없게 한다. **403 이 아니라 404** 를 주는 이유 : 그 번호의 주문이 "있다는 사실" 도 알려 주지 않기 위해서 |
| `oi.unit_price` | 상품 가격이 바뀌어도 주문 내역은 그대로 |
| `order["items"] = ...` | DictCursor 결과는 딕셔너리라 키를 추가할 수 있다 |
| `except HTTPException: raise` | 404 가 500 으로 바뀌지 않게 한다 (2단계와 같은 이유) |

---

## ✅ 4단계 확인

| # | 요청 | 기대 결과 |
|---|---|---|
| 1 | `POST /orders` 로 2~3번 구매 후 `GET /orders` | 방금 산 주문이 **맨 위**에 나온다 |
| 2 | `GET /orders/{방금 주문 번호}` | 200 + `items` 에 상품 1개 |
| 3 | `GET /orders/9999` | 404 |
| 4 | 다른 회원 주문 번호 (시드 데이터의 1번 주문, user_id=2) | **404** |
| 5 | `UPDATE products SET price = 9999 WHERE id = 1;` 후 상세 조회 | `unit_price` 는 **구매 당시 가격** 그대로 |

> 5번 확인 후 가격을 원래대로 돌려 놓는다.

## 생각해 볼 문제

1. 주문 목록에서 `JOIN products` 대신 `LEFT JOIN` 을 써야 하는 경우는 언제일까?
2. 주문 상세를 SQL 2번이 아니라 1번(JOIN)으로 가져오면, 파이썬에서 어떤 처리가 더 필요할까?

다음 단계 : [05_purchase_frontend.md](05_purchase_frontend.md)
