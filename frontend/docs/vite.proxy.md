# Vite proxy 설정 쉽게 이해하기

> **한 줄 요약** : proxy 는 **Vite 개발 서버가 대신 백엔드에 요청을 전달해 주는 "중계" 기능**이다.

---

## 1. 왜 필요한가? (CORS 문제)

프론트와 백엔드는 포트가 다르다.

| 서버 | 주소 |
|------|------|
| 프론트 (Vite) | `http://localhost:5173` |
| 백엔드 (FastAPI) | `http://localhost:8000` |

브라우저는 보안 때문에 **다른 주소(출처, Origin)로 보내는 요청을 기본적으로 막는다.** 이것을 **CORS 정책**이라고 한다.
그래서 5173 에서 8000 으로 직접 `fetch` 하면 다음 에러가 난다.

```
❌ Access to fetch at 'http://localhost:8000/products' from origin
   'http://localhost:5173' has been blocked by CORS policy
```

현재 `backend/app/main.py` 에는 CORS 를 허용하는 설정(`CORSMiddleware`)이 없어서 이 에러가 그대로 발생한다.

---

## 2. proxy 가 해결하는 방법

```
❌ proxy 없이
브라우저(5173) ───────────────────────▶ 백엔드(8000)    ← 브라우저가 차단

✅ proxy 사용
브라우저(5173) ──▶ Vite 서버(5173) ──▶ 백엔드(8000)
     같은 주소라 OK        서버끼리 통신이라 CORS 없음
```

- 브라우저는 **자기 주소(5173)** 로만 요청하므로 막을 이유가 없다.
- Vite 서버가 그 요청을 받아 백엔드로 넘기고, 받은 응답을 브라우저에 돌려준다.
- CORS 는 **브라우저만** 검사하는 규칙이라 서버끼리 주고받을 때는 해당되지 않는다.

---

## 3. 현재 설정 읽기

```js
server: {
  proxy: {
    '/search': process.env.API_TARGET || 'http://localhost:8001',
  },
},
```

| 부분 | 의미 |
|------|------|
| `'/search'` | 주소가 `/search` 로 **시작하는** 요청을 중계한다 |
| `process.env.API_TARGET` | 실행할 때 환경변수 `API_TARGET` 을 주면 그 주소로 보낸다 |
| `\|\| 'http://localhost:8001'` | 환경변수가 없으면 8001 포트(테스트 DB 서버)로 보낸다 |

예시 :

```
fetch('/search/products?keyword=콜라')
  → http://localhost:5173/search/products?keyword=콜라   (브라우저가 보는 주소)
  → http://localhost:8001/search/products?keyword=콜라   (Vite 가 실제로 보내는 주소)
```

**경로는 그대로 붙어서 전달된다.** 앞의 서버 주소만 바뀐다.

---

## 4. 자판기 화면용 설정 추가

```js
proxy: {
  '/search': process.env.API_TARGET || 'http://localhost:8001',
  '/products': 'http://localhost:8000',   // ✅ 추가
},
```

| 프론트 코드 | 실제로 가는 곳 |
|-------------|----------------|
| `fetch('/products')` | `http://localhost:8000/products` |
| `fetch('/products/1')` | `http://localhost:8000/products/1` |
| `fetch('/search/categories')` | `http://localhost:8001/search/categories` |

그래서 프론트 코드에는 `http://localhost:8000` 을 쓰지 않고 `/products` 만 적는다.

---

## 5. 객체 형태로 쓰기 (옵션이 필요할 때)

문자열 대신 객체로 쓰면 세부 옵션을 줄 수 있다.

```js
'/api': {
  target: 'http://localhost:8000',
  changeOrigin: true,                            // 요청 헤더의 Host 를 target 주소로 바꿔 줌
  rewrite: (path) => path.replace(/^\/api/, ''), // '/api/products' → '/products' 로 앞부분 제거
},
```

`rewrite` 는 프론트에서 모든 API 에 `/api` 를 붙여 구분하고 싶을 때 쓴다.
지금 프로젝트처럼 프론트와 백엔드의 경로가 같으면 필요 없다.

