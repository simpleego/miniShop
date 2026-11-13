# 2단계 — 상품 클릭 → 상품 상세

> **User Story** : 방문자는 상품을 클릭하면 상품 상세 페이지를 볼 수 있다.

---

## 1. 요청 / 응답

| 구분 | 내용 |
|------|------|
| 사용자 행동 | 목록에서 상품 카드 클릭 |
| 프론트 처리 | `App` 의 상태 변경 : `selectedId = 클릭한 상품 id`, `page = 'detail'` → 상세 화면으로 전환 |
| API 요청 | `GET /products/{id}` (예 : `GET /products/1`) |
| 백엔드 처리 | `SELECT id, name, price, stock, image_url, description FROM products WHERE id = %s AND is_active = 1` |
| API 응답 (성공) | `200` + 상품 1개 객체 (**description 포함**) |
| API 응답 (없음) | `500` + `{"detail": "상품을 찾을 수 없습니다."}` (※ 백엔드가 404 대신 500 을 사용) |
| API 응답 (DB 오류) | `500` + `{"detail": "상품 상세 조회 에러"}` |
| 화면 결과 | 이미지, 이름, 가격, 재고, 설명 + "← 목록으로" 버튼 |
| "← 목록으로" 클릭 | `page = 'list'` → 목록 화면 (목록 API 다시 호출) |

### 요청

```http
GET /products/1 HTTP/1.1
Host: localhost:5173
```

### 응답 예시 (200 OK)

```json
{
  "id": 1,
  "name": "콜라",
  "price": 1500,
  "stock": 50,
  "image_url": "/products/images/cola.svg",
  "description": "시원한 콜라"
}
```

### 응답 예시 (없는 상품 / 판매중지 상품)

```json
{ "detail": "상품을 찾을 수 없습니다." }
```

---

## 2. 이번 단계에서 만드는 파일

| 파일 | 작업 |
|------|------|
| `src/api/products.js` | 수정 — `fetchProduct(id)` 추가 |
| `src/components/ProductCard.jsx` | 수정 — `onClick` props 추가 |
| `src/pages/ProductList.jsx` | 수정 — `onSelect` props 받아서 카드에 전달 |
| `src/pages/ProductDetail.jsx` | **새로 만듦** — 상세 화면 |
| `src/App.jsx` | 수정 — `page`, `selectedId` 상태로 화면 전환 |
| `src/App.css` | 수정 — 상세 화면 스타일 |

---

## 3. 코드

### 3-1. `src/api/products.js` — 아래 함수 추가

```js
// [2단계] 상품 상세 : GET /products/{id}
export function fetchProduct(id, signal) {
  return request(`${API_BASE}/${id}`, signal)
}
```

### 3-2. `src/components/ProductCard.jsx`

```jsx
import "./ProductCard.css";

// props
//   product : 부모가 넘겨준 상품 정보 객체
//   onClick : 카드를 클릭했을 때 실행할 함수 (부모가 정한다)
function ProductCard({ product, onClick }) {
  const soldOut = product.stock === 0;

  return (
    <div
      className={soldOut ? "card sold-out" : "card"}
      onClick={() => onClick(product)}
      // 키보드 사용자도 Enter 로 선택할 수 있게 한다
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === "Enter" && onClick(product)}
    >
      <img className="card-image" src={product.image_url} alt={product.name} />
      <h3 className="card-name">{product.name}</h3>
      <p className="card-price">{product.price.toLocaleString()}원</p>
      <p className="card-stock">
        {soldOut ? "품절" : `재고 ${product.stock}개`}
      </p>
    </div>
  );
}

export default ProductCard;
```

> 품절 상품도 클릭해서 상세 정보는 볼 수 있다. (구매 버튼은 3단계에서 비활성화한다)

### 3-3. `src/pages/ProductList.jsx` — 바뀌는 부분만

```jsx
// ① props 로 onSelect 받기
function ProductList({ onSelect }) {

  // ... (1단계와 동일) ...

  return (
    <div className="product-grid">
      {products.map((product) => (
        // ② 카드 클릭 시 상품 id 를 부모(App)에 알려준다
        <ProductCard
          key={product.id}
          product={product}
          onClick={(p) => onSelect(p.id)}
        />
      ))}
    </div>
  )
}
```

### 3-4. `src/pages/ProductDetail.jsx` (새 파일)

```jsx
import { useEffect, useState } from 'react'
import { fetchProduct } from '../api/products'
import { toImagePath } from '../utils/image'

// 상품 상세 화면
//   productId : 보여줄 상품 id (App 이 넘겨준다)
//   onBack    : "← 목록으로" 를 눌렀을 때 실행할 함수
function ProductDetail({ productId, onBack }) {
  const [product, setProduct] = useState(null)
  const [error, setError] = useState(null)

  // productId 가 바뀔 때마다 상세 API 를 호출한다
  useEffect(() => {
    const controller = new AbortController()

    fetchProduct(productId, controller.signal)
      .then((data) => setProduct({ ...data, image_url: toImagePath(data.image_url) }))
      .catch((err) => {
        if (err.name === 'AbortError') return
        setError(err.message)
      })

    return () => controller.abort()
  }, [productId])

  // 에러 / 로딩 (product 가 아직 null 이면 로딩 중)
  if (error) {
    return (
      <div>
        <button className="back-button" onClick={onBack}>← 목록으로</button>
        <p className="message error">⚠️ {error}</p>
      </div>
    )
  }
  if (!product) return <p className="message">상품 정보를 불러오는 중...</p>

  const soldOut = product.stock === 0

  return (
    <div>
      <button className="back-button" onClick={onBack}>← 목록으로</button>

      <div className="detail">
        <img className="detail-image" src={product.image_url} alt={product.name} />

        <div className="detail-info">
          <h2 className="detail-name">{product.name}</h2>
          <p className="detail-price">{product.price.toLocaleString()}원</p>
          <p className={soldOut ? 'detail-stock sold-out-text' : 'detail-stock'}>
            {soldOut ? '품절' : `재고 ${product.stock}개`}
          </p>
          <p className="detail-desc">{product.description || '상품 설명이 없습니다.'}</p>

          {/* 3단계에서 장바구니 / 바로구매 버튼을 이 자리에 추가한다 */}
        </div>
      </div>
    </div>
  )
}

export default ProductDetail
```

