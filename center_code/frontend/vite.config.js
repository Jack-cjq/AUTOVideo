import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

function resolveBackendUrl(env) {
  if (env.VITE_BACKEND_URL) return env.VITE_BACKEND_URL
  if (env.VITE_BACKEND_PORT) return `http://localhost:${env.VITE_BACKEND_PORT}`

  // If the API base is absolute like http://localhost:8081/api, reuse its origin for proxy target.
  if (env.VITE_API_BASE_URL && /^https?:\/\//i.test(env.VITE_API_BASE_URL)) {
    try {
      const u = new URL(env.VITE_API_BASE_URL)
      return `${u.protocol}//${u.host}`
    } catch (_) {}
  }

  return 'http://localhost:8080'
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, __dirname, '')
  const backendUrl = resolveBackendUrl(env)

  return {
    plugins: [vue()],
    resolve: {
      alias: {
        '@': resolve(__dirname, 'src')
      }
    },
    server: {
      port: 3001,
      strictPort: false,
      proxy: {
        '/api': {
          target: backendUrl,
          changeOrigin: true,
          secure: false,
          rewrite: (path) => path,
          configure: (proxy, _options) => {
            proxy.on('proxyReq', (proxyReq, req, _res) => {
              if (req.headers.cookie) proxyReq.setHeader('Cookie', req.headers.cookie)
            })
            proxy.on('error', (err, req, res) => {
              console.error('代理错误:', err.message)
              console.error(`无法连接到后端服务器: ${backendUrl}`)
              console.error('请确保后端服务器正在运行')
              console.error('如果后端运行在不同端口，请设置环境变量:')
              console.error('  VITE_BACKEND_PORT=8081 或 VITE_BACKEND_URL=http://localhost:8081')
            })
          }
        },
        '/uploads': {
          target: backendUrl,
          changeOrigin: true,
          secure: false,
          rewrite: (path) => path,
          configure: (proxy, _options) => {
            proxy.on('proxyReq', (_proxyReq, req, _res) => {
              console.log(`[Proxy] 代理请求: ${req.url} -> ${backendUrl}${req.url}`)
            })
            proxy.on('error', (err, req, res) => {
              console.error('上传文件代理错误:', err.message)
              console.error(`无法连接到后端服务器: ${backendUrl}`)
            })
          }
        }
      }
    },
    build: {
      outDir: '../backend/static',
      emptyOutDir: true
    }
  }
})

