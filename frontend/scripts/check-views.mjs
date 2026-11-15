/** Non-browser regression checks. These do not replace rendered acceptance. */
import assert from 'node:assert/strict'
import { fileURLToPath } from 'node:url'
import { createServer } from 'vite'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { startFixtureApi } from './fixture-api.mjs'

const vite = await createServer({ root: fileURLToPath(new URL('..', import.meta.url)), logLevel: 'error', server: { middlewareMode: true, hmr: false, ws: false }, appType: 'custom' })
let fixture
let count = 0
const check = async (name, run) => { await run(); count++; console.log('pass  ' + name) }
try {
  const { startApplication } = await vite.ssrLoadModule('/src/startApplication.ts')
  const { ApplicationError } = await vite.ssrLoadModule('/src/components/ApplicationError.tsx')
  const { readAppConfig } = await vite.ssrLoadModule('/src/services/config.ts')
  const { loadHistory } = await vite.ssrLoadModule('/src/services/history.ts')
  const { createApiHealthDataSource } = await vite.ssrLoadModule('/src/services/apiHealthDataSource.ts')
  const engine = await vite.ssrLoadModule('/src/services/mock/engine.ts')
  await check('valid startup reaches the app without showing recovery', async () => {
    let loaded = false
    await startApplication(async () => ({ ready: true }), value => { loaded = value.ready }, () => assert.fail('Unexpected recovery'))
    assert.equal(loaded, true)
  })
  await check('invalid connection settings produce recovery content instead of an empty root', async () => {
    for (const env of [{ VITE_DATA_SOURCE: 'unknown' }, { VITE_API_BASE_URL: 'file:///private-path' }, { VITE_JOURNAL_TIME_UTC: '25:00:00' }]) {
      let html = ''
      await startApplication(async () => readAppConfig(env), () => assert.fail('Invalid setup started'), () => { html = renderToStaticMarkup(createElement(ApplicationError, { startup: true })) })
      assert.match(html, /Flight Log could not start/)
      assert.match(html, /role="alert"/)
      assert.match(html, /Reload Flight Log/)
      assert.doesNotMatch(html, /private-path|25:00:00|stack/)
    }
  })
  await check('module and startup-callback failures reach the same recovery path', async () => {
    for (const failLoad of [true, false]) {
      let failed = false
      await startApplication(async () => { if (failLoad) throw Error('Module unavailable'); return {} }, () => { throw Error('Initial render failed') }, () => { failed = true })
      assert.equal(failed, true)
    }
    const html = renderToStaticMarkup(createElement(ApplicationError))
    assert.match(html, /This view could not be displayed/)
    assert.match(html, /unsaved journal changes/)
  })
  fixture = await startFixtureApi(engine)
  const api = createApiHealthDataSource({ baseUrl: fixture.url })
  const before = await api.getSummary('AST-001')
  const cutoff = before.meta.as_of
  const late = { ...fixture.store.readings.at(-1), reading_id: 'LATE-OBSERVATION', timestamp: '2026-11-07T18:00:00Z', heart_rate_bpm: 85 }
  fixture.store.readings.push(late)
  await check('history and alerts stay at the displayed summary cutoff while a later reading arrives', async () => {
    const history = await loadHistory(api, 'AST-001', { as_of: cutoff, from_day: 1, to_day: 7 })
    assert.equal(history.readings.length, 7)
    assert.ok(history.readings.every(r => Date.parse(r.timestamp) <= Date.parse(cutoff)))
    assert.equal(history.readings.some(r => r.reading_id === late.reading_id), false)
    const alerts = await api.getAlerts('AST-001', { as_of: cutoff })
    assert.equal(alerts.meta.as_of, cutoff)
  })
  await check('refresh can advance the summary and history together; date filters retain null gaps', async () => {
    const fresh = await api.getSummary('AST-001')
    assert.equal(fresh.data.latest_metrics.heart_rate_bpm.value, 85)
    const history = await loadHistory(api, 'AST-001', { as_of: fresh.meta.as_of, from_day: 5, to_day: 7 })
    assert.deepEqual(history.readings.map(r => r.mission_day), [5, 6, 7, 7])
    assert.equal(history.journal.length, 3)
    assert.equal(history.readings[2].respiratory_rate_bpm, null)
  })
  await check('failed history is rejected and a later retry loads data rather than mock success', async () => {
    fixture.failure = 'server'
    await assert.rejects(loadHistory(api, 'AST-001', { as_of: cutoff }), e => e.kind === 'server')
    fixture.failure = null
    assert.equal((await loadHistory(api, 'AST-001', { as_of: cutoff })).readings.length, 7)
    const empty = await loadHistory(api, 'AST-002', {})
    assert.deepEqual(empty, { readings: [], journal: [] })
  })
  const makePage = (data, total, offset) => ({ data, meta: { schema_version: '0.1.0', as_of: cutoff, total, offset, limit: 1000 } })
  await check('all history pages are read with the same filters and cutoff', async () => {
    const all = Array.from({ length: 1001 }, (_, i) => ({ ...fixture.store.readings[0], reading_id: 'P-' + i }))
    const queries = []
    const source = {
      getReadings: async (_id, query) => { queries.push(query); return makePage(all.slice(query.offset, query.offset + query.limit), all.length, query.offset) },
      getJournal: async () => makePage([], 0, 0),
    }
    const result = await loadHistory(source, 'AST-001', { from_day: 1, to_day: 7, as_of: cutoff })
    assert.equal(result.readings.length, 1001)
    assert.deepEqual(queries.map(q => q.offset), [0, 1000])
    assert.ok(queries.every(q => q.as_of === cutoff && q.from_day === 1 && q.to_day === 7))
  })
  await check('missing, repeated-offset or changing-total pages fail rather than returning partial history', async () => {
    const record = fixture.store.readings[0]
    for (const badPage of [makePage([], 1, 0), makePage([record], 2, 0), makePage([record], 3, 1)]) {
      let calls = 0
      const source = { getJournal: async () => makePage([], 0, 0), getReadings: async () => ++calls === 1 && badPage.meta.total > 1 ? makePage([record], 2, 0) : badPage }
      await assert.rejects(loadHistory(source, 'AST-001', { as_of: cutoff }), e => e.code === 'INCONSISTENT_HISTORY')
    }
  })
  console.log(count + ' startup/view/history checks passed. No browser was controlled or reviewed.')
} finally {
  if (fixture) await fixture.close()
  await vite.close()
}
