/** Optional, loopback-only HTTP test fixture. Not the project's FastAPI backend. */
import { fileURLToPath } from 'node:url'
import { createServer } from 'vite'
import { startFixtureApi } from './fixture-api.mjs'

const vite = await createServer({ root: fileURLToPath(new URL('..', import.meta.url)), logLevel: 'error', server: { middlewareMode: true, hmr: false, ws: false }, appType: 'custom' })
const engine = await vite.ssrLoadModule('/src/services/mock/engine.ts')
const fixture = await startFixtureApi(engine, { port: Number(process.argv[2] ?? 0), origins: ['http://127.0.0.1:5176'] })
console.log(JSON.stringify({ testOnly: true, url: fixture.url }))
// IPC is available only to the parent verification process, never as a browser API endpoint.
process.on('message', message => {
  if (!message || !['failure', 'delayMs', 'analysis', 'reset'].includes(message.key)) return
  if (message.key === 'reset') fixture.store = engine.createSeedStore()
  else fixture[message.key] = message.value
  process.send?.({ id: message.id, ok: true })
})
async function close() { await fixture.close(); await vite.close(); process.exit(0) }
process.on('SIGTERM', close)
process.on('SIGINT', close)
