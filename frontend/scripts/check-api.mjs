/** Exercise the real Fetch client over a test HTTP server, never a claimed backend integration. */
import assert from 'node:assert/strict'
import { fileURLToPath } from 'node:url'
import { readFileSync } from 'node:fs'
import { createServer } from 'vite'
import { startFixtureApi } from './fixture-api.mjs'

const root = fileURLToPath(new URL('..', import.meta.url))
const vite = await createServer({ root, logLevel: 'error', server: { middlewareMode: true, hmr: false, ws: false }, appType: 'custom' })
let fixture
let count = 0
const check = async (name, run) => { await run(); count++; console.log(`pass  ${name}`) }
try {
  const { createApiHealthDataSource, validateApiBaseUrl } = await vite.ssrLoadModule('/src/services/apiHealthDataSource.ts')
  const { responses } = await vite.ssrLoadModule('/src/services/responseValidation.ts')
  const engine = await vite.ssrLoadModule('/src/services/mock/engine.ts')
  const { readAppConfig } = await vite.ssrLoadModule('/src/services/config.ts')
  const examples = JSON.parse(readFileSync(new URL('../../docs/examples/api_examples.json', import.meta.url), 'utf8'))
  const guards = { health: 'health', fictional_profiles: 'astronauts', readings_history_with_null_metric: 'readings', journal_history_for_sleep_chart: 'journal', explainable_synthetic_alert: 'alerts', alerts_not_implemented_is_not_an_all_clear: 'alerts', known_profile_empty_readings: 'readings', journal_created: 'savedJournal', journal_day_updated_same_id: 'savedJournal' }
  await check('runtime guards accept all shared success examples', () => {
    for (const c of examples.cases) {
      if (c.response.status >= 300) continue
      const key = guards[c.name] ?? (['reading_created', 'exact_reading_retry'].includes(c.name) ? 'savedReading' : c.name.startsWith('summary_') ? 'summary' : c.name === 'evaluated_no_active_alerts' ? 'alerts' : undefined)
      assert.ok(key, `Missing guard for ${c.name}`)
      assert.ok(responses[key](c.response.body), c.name)
    }
  })
  fixture = await startFixtureApi(engine)
  const api = createApiHealthDataSource({ baseUrl: fixture.url, timeoutMs: 1000 })
  await check('health and profiles use HTTP envelopes', async () => {
    assert.equal((await api.getHealth()).data.service, 'astrohealth-api')
    assert.equal((await api.getAstronauts()).data[0].astronaut_id, 'AST-001')
  })
  await check('summary retains per-indicator timestamp and null history', async () => {
    const summary = (await api.getSummary('AST-001')).data
    assert.equal(summary.latest_metrics.respiratory_rate_bpm.mission_day, 6)
    assert.equal((await api.getReadings('AST-001', { from_day: 7, to_day: 7 })).data[0].respiratory_rate_bpm, null)
  })
  await check('range, pagination and UTC cutoff reach the server', async () => {
    const page = await api.getReadings('AST-001', { from_day: 2, to_day: 5, limit: 2, offset: 1, as_of: '2026-11-04T23:59:59Z' })
    assert.deepEqual(page.data.map(x => x.mission_day), [3, 4])
    assert.equal(page.meta.total, 3)
  })
  await check('journal history is separate from vital readings', async () => { assert.equal((await api.getJournal('AST-001')).data[0].sleep_hours_last_night, 7.5) })
  await check('empty history and unavailable evaluation stay distinct', async () => {
    assert.deepEqual((await api.getReadings('AST-002')).data, [])
    fixture.analysis = 'not_implemented'
    assert.equal((await api.getAlerts('AST-001')).meta.evaluation_status, 'not_implemented')
    fixture.analysis = 'contract'
    assert.equal((await api.getAlerts('AST-001', { status: 'active' })).data[0].status, 'active')
  })
  await check('404, encoded IDs and 422 retain structured error details', async () => {
    for (const id of ['AST-999', 'AST/999']) await assert.rejects(api.getSummary(id), e => e.kind === 'not_found' && e.status === 404)
    await assert.rejects(api.getSummary('..'), e => e.kind === 'validation')
    await assert.rejects(api.getReadings('AST-001', { from_day: 6, to_day: 2 }), e => e.kind === 'validation' && e.status === 422)
  })
  const input = { timestamp: '2026-11-08T08:00:00Z', mission_day: 8, sleep_hours_last_night: 0, mood_score: 3, notes: 'HTTP test', source_type: 'synthetic', source_id: 'SYN-CORE-001' }
  let journalId
  await check('201 create and 200 correction preserve daily identity and zero', async () => {
    const created = await api.saveJournal('AST-001', input)
    journalId = created.response.data.journal_id
    assert.equal(created.outcome, 'created')
    assert.equal(created.response.data.sleep_hours_last_night, 0)
    const edited = await api.saveJournal('AST-001', { ...input, notes: 'corrected' })
    assert.equal(edited.outcome, 'updated')
    assert.equal(edited.response.data.journal_id, journalId)
    assert.equal((await api.getSummary('AST-001')).data.latest_journal.notes, 'corrected')
  })
  await check('rejected write exposes field feedback', async () => {
    await assert.rejects(api.saveJournal('AST-001', { ...input, mood_score: 6 }), e => e.kind === 'validation' && e.status === 422)
    fixture.failure = 'validation'
    await assert.rejects(api.saveJournal('AST-001', input), e => e.kind === 'validation' && e.details[0].field === 'body.sleep_hours_last_night')
    fixture.failure = null
  })
  await check('lost POST response is uncertain; retry creates no duplicate', async () => {
    fixture.failure = 'unconfirmed'
    await assert.rejects(api.saveJournal('AST-001', { ...input, notes: 'lost response' }), e => e.kind === 'timeout')
    fixture.failure = null
    assert.equal((await api.saveJournal('AST-001', { ...input, notes: 'lost response' })).response.data.journal_id, journalId)
    assert.equal((await api.getJournal('AST-001', { from_day: 8 })).data.length, 1)
  })
  await check('network, timeout and server failures never yield mock success', async () => {
    fixture.failure = 'network'
    await assert.rejects(api.getSummary('AST-001'), e => e.kind === 'network')
    fixture.failure = 'server'
    await assert.rejects(api.getSummary('AST-001'), e => e.kind === 'server' && e.status === 500)
    fixture.failure = null; fixture.delayMs = 100
    const impatient = createApiHealthDataSource({ baseUrl: fixture.url, timeoutMs: 20 })
    await assert.rejects(impatient.getHealth(), e => e.kind === 'timeout')
    fixture.delayMs = 0
  })
  await check('invalid JSON, schema version and missing fields fail closed', async () => {
    for (const failure of ['invalid_json', 'invalid_shape']) {
      fixture.failure = failure
      await assert.rejects(api.getSummary('AST-001'), e => e.code === 'INVALID_RESPONSE')
    }
    fixture.failure = null
  })
  await check('wrong profile and future replay data are rejected', async () => {
    const corrupt = createApiHealthDataSource({ baseUrl: fixture.url, fetch: async () => Response.json(engine.buildSummary(fixture.store, 'AST-001')) })
    await assert.rejects(corrupt.getSummary('AST-002'), e => e.code === 'INVALID_RESPONSE')
    await assert.rejects(corrupt.getSummary('AST-001', { as_of: '2026-11-03T23:59:59Z' }), e => e.code === 'INVALID_RESPONSE')
  })
  await check('a write response for a different day cannot be called saved', async () => {
    const response = engine.upsertJournal(fixture.store, 'AST-001', input).response
    const wrong = createApiHealthDataSource({ baseUrl: fixture.url, fetch: async () => Response.json({ ...response, data: { ...response.data, mission_day: 9 } }, { status: 200 }) })
    await assert.rejects(wrong.saveJournal('AST-001', input), e => e.kind === 'timeout' && e.code === 'INVALID_RESPONSE')
  })
  await check('credentials, fragments and invalid timeout configuration are rejected', () => {
    for (const url of ['ftp://example.com', 'http://user:password@example.com', 'http://example.com/#fragment']) assert.throws(() => validateApiBaseUrl(url))
    assert.throws(() => createApiHealthDataSource({ baseUrl: fixture.url, timeoutMs: 0 }))
    assert.throws(() => readAppConfig({ VITE_DATA_SOURCE: 'automatic' }))
    assert.throws(() => readAppConfig({ VITE_API_TIMEOUT_MS: 'NaN' }))
    assert.throws(() => readAppConfig({ VITE_JOURNAL_TIME_UTC: '25:00:00' }))
    assert.equal(readAppConfig({}).dataSource, 'mock')
    assert.equal(readAppConfig({ VITE_DATA_SOURCE: 'api' }).newJournalDefaults, null)
    assert.deepEqual(readAppConfig({ VITE_DATA_SOURCE: 'api', VITE_JOURNAL_SOURCE_ID: 'SYN-TEST', VITE_JOURNAL_TIME_UTC: '09:30:00' }).newJournalDefaults, { sourceId: 'SYN-TEST', timeUtc: '09:30:00' })
  })
  console.log(`\n${count} HTTP client checks passed. Test-only fixtures do not prove FastAPI/SQLite integration.`)
} finally { await fixture?.close(); await vite.close() }
