# 4단계 — 장바구니 담기 (확인 후 담기)

> **User Story** : 장바구니 버튼을 클릭하면, 해당 상품을 장바구니에 넣기 전에 사용자에게 확인하고 장바구니에 넣는다.

---

## 1. 요청 / 응답

| 구분 | 내용 |
|------|------|
| 사용자 행동 | 상세 화면에서 [🛒 장바구니] 클릭 |
| 프론트 처리 ① | 장바구니에 이미 담긴 수량이 재고 이상이면 → "재고가 부족합니다" 알림 후 **종료** |
| 프론트 처리 ② | 확인창 : `'콜라' 1개를 장바구니에 담을까요? (현재 장바구니: 0개)` |
| [확인] 선택 | `cart` 상태에 추가 (이미 있으면 수량 +1) → localStorage 자동 저장 → "장바구니에 담았습니다" 알림 |
| [취소] 선택 | 아무 일도 일어나지 않음 |
| API 요청 | **없음** (장바구니는 프론트에서만 관리) |
| 화면 결과 | 상세 화면 그대로 + 헤더의 🛒 개수 증가 |

### 상태 변화 예시

콜라(id 1)를 2번, 생수(id 12)를 1번 담았을 때

```js
// 담기 전
cart = []

// 콜라 담기 → 새 항목 추가
cart = [
  { id: 1, name: '콜라', price: 1500, image_url: '/images/cola.svg', stock: 50, quantity: 1 }
]

// 콜라 한 번 더 → 같은 상품이므로 수량 +1
cart = [
  { id: 1, name: '콜라', price: 1500, image_url: '/images/cola.svg', stock: 50, quantity: 2 }
]

// 생수 담기 → 새 항목 추가
cart = [
  { id: 1,  name: '콜라',       price: 1500, image_url: '/images/cola.svg',  stock: 50,  quantity: 2 },
  { id: 12, name: '생수 500ml', price: 1000, image_url: '/images/water.svg', stock: 100, quantity: 1 }
]
```

### localStorage 저장 내용

개발자도구 → Application → Local Storage → `http://localhost:5173`

| Key | Value |
|-----|-------|
| `vm-cart` | `[{"id":1,"name":"콜라","price":1500,"image_url":"/images/cola.svg","stock":50,"quantity":2},{"id":12,...}]` |

---

## 2. 이번 단계에서 만드는 파일

| 파일 | 작업 |
|------|------|
| `src/hooks/useCart.js` | **새로 만듦** — 장바구니 상태 + localStorage |
| `src/App.jsx` | 수정 — `useCart` 사용, `handleAddToCart` 완성, 헤더에 개수 표시 |
| `src/App.css` | 수정 — 헤더 장바구니 배지 |

---

## 3. 코드

### 3-1. `src/hooks/useCart.js` (새 파일)

```js
import { useEffect, useState } from 'react'

// localStorage 에 저장할 때 쓰는 이름(key)
const STORAGE_KEY = 'vm-cart'

// 저장된 장바구니 읽기
//   저장된 값이 없거나, 깨졌거나, 브라우저가 localStorage 를 막은 경우 빈 배열
function loadCart() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    return saved ? JSON.parse(saved) : []
  } catch {
    return []
  }
}

// 장바구니 커스텀 훅
//   여러 컴포넌트에서 쓰는 장바구니 로직을 한 곳에 모아 둔다.
function useCart() {
  // 처음 한 번만 localStorage 에서 읽어 초기값으로 쓴다 (함수를 넘기면 첫 렌더링 때만 실행)
  const [cart, setCart] = useState(loadCart)

  // cart 가 바뀔 때마다 localStorage 에 저장
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(cart))
    } catch {
      // 저장 실패(용량 초과, 시크릿 모드 등)해도 화면은 계속 동작하게 둔다
    }
  }, [cart])

  // 장바구니에 담긴 특정 상품의 수량 (없으면 0)
  function getQuantity(productId) {
    const item = cart.find((i) => i.id === productId)
    return item ? item.quantity : 0
  }

  // 상품 1개 담기 : 이미 있으면 수량 +1, 없으면 새 항목 추가
  //   상태는 직접 바꾸지 않고(push 금지) 새 배열을 만들어 setCart 에 넘긴다.
  function addToCart(product) {
    const exists = cart.some((i) => i.id === product.id)

    if (exists) {
      setCart(
        cart.map((i) =>
          i.id === product.id ? { ...i, quantity: i.quantity + 1 } : i
        )
      )
    } else {
      setCart([
        ...cart,
        {
          id: product.id,
          name: product.name,
          price: product.price,
          image_url: product.image_url,
          stock: product.stock,
          quantity: 1,
        },
      ])
    }
  }

  // 장바구니 전체 수량 (헤더 표시용) : 콜라 2 + 생수 1 = 3
  const totalCount = cart.reduce((sum, i) => sum + i.quantity, 0)

  return { cart, getQuantity, addToCart, totalCount }
}

export default useCart
```

