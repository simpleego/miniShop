# 미니 쇼핑몰 메인 화면 구성

미니 쇼핑몰이라면 "투입 금액" 같은 자판기 개념은 빼고, **장바구니·로그인·여러 페이지 이동**을 중심으로 구성하는 게 좋습니다. 가장 큰 차이는 화면이 하나가 아니라 **여러 페이지**가 된다는 점입니다. 그래서 상단과 하단은 모든 페이지에서 공통으로 쓰고, 바디만 페이지마다 바뀌는 구조가 됩니다.

## 1. 메인 화면 구성

```
┌────────────────────────────────────────────────┐
│ HEADER                                         │
│ [🥤 로고]  [ 검색창 🔍 ]   로그인 | 🛒 장바구니(3) │
│ 전체 | 탄산 | 생수 | 주스 | 커피     ← 카테고리 메뉴 │
├────────────────────────────────────────────────┤
│ BODY (페이지마다 바뀌는 영역)                     │
│  ┌──────────────────────────────────────────┐  │
│  │  배너 / 이벤트 슬라이드                     │  │
│  └──────────────────────────────────────────┘  │
│  ■ 인기 상품                                    │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐           │
│  │ 이미지 │ │ 이미지 │ │ 이미지 │ │ 이미지 │           │
│  │ 콜라   │ │ 사이다 │ │ 물    │ │ 오렌지 │           │
│  │1,500원│ │ 품절  │ │ 800원 │ │ 800원 │           │
│  │[담기] │ │      │ │[담기] │ │[담기] │           │
│  └──────┘ └──────┘ └──────┘ └──────┘           │
│  ■ 신상품 ...                                   │
├────────────────────────────────────────────────┤
│ FOOTER                                         │
│ 회사 정보 | 이용약관 | 개인정보처리방침 | 고객센터     │
│ © 2026 음료 자판기                               │
└────────────────────────────────────────────────┘
```

## 2. 페이지 구성 (React Router 사용)

| 경로 | 페이지 | 내용 |
|---|---|---|
| `/` | Home | 배너, 인기/신상품 목록 |
| `/products?category=탄산` | ProductList | 카테고리별/검색 결과 목록 |
| `/products/:id` | ProductDetail | 상세 정보, 수량 선택, 장바구니 담기 |
| `/cart` | Cart | 담은 상품, 수량 변경, 합계 |
| `/order` | Order | 배송지 입력, 결제 |
| `/login`, `/signup` | 로그인 / 회원가입 | |
| `/mypage` | MyPage | 주문 내역 |

## 3. 폴더 구조

```
src/
├─ App.jsx                 ← 라우터 설정만 담당
├─ layouts/
│  └─ MainLayout.jsx       ← Header + <Outlet/> + Footer
├─ components/
│  ├─ Header.jsx
│  ├─ SearchBar.jsx
│  ├─ CategoryNav.jsx
│  ├─ Banner.jsx
│  ├─ ProductCard.jsx      ← 이미 있음
│  ├─ ProductGrid.jsx
│  └─ Footer.jsx
├─ pages/
│  ├─ Home.jsx
│  ├─ ProductList.jsx
│  ├─ ProductDetail.jsx
│  ├─ Cart.jsx
│  └─ Login.jsx
├─ context/
│  └─ CartContext.jsx      ← 장바구니 전역 상태
└─ api/
   └─ productApi.js        ← 백엔드 호출 함수
```

## 4. 핵심 코드

### App.jsx: 이제는 조립이 아니라 라우팅을 담당합니다

```jsx
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import MainLayout from './layouts/MainLayout'
import Home from './pages/Home'
import ProductDetail from './pages/ProductDetail'
import Cart from './pages/Cart'
import { CartProvider } from './context/CartContext'

export default function App() {
  return (
    <CartProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<MainLayout />}>
            <Route path="/" element={<Home />} />
            <Route path="/products/:id" element={<ProductDetail />} />
            <Route path="/cart" element={<Cart />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </CartProvider>
  )
}
```

### MainLayout.jsx: 상단과 하단을 고정하고 바디만 교체합니다

```jsx
import { Outlet } from 'react-router-dom'
import Header from '../components/Header'
import Footer from '../components/Footer'

export default function MainLayout() {
  return (
    <div className="layout">
      <Header />
      <main className="content"><Outlet /></main>  {/* 여기만 페이지별로 바뀜 */}
      <Footer />
    </div>
  )
}
```

### CartContext.jsx: 장바구니를 어디서든 쓸 수 있게 합니다

```jsx
import { createContext, useContext, useState } from 'react'

const CartContext = createContext()

export function CartProvider({ children }) {
  const [items, setItems] = useState([])

  const addToCart = (product, qty = 1) => {
    setItems((prev) => {
      const found = prev.find((i) => i.id === product.id)
      return found
        ? prev.map((i) => (i.id === product.id ? { ...i, qty: i.qty + qty } : i))
        : [...prev, { ...product, qty }]
    })
  }

  const removeFromCart = (id) => setItems((prev) => prev.filter((i) => i.id !== id))
  const totalCount = items.reduce((sum, i) => sum + i.qty, 0)

  return (
    <CartContext.Provider value={{ items, addToCart, removeFromCart, totalCount }}>
      {children}
    </CartContext.Provider>
  )
}

export const useCart = () => useContext(CartContext)
```

### Header.jsx: 장바구니 개수를 Context에서 직접 읽습니다

```jsx
import { Link } from 'react-router-dom'
import { useCart } from '../context/CartContext'

export default function Header() {
  const { totalCount } = useCart()
  return (
    <header className="header">
      <Link to="/" className="logo">🥤 음료 자판기</Link>
      <input className="search" placeholder="음료 검색" />
      <nav>
        <Link to="/login">로그인</Link>
        <Link to="/cart">🛒 장바구니({totalCount})</Link>
      </nav>
    </header>
  )
}
```

## 5. 이전 구조와 달라지는 점

| 구분 | 자판기 방식 | 미니 쇼핑몰 방식 |
|---|---|---|
| App.jsx 역할 | 컴포넌트 조립 + 상태 관리 | 라우팅 설정 |
| 공통 레이아웃 | App에 직접 배치 | MainLayout + `<Outlet/>` |
| 공유 상태 | 투입 금액 (props로 전달) | 장바구니, 로그인 정보 (Context) |
| 하단 | 금액 투입, 반환 버튼 | 회사 정보, 약관 링크 |
| 상품 클릭 | 즉시 구매 | 상세 페이지로 이동 또는 장바구니 담기 |

장바구니를 props 대신 Context로 관리하는 이유가 있습니다. Header(개수 표시), ProductCard(담기), Cart 페이지(목록)처럼 **서로 멀리 떨어진 컴포넌트들이 같은 데이터를 쓰기 때문**입니다. props로 넘기면 중간 컴포넌트를 여러 단계 거쳐야 합니다.

## 6. 추천 진행 순서

1. `npm install react-router-dom`
2. MainLayout + Header + Footer + Home 페이지 (지금 있는 상품 그리드를 Home으로 옮기기)
3. CartContext와 장바구니 페이지
4. 상품 상세 페이지
5. 백엔드 API 연동 (상품 목록 → 장바구니 → 주문 순서)
6. 로그인/회원가입
