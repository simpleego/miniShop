# 1. 준비 — 기존 코드 정리와 주문 라우터 만들기

> 목표 : 구매 API 를 넣을 **빈 파일(`app/order01.py`)** 을 만들고 `main.py` 에 연결한다.
> 그 전에 상품 상세 조회의 상태코드 문제를 먼저 고친다.

---

## 1-1. 상품 상세 조회 바로잡기 (`app/main.py`)

현재 `get_product` 에는 문제가 2가지 있다.

```python
try:
    product = find_product_by_id(product_id)

    # 상품이 없는 경우
    logger.info("상품 상세 조회 결과 (id=%s) : 없음", product_id)   # ❶ 찾았을 때도 "없음" 이 찍힌다
except Exception as e:
    ...
if product is None:
        raise HTTPException(status_code=500, detail="상품을 찾을 수 없습니다.")  # ❷ 500 이 아니라 404
```

| 문제 | 왜 문제인가 |
|---|---|
| ❶ 로그 위치 | 상품을 찾아도 "없음" 로그가 찍혀서 로그를 믿을 수 없다 |
| ❷ 500 | 500 은 **서버가 고장났다**는 뜻이다. 없는 상품을 요청한 건 서버 잘못이 아니므로 **404 Not Found** 가 맞다 |

### 수정 후

```python
@app.get("/products/{product_id}", tags=["product"])
def get_product(product_id: int):
    try:
        product = find_product_by_id(product_id)
    except Exception as e:
        logger.error("상품 상세 조회 실패 id=%s: %s", product_id, e)
        raise HTTPException(status_code=500, detail="상품 상세 조회 에러")

    if product is None:
        logger.info("상품 상세 조회 결과 (id=%s) : 없음", product_id)
        raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다.")

    logger.info("상품 상세 조회 결과 (id=%s) : %s", product_id, product["name"])
    return product
```

### 확인

브라우저에서 `http://localhost:8000/docs` 를 열고 `GET /products/{product_id}` 를 실행한다.

| 입력 | 기대 결과 |
|---|---|
| `1` | 200 + 상품 정보 |
| `9999` | **404** + `상품을 찾을 수 없습니다.` |
| `abc` | 422 (정수가 아님) |

---

## 1-2. 트랜잭션이 가능한지 확인 (`app/database.py`)

구매 기능은 **트랜잭션**(여러 SQL 을 하나로 묶기)을 사용한다.
PyMySQL 은 기본값이 `autocommit=False` 라서 `conn.commit()` 을 호출해야 DB 에 실제로 저장된다.

```python
return pymysql.connect(
    ...
    cursorclass=DictCursor,
    # autocommit=True   ← ❌ 이 줄이 있으면 SQL 마다 즉시 저장되어 rollback 이 안 된다
)
```

> 현재 `database.py` 에는 `autocommit` 설정이 없으므로(= False) 그대로 쓰면 된다.

| 용어 | 뜻 |
|---|---|
| `commit()` | 지금까지 실행한 SQL 을 DB 에 **확정 저장** |
| `rollback()` | 마지막 commit 이후 실행한 SQL 을 **전부 취소** |
| autocommit | SQL 한 문장마다 자동으로 commit (켜면 묶어서 취소할 수 없다) |

> 💡 지금까지 만든 조회(SELECT) 기능에서 `commit()` 을 안 써도 됐던 이유 : 읽기만 하고 바꾼 게 없기 때문이다.

---

## 1-3. 주문자 id 확인

로그인이 없으므로 주문자를 `user_id = 1` 로 고정한다. 이 회원이 DB 에 있는지 확인한다.

```sql
SELECT id, email, name FROM users WHERE id = 1;
```

> 결과가 없으면 `orders.user_id` 외래키 때문에 주문 INSERT 가 실패한다.
> 다른 id 가 있다면 그 값을 쓰면 된다.

---

## 1-4. 주문 라우터 파일 만들기 (`app/order01.py`, 신규)

검색 기능을 `product01.py` 로 분리했던 것처럼, 주문 기능도 파일을 나눈다.

```python
# =============================================================================
# 주문(구매) API
#
#   POST /orders              구매하기 (주문 생성)
#   GET  /orders              내 주문 목록          (4단계)
#   GET  /orders/{order_id}   주문 상세             (4단계)
#
#   ※ 로그인 기능이 아직 없어서 주문자는 TEMP_USER_ID 로 고정한다.
# =============================================================================

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .database import get_connection

logger = logging.getLogger(__name__)

# prefix="/orders" : 이 파일의 모든 주소 앞에 /orders 가 붙는다
router = APIRouter(prefix="/orders", tags=["orders"])

# 로그인 기능을 만들기 전까지 사용할 임시 주문자 id
TEMP_USER_ID = 1


# -----------------------------------------------------------------------------
# 구매 요청 본문 모양
#   가격(price)은 받지 않는다 → 서버가 DB 가격으로 계산한다.
# -----------------------------------------------------------------------------
class OrderIn(BaseModel):
    product_id: int = Field(ge=1)           # 상품 번호 (1 이상)
    quantity: int = Field(ge=1, le=10)      # 수량 (1 ~ 10개, 자판기라 한 번에 10개까지)


@router.post("", status_code=201)
def create_order(item: OrderIn):
    # 2단계에서 구현한다
    return {"message": "주문 API 준비 완료", "request": item}
```

> `@router.post("")` : prefix 가 `/orders` 이므로 최종 주소는 `POST /orders` 다.
> `"/"` 로 쓰면 주소가 `/orders/` 가 되어 끝에 `/` 를 붙여야 하므로 `""` 로 쓴다.

---

## 1-5. `main.py` 에 라우터 등록

```python
from .database import get_connection
from .product01 import router as search_router
from .order01 import router as order_router      # ✅ 추가

app = FastAPI(title="음료수 자판기 ")
app.include_router(search_router)   # 상품 검색 API (/search/...)
app.include_router(order_router)    # ✅ 주문 API (/orders/...)
```

---

## ✅ 1단계 확인

서버를 다시 실행하고 `http://localhost:8000/docs` 에서 확인한다.

```bash
uvicorn app.main:app --reload
```

| 요청 본문 | 기대 결과 |
|---|---|
| `{"product_id": 1, "quantity": 2}` | 201 + `"주문 API 준비 완료"` |
| `{"product_id": 1, "quantity": 0}` | 422 (1 이상이어야 함) |
| `{"product_id": 1, "quantity": 11}` | 422 (10 이하여야 함) |
| `{"product_id": 1}` | 422 (quantity 누락) |
| `{"product_id": 1, "quantity": 2, "price": 1}` | 201 — `price` 는 **무시**된다 |

> 마지막 줄이 중요하다. 클라이언트가 가격을 보내도 `OrderIn` 에 없는 필드라서 서버는 쓰지 않는다.

다음 단계 : [02_purchase_order_api.md](02_purchase_order_api.md)
