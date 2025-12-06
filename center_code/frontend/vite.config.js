import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    port: 3000,
    strictPort: false,  // 如果端口被占用，自动尝试下一个端口
    proxy: {
      '/api': {
        target: 'http://localhost:5001',  // 后端端口，请根据实际运行端口修改
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path,  // 保持路径不变
        configure: (proxy, _options) => {
          proxy.on('proxyReq', (proxyReq, req, _res) => {
            // 确保 cookie 被传递
            if (req.headers.cookie) {
              proxyReq.setHeader('Cookie', req.headers.cookie);
            }
          });
        }
      }
    }
  },
  build: {
    outDir: '../backend/static',
    emptyOutDir: true
  }
})

