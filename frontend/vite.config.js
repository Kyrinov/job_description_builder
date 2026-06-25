import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Vite dev server config for the JD Builder v2.0 SPA.
// - React 18 JSX transform via @vitejs/plugin-react
// - Dev server on port 5173 (Vite default)
// - /api/* proxied to FastAPI on :8000 (FE-02)
//   The FastAPI app (Phase 10 Plan 02+03) mounts all routes under /api
//   so the proxy is a simple pass-through (no rewrite).
//
// Test block (added Phase 13 Plan 01 / Wave 0):
// - Vitest + jsdom test runner for FE-04 (state slices) and FE-05
//   (localStorage crash-recovery) test stubs.
// - `globals: true` exposes `describe`, `it`, `expect`, `vi` without import.
// - `setupFiles: []` left empty for now; per-suite setup can be added later.
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
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: [],
  },
})
