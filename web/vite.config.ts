import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(import.meta.dirname, './src'),
    },
  },
  server: {
    // Dev-only: the app always fetches relative paths (e.g. /api/v1/health)
    // so the same code works once the SPA and API share an origin in prod.
    proxy: {
      '/api': 'http://localhost:8080',
    },
  },
})
