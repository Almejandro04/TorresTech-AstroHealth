/**
 * Verifies that the frontend mock reproduces the shared contract examples.
 *
 *   npm run check:mocks
 *
 * It loads the real TypeScript mock engine through Vite and compares its output, field by
 * field, with docs/examples/mission_seed.json and docs/examples/api_examples.json.
 */
import { readFileSync } from 'node:fs'
import { isDeepStrictEqual } from 'node:util'
import { fileURLToPath } from 'node:url'
import { createServer } from 'vite'

const root = fileURLToPath(new URL('..', import.meta.url))
const readJson = (path) => JSON.parse(readFileSync(new URL(`../../docs/examples/${path}`, import.meta.url), 'utf8'))
const seedFile = readJson('mission_seed.json')
const examples = readJson('api_examples.json')
const exampleBody = (name) => {
  const found = examples.cases.find((candidate) => candidate.name === name)
  if (!found) throw new Error(`Shared example not found: ${name}`)
  return found
}

const server = await createServer({ root, logLevel: 'error', server: { middlewareMode: true, hmr: false, ws: false }, appType: 'custom' })
let failures = 0
const check = (label, actual, expected) => {
  const pass = isDeepStrictEqual(actual, expected)
  if (!pass) failures += 1
  console.log(`${pass ? 'pass' : 'FAIL'}  ${label}`)
  if (!pass) console.log('      actual:  ', JSON.stringify(actual), '\n      expected:', JSON.stringify(expected))
}
const rejection = (run) => {
  try {
    run()
    return null
  } catch (error) {
    return { status: error.status, code: error.code, details: error.details }
  }
}

