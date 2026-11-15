/** Test-only HTTP fixture server. This is not FastAPI, SQLite, or the backend deliverable. */
import { createServer } from 'node:http'

export async function startFixtureApi(engine, { port = 0, origins = ['http://127.0.0.1:5175'] } = {}) {
  const fixture = { store: engine.createSeedStore(), failure: null, delayMs: 0, analysis: 'contract' }
  const server = createServer(async (req, res) => {
    const origin = req.headers.origin
    if (origins.includes(origin)) res.setHeader('Access-Control-Allow-Origin', origin)
    res.setHeader('Vary', 'Origin')
    res.setHeader('X-AstroHealth-Test-Only', 'contract-fixture-server')
    res.setHeader('Content-Type', 'application/json')
    if (req.method === 'OPTIONS') {
      res.setHeader('Access-Control-Allow-Methods', 'GET, POST')
      res.setHeader('Access-Control-Allow-Headers', 'Content-Type')
      res.writeHead(origins.includes(origin) ? 204 : 400).end()
      return
    }
    if (fixture.delayMs) await new Promise(resolve => setTimeout(resolve, fixture.delayMs))
    const send = (status, body) => { res.writeHead(status); res.end(JSON.stringify(body)) }
    const fail = (status, code, details = []) => send(status, { error: { code, message: 'Test fixture request failed.', details }, meta: { schema_version: '0.1.0', as_of: null } })
    if (fixture.failure === 'network') { res.destroy(); return }
    if (fixture.failure === 'server') { fail(500, 'INTERNAL_ERROR'); return }
    if (fixture.failure === 'invalid_json') { res.writeHead(200); res.end('<html>not JSON</html>'); return }
    if (fixture.failure === 'invalid_shape') { send(200, { data: {}, meta: { schema_version: '9.0.0', as_of: null } }); return }
    try {
      const url = new URL(req.url, 'http://127.0.0.1')
      const query = Object.fromEntries([...url.searchParams].map(([k, v]) => [k, ['limit', 'offset', 'from_day', 'to_day'].includes(k) ? Number(v) : v]))
      if (url.pathname === '/api/health') { send(200, { data: { status: 'ok', service: 'astrohealth-api' }, meta: { schema_version: '0.1.0', as_of: null } }); return }
      if (url.pathname === '/api/astronauts') { send(200, engine.listAstronauts(fixture.store, query)); return }
      const match = url.pathname.match(/^\/api\/astronauts\/([^/]+)\/(readings|journal|summary|alerts)$/)
      if (!match) { fail(404, 'NOT_FOUND'); return }
      const [, rawId, resource] = match
      const id = decodeURIComponent(rawId)
      if (req.method === 'POST' && resource === 'journal') {
        if (fixture.failure === 'validation') { fail(422, 'VALIDATION_ERROR', [{ field: 'body.sleep_hours_last_night', message: 'Test rejection.' }]); return }
        let body = ''
        for await (const chunk of req) body += chunk
        const result = engine.upsertJournal(fixture.store, id, JSON.parse(body))
        if (fixture.failure === 'unconfirmed') { res.destroy(); return }
        send(result.outcome === 'created' ? 201 : 200, result.response)
        return
      }
      if (req.method !== 'GET') { fail(405, 'METHOD_NOT_ALLOWED'); return }
      const response = resource === 'readings' ? engine.listReadings(fixture.store, id, query)
        : resource === 'journal' ? engine.listJournal(fixture.store, id, query)
        : resource === 'summary' ? engine.buildSummary(fixture.store, id, query, fixture.analysis)
        : engine.listAlerts(fixture.store, id, query, fixture.analysis)
      send(200, response)
    } catch (error) { fail(error.status ?? 422, error.code ?? 'VALIDATION_ERROR', error.details ?? []) }
  })
  await new Promise((resolve, reject) => { server.once('error', reject); server.listen(port, '127.0.0.1', resolve) })
  return Object.assign(fixture, {
    server, url: `http://127.0.0.1:${server.address().port}`,
    async close() { server.closeAllConnections(); await new Promise(resolve => server.close(resolve)) },
  })
}
