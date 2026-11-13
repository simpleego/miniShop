# 5단계 — 바로구매 → 구매 화면

> **User Story** : 상품 상세 화면에서 바로구매 버튼을 클릭하면 장바구니에 있는 모든 상품을 구매 상품으로 나열하고,
> 각각의 상품명, 단가, 수량과 총금액을 표시하며, 하단에 결제하기 버튼을 배치한다.
> **결제하기 버튼의 기능은 구현하지 않는다.**
>
> 결정사항 : **현재 상품 + 장바구니 전체** — 보고 있는 상품이 장바구니에 없으면 1개를 넣은 뒤 구매 화면으로 이동한다.

---

## 1. 요청 / 응답

| 구분 | 내용 |
|------|------|
| 사용자 행동 | 상세 화면에서 [바로구매] 클릭 |
| 프론트 처리 ① | 현재 상품이 장바구니에 **없으면** 수량 1 로 추가 / **있으면** 수량 그대로 |
| 프론트 처리 ② | `page = 'checkout'` → 구매 화면으로 전환 |
| API 요청 | **없음** |
| 화면 결과 | 장바구니 전체 상품 표 (상품명, 단가, 수량, 금액) + 총금액 + [결제하기] 버튼 |
| [결제하기] 클릭 | **아무 동작 없음** (기능 미구현) |
| "← 상품으로 돌아가기" 클릭 | `page = 'detail'` → 보던 상품 상세 화면 |

### 시나리오별 결과

| 장바구니 (바로구매 전) | 보고 있는 상품 | 구매 화면에 나오는 목록 |
|------------------------|----------------|--------------------------|
| 비어 있음 | 콜라 | 콜라 × 1 |
| 생수 × 1 | 콜라 | 생수 × 1, 콜라 × 1 |
| 콜라 × 2, 생수 × 1 | 콜라 | 콜라 × 2, 생수 × 1 (콜라 수량 그대로) |

### 화면 예시 (콜라 × 2, 생수 × 1)

```
← 상품으로 돌아가기

구매 상품 확인
┌──────────────┬─────────┬──────┬─────────┐
│ 상품명        │    단가  │ 수량  │    금액  │
├──────────────┼─────────┼──────┼─────────┤
│ 🥤 콜라       │ 1,500원 │  2   │ 3,000원 │
│ 💧 생수 500ml │ 1,000원 │  1   │ 1,000원 │
└──────────────┴─────────┴──────┴─────────┘
                      총 3개   총금액 4,000원

            [        결제하기        ]
```

---

## 2. 이번 단계에서 만드는 파일

| 파일 | 작업 |
|------|------|
| `src/hooks/useCart.js` | 수정 — `ensureInCart`, `totalPrice` 추가 |
| `src/pages/Checkout.jsx` | **새로 만듦** — 구매 화면 |
| `src/App.jsx` | 수정 — `handleBuyNow` 완성, `checkout` 화면 추가 |
| `src/App.css` | 수정 — 구매 화면 스타일 |

---

## 3. 코드

### 3-1. `src/hooks/useCart.js` — 추가하는 부분

`addToCart` 아래에 함수를 추가하고, `return` 에 넣는다.

```js
  // [5단계] 바로구매용 : 장바구니에 없을 때만 1개 추가 (이미 있으면 수량 그대로)
  function ensureInCart(product) {
    if (getQuantity(product.id) === 0) {
      addToCart(product)
    }
  }

  // 장바구니 전체 수량 (헤더 표시용)
  const totalCount = cart.reduce((sum, i) => sum + i.quantity, 0)

  // [5단계] 총금액 : Σ (단가 × 수량)
  const totalPrice = cart.reduce((sum, i) => sum + i.price * i.quantity, 0)

  return { cart, getQuantity, addToCart, ensureInCart, totalCount, totalPrice }
```

### 3-2. `src/pages/Checkout.jsx` (새 파일)

