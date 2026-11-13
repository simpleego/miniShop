# App.jsx — SQL(DB) 버전

> 지금까지 `App.jsx` 는 상품 목록을 **코드 안의 배열(하드코딩)** 로 가지고 있었다.
> 이제 백엔드 `backend/app/main.py` 가 MariaDB(`products` 테이블)에서 상품을 꺼내 주므로,
> 프론트는 **백엔드 API 를 호출해서 받은 데이터로 화면을 그리도록** 바꾼다.

---

## 1. 백엔드(main.py)에서 확인한 내용

| 항목 | 내용 |
|------|------|
| 상품 목록 API | `GET /products` |
| 실행 SQL | `SELECT id, name, price, stock, image_url FROM products WHERE is_active = 1 ORDER BY price` |
| 응답 모양 | 상품 객체의 **배열** (DictCursor 사용 → JSON 객체로 변환됨) |
| 실패 시 | `500` + `{"detail": "상품 목록 조회 에러"}` |
| 상품 상세 API | `GET /products/{product_id}` (description 포함) — 이번 화면에서는 사용하지 않음 |
| POST / PUT / DELETE | 아직 구현되지 않음 (`return None`) |

응답 예시:

```json
[
  { "id": 12, "name": "생수 500ml", "price": 1000, "stock": 100, "image_url": "/products/images/water.svg" },
  { "id": 4,  "name": "사이다",     "price": 1400, "stock": 30,  "image_url": "/products/images/cider.svg" },
  { "id": 1,  "name": "콜라",       "price": 1500, "stock": 50,  "image_url": "/products/images/cola.svg" }
]
```

필드 이름(`id, name, price, stock, image_url`)이 기존 하드코딩 배열과 **똑같기 때문에**
`ProductCard` 컴포넌트는 고치지 않고 그대로 쓸 수 있다.

### 주의할 점 2가지

1. **CORS 설정이 없다** — `main.py` 에 `CORSMiddleware` 가 없으므로, 브라우저에서
   `http://localhost:5173` → `http://localhost:8000` 으로 직접 요청하면 차단된다.
   → **Vite 프록시**를 사용해서 해결한다. (아래 3번)
2. **이미지 파일을 서빙하지 않는다** — DB 의 `image_url` 은 `/products/images/cola.svg` 인데,
   `main.py` 에 `StaticFiles` 마운트가 없어서 백엔드가 이 파일을 내려주지 않는다.
   → 같은 이미지가 프론트 `public/images/` 에 있으므로, 프론트에서 경로를
   `/images/cola.svg` 로 바꿔서 사용한다. (아래 4번)

---

## 2. 전체 흐름

```
[브라우저]                [Vite 개발서버 :5173]           [FastAPI :8000]           [MariaDB]
 App.jsx
  fetch('/products')  ──▶  proxy '/products'  ─────────▶  GET /products  ──SQL──▶  products 테이블
                                                           find_all_products()
  setProducts(data)   ◀──────────────────────────────────  JSON 배열       ◀──────  행(row) 목록
  ↓
 ProductCard 반복 렌더링
```

---

## 3. vite.config.js — 프록시 추가

`/products` 로 시작하는 요청을 백엔드(8000)로 넘겨준다.
브라우저 입장에서는 같은 주소(5173)로 요청하는 것이므로 CORS 문제가 생기지 않는다.

```js
  server: {
    proxy: {
      // 상품 검색 테스트 화면(test.html)용
      '/search': process.env.API_TARGET || 'http://localhost:8001',

      // ✅ 추가 : 자판기 메인 화면(App.jsx)용 상품 목록 API
      '/products': 'http://localhost:8000',
    },
  },
```

> 프록시 설정을 바꾼 뒤에는 `npm run dev` 를 **다시 실행**해야 적용된다.

---

## 4. App.jsx 코드

