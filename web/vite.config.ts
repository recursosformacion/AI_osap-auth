import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // La API se proxya bajo /auth-api (prefijo dedicado) al backend real de osap-auth,
    // reescribiendo la ruta: /auth-api/auth/login -> /auth/login. Así no choca con las
    // rutas de la SPA (/auth/login es a la vez página y endpoint).
    proxy: {
      '/auth-api': {
        target: 'http://127.0.0.1:8200',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/auth-api/, ''),
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './tests/setup.ts',
  },
})
