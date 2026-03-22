import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3002,
    proxy: {
      '/api/ads':         { target: 'http://localhost:3000', changeOrigin: true, rewrite: (p) => p.replace(/^\/api\/ads/, '') },
      '/api/transcoding': { target: 'http://localhost:8002', changeOrigin: true, rewrite: (p) => p.replace(/^\/api\/transcoding/, '') },
      '/api/packaging':   { target: 'http://localhost:8003', changeOrigin: true, rewrite: (p) => p.replace(/^\/api\/packaging/, '') },
      '/api/scte35':      { target: 'http://localhost:8001', changeOrigin: true, rewrite: (p) => p.replace(/^\/api\/scte35/, '') },
      '/api/ai':          { target: 'http://localhost:8000', changeOrigin: true, rewrite: (p) => p.replace(/^\/api\/ai/, '') },
      '/api/srs':         { target: 'http://localhost:1985', changeOrigin: true, rewrite: (p) => p.replace(/^\/api\/srs/, '') },
    },
  },
})
