# 상품 검색 SQL 정리

> 대상 DB : MariaDB 11.4 / `vmshop`
> 관련 코드 : [app/product01.py](app/product01.py), [app/main.py](app/main.py)

---

## 1. 검색 구조

```
┌──────────────────────────────────────────────┐
│ [ 상품명 검색창 (1차 검색)         ] [검색]  │  ← keyword
├──────────────────────────────────────────────┤
│ [결과 내 재검색 (2차) ]   [정렬 옵션 ▼]      │  ← sub_keyword, sort
├──────────────────────────────────────────────┤
│  상품 목록 ...                               │
└──────────────────────────────────────────────┘
```

| 단계 | 파라미터 | 동작 |
|---|---|---|
| 1차 검색 | `keyword` | 상품명에 검색어가 포함된 상품 (비우면 전체) |
| 2차 검색 | `sub_keyword` | 1차 결과 안에서 한 번 더 걸러냄 (`AND` 조건) |
| 정렬 | `sort` | 옵션바에서 선택한 순서로 정렬 |
| 페이지 | `page`, `size` | 페이지 번호(1부터), 한 페이지 상품 수(기본 20, 최대 100) |

---

## 2. API

| 메서드 | 주소 | 설명 |
|---|---|---|
| GET | `/search/products` | 상품 검색 (1차 + 2차 + 정렬 + 페이지) |
| GET | `/search/sort-options` | 옵션바 정렬 목록 (`value`, `label`) |

### 요청 예시

```
GET /search/products?keyword=주스
GET /search/products?keyword=주스&sub_keyword=오렌지
GET /search/products?keyword=수&sub_keyword=생&sort=price_high
GET /search/products?sort=newest&page=2&size=10
```

### 응답 예시

```json
{
  "keyword": "수",
  "sub_keyword": "생",
  "sort": "price_high",
  "page": 1,
  "size": 20,
  "total": 1,
  "total_pages": 1,
  "items": [
    {
      "id": 4, "name": "생수", "price": 1000, "stock": 25,
      "image_url": "/products/images/water.svg",
      "created_at": "2026-11-10T14:27:57", "sold_qty": 0
    }
  ]
}
```

### 정렬 옵션

| value | 화면 이름 | ORDER BY |
|---|---|---|
| `recommend` (기본) | 추천순 | `(p.stock > 0) DESC, sold_qty DESC, p.created_at DESC, p.id DESC` |
| `popular` | 판매 인기순 | `sold_qty DESC, p.id DESC` |
| `newest` | 신규상품순 | `p.created_at DESC, p.id DESC` |
| `price_low` | 낮은 가격순 | `p.price ASC, p.id DESC` |
| `price_high` | 높은 가격순 | `p.price DESC, p.id DESC` |

- 마지막의 `p.id DESC` 는 값이 같은 상품끼리 순서가 고정되게 합니다. 페이지를 넘길 때 상품이 중복되거나 누락되지 않습니다.
- 추천순은 추천 컬럼이 아직 없어서 **재고 있는 상품 → 많이 팔린 상품 → 최근 등록 상품** 순으로 계산합니다.

> 주소를 `/products/search` 로 하지 않은 이유 : `main.py` 의 `GET /products/{product_id}` 가 먼저 등록되어 있어서
> `search` 를 상품 id 로 받아 422 오류가 납니다.

---

## 3. 사용하는 SQL

### 3-1. 전체 건수

```sql
SELECT COUNT(*) AS total
FROM products p
WHERE p.is_active = 1
  AND p.name LIKE %s      -- 1차 검색어 (keyword 가 있을 때만)
  AND p.name LIKE %s      -- 2차 검색어 (sub_keyword 가 있을 때만)
```

### 3-2. 현재 페이지 상품 목록

