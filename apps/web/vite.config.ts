import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'

// packages/assemble is plain TypeScript source in this repo (the cursor-rebuild effect); it is bundled, not installed.
const assemble = fileURLToPath(new URL('../../packages/assemble/src/index.ts', import.meta.url))

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { assemble } },
  server: { fs: { allow: ['.', '../../packages/assemble'] } },
})
