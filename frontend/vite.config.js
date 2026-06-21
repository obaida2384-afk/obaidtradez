import { defineConfig, loadEnv, transformWithEsbuild } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig(({ mode }) => {
  const env = { ...loadEnv(mode, process.cwd(), ''), ...process.env }

  const backendUrl =
    env.REACT_APP_BACKEND_URL ||
    'https://obaidtradez-backend-production.up.railway.app'
  const port = Number(env.PORT) || 5173
  const hmrClientPort = env.WDS_SOCKET_PORT ? Number(env.WDS_SOCKET_PORT) : undefined

  return {
    plugins: [
      {
        name: 'treat-js-files-as-jsx',
        async transform(code, id) {
          if (!id.match(/src\/.*\.js$/) || id.includes('node_modules')) return null
          return transformWithEsbuild(code, id, { loader: 'jsx', jsx: 'automatic' })
        },
      },
      react(),
    ],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      host: true,
      port,
      allowedHosts: true,
      hmr: hmrClientPort ? { clientPort: hmrClientPort, protocol: 'wss' } : undefined,
    },
    define: {
      'process.env.REACT_APP_BACKEND_URL': JSON.stringify(backendUrl),
      'process.env.NODE_ENV': JSON.stringify(env.NODE_ENV || 'production'),
    },
    optimizeDeps: {
      esbuildOptions: {
        loader: { '.js': 'jsx' },
      },
    },
    build: {
      outDir: 'dist',
    },
  }
})
