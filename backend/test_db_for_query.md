# 상품 검색 테스트 DB 정리

> 테스트 DB : `test_vmshop` (운영 DB `vmshop` 과 분리)
> 관련 문서 : [product_querys.md](product_querys.md) (검색 API · SQL · 테이블 설계)
> 관련 코드 : [app/product01.py](app/product01.py)

---

## 1. 개요

[product_querys.md](product_querys.md)에서 설계한 상품 검색 기능을 확인하기 위해 만든 테스트 DB입니다.

- 운영 DB `vmshop` 은 건드리지 않았습니다.
- `vmshop_user` 계정은 `test_` 로 시작하는 DB를 만들 수 있는 권한이 있어서, 그 이름으로 별도 DB를 만들었습니다.
- 운영 DB와 같은 구조에 **A안 (추천 필드 + 정렬 인덱스)** 을 미리 적용했습니다.

---

## 2. 파일

| 파일 | 내용 |
|---|---|
| [sql/01_test_schema.sql](sql/01_test_schema.sql) | `test_vmshop` DB와 테이블 4개 생성 (`users`, `products`, `orders`, `order_items`) |
| [sql/02_test_seed.sql](sql/02_test_seed.sql) | 가상 데이터 입력 + 맨 아래 주석에 예상 결과 |

- 두 파일 모두 **여러 번 실행해도 같은 상태로 다시 만들어집니다.**
- 대신 실행할 때마다 **기존 테스트 데이터는 사라집니다.**
  - `01_test_schema.sql` : 테이블을 지우고 다시 만듭니다.
  - `02_test_seed.sql` : 처음에 `TRUNCATE` 로 데이터를 비웁니다.

### 실행 순서

```
01_test_schema.sql  →  02_test_seed.sql
```

HeidiSQL 같은 DB 도구에서 파일을 열어 그대로 실행하면 됩니다.

---

## 3. 운영 DB와 다른 점 (A안)

```sql
-- products 에 추가된 컬럼
is_recommended TINYINT(1) NOT NULL DEFAULT 0 COMMENT '추천 상품 여부',
recommend_rank INT        NOT NULL DEFAULT 0 COMMENT '추천 순서 (클수록 위)',

-- 정렬용 인덱스
CREATE INDEX idx_products_active_created ON products (is_active, created_at);
CREATE INDEX idx_products_active_price   ON products (is_active, price);
CREATE INDEX idx_products_active_reco    ON products (is_active, is_recommended, recommend_rank);
```

나머지 테이블(`users`, `orders`, `order_items`)은 운영 DB와 같은 구조입니다.

---

## 4. 데이터 설계

### 4-1. 데이터 양

| 테이블 | 건수 |
|---|---|
| `users` | 8명 (관리자 1, 일반 7). 비밀번호는 가짜 값 `test-hash` |
| `products` | 35개 (판매중 33, 판매중지 2) |
| `orders` | 16건 (PAID 15, CANCELLED 1) |
| `order_items` | 38줄 |

### 4-2. 검색 기능별로 확인할 수 있게 만든 데이터

| 확인 대상 | 데이터 |
|---|---|
| 1차 검색 | "콜라" 3개, "주스" 6개, "커피" 4개, "수" 6개 등 |
| 2차 검색 | "수" → "생" 으로 좁히면 생수 2개만 |
| 신규상품순 | 등록일을 2026-07 ~ 2026-11 로 분산 |
| 가격순 | 1,000원 ~ 3,200원, 같은 가격도 섞음 |
| 판매 인기순 | 주문 수량을 상품마다 다르게 |
| 추천순 (A안) | 5개 상품을 추천 지정, `recommend_rank` 로 순서 지정 |
| 품절 | `stock = 0` 상품 5개 |
| 판매중지 | `is_active = 0` 상품 2개 → 검색에 나오면 안 됨 |
| 취소 주문 | `CANCELLED` 주문 → 판매량에 들어가면 안 됨 |
| LIKE 특수문자 | "100% 오렌지주스", "언더바_테스트 음료" |

### 4-3. 일부러 넣은 함정 데이터

| 상품 | 상황 | 올바른 결과 |
|---|---|---|
| `단종 콜라` (id 33) | 판매중지인데 50개 팔림 | 검색에 나오면 안 됨 |
| `테스트 주스` (id 34) | 판매중지인데 추천 지정, 가장 비쌈 (9,999원) | 추천순·높은 가격순에 나오면 안 됨 |
| `홍차` (id 21) | 취소 주문 60개뿐 | 판매량 0 |
| `생수 500ml` (id 12) | 취소 주문에 20개 포함 | 판매량 40 (60이 아님) |
| `100% 오렌지주스` (id 7) | 이름에 `%` | `%` 검색 시 이 상품만 |
| `언더바_테스트 음료` (id 35) | 이름에 `_` | `_` 검색 시 이 상품만 |

### 4-4. 추천 지정 상품

| 순서 | 상품 | recommend_rank |
|---|---|---|
| 1 | 콜라 | 90 |
| 2 | 아메리카노 커피 | 80 |
| 3 | 100% 오렌지주스 | 70 |
| 4 | 바나나우유 | 60 |
| 5 | 생수 500ml | 50 |
| (제외) | 테스트 주스 | 99 (판매중지라 나오면 안 됨) |

