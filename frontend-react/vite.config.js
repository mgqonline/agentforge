import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    {
      name: 'vanilla-fallback',
      configureServer(server) {
        server.middlewares.use((req, res, next) => {
          if (req.url === '/vanilla' || req.url === '/vanilla/') {
            req.url = '/vanilla/index.html';
          }
          next();
        });
      }
    }
  ],
  server: {
    port: 6000,
    proxy: {
      '/api': {
        target: 'http://localhost:6001',
        changeOrigin: true
      },
      '/ws': {
        target: 'ws://localhost:6001',
        ws: true
      }
    }
  },
  preview: {
    port: 6000
  }
})
