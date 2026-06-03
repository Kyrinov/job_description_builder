import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Vite dev server config for the JD Builder v2.0 SPA.
// - React 18 JSX transform via @vitejs/plugin-react
// - Dev server on port 5173 (Vite default)
// - /api/* proxied to FastAPI on :8000 (FE-02)
//   The FastAPI app (Phase 10 Plan 02+03) mounts all routes under /api
//   so the proxy is a simple pass-through (no rewrite).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
})
