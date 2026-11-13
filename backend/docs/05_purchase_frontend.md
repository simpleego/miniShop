# 5. 프론트 연동 — 구매 버튼

> 목표 : 상품 카드에 **수량 선택 + 구매 버튼**을 붙이고, 구매 후 재고를 갱신한다.
> 작업 위치 : `frontend/` 폴더

---

## 5-1. 화면 구성

```
┌─────────────────┐
│    [이미지]      │
│     콜라         │
│    1,500원       │
│   재고 10개      │
│  [ - ]  2  [ + ] │  ← 수량 (1 ~ min(재고, 10))
│  [ 구매하기 ]    │  ← 품절이면 비활성화, 처리 중이면 "구매 중..."
└─────────────────┘
       ↓ 구매 성공
  "콜라 2개 구매 완료 (3,000원)" 메시지 + 상품 목록 다시 불러오기
```

| 상황 | 화면 동작 |
|---|---|
| 품절 (stock = 0) | 버튼 비활성화, 수량 선택 숨김 |
| 구매 요청 중 | 버튼 비활성화 (**두 번 클릭 방지**) |
| 201 성공 | 성공 메시지, 목록 새로고침 |
| 409 재고 부족 | 서버가 보낸 `detail` 표시, 목록 새로고침 (다른 사람이 먼저 샀을 수 있음) |
| 404 / 500 | 서버가 보낸 `detail` 표시 |

---

## 5-2. 프록시 추가 (`vite.config.js`)

`/products` 처럼 `/orders` 요청도 백엔드로 전달한다.

```js
    proxy: {
      '/search': process.env.API_TARGET || 'http://localhost:8001',
      '/products': 'http://localhost:8000',
      // ✅ 추가 : 주문(구매) API
      '/orders': 'http://localhost:8000',
    },
```

> `vite.config.js` 를 바꾸면 `npm run dev` 를 **다시 실행**해야 적용된다.

---

## 5-3. 주문 API 함수 (`src/api/orders.js`, 신규)

```js
// 백엔드 주문 API 기본주소
const API_BASE = '/orders'

// [구매하기] POST /orders
//   가격은 보내지 않는다 → 서버가 DB 가격으로 계산한다
export async function createOrder(productId, quantity) {
    const res = await fetch(API_BASE, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ product_id: productId, quantity }),
    })

    const body = await res.json().catch(() => ({}))

    if (!res.ok) {
        // 422 는 detail 이 배열이라 문자열 메시지로 바꿔 준다
        const message = typeof body.detail === 'string'
            ? body.detail
            : `요청 오류 (${res.status})`
        throw new Error(message)
    }

    return body   // { order_id, product_name, quantity, total_price, ... }
}
```

| 포인트 | 설명 |
|---|---|
| `method: 'POST'` | fetch 기본값은 GET 이다 |
| `Content-Type` 헤더 | 없으면 FastAPI 가 JSON 으로 읽지 못해 422 가 난다 |
| `JSON.stringify` | 자바스크립트 객체 → JSON 문자열 |
| `product_id` (snake_case) | 백엔드 `OrderIn` 필드 이름과 **똑같이** 맞춘다 |

---

## 5-4. 상품 카드 (`src/components/ProductCard.jsx`)

카드는 **수량 선택**만 직접 관리하고, 실제 구매는 부모(`ProductList`)에게 맡긴다.

```jsx
import { useState } from "react";
import "./ProductCard.css";

// 한 번에 살 수 있는 최대 수량 (백엔드 OrderIn 의 le=10 과 맞춘다)
const MAX_QUANTITY = 10;

// props
//   product : 상품 정보
//   onBuy   : 구매 버튼을 눌렀을 때 부모가 실행할 함수 (product, quantity)
//   buying  : 지금 이 상품을 구매 처리 중인지
function ProductCard({ product, onBuy, buying }) {
  const soldOut = product.stock === 0;
  const maxQty = Math.min(product.stock, MAX_QUANTITY);
  const [quantity, setQuantity] = useState(1);

  // 재고가 줄어 선택한 수량이 재고보다 크면 화면에서는 재고만큼으로 보여 준다
  const qty = Math.min(quantity, Math.max(maxQty, 1));

  return (
    <div className={soldOut ? "card sold-out" : "card"}>
      <img className="card-image" src={product.image_url} alt={product.name} />
      <h3 className="card-name">{product.name}</h3>
      <p className="card-price">{product.price.toLocaleString()}원</p>
      <p className="card-stock">
        {soldOut ? "품절" : `재고 ${product.stock}개`}
      </p>

      {!soldOut && (
        <div className="card-qty">
          <button onClick={() => setQuantity(qty - 1)} disabled={qty <= 1}>-</button>
          <span>{qty}</span>
          <button onClick={() => setQuantity(qty + 1)} disabled={qty >= maxQty}>+</button>
        </div>
      )}

      <button
        className="card-buy"
        disabled={soldOut || buying}
        onClick={() => onBuy(product, qty)}
      >
        {soldOut ? "품절" : buying ? "구매 중..." : "구매하기"}
      </button>
    </div>
  );
}

export default ProductCard;
```

> 💡 화면에서 수량을 재고 이하로 막는 것은 **사용자 안내용**일 뿐이다.
> 화면의 재고는 목록을 불러온 시점의 값이라 이미 바뀌었을 수 있다. **최종 판단은 서버의 409** 다.

### 스타일 추가 (`src/components/ProductCard.css`)

