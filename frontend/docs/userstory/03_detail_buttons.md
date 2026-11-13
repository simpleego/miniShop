# 3단계 — 상세 화면에 장바구니 / 바로구매 버튼 배치

> **User Story** : 상품 상세 페이지에는 장바구니, 바로구매 버튼이 있고, 클릭하면 해당 기능이 수행된다.
>
> 이번 단계는 **버튼 배치 + 클릭 이벤트 연결**까지 한다.
> 버튼이 실제로 하는 일은 4단계(장바구니), 5단계(바로구매)에서 채운다.

---

## 1. 요청 / 응답

| 구분 | 장바구니 버튼 | 바로구매 버튼 |
|------|---------------|---------------|
| 사용자 행동 | 상세 화면에서 [🛒 장바구니] 클릭 | 상세 화면에서 [바로구매] 클릭 |
| 프론트 처리 | `ProductDetail` → `onAddToCart(product)` 호출 → App 의 `handleAddToCart` 실행 | `ProductDetail` → `onBuyNow(product)` 호출 → App 의 `handleBuyNow` 실행 |
| API 요청 | 없음 | 없음 |
| 화면 결과 (3단계) | 임시 알림 "장바구니 기능 : 콜라" | 임시 알림 "바로구매 기능 : 콜라" |
| 품절 상품 | 버튼 비활성화 (클릭 불가) | 버튼 비활성화 (클릭 불가) |

> 버튼 클릭 시 함수에 넘기는 `product` 는 2단계에서 상세 API 로 받은 **최신 상품 정보**다.
>
> ```json
> { "id": 1, "name": "콜라", "price": 1500, "stock": 50, "image_url": "/images/cola.svg", "description": "시원한 콜라" }
> ```

---

## 2. 이번 단계에서 만드는 파일

| 파일 | 작업 |
|------|------|
| `src/pages/ProductDetail.jsx` | 수정 — 버튼 2개, `onAddToCart` / `onBuyNow` props |
| `src/App.jsx` | 수정 — 임시 핸들러 2개를 만들어 상세 화면에 전달 |
| `src/App.css` | 수정 — 버튼 스타일 |

---

## 3. 코드

### 3-1. `src/pages/ProductDetail.jsx` — 바뀌는 부분

```jsx
// ① props 에 onAddToCart, onBuyNow 추가
function ProductDetail({ productId, onBack, onAddToCart, onBuyNow }) {

  // ... (2단계와 동일 : 상태, useEffect, 에러/로딩 처리) ...

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

          {/* ② 버튼 영역 : 품절이면 두 버튼 모두 비활성화 */}
          <div className="detail-buttons">
            <button
              className="btn btn-outline"
              disabled={soldOut}
              onClick={() => onAddToCart(product)}
            >
              🛒 장바구니
            </button>
            <button
              className="btn btn-primary"
              disabled={soldOut}
              onClick={() => onBuyNow(product)}
            >
              바로구매
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
```

### 3-2. `src/App.jsx`

```jsx
import { useState } from 'react'
import './App.css'
import ProductList from './pages/ProductList'
import ProductDetail from './pages/ProductDetail'

function App() {
  const [page, setPage] = useState('list')
  const [selectedId, setSelectedId] = useState(null)

  function handleSelect(id) {
    setSelectedId(id)
    setPage('detail')
  }

  function goList() {
    setPage('list')
  }

  // ✅ 장바구니 버튼 (임시) — 4단계에서 완성
  function handleAddToCart(product) {
    alert(`장바구니 기능 : ${product.name}`)
  }

  // ✅ 바로구매 버튼 (임시) — 5단계에서 완성
  function handleBuyNow(product) {
    alert(`바로구매 기능 : ${product.name}`)
  }

  return (
    <div className="container">
      <header className="header">
        <h1 className="title" onClick={goList}>🥤 음료수 자판기</h1>
      </header>

      {page === 'list' && <ProductList onSelect={handleSelect} />}

      {page === 'detail' && (
        <ProductDetail
          key={selectedId}
          productId={selectedId}
          onBack={goList}
          onAddToCart={handleAddToCart}
          onBuyNow={handleBuyNow}
        />
      )}
    </div>
  )
}

export default App
```

### 3-3. `src/App.css` 에 추가

```css
.detail-buttons {
  display: flex;
  gap: 12px;
  margin-top: 24px;
}

.btn {
  flex: 1;
  padding: 12px 16px;
  font-size: 16px;
  font-weight: bold;
  border-radius: 8px;
  cursor: pointer;
}

.btn-outline {
  background: #fff;
  color: #1976d2;
  border: 2px solid #1976d2;
}

.btn-primary {
  background: #1976d2;
  color: #fff;
  border: 2px solid #1976d2;
}

.btn:disabled {
  background: #e0e0e0;
  color: #9e9e9e;
  border-color: #e0e0e0;
  cursor: not-allowed;
}
```

---

## 4. 설명

### 왜 버튼 기능을 App 에 두나?
- **장바구니** 데이터는 상세 화면, 구매 화면, 헤더(개수)가 함께 쓴다 → App 에 있어야 한다.
- **바로구매**는 화면을 `checkout` 으로 바꿔야 한다 → `page` 상태가 있는 App 에서 처리해야 한다.

그래서 `ProductDetail` 은 **"버튼이 눌렸다 + 어떤 상품인지"만 알려주고**, 실제 동작은 App 이 결정한다.
(1·2단계의 `onSelect` 와 같은 패턴)

### 먼저 임시 동작(alert)으로 연결하는 이유
화면 → 이벤트 → 처리 함수까지 **연결이 되는지 먼저 확인**하고, 그 다음에 기능을 채운다.
한 번에 다 만들면 오류가 났을 때 어디가 문제인지 찾기 어렵다.

### `disabled` 속성
`disabled` 인 버튼은 클릭 이벤트가 발생하지 않는다. 품절 상품은 담거나 살 수 없으므로
화면에서 아예 막는 것이 사용자에게 가장 분명하다.

---

## 5. 확인

- [ ] 상세 화면에 [🛒 장바구니] [바로구매] 버튼이 보인다
- [ ] 각각 클릭하면 상품 이름이 들어간 알림창이 뜬다
- [ ] 품절 상품의 상세 화면에서는 두 버튼이 회색이고 클릭되지 않는다
