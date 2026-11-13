# 2. 단일 상품 구매 API + 트랜잭션

> 목표 : `POST /orders` 를 완성한다.
> 핵심 : **서버에서 가격 계산**, **트랜잭션(commit / rollback)**, **상태코드 구분**

---

## 2-1. 먼저 SQL 로 연습하기

코드를 쓰기 전에 DB 도구(HeidiSQL, DBeaver 등)에서 구매 과정을 직접 실행해 본다.
콜라(id=1) 2개를 산다고 하자.

```sql
START TRANSACTION;                                  -- 트랜잭션 시작

-- ① 상품 조회 : 판매중인지, 가격과 재고는 얼마인지
SELECT id, name, price, stock FROM products WHERE id = 1 AND is_active = 1;

-- ② 주문 1건 저장 (총액 = 가격 × 수량, 직접 계산해서 넣는다)
INSERT INTO orders (user_id, total_price, status) VALUES (1, 3000, 'PAID');
SELECT LAST_INSERT_ID();                            -- 방금 만든 주문 번호

-- ③ 주문 상품 저장 (order_id 는 위에서 얻은 번호)
INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (17, 1, 2, 1500);

-- ④ 재고 차감
UPDATE products SET stock = stock - 2 WHERE id = 1;

ROLLBACK;                                           -- 연습이니까 전부 취소
```

`ROLLBACK` 후에 다시 조회해 보면 주문도, 재고 변화도 **전부 사라진 것**을 확인할 수 있다.

```sql
SELECT stock FROM products WHERE id = 1;            -- 재고가 원래대로
SELECT * FROM orders ORDER BY id DESC LIMIT 1;      -- 연습 주문이 없다
```

> 🤔 생각해 보기 : ②, ③ 은 성공했는데 ④ 에서 오류가 나면? 트랜잭션이 없으면
> **돈은 받았는데(주문 저장) 재고는 그대로**인 상태가 된다. 그래서 묶어야 한다.

---

## 2-2. 구매 API 구현 (`app/order01.py`)

1단계에서 만든 `create_order` 를 아래처럼 바꾼다.

```python
@router.post("", status_code=201)
def create_order(item: OrderIn):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # -----------------------------------------------------------------
            # ① 상품 조회 : 판매중(is_active = 1)인 상품만
            # -----------------------------------------------------------------
            cursor.execute(
                """
                SELECT id, name, price, stock
                FROM products
                WHERE id = %s AND is_active = 1
                """,
                (item.product_id,),
            )
            product = cursor.fetchone()

            if product is None:
                raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다.")

            # -----------------------------------------------------------------
            # ② 재고 확인
            #   ⚠️ 이 방식은 동시에 주문이 들어오면 문제가 생긴다 → 3단계에서 고친다
            # -----------------------------------------------------------------
            if product["stock"] < item.quantity:
                raise HTTPException(
                    status_code=409,
                    detail=f"재고가 부족합니다. (남은 재고: {product['stock']}개)",
                )

            # -----------------------------------------------------------------
            # ③ 금액 계산 : 반드시 DB 의 가격으로 계산한다
            # -----------------------------------------------------------------
            unit_price = product["price"]
            total_price = unit_price * item.quantity

            # -----------------------------------------------------------------
            # ④ 주문 1건 저장
            #   cursor.lastrowid : 방금 INSERT 한 행의 AUTO_INCREMENT 값 (= 새 주문 번호)
            # -----------------------------------------------------------------
            cursor.execute(
                "INSERT INTO orders (user_id, total_price, status) VALUES (%s, %s, 'PAID')",
                (TEMP_USER_ID, total_price),
            )
            order_id = cursor.lastrowid

            # -----------------------------------------------------------------
            # ⑤ 주문 상품 저장 : 구매 당시 가격(unit_price)을 함께 저장한다
            # -----------------------------------------------------------------
            cursor.execute(
                """
                INSERT INTO order_items (order_id, product_id, quantity, unit_price)
                VALUES (%s, %s, %s, %s)
                """,
                (order_id, product["id"], item.quantity, unit_price),
            )

            # -----------------------------------------------------------------
            # ⑥ 재고 차감
            # -----------------------------------------------------------------
            cursor.execute(
                "UPDATE products SET stock = stock - %s WHERE id = %s",
                (item.quantity, product["id"]),
            )

        # ④ ~ ⑥ 이 모두 성공했을 때만 DB 에 확정 저장
        conn.commit()

    except HTTPException:
        # 404, 409 처럼 우리가 일부러 낸 오류 → 취소하고 그대로 프론트에 전달
        conn.rollback()
        raise
    except Exception as e:
        # 예상하지 못한 오류 (DB 연결 끊김, SQL 오타 등) → 취소하고 500
        conn.rollback()
        logger.error("주문 처리 실패 %s: %s", item, e)
        raise HTTPException(status_code=500, detail="주문 처리 중 오류가 발생했습니다.")
    finally:
        # 성공이든 실패든 연결은 반드시 닫는다
        conn.close()

    logger.info("주문 완료 order_id=%s, 상품=%s, 수량=%s", order_id, product["name"], item.quantity)

    return {
        "order_id": order_id,
        "product_id": product["id"],
        "product_name": product["name"],
        "quantity": item.quantity,
        "unit_price": unit_price,
        "total_price": total_price,
        "status": "PAID",
    }
```