```jsx
import { useEffect, useState } from 'react'
import './App.css'

import ProductCard from './components/ProductCard'

// 백엔드 상품 목록 API 주소
//   Vite 프록시가 '/products' 요청을 http://localhost:8000 으로 전달한다. (vite.config.js)
const PRODUCTS_API = '/products'

// DB 의 image_url("/products/images/cola.svg") 을
// 프론트 public 폴더 경로("/images/cola.svg") 로 바꾼다.
//   백엔드가 아직 이미지 파일을 내려주지 않기 때문에, 같은 파일이 있는 public/images 를 쓴다.
//   image_url 이 비어 있으면(NULL) 기본 이미지를 보여준다.
function toImagePath(imageUrl) {
  if (!imageUrl) return '/favicon.svg'
  const fileName = imageUrl.split('/').pop()   // "cola.svg"
  return `/images/${fileName}`
}

function App() {
  // 화면 상태 3가지 : 데이터, 로딩 중인지, 에러 메시지
  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // 화면이 처음 나타날 때 한 번만 상품 목록을 불러온다. (의존성 배열 [])
  useEffect(() => {
    // 컴포넌트가 사라지면 진행 중인 요청을 취소하기 위한 컨트롤러
    const controller = new AbortController()

    async function loadProducts() {
      try {
        const res = await fetch(PRODUCTS_API, { signal: controller.signal })

        // fetch 는 404, 500 이어도 예외를 던지지 않는다 → 직접 확인해야 한다
        if (!res.ok) {
          const body = await res.json().catch(() => ({}))
          throw new Error(body.detail || `서버 오류 (${res.status})`)
        }

        const data = await res.json()

        // 이미지 경로만 프론트용으로 바꿔서 저장 (나머지 필드는 그대로)
        setProducts(
          data.map((p) => ({ ...p, image_url: toImagePath(p.image_url) }))
        )
      } catch (err) {
        if (err.name === 'AbortError') return   // 취소된 요청은 에러로 보지 않는다
        setError(err.message || '상품 목록을 불러오지 못했습니다.')
      } finally {
        if (!controller.signal.aborted) setLoading(false)
      }
    }

    loadProducts()

    // 정리(cleanup) 함수 : 컴포넌트가 사라질 때 요청 취소
    return () => controller.abort()
  }, [])

  return (
    <div className="container">
      <h1 className="title">🥤 음료수 자판기</h1>

      {/* 1) 로딩 중 */}
      {loading && <p className="message">상품을 불러오는 중...</p>}

      {/* 2) 에러 */}
      {error && <p className="message error">⚠️ {error}</p>}

      {/* 3) 성공했지만 상품이 0개 */}
      {!loading && !error && products.length === 0 && (
        <p className="message">판매 중인 상품이 없습니다.</p>
      )}

      {/* 4) 성공 : 상품 카드 목록 */}
      {!loading && !error && products.length > 0 && (
        <div className="product-grid">
          {products.map((product) => (
            <ProductCard key={product.id} product={product} />
          ))}
        </div>
      )}
    </div>
  )
}

export default App
```

### App.css 에 추가할 스타일 (선택)

```css
.message {
  text-align: center;
  color: #666;
  margin: 40px 0;
}

.message.error {
  color: #d32f2f;
}
```

---

## 5. 코드 설명

### 5-1. 하드코딩 배열 → `useState`

| 이전 | 이후 |
|------|------|
| `const products = [ {...}, {...} ]` (파일 맨 위 상수) | `const [products, setProducts] = useState([])` |
| 값이 바뀌지 않음 | 서버 응답이 오면 `setProducts` 로 바꾸고 → 화면이 다시 그려짐 |

처음 값은 빈 배열 `[]` 이다. 데이터가 오기 전에도 `products.map(...)` 이 에러 없이 동작하게 하기 위해서다.

### 5-2. `useEffect(..., [])` — 처음 한 번만 호출

- 컴포넌트 함수 본문에서 바로 `fetch` 하면 **렌더링할 때마다** 요청이 나가고,
  `setProducts` → 다시 렌더링 → 또 `fetch` ... **무한 반복**이 된다.
- `useEffect` 의 두 번째 인자를 `[]` 로 주면 **화면에 처음 나타날 때 한 번만** 실행된다.
- 개발 모드(StrictMode)에서는 effect 가 두 번 실행될 수 있는데,
  cleanup 에서 `controller.abort()` 로 첫 요청을 취소하므로 문제없다.