---

## 6. 꼭 기억할 점

1. **`vite.config.js` 를 수정하면 `npm run dev` 를 다시 실행**해야 적용된다.
2. **개발 서버에서만** 동작한다. `npm run build` 로 만든 배포 결과물에는 proxy 가 없다.
   배포할 때는 Nginx 같은 웹서버 설정이나 백엔드의 CORS 설정으로 해결한다.
3. **경로 앞부분이 겹치면 함께 넘어간다.** `/products` 를 설정하면 `/products/images/cola.svg` 도 백엔드로 간다.
   그래서 이미지는 `public` 폴더의 `/images/...` 경로를 쓴다. (`userstory/01_product_list.md` 의 `toImagePath` 참고)
4. **브라우저 Network 탭에는 `localhost:5173/products` 로 보인다.**
   실제로 8000 번에 도착했는지는 백엔드 터미널 로그(`상품 목록 조회`)로 확인한다.

---

## 7. 배포할 때는?

`vite.config.js` 의 proxy 설정 자체는 **개발 중에만** 쓰인다.
`npm run dev` 로 띄운 Vite 개발 서버만 이 설정을 읽고, `npm run build` 로 만든 결과물(`dist` 폴더)은
HTML, JS, CSS 파일일 뿐이라 중계해 줄 서버가 없다.

하지만 **프론트와 백엔드의 주소가 다르다는 문제는 배포한 뒤에도 그대로 남는다.**
그래서 배포할 때는 아래 방법 중 하나로 해결한다.

| 방법 | 구조 | 프론트 코드 |
|------|------|-------------|
| **① Nginx 리버스 프록시** (가장 많이 씀) | Nginx 한 서버가 화면 파일은 직접 주고, `/products` 요청은 백엔드로 넘긴다 | `fetch('/products')` 그대로 |
| **② FastAPI 가 화면까지 제공** | 빌드한 `dist` 를 FastAPI 의 `StaticFiles` 로 서빙한다 | `fetch('/products')` 그대로 |
| **③ 주소를 분리하고 CORS 허용** | `shop.com` / `api.shop.com` 처럼 따로 운영하고, 백엔드에 `CORSMiddleware` 를 추가한다 | 전체 주소 필요 (예 : `https://api.shop.com/products`) |

### 7-1. ① Nginx — Vite proxy 와 같은 개념이 Nginx 로 옮겨간다

```nginx
server {
    listen 80;

    # 화면 파일 (npm run build 결과물)
    location / {
        root /var/www/vmshop/dist;
        try_files $uri /index.html;
    }

    # API 요청은 백엔드로 중계 (Vite proxy 가 하던 일)
    location /products {
        proxy_pass http://localhost:8000;
    }
}
```

브라우저 입장에서는 모든 요청이 같은 주소로 가므로 CORS 문제가 생기지 않는다.

### 7-2. ③ 주소를 분리할 때 — 백엔드에서 허용해 줘야 한다

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://shop.com"],   # 허용할 프론트 주소
    allow_methods=["*"],
    allow_headers=["*"],
)
```

프론트는 API 주소를 환경변수로 바꿔 끼운다.

```js
// .env.production 파일 : VITE_API_BASE=https://api.shop.com
const API_BASE = `${import.meta.env.VITE_API_BASE ?? ''}/products`
```

> Vite 는 `VITE_` 로 시작하는 환경변수만 프론트 코드(`import.meta.env`)에서 읽을 수 있다.

### 7-3. 정리

- **proxy 설정 자체는 개발용**이다.
- 배포 방식으로 ①, ② 를 고르면 **프론트 코드를 고칠 필요가 없다.**
  → 개발할 때 `fetch('/products')` 처럼 **상대 경로**로 써 두는 이유가 바로 이것이다.
- ③ 을 고르면 백엔드에 CORS 설정을 넣고, 프론트에 API 주소 환경변수를 추가해야 한다.