### 코드 읽기 포인트

| 코드 | 설명 |
|---|---|
| `try / except / finally` | 성공 → `commit`, 실패 → `rollback`, 항상 → `close` |
| `except HTTPException: ... raise` | 404/409 를 500 으로 바꾸지 않고 그대로 다시 던진다. 이 줄이 없으면 아래 `except Exception` 이 잡아서 **모든 실패가 500** 이 된다 |
| `cursor.lastrowid` | SQL 의 `LAST_INSERT_ID()` 와 같다 |
| `unit_price = product["price"]` | 요청 값이 아닌 **DB 값**으로 계산 |
| `return` 이 `try` 밖에 있음 | commit 이 끝난 뒤에만 성공 응답을 보낸다 |

---

## 2-3. 실습 : rollback 눈으로 확인하기

트랜잭션이 정말 동작하는지 **일부러 오류를 내서** 확인해 본다.
⑤ 주문 상품 저장과 ⑥ 재고 차감 사이에 아래 한 줄을 잠깐 넣는다.

```python
            raise Exception("일부러 낸 오류 (rollback 테스트)")
```

1. 구매 요청 전에 상태를 기록한다.
   ```sql
   SELECT stock FROM products WHERE id = 1;
   SELECT MAX(id) FROM orders;
   ```
2. `POST /orders {"product_id": 1, "quantity": 1}` 실행 → **500** 이 와야 한다.
3. 다시 조회한다. 재고도, 주문 번호도 **그대로**여야 한다.
4. `conn.rollback()` 을 주석 처리하고 다시 해 본다. 어떻게 되는가?

> 💡 4번 결과 : rollback 을 안 해도 commit 을 하지 않았으므로 `conn.close()` 때 저장되지 않는다.
> 하지만 **AUTO_INCREMENT 번호는 하나 소모**되어 다음 주문 번호가 건너뛴다. (정상 동작이다)
> rollback 은 "확정하지 않음" 을 명확하게 드러내므로 항상 써 주는 것이 좋다.

확인이 끝나면 **오류를 내는 줄은 반드시 지운다.**

---

## ✅ 2단계 확인

`http://localhost:8000/docs` 의 `POST /orders` 로 테스트한다. 테스트 DB(`test_vmshop`) 기준이다.

| # | 요청 본문 | 기대 결과 | 확인할 것 |
|---|---|---|---|
| 1 | `{"product_id": 1, "quantity": 2}` | 201 | `total_price` = 가격 × 2, DB 재고가 2 줄었는지 |
| 2 | 재고보다 많은 수량 | 409 | `detail` 에 남은 재고 표시, 재고 변화 없음 |
| 3 | 품절 상품(stock = 0) 1개 | 409 | |
| 4 | `{"product_id": 9999, "quantity": 1}` | 404 | |
| 5 | 판매중지 상품(is_active = 0) | 404 | 판매중지는 "없는 상품" 으로 취급 |
| 6 | `{"product_id": 1, "quantity": 0}` | 422 | |

품절, 판매중지 상품 id 는 아래 SQL 로 찾는다.

```sql
SELECT id, name, stock, is_active FROM products WHERE stock = 0 OR is_active = 0;
```

주문이 제대로 저장되었는지 확인한다.

```sql
SELECT o.id, o.user_id, o.total_price, o.status, o.created_at,
       oi.product_id, oi.quantity, oi.unit_price
FROM orders o
JOIN order_items oi ON oi.order_id = o.id
ORDER BY o.id DESC
LIMIT 5;
```

> ⚠️ 테스트하면 실제로 재고가 줄어든다. 처음 상태로 돌리려면
> `sql/01_test_schema.sql` → `sql/02_test_seed.sql` 을 다시 실행한다.

---

## 생각해 볼 문제

1. ② 재고 확인을 지우고 재고보다 많이 사면 어떻게 될까? (힌트 : `CHECK (stock >= 0)`)
2. 응답에 `total_price` 를 돌려주는 이유는? 프론트가 직접 계산하면 안 될까?
3. `quantity` 최대값을 10 으로 제한한 이유는? 제한이 없으면 어떤 문제가 생길 수 있을까?

다음 단계 : [03_purchase_concurrency.md](03_purchase_concurrency.md)