### 3-5. `src/App.jsx`

```jsx
import { useState } from 'react'
import './App.css'
import ProductList from './pages/ProductList'
import ProductDetail from './pages/ProductDetail'

function App() {
  // 지금 보여줄 화면 : 'list' | 'detail'
  const [page, setPage] = useState('list')
  // 상세 화면에서 보여줄 상품 id
  const [selectedId, setSelectedId] = useState(null)

  // 목록에서 상품을 클릭했을 때
  function handleSelect(id) {
    setSelectedId(id)
    setPage('detail')
  }

  // 목록으로 돌아가기
  function goList() {
    setPage('list')
  }

  return (
    <div className="container">
      <header className="header">
        <h1 className="title" onClick={goList}>🥤 음료수 자판기</h1>
      </header>

      {page === 'list' && <ProductList onSelect={handleSelect} />}

      {page === 'detail' && (
        // key 를 상품 id 로 주면, 다른 상품을 보여줄 때 상세 화면을 새로 만든다 (이전 상품 상태가 남지 않음)
        <ProductDetail key={selectedId} productId={selectedId} onBack={goList} />
      )}
    </div>
  )
}

export default App
```

### 3-6. `src/App.css` 에 추가

```css
.title {
  cursor: pointer;
}

.card {
  cursor: pointer;
  transition: transform 0.15s;
}

.card:hover {
  transform: translateY(-4px);
}

.back-button {
  background: none;
  border: none;
  color: #1976d2;
  font-size: 15px;
  cursor: pointer;
  padding: 4px 0;
  margin-bottom: 12px;
}

.detail {
  display: flex;
  gap: 32px;
  flex-wrap: wrap;
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
}

.detail-image {
  width: 220px;
  height: 220px;
  object-fit: contain;
}

.detail-info {
  flex: 1;
  min-width: 220px;
}

.detail-name {
  margin: 0 0 8px;
}

.detail-price {
  font-size: 24px;
  font-weight: bold;
  margin: 8px 0;
}

.detail-stock {
  color: #388e3c;
}

.sold-out-text {
  color: #d32f2f;
}

.detail-desc {
  color: #555;
  margin: 16px 0;
}
```

---

## 4. 설명

### 화면 전환 = 상태 바꾸기
라우터 없이 `page` 상태 값에 따라 **어떤 컴포넌트를 그릴지** 정한다.

```jsx
{page === 'list'   && <ProductList ... />}
{page === 'detail' && <ProductDetail ... />}
```

`setPage('detail')` 을 호출하면 App 이 다시 렌더링되면서 목록 대신 상세 화면이 그려진다.
(단점 : 주소창이 바뀌지 않으므로 새로고침하면 목록으로 돌아간다 — 결정사항에서 감수하기로 함)

### 자식 → 부모로 알리기 (콜백 props)
클릭은 `ProductCard`(손자)에서 일어나지만, 화면을 바꾸는 상태는 `App`(할아버지)에 있다.
그래서 App 이 함수를 내려주고, 아래에서 그 함수를 호출해 "이 상품이 클릭됐다"고 알린다.

```
App ──onSelect──▶ ProductList ──onClick──▶ ProductCard
 ▲                                            │ 클릭
 └────────── handleSelect(id) 호출 ◀───────────┘
```

### 왜 상세 API 를 다시 호출하나?
- 목록 API 에는 `description` 이 없다.
- 목록을 본 뒤 시간이 지났을 수 있으므로, 상세에서 **최신 재고**를 다시 받아야 3·4단계의 재고 확인이 정확하다.

### `key={selectedId}` 의 역할
key 가 바뀌면 React 는 컴포넌트를 **새로 만든다.** 이전 상품의 `product`, `error` 상태가
잠깐 보이는 문제를 막고, effect 안에서 상태를 초기화하는 코드를 따로 쓰지 않아도 된다.

### `AbortController` 는?
1단계와 같은 패턴이다. 왜 필요한지, 빼면 어떤 일이 생기는지는
[01_product_list.md 의 6. 참고 — AbortController 자세히 보기](01_product_list.md#6-참고--abortcontroller-자세히-보기) 를 참고한다.

---

## 5. 확인

- [ ] 카드에 마우스를 올리면 살짝 떠오르고 커서가 손가락 모양이다
- [ ] 카드를 클릭하면 상세 화면에 설명(description)까지 보인다
- [ ] 브라우저 개발자도구 Network 탭에서 `GET /products/1` 요청과 응답을 확인한다
- [ ] "← 목록으로" 또는 제목을 클릭하면 목록으로 돌아간다
- [ ] 품절 상품도 상세 화면이 열리고 "품절" 이 빨간색으로 보인다
