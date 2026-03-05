import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath } from 'node:url'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  // TESTING
  server: { 
  setupMiddlewares(middlewares) {
    middlewares.use('/txt-content', (req, res, next) => {
      res.setHeader('Content-Type', 'text/plain')
      res.end('Hello from the frontend mock endpoint!\nThis simulates your API txt response.')
    })
    return middlewares
  }
}
// TESTING
})
