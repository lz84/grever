import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { join } from 'path'
import { readFileSync } from 'fs'

export default defineConfig(({ mode }) => {
  // Load .env for backend address
  const env = loadEnv(mode, process.cwd(), '')
  const apiBaseUrl = env.VITE_API_BASE_URL || 'http://localhost:8093'

  return {
    plugins: [
      react(),
      tailwindcss(),
      {
        name: 'spa-fallback',
        configureServer(server) {
          // Register middleware AFTER Vite's built-in middlewares
          return () => {
            server.middlewares.use((req, res, next) => {
              // Skip API requests and file requests (with extensions)
              if (req.url?.startsWith('/api/') || req.url?.includes('.')) {
                return next()
              }
              // Rewrite SPA routes to index.html
              const indexPath = join(server.config.root, 'index.html')
              try {
                const html = readFileSync(indexPath, 'utf-8')
                res.setHeader('Content-Type', 'text/html')
                res.end(html)
              } catch {
                next()
              }
            })
          }
        },
      },
    ],
    resolve: {
      alias: {
        '@': join(__dirname, 'src'),
      },
    },
    server: {
      port: 5173,
      open: true,
      proxy: {
        '/api/v1': {
          target: apiBaseUrl,
          changeOrigin: true,
          secure: false,
          ws: true,
          followRedirects: true,
          rewrite: (path) => {
            const [base, query] = path.split('?')
            // FastAPI 对无尾部斜杠的路径返回 307 重定向，
            // http-proxy-middleware 对 307 的 location 头处理有问题，
            // 所以直接在代理层补上尾部斜杠避免重定向。
            const needsSlash = [
              '/api/v1/goals',
              '/api/v1/projects',
              '/api/v1/tasks',
              // '/api/v1/agents' — 移除！/agents 和 /agents/ 对应不同后端端点
              '/api/v1/workflows',
              '/api/v1/solutions',
              '/api/v1/disputes',
              '/api/v1/scenarios',
              '/api/v1/health',
            ].includes(base)
            if (needsSlash) {
              return base + '/' + (query ? '?' + query : '')
            }
            return path
          },
        },
      },
    },
  }
})