```jsx
// 구매 화면
//   cart       : 장바구니 배열 (App 이 넘겨준다)
//   totalCount : 전체 수량
//   totalPrice : 총금액
//   onBack     : "← 상품으로 돌아가기" 를 눌렀을 때 실행할 함수
function Checkout({ cart, totalCount, totalPrice, onBack }) {
  return (
    <div>
      <button className="back-button" onClick={onBack}>← 상품으로 돌아가기</button>

      <div className="checkout">
        <h2 className="checkout-title">구매 상품 확인</h2>

        {cart.length === 0 ? (
          <p className="message">구매할 상품이 없습니다.</p>
        ) : (
          <>
            <table className="checkout-table">
              <thead>
                <tr>
                  <th>상품명</th>
                  <th className="num">단가</th>
                  <th className="num">수량</th>
                  <th className="num">금액</th>
                </tr>
              </thead>
              <tbody>
                {cart.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <div className="checkout-product">
                        <img src={item.image_url} alt="" className="checkout-image" />
                        {item.name}
                      </div>
                    </td>
                    <td className="num">{item.price.toLocaleString()}원</td>
                    <td className="num">{item.quantity}</td>
                    <td className="num">{(item.price * item.quantity).toLocaleString()}원</td>
                  </tr>
                ))}
              </tbody>
            </table>

            <div className="checkout-total">
              <span>총 {totalCount}개</span>
              <span>
                총금액 <strong>{totalPrice.toLocaleString()}원</strong>
              </span>
            </div>

            {/* 결제하기 버튼 : 배치만 하고 기능은 구현하지 않는다 (요구사항) */}
            {/* TODO: 결제 기능 구현 시 onClick 연결 → 주문 API(POST /orders) 호출 */}
            <button className="btn btn-primary checkout-pay" type="button">
              결제하기
            </button>
          </>
        )}
      </div>
    </div>
  )
}

export default Checkout
```

### 3-3. `src/App.jsx` (최종)

```jsx
import { useState } from 'react'
import './App.css'
import ProductList from './pages/ProductList'
import ProductDetail from './pages/ProductDetail'
import Checkout from './pages/Checkout'
import useCart from './hooks/useCart'

function App() {
  // 지금 보여줄 화면 : 'list' | 'detail' | 'checkout'
  const [page, setPage] = useState('list')
  // 상세 화면에서 보여줄 상품 id (구매 화면에서 돌아올 때도 사용)
  const [selectedId, setSelectedId] = useState(null)

  // 장바구니 (localStorage 에 자동 저장)
  const { cart, getQuantity, addToCart, ensureInCart, totalCount, totalPrice } = useCart()

  // 목록에서 상품 클릭 → 상세 화면
  function handleSelect(id) {
    setSelectedId(id)
    setPage('detail')
  }

  // 목록으로
  function goList() {
    setPage('list')
  }

  // 구매 화면 → 보던 상품 상세로
  function goDetail() {
    setPage('detail')
  }

  // 장바구니 버튼 : 재고 확인 → 사용자 확인 → 담기
  function handleAddToCart(product) {
    const inCart = getQuantity(product.id)

    if (inCart >= product.stock) {
      alert(`재고가 부족합니다. (재고 ${product.stock}개, 장바구니 ${inCart}개)`)
      return
    }

    const ok = window.confirm(
      `'${product.name}' 1개를 장바구니에 담을까요?\n(현재 장바구니: ${inCart}개)`
    )
    if (!ok) return

    addToCart(product)
    alert('장바구니에 담았습니다.')
  }

  // ✅ 바로구매 버튼 : 현재 상품이 장바구니에 없으면 넣고 → 구매 화면으로
  function handleBuyNow(product) {
    ensureInCart(product)
    setPage('checkout')
  }

  return (
    <div className="container">
      <header className="header">
        <h1 className="title" onClick={goList}>🥤 음료수 자판기</h1>
        <span className="cart-badge">🛒 {totalCount}</span>
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

      {page === 'checkout' && (
        <Checkout
          cart={cart}
          totalCount={totalCount}
          totalPrice={totalPrice}
          onBack={goDetail}
        />
      )}
    </div>
  )
}

export default App
```

### 3-4. `src/App.css` 에 추가

