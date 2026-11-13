# Tailwind CSS 설치 가이드 (Vite + React)

이 프로젝트(`frontend`)에 Tailwind CSS v4를 설치하고 적용하는 방법입니다.

- 대상 환경: Vite 8, React 19
- 작업 위치: `frontend` 폴더

---

## 1. 왜 설치가 필요한가

`App.jsx`에서 `grid`, `gap-4`, `mx-auto` 같은 Tailwind 클래스를 써도 Tailwind가 설치되어 있지 않으면 브라우저는 이 클래스들을 그냥 무시합니다.
그래서 `grid` 배치가 적용되지 않고, 상품 카드가 세로로만 쌓였습니다.

---

## 2. 패키지 설치

`frontend` 폴더에서 아래 명령을 실행합니다.

```bash
npm install tailwindcss @tailwindcss/vite
```

| 패키지 | 역할 |
| --- | --- |
| `tailwindcss` | Tailwind CSS 본체 |
| `@tailwindcss/vite` | Vite에서 Tailwind를 처리해 주는 플러그인 |

> v4부터는 `postcss`, `autoprefixer`, `tailwind.config.js` 파일이 없어도 됩니다.

---

## 3. Vite 설정에 플러그인 추가

`vite.config.js` 파일을 열고 `tailwindcss()` 플러그인을 추가합니다.

```js
import react, { reactCompilerPreset } from '@vitejs/plugin-react'
import babel from '@rolldown/plugin-babel'
import tailwindcss from '@tailwindcss/vite'   // 추가
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    babel({ presets: [reactCompilerPreset()] }),
    tailwindcss(),                            // 추가
  ],
})
```

---

## 4. CSS 파일에 Tailwind 불러오기

`src/index.css` 파일의 **맨 위**에 아래 한 줄을 추가합니다.

```css
@import "tailwindcss";

body {
  margin: 0;
  font-family: "Malgun Gothic", sans-serif;
  background: #f5f5f5;
}
```

`index.css`는 `main.jsx`에서 이미 불러오고 있으므로 다른 파일은 고치지 않아도 됩니다.

---

## 5. 개발 서버 다시 시작

설정 파일을 바꿨으니 개발 서버를 껐다가 다시 켭니다.

```bash
npm run dev
```

브라우저에서 http://localhost:5173 을 열어 확인합니다.

---

## 6. 적용 확인

`App.jsx`에서 Tailwind 클래스를 써서 확인합니다.

```jsx
<div className="mx-auto max-w-[900px] px-4 py-6">
  <h1 className="my-[0.67em] text-center text-[2em] font-bold">🥤 음료수 자판기</h1>

  <div className="grid grid-cols-[repeat(auto-fill,minmax(200px,1fr))] gap-4">
    {/* 상품 카드 */}
  </div>
</div>
```

상품 카드가 **가로로** 여러 개씩 배치되면 제대로 적용된 것입니다.

---

## 7. 주의할 점

### `.container` 클래스 이름 충돌

Tailwind에는 `container`라는 클래스가 이미 있습니다.
`App.css`의 `.container`와 이름이 같아서 두 스타일이 섞여 적용될 수 있습니다.
둘 중 하나만 쓰는 것이 좋습니다.

- Tailwind만 쓸 경우: `className="container"` 대신 `mx-auto max-w-[900px] px-4 py-6`을 씁니다.
- `App.css`를 계속 쓸 경우: 클래스 이름을 `.page` 같은 다른 이름으로 바꿉니다.

### 기본 스타일 초기화 (Preflight)

Tailwind는 브라우저 기본 스타일을 초기화합니다.
그래서 `h1`, `h3` 같은 제목의 글자 크기와 굵기, `p`의 여백이 사라집니다.
제목이 작게 보이면 `text-2xl font-bold` 같은 클래스를 직접 붙여 줍니다.

### 클래스가 적용되지 않을 때

1. `vite.config.js`에 `tailwindcss()`를 추가했는지 확인합니다.
2. `index.css` 맨 위에 `@import "tailwindcss";`가 있는지 확인합니다.
3. 개발 서버를 다시 시작합니다.
4. 브라우저에서 강력 새로고침(`Ctrl + Shift + R`)을 합니다.

---

## 참고

- Tailwind CSS 공식 문서 (Vite 설치): https://tailwindcss.com/docs/installation/using-vite
