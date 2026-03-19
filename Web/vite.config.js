import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

// 可以安全忽略的 socket 错误码
// - ECONNRESET/EPIPE/ECONNABORTED: 连接中断
// - ECONNREFUSED/ENOTFOUND: 代理目标后端未启动或域名暂不可达
const IGNORABLE_CODES = new Set(['ECONNRESET', 'EPIPE', 'ECONNABORTED', 'ECONNREFUSED', 'ENOTFOUND'])

function swallowSocketError(err) {
  if (!IGNORABLE_CODES.has(err.code)) throw err
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const apiProxyTarget = env.VITE_API_PROXY_TARGET || 'http://127.0.0.1:8000'
  const publicBase = env.VITE_PUBLIC_BASE || '/'

  return {
    base: publicBase,
    plugins: [vue()],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url))
      }
    },
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target: apiProxyTarget,
          changeOrigin: true,
          // 防止代理到后端的连接被重置时抛出未处理异常
          configure: (proxy) => {
            proxy.on('error', swallowSocketError)
          }
        }
      }
    },
    // 处理 HMR WebSocket 及 HTTP 升级 socket 的 ECONNRESET
    configureServer(server) {
      // HTTP server 上每个升级的 WebSocket socket 都加上错误监听
      server.httpServer?.on('upgrade', (_req, socket) => {
        socket.on('error', swallowSocketError)
      })
      // 兜底：Vite 暴露的 ws 层错误（Vite 5 server.ws 为内部 WebSocketServer 封装）
      server.ws?.on?.('error', swallowSocketError)
    }
  }
})
