# 3. 동시 구매 문제와 조건부 UPDATE

> 목표 : 두 사람이 **마지막 1개를 동시에** 사도 한 명만 성공하게 만든다.
> 이론 설명은 [frontend/docs/cart_process.md](../../frontend/docs/cart_process.md) 2~3장에 자세히 있다. 여기서는 **직접 문제를 재현하고 고친다.**

---

## 3-1. 2단계 코드의 문제

2단계 코드는 **읽고 → 확인하고 → 쓰는** 방식이다.

```python
SELECT stock ...                  # ① 읽기
if product["stock"] < quantity:   # ② 확인 (파이썬에서)
UPDATE products SET stock = stock - %s ...   # ③ 쓰기
```

① 과 ③ 사이에 다른 요청이 끼어들 수 있다. 재고 1개인 상품을 A, B 가 동시에 사면

```
시간   요청 A                         요청 B
 1    SELECT stock → 1
 2                                    SELECT stock → 1
 3    1 >= 1 OK
 4                                    1 >= 1 OK
 5    INSERT 주문, UPDATE stock → 0
 6                                    INSERT 주문, UPDATE stock → -1 ❌
```

이 프로젝트는 `CHECK (stock >= 0)` 덕분에 6번에서 DB 오류가 나서 B 는 **500** 을 받는다.
초과 판매는 막았지만, B 에게 "재고 부족(409)" 이 아니라 "서버 오류(500)" 가 간다. 올바른 응답이 아니다.

---

## 3-2. 문제 재현하기

사람 손으로는 동시에 누르기 어려우므로 스크립트로 요청 10개를 **동시에** 보낸다.
`backend` 폴더에 `test_concurrency.py` 를 만든다. (실습 후 지워도 된다)

```python
# 동시 구매 테스트 : 같은 상품을 10명이 동시에 1개씩 구매
#   실행 : python test_concurrency.py
import json
import threading
import urllib.request
from collections import Counter

URL = "http://localhost:8000/orders"
PRODUCT_ID = 1      # 테스트할 상품
USERS = 10          # 동시에 구매할 사람 수

results = []

def buy():
    body = json.dumps({"product_id": PRODUCT_ID, "quantity": 1}).encode()
    req = urllib.request.Request(URL, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as res:
            results.append(res.status)
    except urllib.error.HTTPError as e:
        results.append(e.code)

threads = [threading.Thread(target=buy) for _ in range(USERS)]
for t in threads:
    t.start()
for t in threads:
    t.join()

print("응답 코드별 개수 :", dict(Counter(results)))
```

### 실험 순서

1. 상품 재고를 **3개**로 맞춘다.
   ```sql
   UPDATE products SET stock = 3 WHERE id = 1;
   ```
2. 서버를 **worker 여러 개**로 실행한다. (`--reload` 는 worker 가 1개라 재현이 잘 안 된다)
   ```bash
   uvicorn app.main:app --workers 4
   ```
3. `python test_concurrency.py` 를 실행한다.
4. 결과와 DB 를 확인한다.
   ```sql
   SELECT stock FROM products WHERE id = 1;
   SELECT COUNT(*) FROM order_items WHERE product_id = 1
     AND order_id > (SELECT MAX(id) - 10 FROM orders);
   ```

### 기대하는 결과 vs 2단계 코드

| | 기대 | 2단계 코드 (실행할 때마다 다를 수 있음) |
|---|---|---|
| 201 | 3개 | 3개 |
| 409 | 7개 | 몇 개는 **500** 으로 나온다 |

> 컴퓨터가 빨라서 한 번에 재현이 안 될 수 있다. 여러 번 실행하거나 `USERS` 를 50 으로 늘려 본다.
> 확인 → 재고 차감 사이에 `time.sleep(0.1)` 을 잠깐 넣으면 확실하게 재현된다.

---

## 3-3. 해결 : 조건부 UPDATE

**확인과 차감을 SQL 한 문장**으로 합친다. DB 는 같은 행을 바꾸는 UPDATE 를 한 번에 하나씩 처리하므로 끼어들 틈이 없다.

```sql
UPDATE products
SET stock = stock - %s
WHERE id = %s
  AND is_active = 1
  AND stock >= %s          -- 재고가 충분할 때만 차감
```

