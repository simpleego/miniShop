import react, { reactCompilerPreset } from '@vitejs/plugin-react'
import babel from '@rolldown/plugin-babel'
import { defineConfig } from 'vite'
import process from 'node:process'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    babel({ presets: [reactCompilerPreset()] })
  ],
  server: {
    proxy: {
      // 상품 검색 테스트 화면(test.html)용 : /search/... 요청을 백엔드로 전달
      //   기본은 테스트 DB(test_vmshop)로 띄운 8001 포트 서버
      //   다른 서버로 보내려면 실행 시 API_TARGET 환경변수 지정 (예: http://localhost:8000)
      '/search': process.env.API_TARGET || 'http://localhost:8001',
      // ✅ 추가 : 자판기 화면용 상품 API (목록, 상세)
      '/products': 'http://localhost:8000',
    },
  },
})