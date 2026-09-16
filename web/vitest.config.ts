import path from 'node:path'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(import.meta.dirname, './src'),
    },
  },
  test: {
    environment: 'jsdom',
    // `@testing-library/react`'s automatic unmount-between-tests only
    // registers itself when it finds a global `afterEach` — without this,
    // one test's rendered DOM leaks into the next.
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
  },
})