```sql
SELECT
    p.id,
    p.name,
    p.price,
    p.stock,
    p.image_url,
    p.created_at,
    COALESCE(s.sold_qty, 0) AS sold_qty
FROM products p
LEFT JOIN (
    -- 결제 완료 주문의 상품별 판매 수량 합계
    SELECT oi.product_id, SUM(oi.quantity) AS sold_qty
    FROM order_items oi
    JOIN orders o ON o.id = oi.order_id
    WHERE o.status = 'PAID'
    GROUP BY oi.product_id
) s ON s.product_id = p.id
WHERE p.is_active = 1
  AND p.name LIKE %s      -- 1차 검색어
  AND p.name LIKE %s      -- 2차 검색어
ORDER BY {정렬 옵션별 문장}
LIMIT %s OFFSET %s        -- size, (page - 1) * size
```

- `LEFT JOIN` 을 쓰기 때문에 한 번도 안 팔린 상품도 빠지지 않습니다. 그 상품의 `sold_qty` 는 `NULL` 인데, `COALESCE` 로 0으로 바꿉니다.
- `SUM` 결과는 `Decimal` 로 오기 때문에, 코드에서 `int` 로 바꿔 JSON으로 보냅니다.

### 3-3. 보안 처리

| 위험 | 처리 |
|---|---|
| 검색어로 SQL 인젝션 | 검색어는 `%s` 빈칸으로만 넣습니다 (파라미터 바인딩). |
| `ORDER BY` 는 바인딩이 안 됨 | 미리 정해 둔 5개 문장 중 하나만 고릅니다 (화이트리스트). 목록에 없는 값은 422 오류입니다. |
| `%`, `_` 입력 시 전체 검색 | 검색어 안의 `\`, `%`, `_` 앞에 `\` 를 붙여 일반 글자로 취급합니다. |

```python
def to_like_pattern(text):
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"
```

---

## 4. 현재 테이블 구조 (검색 관련)

```sql
CREATE TABLE products (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  name        VARCHAR(50)  NOT NULL,
  price       INT          NOT NULL,              -- CHECK (price >= 0)
  stock       INT          NOT NULL DEFAULT 0,    -- CHECK (stock >= 0)
  image_url   VARCHAR(255) DEFAULT NULL,
  description VARCHAR(255) DEFAULT NULL,
  is_active   TINYINT(1)   NOT NULL DEFAULT 1,
  created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
);
-- 인덱스 : PRIMARY KEY 만 있음

orders      (id, user_id, total_price, status DEFAULT 'PAID', created_at)
order_items (id, order_id, product_id, quantity, unit_price)
```

---

## 5. 필드 추가 vs 별도 테이블

### 판단 기준

| 경우 | 방법 | 예 |
|---|---|---|
| 상품 하나에 값이 하나 | `products` 에 **필드 추가** | 추천 여부, 추천 순서 |
| 상품 하나에 여러 개, 또는 기간/이력이 있음 | **별도 테이블** | 리뷰, 기간 한정 기획전, 카테고리 |
| 다른 테이블에서 계산되는 값 | 처음엔 **계산**, 느려지면 컬럼으로 저장 | 판매량 |

### 기능별 판단

| 기능 | 현재 상태 | 판단 |
|---|---|---|
| 1차/2차 검색 (상품명) | `name` 있음 | 변경 없음 |
| 신규상품순 | `created_at` 있음 | 인덱스만 추가 |
| 가격순 | `price` 있음 | 인덱스만 추가 |
| 판매 인기순 | `order_items` 에서 집계 | 지금은 계산. 주문이 많아지면 `sales_count` 컬럼 추가 |
| 추천순 | 정보 없음 | **A안 (필드 추가)** 또는 B안 (별도 테이블) |

### 추천순 선택지

- **A안. `products` 에 필드 추가 (지금 단계에 추천)**
  관리자가 상품별로 추천을 켜고 끄는 정도라면 충분합니다.
- **B안. 별도 테이블 `product_recommendations`**
  "메인 추천", "여름 기획전"처럼 추천 구역이 여러 개이거나 기간이 정해진 추천이 필요할 때 씁니다.
  한 상품이 여러 구역에 들어가는 1:N 관계라서 테이블로 나눠야 합니다.

---

## 6. 제안 SQL (아직 실행하지 않음)

### 6-1. A안 : 추천 필드 + 정렬용 인덱스

```sql
-- 추천 정보 : 관리자가 지정
ALTER TABLE products
  ADD COLUMN is_recommended TINYINT(1) NOT NULL DEFAULT 0 COMMENT '추천 상품 여부',
  ADD COLUMN recommend_rank INT        NOT NULL DEFAULT 0 COMMENT '추천 순서 (클수록 위)';