try {
  const seed = await server.ssrLoadModule('/src/services/mock/seed.ts')
  const engine = await server.ssrLoadModule('/src/services/mock/engine.ts')
  const fixtures = await server.ssrLoadModule('/src/services/mock/alertFixtures.ts')
  const store = () => engine.createSeedStore()
  const plain = (value) => JSON.parse(JSON.stringify(value))

  console.log('Seed parity (docs/examples/mission_seed.json)')
  check('astronauts', plain(seed.seedAstronauts), seedFile.astronauts)
  check('readings', plain(seed.seedReadings), seedFile.readings)
  check('journal', plain(seed.seedJournal), seedFile.journal)

  console.log('\nResponse parity (docs/examples/api_examples.json)')
  const cases = [
    ['fictional_profiles', () => engine.listAstronauts(store())],
    ['readings_history_with_null_metric', (q) => engine.listReadings(store(), 'AST-001', q)],
    ['journal_history_for_sleep_chart', (q) => engine.listJournal(store(), 'AST-001', q)],
    ['summary_normal_reference_fixture', (q) => engine.buildSummary(store(), 'AST-001', q)],
    ['summary_introduced_change_and_missing_metric', (q) => engine.buildSummary(store(), 'AST-001', q)],
    ['summary_before_later_same_day_reading', (q) => engine.buildSummary(store(), 'AST-001', q)],
    ['summary_before_analysis_is_implemented', (q) => engine.buildSummary(store(), 'AST-001', q, 'not_implemented')],
    ['summary_profile_without_observations', () => engine.buildSummary(store(), 'AST-002')],
    ['evaluated_no_active_alerts', (q) => engine.listAlerts(store(), 'AST-001', q)],
    ['explainable_synthetic_alert', (q) => engine.listAlerts(store(), 'AST-001', q)],
    ['alerts_not_implemented_is_not_an_all_clear', (q) => engine.listAlerts(store(), 'AST-001', q, 'not_implemented')],
    ['known_profile_empty_readings', () => engine.listReadings(store(), 'AST-002')],
  ]
  for (const [name, run] of cases) {
    const example = exampleBody(name)
    check(name, plain(run(example.request.query ?? {})), example.response.body)
  }

  console.log('\nJournal writes')
  for (const name of ['journal_created', 'journal_day_updated_same_id']) {
    const example = exampleBody(name)
    const result = engine.upsertJournal(store(), 'AST-001', example.request.body)
    check(`${name}: body`, plain(result.response), example.response.body)
    check(`${name}: status`, result.outcome, example.response.status === 201 ? 'created' : 'updated')
  }

  console.log('\nErrors')
  const unknown = exampleBody('unknown_profile')
  check('unknown_profile', rejection(() => engine.buildSummary(store(), 'AST-999')), {
    status: unknown.response.status,
    code: unknown.response.body.error.code,
    details: unknown.response.body.error.details,
  })
  const mood = exampleBody('invalid_mood_score')
  check('invalid_mood_score', rejection(() => engine.upsertJournal(store(), 'AST-001', mood.request.body)), {
    status: mood.response.status,
    code: mood.response.body.error.code,
    details: mood.response.body.error.details,
  })
  check('journal with no sleep, mood, or note is rejected',
    rejection(() => engine.upsertJournal(store(), 'AST-001', { ...mood.request.body, sleep_hours_last_night: null, mood_score: null, notes: '   ' }))?.status, 422)
  check('cutoff outside the mission is rejected',
    rejection(() => engine.buildSummary(store(), 'AST-001', { as_of: '2027-01-01T00:00:00Z' }))?.status, 422)
  check('reversed day range is rejected', rejection(() => engine.listReadings(store(), 'AST-001', { from_day: 5, to_day: 2 }))?.status, 422)

  console.log('\nReplay and mock-only policies')
  const day3 = engine.buildSummary(store(), 'AST-001', { as_of: '2026-11-03T23:59:59Z' }).data
  check('day 3: reference window still open -> insufficient_data', day3.baselines.heart_rate_bpm.status, 'insufficient_data')
  check('day 3: three samples counted, no value invented', [day3.baselines.heart_rate_bpm.sample_count, day3.baselines.heart_rate_bpm.value], [3, null])
  check('day 3: alert evaluation is not an all-clear', day3.alert_summary, { evaluation_status: 'insufficient_data', active_count: null, highest_severity: null, recent: [] })
  check('day 3: no later observation leaks into the view', [day3.mission_day, day3.latest_metrics.heart_rate_bpm.mission_day], [3, 3])
  const day6 = engine.listAlerts(store(), 'AST-001', { as_of: '2026-11-06T23:59:59Z' }, 'samples')
  check('day 6: only alerts detected by then are listed', day6.data.map((alert) => alert.alert_id), ['SAMPLE-INFO-SPO2'])
  check('day 6: an alert resolved later still reads as active', [day6.data[0]?.status, day6.data[0]?.resolved_at], ['active', null])
  const latestSamples = engine.buildSummary(store(), 'AST-001', {}, 'samples').data.alert_summary
  check('samples: summary counts active alerts only', [latestSamples.active_count, latestSamples.highest_severity], [3, 'critical'])
  check('every presentation sample is labeled', fixtures.presentationAlerts.every((alert) =>
    alert.rule_id === fixtures.PRESENTATION_RULE_ID && alert.description.startsWith('Presentation sample') && alert.explanation.includes('No detection rule produced it')), true)

  const session = store()
  const edited = engine.upsertJournal(session, 'AST-001', { ...exampleBody('journal_day_updated_same_id').request.body, sleep_hours_last_night: 0, notes: '  Slept poorly.  ' })
  check('journal edit: sleep 0 is kept as a value, notes are trimmed', [edited.response.data.sleep_hours_last_night, edited.response.data.notes], [0, 'Slept poorly.'])
  check('journal edit: still one entry per day', session.journal.filter((entry) => entry.mission_day === 7).length, 1)
  check('journal edit: latest sleep snapshot follows the correction', engine.buildSummary(session, 'AST-001').data.latest_metrics.sleep_hours_last_night.value, 0)
} finally {
  await server.close()
}

if (failures > 0) {
  console.error(`\n${failures} mock check(s) failed.`)
  process.exit(1)
}
console.log('\nThe mock reproduces the shared contract examples.')