```css
.card-qty {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin: 8px 0;
}
.card-qty button {
  width: 28px;
  height: 28px;
}
.card-buy {
  width: 100%;
  padding: 8px;
  border: none;
  border-radius: 6px;
  background: #2563eb;
  color: white;
  cursor: pointer;
}
.card-buy:disabled {
  background: #9ca3af;
  cursor: not-allowed;
}
```

---

## 5-5. 상품 목록 (`src/pages/ProductList.jsx`)

변경할 것은 3가지다.

1. 목록 불러오기를 **함수로 분리**해서 구매 후에도 다시 호출할 수 있게 한다.
2. 구매 처리 함수 `handleBuy` 를 만든다.
3. 결과 메시지와 "구매 중인 상품 id" 상태를 추가한다.

```jsx
import { useCallback, useEffect, useState } from "react";
import ProductCard from "../components/ProductCard";
import { fetchProducts } from "../api/products";
import { createOrder } from "../api/orders";
import { toImagePath } from "../utils/image";

function ProductList() {
    const [products, setProducts] = useState([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)

    // ✅ 추가 : 구매 관련 상태
    const [buyingId, setBuyingId] = useState(null)   // 지금 구매 처리 중인 상품 id
    const [notice, setNotice] = useState(null)       // { type: 'success' | 'error', text }

    // ✅ 변경 : 목록 불러오기를 함수로 분리 (처음 + 구매 후에 호출)
    const loadProducts = useCallback((signal) => {
        return fetchProducts(signal)
            .then((data) => {
                setProducts(data.map((p) => ({ ...p, image_url: toImagePath(p.image_url) })))
            })
            .catch((err) => {
                if (err.name === 'AbortError') return
                setError(err.message)
            })
    }, [])

    useEffect(() => {
        const controller = new AbortController()
        loadProducts(controller.signal).finally(() => {
            if (!controller.signal.aborted) setLoading(false)
        })
        return () => controller.abort()
    }, [loadProducts])

    // ✅ 추가 : 구매 처리
    async function handleBuy(product, quantity) {
        const ok = window.confirm(
            `${product.name} ${quantity}개를 구매할까요?\n` +
            `(예상 금액 ${(product.price * quantity).toLocaleString()}원)`
        )
        if (!ok) return

        setBuyingId(product.id)
        setNotice(null)
        try {
            const order = await createOrder(product.id, quantity)
            setNotice({
                type: 'success',
                // 금액은 서버가 계산한 값(total_price)을 보여 준다
                text: `${order.product_name} ${order.quantity}개 구매 완료 ` +
                      `(${order.total_price.toLocaleString()}원, 주문번호 ${order.order_id})`,
            })
        } catch (err) {
            setNotice({ type: 'error', text: err.message })
        } finally {
            setBuyingId(null)
            // 성공이든 실패(재고 부족)든 최신 재고로 다시 그린다
            loadProducts()
        }
    }

    if (loading) return <p className="message">상품을 불러오는 중...</p>
    if (error) return <p className="message error">⚠️ {error}</p>
    if (products.length === 0) return <p className="message">판매 중인 상품이 없습니다.</p>

    return (
        <>
            {notice && (
                <p className={`message ${notice.type}`}>
                    {notice.type === 'success' ? '✅' : '⚠️'} {notice.text}
                </p>
            )}
            <div className="product-grid">
                {products.map((product) => (
                    <ProductCard
                        key={product.id}
                        product={product}
                        onBuy={handleBuy}
                        buying={buyingId === product.id}
                    />
                ))}
            </div>
        </>
    )
}

export default ProductList
```

### 코드 읽기 포인트

| 코드 | 설명 |
|---|---|
| `useCallback` | `loadProducts` 를 매번 새로 만들지 않아 `useEffect` 가 반복 실행되지 않는다 |
| `window.confirm` | 실수로 누른 구매를 막는다. "예상 금액" 은 안내용이고 **확정 금액은 서버 응답** |
| `setBuyingId` | 처리 중에 버튼을 막아 **중복 주문**을 방지한다 |
| `finally { loadProducts() }` | 409 가 났다면 다른 사람이 먼저 산 것이므로 최신 재고를 보여 준다 |

---

## ✅ 5단계 확인

백엔드(8000)와 프론트(`npm run dev`)를 모두 실행하고 브라우저에서 확인한다.

| # | 동작 | 기대 결과 |
|---|---|---|
| 1 | 콜라 수량 2 → 구매하기 → 확인 | 성공 메시지, 재고가 2 줄어든다 |
| 2 | `+` 를 계속 누름 | 재고와 10 중 작은 값에서 멈춘다 |
| 3 | 품절 상품 | 버튼 비활성화, 수량 선택 없음 |
| 4 | 구매하기 → **취소** | 아무 요청도 가지 않는다 (개발자 도구 Network 탭 확인) |
| 5 | 재고 3개 상품 수량 3 선택 → DB 에서 `stock = 1` 로 변경 → 구매 | **409 메시지**, 재고 1개로 갱신 |
| 6 | 백엔드 서버를 끄고 구매 | 오류 메시지 표시 (화면이 멈추지 않음) |
| 7 | Network 탭에서 요청 본문 확인 | `product_id`, `quantity` 만 있고 **가격이 없다** |

## 생각해 볼 문제

1. 5번 상황에서 화면 재고(3)와 서버 재고(1)가 달랐다. 어떻게 하면 이런 상황을 줄일 수 있을까?
2. `buyingId` 대신 `boolean` 하나(`buying`)만 쓰면 어떤 차이가 있을까?

다음 단계 (심화) : [06_purchase_advanced.md](06_purchase_advanced.md)
