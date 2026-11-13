# miniShop

수업용 미니 쇼핑몰 — **웹 음료수 자판기** (FastAPI + MariaDB + React)

> 기준일 : 2026-11-13
> 이 저장소는 **현재 서버에서 요청/응답이 되는 기능**만 담고 있다.
> 앞으로 만들 기능(구매하기 등)은 `docs` 폴더의 실습 문서로 이어서 진행한다.

---

## 1. 현재 동작하는 기능

### 화면 (frontend, http://localhost:5173)

| 화면 | 요청 API | 설명 |
|---|---|---|
| 상품 목록 (`App.jsx` → `pages/ProductList.jsx`) | `GET /products` | 판매중인 상품을 카드로 표시, 품절 표시 |

### API (backend, http://localhost:8000)

| 메서드 | 주소 | 상태 | 비고 |
|---|---|---|---|
| GET | `/` | ✅ 200 | 서버 동작 확인 |
| GET | `/products` | ✅ 200 | 상품 목록 (가격순) |
| GET | `/products/{product_id}` | ✅ 200 | 상품 상세 (`description` 포함) |
| GET | `/search/sort-options` | ✅ 200 | 정렬 옵션 목록 |
| GET | `/search/products` | ⚠️ 테스트 DB 전용 | `vmShop` DB 에서는 500. `test_vmshop` DB 로 실행해야 동작 |
| GET | `/search/categories` | ⚠️ 테스트 DB 전용 | 위와 같음 |
| POST / PUT / DELETE | `/products...` | 🚧 미구현 | 함수만 있고 `None` 을 돌려준다 |

API 문서(Swagger) : 서버 실행 후 http://localhost:8000/docs

### 알려진 문제 (다음 작업 때 고칠 것)

| 위치 | 문제 | 고치는 방법 |
|---|---|---|
| `backend/app/main.py` `find_all_products` | SQL 에 `NAME` 이라고 써서 응답 키가 `"NAME"` 이 된다. 프론트는 `product.name` 을 읽으므로 상품명이 비어 보인다 | SQL 을 `name` 으로 수정 |
| `backend/app/main.py` `get_product` | 없는 상품인데 500 을 돌려준다 | 404 로 수정 ([backend/docs/01_purchase_prepare.md](backend/docs/01_purchase_prepare.md) 1-1 참고) |
| `/search/*` | 운영 DB(`vmShop`)에 `categories` 테이블, 추천 컬럼이 없다 | `test_vmshop` 사용, 또는 운영 DB 에 같은 구조 반영 |

---

## 2. 폴더 구조

```
miniShop/
├── backend/                  FastAPI 서버
│   ├── app/
│   │   ├── main.py           앱 시작점, 상품 목록/상세 API
│   │   ├── product01.py      상품 검색 API (/search/...)
│   │   └── database.py       DB 연결 (.env 사용)
│   ├── sql/                  테스트 DB(test_vmshop) 생성 + 데이터 스크립트
│   ├── docs/                 구매하기 기능 실습 문서 (다음 작업)
│   ├── products/images/      상품 이미지 원본
│   ├── product_querys.md     상품 검색 SQL 정리
│   ├── test_db_for_query.md  테스트 DB 설명
│   ├── requirements.txt
│   └── .env.example          DB 설정 예시 (.env 로 복사해서 사용)
│
└── frontend/                 React + Vite
    ├── src/
    │   ├── App.jsx           화면 시작점
    │   ├── pages/ProductList.jsx
    │   ├── components/ProductCard.jsx
    │   ├── api/products.js   백엔드 API 호출 함수
    │   └── utils/image.js    이미지 경로 변환
    ├── public/images/        상품 이미지 (화면에서 사용)
    ├── docs/                 화면 실습 문서, 유저스토리
    └── vite.config.js        개발 서버 프록시 (/products → 8000)
```

---

## 3. 다른 컴퓨터에서 이어서 작업하기

### 준비물

- Python 3.11 이상, Node.js 20 이상, MariaDB (11.x 권장)

### ① 저장소 받기

```bash
git clone https://github.com/simpleego/miniShop.git
cd miniShop
```

### ② DB 만들기

`vmshop_user` 계정이 없다면 먼저 만든다. (root 로 접속해서 실행)

```sql
CREATE USER 'vmshop_user'@'localhost' IDENTIFIED BY '비밀번호';
GRANT ALL PRIVILEGES ON `vmShop`.* TO 'vmshop_user'@'localhost';
GRANT ALL PRIVILEGES ON `test\_%`.* TO 'vmshop_user'@'localhost';
FLUSH PRIVILEGES;
```

테스트 DB 와 데이터를 만든다. (상품 36개, 카테고리, 회원, 주문 포함)

```bash
mysql -u vmshop_user -p < backend/sql/01_test_schema.sql
mysql -u vmshop_user -p < backend/sql/02_test_seed.sql
```

> 운영 DB(`vmShop`) 생성 스크립트는 저장소에 없다. 새 컴퓨터에서는 `test_vmshop` 으로 작업하면 검색 API 까지 모두 동작한다.

### ③ 백엔드 실행

```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env        # 그리고 .env 의 DB_PASSWORD 를 채운다

uvicorn app.main:app --reload --port 8000
```

확인 : http://localhost:8000/products

### ④ 프론트 실행 (새 터미널)

```bash
cd frontend
npm install
npm run dev
```

확인 : http://localhost:5173

> `vite.config.js` 의 `/search` 프록시는 기본이 8001 포트(테스트 DB 서버)다.
> 8000 서버 하나만 띄웠다면 `API_TARGET=http://localhost:8000 npm run dev` 로 실행한다.

---

## 4. 다음 작업

| 순서 | 내용 | 문서 |
|---|---|---|
| 1 | 위 "알려진 문제" 수정 | 이 README |
| 2 | 구매하기 기능 (주문 API + 트랜잭션 + 화면 구매 버튼) | [backend/docs/README.md](backend/docs/README.md) |
| 3 | 상품 상세, 장바구니, 결제 화면 | [frontend/docs/userstory/00_overview.md](frontend/docs/userstory/00_overview.md) |
