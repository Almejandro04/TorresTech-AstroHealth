/** Read-only probe of a real running backend using the same HTTP client as the UI. */
import { fileURLToPath } from 'node:url'
import { createServer } from 'vite'

const baseUrl = process.argv[2] ?? 'http://localhost:8000'
const vite = await createServer({ root: fileURLToPath(new URL('..', import.meta.url)), logLevel: 'error', server: { middlewareMode: true, hmr: false, ws: false }, appType: 'custom' })
try {
  const { createApiHealthDataSource } = await vite.ssrLoadModule('/src/services/apiHealthDataSource.ts')
  const response = await createApiHealthDataSource({ baseUrl }).getHealth()
  console.log(JSON.stringify(response, null, 2))
  console.log('Real /api/health passed. This does not prove that mission data endpoints exist.')
} finally { await vite.close() }
