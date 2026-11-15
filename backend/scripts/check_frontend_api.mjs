/** Probe a disposable running FastAPI database with the unchanged UI client.
 * Node 22.13+; no frontend install, Vite server, build, or file writes needed.
 * This sends synthetic readings/journal writes: use a dedicated test database.
 */
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { stripTypeScriptTypes } from 'node:module'

const baseUrl = process.argv[2]
assert.ok(baseUrl, 'Usage: node backend/scripts/check_frontend_api.mjs http://127.0.0.1:PORT (disposable DB only)')
const source = name => readFileSync(new URL(`../../frontend/src/services/${name}.ts`, import.meta.url), 'utf8')
const moduleUrl = code => `data:text/javascript;base64,${Buffer.from(code).toString('base64')}`
const errorsUrl = moduleUrl(stripTypeScriptTypes(source('errors')))
const guardsUrl = moduleUrl(stripTypeScriptTypes(source('responseValidation')))
const clientCode = stripTypeScriptTypes(source('apiHealthDataSource'))
  .replace("'./errors'", JSON.stringify(errorsUrl))
  .replace("'./responseValidation'", JSON.stringify(guardsUrl))
const { createApiHealthDataSource } = await import(moduleUrl(clientCode))
const { responses, matchesView, errorDetails } = await import(guardsUrl)
const api = createApiHealthDataSource({ baseUrl, timeoutMs: 5000 })
let count = 0
const check = async (name, run) => { await run(); count++; console.log(`pass ${name}`) }
await check('health and profile envelopes', async () => {
  assert.equal((await api.getHealth()).data.status, 'ok')
  assert.ok((await api.getAstronauts()).data.some(p => p.astronaut_id === 'AST-001'))
})
await check('summary snapshots and honest analysis placeholders', async () => {
  const { data } = await api.getSummary('AST-001')
  assert.equal(data.latest_metrics.respiratory_rate_bpm.mission_day, 6)
  for (const baseline of Object.values(data.baselines)) {
    assert.equal(baseline.status, 'not_implemented')
    assert.equal(baseline.measurement_context, null)
  }
  assert.equal(data.alert_summary.active_count, null)
})
await check('history, pagination, cutoff and view guards', async () => {
  const query = { from_day: 2, to_day: 6, limit: 2, offset: 1, as_of: '2026-11-04T23:59:59Z' }
  const readings = await api.getReadings('AST-001', query)
  assert.deepEqual(readings.data.map(r => r.mission_day), [3, 4])
  assert.equal(readings.meta.total, 3)
  assert.ok(matchesView(readings, 'AST-001', query.as_of))
  assert.ok((await api.getJournal('AST-001', query)).data.length > 0)
})
await check('empty profile and unevaluated alerts', async () => {
  assert.equal((await api.getSummary('AST-002')).data.mission_day, null)
  assert.deepEqual((await api.getReadings('AST-002')).data, [])
  const alerts = await api.getAlerts('AST-001', { status: 'active' })
  assert.deepEqual(alerts.data, [])
  assert.equal(alerts.meta.evaluation_status, 'not_implemented')
})
await check('404 and 422 reach real client errorDetails', async () => {
  await assert.rejects(api.getSummary('AST-999'), e => e.kind === 'not_found' && e.code === 'ASTRONAUT_NOT_FOUND')
  await assert.rejects(api.getReadings('AST-001', { from_day: 6, to_day: 2 }), e => e.kind === 'validation' && e.details[0].field === 'query.to_day')
  const response = await fetch(`${baseUrl}/api/missing`)
  assert.equal(errorDetails(await response.json()).code, 'NOT_FOUND')
})
await check('journal create, correction, retry and stable identity', async () => {
  const entry = { timestamp: '2026-11-09T08:00:00Z', mission_day: 9, sleep_hours_last_night: 0,
    mood_score: 3, notes: 'Real frontend adapter probe', source_type: 'synthetic', source_id: 'SYN-CORE-001' }
  const created = await api.saveJournal('AST-001', entry)
  assert.equal(created.outcome, 'created')
  const corrected = await api.saveJournal('AST-001', { ...entry, notes: 'Corrected' })
  const retry = await api.saveJournal('AST-001', { ...entry, notes: 'Corrected' })
  assert.equal(corrected.outcome, 'updated')
  assert.equal(corrected.response.data.journal_id, created.response.data.journal_id)
  assert.equal(retry.response.data.journal_id, created.response.data.journal_id)
  const history = await api.getJournal('AST-001', { from_day: 9, to_day: 9 })
  assert.equal(history.meta.total, 1)
  assert.equal(history.data[0].sleep_hours_last_night, 0)
  const summary = await api.getSummary('AST-001')
  assert.equal(summary.data.latest_metrics.sleep_hours_last_night.record_id, created.response.data.journal_id)
  await assert.rejects(api.saveJournal('AST-001', { ...entry, mood_score: 6 }), e => e.kind === 'validation' && e.details.some(d => d.field === 'body.mood_score'))
})
await check('reading creation, canonical retry and conflict', async () => {
  const input = { timestamp: '2026-11-10T12:00:00.1234567Z', mission_day: 10, heart_rate_bpm: 81,
    spo2_percent: 97, respiratory_rate_bpm: null, measurement_context: 'rest', source_type: 'synthetic', source_id: 'SYN-CORE-001' }
  const post = body => fetch(`${baseUrl}/api/astronauts/AST-001/readings`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  })
  const created = await post(input)
  assert.equal(created.status, 201)
  const record = await created.json()
  assert.ok(responses.savedReading(record) && matchesView(record, 'AST-001'))
  const retry = await post({ ...input, timestamp: input.timestamp.replace('7Z', '700Z') })
  assert.equal(retry.status, 200)
  assert.equal((await retry.json()).data.reading_id, record.data.reading_id)
  const conflict = await post({ ...input, heart_rate_bpm: 99 })
  assert.equal(conflict.status, 409)
  assert.equal(errorDetails(await conflict.json()).code, 'READING_CONFLICT')
  assert.equal((await api.getReadings('AST-001', { from_day: 10 })).data[0].reading_id, record.data.reading_id)
})
console.log(`${count} real FastAPI/SQLite frontend-client checks passed. No browser/UI behavior was tested.`)
