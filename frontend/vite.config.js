import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/query':  'http://backend:8000',
      '/health': 'http://backend:8000',
    }
  }
})
