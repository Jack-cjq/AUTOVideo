import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

// 从环境变量获取后端地址，默认使用5000端口（后端默认端口）
// 可以通过环境变量 VITE_BACKEND_PORT 或 VITE_BACKEND_URL 配置
// 例如：VITE_BACKEND_PORT=5001 或 VITE_BACKEND_URL=http://localhost:5001
const getBackendUrl = () => {
  if (process.env.VITE_BACKEND_URL) {
    return process.env.VITE_BACKEND_URL
  }
  const port = process.env.VITE_BACKEND_PORT || '5000'
  return `http://localhost:${port}`
}

const backendUrl = getBackendUrl()

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
        target: backendUrl,  // 后端地址，默认 http://localhost:5000
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
          // 添加错误处理，提供更友好的错误提示
          proxy.on('error', (err, req, res) => {
            console.error('代理错误:', err.message);
            console.error(`无法连接到后端服务器: ${backendUrl}`);
            console.error('请确保后端服务器正在运行');
            console.error('如果后端运行在不同端口，请设置环境变量:');
            console.error('  VITE_BACKEND_PORT=5001 或 VITE_BACKEND_URL=http://localhost:5001');
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