### 3-2. `src/App.jsx`

```jsx
import { useState } from 'react'
import './App.css'
import ProductList from './pages/ProductList'
import ProductDetail from './pages/ProductDetail'
import useCart from './hooks/useCart'

function App() {
  const [page, setPage] = useState('list')
  const [selectedId, setSelectedId] = useState(null)

  // ✅ 장바구니 (localStorage 에 자동 저장)
  const { getQuantity, addToCart, totalCount } = useCart()

  function handleSelect(id) {
    setSelectedId(id)
    setPage('detail')
  }

  function goList() {
    setPage('list')
  }

  // ✅ 장바구니 버튼 : 재고 확인 → 사용자 확인 → 담기
  function handleAddToCart(product) {
    const inCart = getQuantity(product.id)

    // ① 이미 재고만큼 담았으면 더 담을 수 없다 (확인창도 띄우지 않음)
    if (inCart >= product.stock) {
      alert(`재고가 부족합니다. (재고 ${product.stock}개, 장바구니 ${inCart}개)`)
      return
    }

    // ② 담기 전에 사용자에게 확인
    const ok = window.confirm(
      `'${product.name}' 1개를 장바구니에 담을까요?\n(현재 장바구니: ${inCart}개)`
    )
    if (!ok) return   // 취소 → 아무것도 하지 않음

    // ③ 담기
    addToCart(product)
    alert('장바구니에 담았습니다.')
  }

  // 바로구매 버튼 (임시) — 5단계에서 완성
  function handleBuyNow(product) {
    alert(`바로구매 기능 : ${product.name}`)
  }

  return (
    <div className="container">
      <header className="header">
        <h1 className="title" onClick={goList}>🥤 음료수 자판기</h1>
        {/* ✅ 장바구니 개수 표시 */}
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
    </div>
  )
}

export default App
```

### 3-3. `src/App.css` 에 추가

```css
.cart-badge {
  background: #1976d2;
  color: #fff;
  padding: 6px 14px;
  border-radius: 20px;
  font-weight: bold;
}
```

---

## 4. 설명

### 커스텀 훅(`useCart`)이란?
`use` 로 시작하는 함수 안에서 `useState`, `useEffect` 를 사용해 **상태 로직을 묶어 둔 것**이다.
App 은 "장바구니를 어떻게 저장하는지" 몰라도 `addToCart(product)` 만 호출하면 된다.
5단계에서 바로구매용 함수를 여기에 하나 더 추가한다.

### 불변성 — 배열을 직접 바꾸지 않는다

```js
cart.push(newItem)          // ❌ 같은 배열이 바뀌어서 React 가 변경을 알아채지 못한다
cart[0].quantity += 1       // ❌ 마찬가지

setCart([...cart, newItem])                    // ✅ 새 배열
setCart(cart.map(i => i.id === id ? { ...i, quantity: i.quantity + 1 } : i))  // ✅ 새 배열 + 새 객체
```

### localStorage 흐름

```
첫 렌더링 : useState(loadCart)  → localStorage 의 'vm-cart' 읽기 → cart 초기값
담기      : setCart(새 배열)     → 화면 다시 그림 → useEffect([cart]) 실행 → localStorage 저장
새로고침  : 다시 loadCart        → 저장해 둔 장바구니 복원
```

- localStorage 는 **문자열만** 저장하므로 `JSON.stringify` / `JSON.parse` 로 변환한다.
- `try / catch` : 시크릿 모드나 저장 공간 부족 등으로 실패해도 화면이 멈추지 않게 한다.

### `window.confirm()`
- [확인] → `true`, [취소] → `false` 를 돌려준다.
- 사용자가 고를 때까지 코드 실행이 멈춘다 (가장 간단한 확인 방법).
- 디자인을 바꿀 수 없으므로, 실무에서는 직접 만든 모달 컴포넌트를 많이 쓴다. → 개선 과제

### 재고 확인을 확인창보다 먼저 하는 이유
"담을까요?" → [확인] → "재고가 부족합니다" 순서면 사용자가 헛수고를 한다.
담을 수 없는 경우는 **묻기 전에** 알려준다.

---

## 5. 확인

- [ ] [🛒 장바구니] 클릭 → 확인창 → [확인] → "담았습니다" + 헤더 숫자 증가
- [ ] 확인창에서 [취소] → 헤더 숫자 변화 없음
- [ ] 같은 상품을 여러 번 담으면 확인창의 "현재 장바구니" 숫자가 늘어난다
- [ ] 새로고침해도 헤더 숫자가 유지된다
- [ ] 개발자도구 → Application → Local Storage 에서 `vm-cart` 값을 확인한다
- [ ] (재고 테스트) DB 에서 재고 1개인 상품을 2번 담으면 두 번째에 "재고가 부족합니다"