### 5-3. `res.ok` 확인

`fetch` 는 **네트워크가 끊겼을 때만** 예외를 던진다. 백엔드가 `500` 을 돌려줘도 정상 응답으로 취급하므로
`res.ok`(상태코드 200~299 여부)를 직접 확인해야 한다.
백엔드의 `HTTPException(detail=...)` 메시지는 `body.detail` 로 꺼내서 화면에 보여준다.

### 5-4. 로딩 / 에러 / 빈 목록 / 성공 — 4가지 화면

서버 요청은 시간이 걸리고 실패할 수도 있으므로, 상태에 따라 다른 화면을 보여준다.

| 상황 | 예 | 화면 |
|------|----|------|
| `loading === true` | 응답 기다리는 중 | "상품을 불러오는 중..." |
| `error` 있음 | 백엔드 꺼짐, DB 연결 실패(500) | "⚠️ 상품 목록 조회 에러" |
| 성공 + 0개 | `is_active = 1` 상품이 없음 | "판매 중인 상품이 없습니다." |
| 성공 + 1개 이상 | 정상 | 상품 카드 목록 |

### 5-5. 이미지 경로 변환 `toImagePath`

```
DB 값          : /products/images/cola.svg
split('/').pop : cola.svg
최종 경로       : /images/cola.svg   → frontend/public/images/cola.svg 가 보인다
```

`image_url` 은 DB 에서 `NULL` 이 될 수 있는 컬럼이라(`DEFAULT NULL`) 값이 없을 때 기본 이미지로 대체한다.

### 5-6. 정렬 순서

정렬은 백엔드 SQL 의 `ORDER BY price` 가 이미 하고 있으므로 프론트에서는 **받은 순서 그대로** 출력한다.
(가격이 낮은 상품부터 표시됨)

---

## 6. 실행 순서

```bash
# 1) MariaDB 실행 확인 (backend/.env 의 DB_NAME 데이터베이스에 products 데이터가 있어야 함)

# 2) 백엔드 실행 (backend 폴더에서)
uvicorn app.main:app --reload --port 8000

# 3) 브라우저에서 API 먼저 확인
#    http://localhost:8000/products   → JSON 배열이 보이면 OK
#    http://localhost:8000/docs       → Swagger 에서 테스트 가능

# 4) 프론트 실행 (frontend 폴더에서)
npm run dev

# 5) http://localhost:5173 접속
```

### 문제가 생길 때 확인 순서

| 증상 | 원인 / 확인할 것 |
|------|------------------|
| "서버 오류 (500)" 또는 프록시 에러 | 백엔드가 실행 중인지, 포트가 8000 인지 |
| "상품 목록 조회 에러" | DB 연결 실패 → `.env` 계정/DB 이름, MariaDB 실행 여부. 백엔드 터미널의 `[ERROR]` 로그 확인 |
| 카드는 나오는데 이미지가 깨짐 | `public/images/` 에 같은 파일명이 있는지 (seed 데이터의 이미지 이름 확인) |
| 화면에 아무 변화 없음 | `vite.config.js` 수정 후 `npm run dev` 재시작 했는지 |

---

## 7. 다음 단계 (참고)

- **백엔드에서 이미지 서빙하기** : `main.py` 에 아래를 추가하면 `toImagePath` 변환 없이
  DB 의 `image_url` 을 그대로 쓸 수 있다. (이때는 vite 프록시가 `/products/images/...` 도 백엔드로 넘긴다)
  ```python
  from fastapi.staticfiles import StaticFiles
  app.mount("/products/images", StaticFiles(directory="products/images"), name="product-images")
  ```
  > `app.mount` 는 `@app.get("/products/{product_id}")` 보다 **먼저** 선언해야 경로가 겹치지 않는다.
- **상세 조회 연결** : 카드 클릭 시 `GET /products/{id}` 를 호출해 `description` 표시.
  (현재 `main.py` 는 상품이 없을 때 `500` 을 돌려주는데, 의미상 `404` 가 맞다.)
- **CRUD** : `POST / PUT / DELETE` 가 백엔드에 구현되면 관리자 화면(등록·수정·삭제 폼)을 추가한다.