-- 정렬용 인덱스 : 판매 중인 상품을 정렬할 때 테이블 전체를 읽지 않게 한다
CREATE INDEX idx_products_active_created ON products (is_active, created_at);
CREATE INDEX idx_products_active_price   ON products (is_active, price);
CREATE INDEX idx_products_active_reco    ON products (is_active, is_recommended, recommend_rank);
```

A안 적용 후 추천순 정렬은 이렇게 바뀝니다.

```sql
ORDER BY p.is_recommended DESC, p.recommend_rank DESC, sold_qty DESC, p.created_at DESC, p.id DESC
```

### 6-2. B안 : 추천 구역별 별도 테이블 (필요해질 때)

```sql
CREATE TABLE product_recommendations (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  product_id  INT         NOT NULL,
  section     VARCHAR(30) NOT NULL COMMENT '추천 구역 (main, summer_event ...)',
  sort_order  INT         NOT NULL DEFAULT 0,
  start_at    DATETIME    NULL COMMENT '노출 시작 (NULL 이면 즉시)',
  end_at      DATETIME    NULL COMMENT '노출 종료 (NULL 이면 무기한)',
  created_at  DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_reco_section_product (section, product_id),
  KEY idx_reco_section_order (section, sort_order),
  CONSTRAINT fk_reco_product FOREIGN KEY (product_id) REFERENCES products (id)
);
```

---

## 7. 나중에 검토할 것

- **판매량 컬럼** : 주문이 많아지면 매번 `order_items` 를 집계하는 것이 느려집니다. 그때 `products.sales_count` 를 추가하고, 주문할 때 재고를 줄이는 같은 트랜잭션에서 함께 `+수량` 합니다.

  ```sql
  ALTER TABLE products ADD COLUMN sales_count INT NOT NULL DEFAULT 0 COMMENT '누적 판매 수량';

  -- 주문 처리 트랜잭션 안에서
  UPDATE products
  SET stock = stock - %s, sales_count = sales_count + %s
  WHERE id = %s AND stock >= %s;
  ```

- **상품명 검색 속도** : `LIKE '%검색어%'` 는 앞에 `%` 가 있어서 인덱스를 쓰지 못합니다. 상품이 수천 개 정도까지는 문제없습니다. MariaDB의 FULLTEXT 검색은 한글 단어를 잘 나누지 못하므로, 상품이 아주 많아지면 검색 엔진(Elasticsearch 등)을 검토합니다.
- **카테고리** : 쇼핑몰 검색에는 보통 카테고리 필터가 붙습니다. 이것은 별도 테이블로 만듭니다.

  ```sql
  CREATE TABLE categories (
    id   INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(30) NOT NULL UNIQUE
  );

  ALTER TABLE products
    ADD COLUMN category_id INT NULL,
    ADD CONSTRAINT fk_products_category FOREIGN KEY (category_id) REFERENCES categories (id);
  ```

---

## 8. 테스트 메모

- 판매 인기순은 `orders` 와 `order_items` 가 비어 있어 지금은 모든 상품의 `sold_qty` 가 0입니다. 주문 데이터가 생기면 순서가 달라집니다.
- Git Bash의 curl로 한글 검색어를 그대로 보내면 인코딩이 깨져서 0건이 나옵니다. 브라우저나 `/docs` 화면에서 테스트하거나, `keyword=%EC%88%98`(수)처럼 인코딩해서 보내면 됩니다.
