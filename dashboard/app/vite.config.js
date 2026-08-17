import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
// Proxy is configured so that in development, API calls are forwarded to the
// correct backend ports, avoiding any CORS pre-flight issues in the browser.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Person 2 — Voice Intake Flask API (port 5000)
      '/intake': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      },
      '/transcribe': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      },
      '/languages': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      },
      // Person 3 — Decision Engine FastAPI (port 8000)
      '/triage': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/my-queue': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/queue': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/override': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/login': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/reassign': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
