import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vitest/config'

// Kept separate from vite.config.ts so the build config stays about building.
// Default environment is node; a file that needs the DOM opts in with
//   // @vitest-environment jsdom
export default defineConfig({
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  test: {
    include: ['src/**/*.test.{ts,tsx}'],
    restoreMocks: true,
  },
})