```css
.checkout {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
}

.checkout-title {
  margin: 0 0 16px;
}

.checkout-table {
  width: 100%;
  border-collapse: collapse;
}

.checkout-table th,
.checkout-table td {
  padding: 12px 8px;
  border-bottom: 1px solid #eee;
  text-align: left;
}

.checkout-table th {
  background: #f5f5f5;
  font-size: 14px;
  color: #555;
}

.checkout-table .num {
  text-align: right;
  white-space: nowrap;
}

.checkout-product {
  display: flex;
  align-items: center;
  gap: 8px;
}

.checkout-image {
  width: 36px;
  height: 36px;
  object-fit: contain;
}

.checkout-total {
  display: flex;
  justify-content: flex-end;
  gap: 24px;
  align-items: baseline;
  margin: 20px 0;
  font-size: 18px;
}

.checkout-total strong {
  font-size: 24px;
  color: #d32f2f;
}

.checkout-pay {
  width: 100%;
}
```

---

## 4. 설명

### 바로구매 = 담기 + 화면 전환

```js
function handleBuyNow(product) {
  ensureInCart(product)   // ① 장바구니에 없으면 1개 추가 (확인창 없음)
  setPage('checkout')     // ② 구매 화면으로
}
```

- 바로구매는 사용자가 이미 "사겠다"고 의사를 밝힌 것이므로 **확인창을 띄우지 않는다.**
- 이미 담긴 상품이면 수량을 늘리지 않는다 → 바로구매를 여러 번 눌러도 수량이 계속 늘어나지 않는다.
- `setCart` 와 `setPage` 는 React 가 **한 번에 묶어서(batching)** 처리하므로,
  구매 화면이 그려질 때는 이미 상품이 장바구니에 들어가 있다.

### 금액 계산은 저장하지 않고 "계산"한다
`totalPrice`, 각 줄의 `price * quantity` 는 상태로 따로 저장하지 않는다.
`cart` 만 있으면 언제든 계산할 수 있으므로, 상태를 두 개로 나누면 값이 서로 어긋날 위험만 생긴다.

```js
const totalPrice = cart.reduce((sum, i) => sum + i.price * i.quantity, 0)
//   콜라   0    + 1500 × 2 = 3000
//   생수   3000 + 1000 × 1 = 4000
```

### 결제하기 버튼
요구사항대로 **onClick 을 연결하지 않았다.** 나중에 결제를 구현할 때는

1. 백엔드에 주문 API(`POST /orders`)를 만들고 (`orders`, `order_items` 테이블 사용)
2. 서버에서 **가격과 재고를 다시 확인**한 뒤 (장바구니의 가격은 담을 때의 값이라 바뀌었을 수 있다)
3. 성공하면 장바구니를 비우는 함수(`clearCart`)를 `useCart` 에 추가한다.

### "← 상품으로 돌아가기"
`selectedId` 를 그대로 가지고 있으므로 `setPage('detail')` 만 하면 보던 상품으로 돌아간다.
이때 상세 화면은 다시 만들어지면서 상세 API 를 다시 호출한다(최신 재고 반영).

---

## 5. 확인

- [ ] 장바구니가 빈 상태에서 콜라 [바로구매] → 구매 화면에 콜라 × 1, 헤더 🛒 1
- [ ] 생수를 장바구니에 담고 → 콜라 [바로구매] → 생수, 콜라 두 줄
- [ ] 콜라 2개를 담고 → 콜라 [바로구매] → 콜라 수량 2 그대로
- [ ] 각 줄의 금액 = 단가 × 수량, 총금액 = 금액의 합
- [ ] [결제하기] 를 눌러도 아무 일도 일어나지 않는다
- [ ] "← 상품으로 돌아가기" → 보던 상품 상세 화면

---

## 6. 개선 과제 (다음 시간)

| 과제 | 내용 |
|------|------|
| 장바구니 페이지 | 헤더의 🛒 를 누르면 장바구니 화면으로 이동 |
| 수량 변경 / 삭제 | 구매 화면에서 +/− 버튼, 삭제 버튼 (재고 이하로 제한) |
| 확인 모달 | `window.confirm` 대신 직접 만든 모달 컴포넌트 |
| 라우터 도입 | `react-router-dom` 으로 바꿔 주소(`/products/1`, `/checkout`)와 새로고침 지원 |
| 결제 | `POST /orders` API + 결제하기 버튼 연결 |