- 재고가 충분하면 → 1행이 바뀐다 (`rowcount == 1`)
- 재고가 부족하면 → 조건에 안 맞아 0행이 바뀐다 (`rowcount == 0`) → **409**

### 순서도 바꾼다

재고 차감을 **가장 먼저** 한다. 재고를 못 잡았으면 주문을 INSERT 할 필요가 없기 때문이다.

```
2단계 : 상품 조회 → 재고 확인 → 주문 저장 → 주문상품 저장 → 재고 차감
3단계 : 상품 조회 → [재고 차감 (조건부)] → 주문 저장 → 주문상품 저장
                     └ rowcount == 0 이면 409
```

---

## 3-4. 코드 수정 (`app/order01.py`)

2단계의 **② 재고 확인**과 **⑥ 재고 차감**을 지우고, ① 상품 조회 바로 아래에 다음을 넣는다.

```python
            # -----------------------------------------------------------------
            # ② 재고 차감 (조건부 UPDATE)
            #   확인과 차감을 SQL 한 문장으로 처리 → 동시에 주문이 와도 초과 판매되지 않는다
            #   cursor.rowcount : 이 SQL 로 바뀐 행 수
            # -----------------------------------------------------------------
            cursor.execute(
                """
                UPDATE products
                SET stock = stock - %s
                WHERE id = %s AND is_active = 1 AND stock >= %s
                """,
                (item.quantity, product["id"], item.quantity),
            )

            if cursor.rowcount == 0:
                # 남은 재고를 알려 주기 위해 다시 조회한다
                cursor.execute("SELECT stock FROM products WHERE id = %s", (product["id"],))
                remain = cursor.fetchone()["stock"]
                raise HTTPException(
                    status_code=409,
                    detail=f"재고가 부족합니다. (남은 재고: {remain}개)",
                )
```

> ① 의 SELECT 는 그대로 둔다. **404 판단**과 **가격 조회**에 필요하기 때문이다.
> 재고 판단은 이제 SELECT 결과(`product["stock"]`)가 아니라 UPDATE 결과(`rowcount`)로 한다.

### 왜 이걸로 충분할까?

UPDATE 가 실행되면 그 행에는 **잠금(lock)** 이 걸린다. 같은 행을 UPDATE 하려는 다른 요청은
앞의 트랜잭션이 `commit` 또는 `rollback` 할 때까지 **기다린다.** 기다린 뒤에는 바뀐 재고를 보고 조건을 다시 검사한다.

```
시간   요청 A                                  요청 B
 1    UPDATE ... stock >= 1  → 1행 (잠금)
 2                                             UPDATE ... stock >= 1  → 대기 ⏳
 3    INSERT 주문, COMMIT  (잠금 해제)
 4                                             stock = 0 이라 조건 불일치 → 0행 → 409 ✅
```

---

## ✅ 3단계 확인

3-2 실험을 다시 실행한다. (재고 3개, worker 4개, 동시 요청 10개)

| 확인 항목 | 기대 결과 |
|---|---|
| 응답 코드 | `{201: 3, 409: 7}` — **500 이 없어야 한다** |
| DB 재고 | 0 |
| 새로 생긴 주문 수 | 3건 |

2단계 확인 표(201 / 404 / 409 / 422)도 다시 한 번 실행해서 기존 기능이 그대로인지 확인한다.

---

## 참고 : 다른 방법 `SELECT ... FOR UPDATE`

```sql
SELECT stock FROM products WHERE id = %s FOR UPDATE;   -- 읽을 때부터 잠근다
-- 파이썬에서 확인 후
UPDATE products SET stock = stock - %s WHERE id = %s;
```

| | 조건부 UPDATE | SELECT ... FOR UPDATE |
|---|---|---|
| 코드 | SQL 한 줄 | 잠금 → 확인 → 차감 |
| 장점 | 간단하고 빠르다 | 복잡한 조건(쿠폰, 회원 등급 등)을 파이썬에서 검사할 수 있다 |
| 이 실습 | ✅ 사용 | 개념만 알아 둔다 |

## 생각해 볼 문제

1. 조건부 UPDATE 후 주문 INSERT 에서 오류가 나면 차감된 재고는 어떻게 될까?
2. `CHECK (stock >= 0)` 제약이 있는데 조건부 UPDATE 가 왜 또 필요할까?

다음 단계 : [04_purchase_order_query.md](04_purchase_order_query.md)