### 4-5. 주문 가격 계산

`order_items.unit_price` 와 `orders.total_price` 는 직접 적지 않고, 입력 후 `UPDATE` 로 자동 계산합니다.

```sql
-- 주문 당시 가격 = 현재 상품 가격
UPDATE order_items oi
JOIN products p ON p.id = oi.product_id
SET oi.unit_price = p.price;

-- 주문 총액 = 주문 상품 (수량 × 단가) 합계
UPDATE orders o
JOIN (
  SELECT order_id, SUM(quantity * unit_price) AS total
  FROM order_items
  GROUP BY order_id
) t ON t.order_id = o.id
SET o.total_price = t.total;
```

---

## 5. 예상 결과와 실제 결과

테스트 서버(포트 8001, `DB_NAME=test_vmshop`)로 `/search/products` 를 호출해 확인했습니다.
**모든 결과가 예상과 같았습니다.**

### 5-1. 판매 인기순 (`sort=popular`)

PAID 주문만, 판매중 상품만 집계합니다.

```
생수 500ml 40 > 콜라 35 > 아메리카노 커피 28 > 바나나우유 20 > 사이다 15
> 100% 오렌지주스 10 > 이온음료 9 > 녹차 8 > 망고주스 6 > 옥수수수염차 5
> 생수 2L 4 > 콜드브루 커피 3 > 사과주스 2 > 나머지 0
```

- 홍차는 취소 주문뿐이라 0입니다.
- 단종 콜라(50개)는 판매중지라 나오지 않습니다.

### 5-2. 검색 결과

| 요청 | 결과 | 건수 |
|---|---|---|
| 전체 | 판매중지 2개 제외 | 33 |
| `keyword=콜라` | 콜라, 제로콜라, 체리콜라 (단종 콜라 제외) | 3 |
| `keyword=주스` | 오렌지주스 ~ 토마토주스 (테스트 주스 제외) | 6 |
| `keyword=커피` | 아메리카노, 카페라떼, 콜드브루, 바닐라라떼 | 4 |
| `keyword=수` | 생수 500ml, 생수 2L, 탄산수, 레몬 탄산수, 옥수수수염차, 수정과 | 6 |
| `keyword=수&sub_keyword=생` | 생수 500ml, 생수 2L | 2 |
| `keyword=%` | 100% 오렌지주스 (전체가 나오지 않음) | 1 |
| `keyword=_` | 언더바_테스트 음료 | 1 |

### 5-3. 정렬 결과

| 요청 | 앞쪽 결과 |
|---|---|
| `sort=newest` | 언더바_테스트 음료(11/11) → 콜드브루 커피(11/08) → 100% 오렌지주스(11/05) → 망고주스(11/01) ... |
| `sort=price_low` | 언더바_테스트 음료 1,000 → 생수 500ml 1,000 → 탄산수 1,200 → 레몬 탄산수 1,400 ... |
| `sort=price_high` | 콜드브루 커피 3,200 → 바닐라라떼 커피 3,000 → 카페라떼 커피 2,800 ... (테스트 주스 9,999 제외) |

같은 가격(1,000원)은 `p.id DESC` 기준이라 id가 큰 상품이 먼저 나옵니다.

---

## 6. 테스트 DB로 서버 실행하기

**방법 1.** `.env` 의 `DB_NAME` 을 바꿉니다.

```
DB_NAME=test_vmshop
```

**방법 2.** `.env` 는 그대로 두고, PowerShell에서 환경변수를 지정해 다른 포트로 실행합니다.

```powershell
$env:DB_NAME='test_vmshop'; .\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8001
```

`load_dotenv()` 는 이미 있는 환경변수를 덮어쓰지 않습니다. 그래서 방법 2로 지정한 값이 `.env` 보다 먼저 적용됩니다.

---

## 7. 남은 작업

- **추천순 정렬이 아직 추천 컬럼을 쓰지 않습니다.**
  테스트 DB에는 `is_recommended`, `recommend_rank` 데이터가 있지만, [product01.py](app/product01.py)의 추천순은 아직 "재고 있는 상품 → 판매량 → 등록일" 순입니다. 그래서 지금은 인기순과 거의 같은 결과가 나옵니다.
  코드를 바로 바꾸지 않은 이유는 운영 DB `vmshop` 에는 이 컬럼이 없어서, 바꾸면 지금 서버가 오류를 내기 때문입니다.
- 진행하려면 아래 두 가지를 함께 해야 합니다.
  1. 운영 DB에 A안 SQL 적용 ([product_querys.md](product_querys.md) 6-1)
  2. 추천순 정렬 변경

     ```sql
     ORDER BY p.is_recommended DESC, p.recommend_rank DESC, sold_qty DESC, p.created_at DESC, p.id DESC
     ```

---

## 8. 테스트 메모

- Git Bash의 curl로 한글 검색어를 그대로 보내면 인코딩이 깨져서 0건이 나옵니다. 브라우저나 `/docs` 화면에서 테스트하거나, `keyword=%EC%88%98`(수)처럼 인코딩해서 보내면 됩니다.
- Python 스크립트에서 `.sql` 파일을 실행할 때는 여러 문장을 한 번에 보내야 하므로 `client_flag=CLIENT.MULTI_STATEMENTS` 옵션이 필요합니다.
