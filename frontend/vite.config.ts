import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/pdf': {
        target: 'http://localhost:3001',
        rewrite: (path: string) => path.replace(/^\/pdf/, '')
      },
      '/chat': {
        target: 'http://localhost:3000',
        changeOrigin: true
      },
      '/api': {
        target: 'http://localhost:3000',
        changeOrigin: true
      }
    },
    host: '0.0.0.0',  
    port: 5173,        
  },
})
