import assert from 'node:assert/strict'
import { fileURLToPath } from 'node:url'
import { createServer } from 'vite'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'

const vite = await createServer({ root: fileURLToPath(new URL('..', import.meta.url)), logLevel: 'error', server: { middlewareMode: true, hmr: false, ws: false }, appType: 'custom' })
let checks = 0
const check = (name, run) => { run(); checks++; console.log(`pass  ${name}`) }
try {
  const { buildMetricHistory, splitIntoRuns } = await vite.ssrLoadModule('/src/lib/series.ts')
  const { buildJournalInput } = await vite.ssrLoadModule('/src/services/journalDefaults.ts')
  const { createSeedStore } = await vite.ssrLoadModule('/src/services/mock/engine.ts')
  const { describeBaseline, MetricChart } = await vite.ssrLoadModule('/src/components/MetricChart.tsx')
  const store = createSeedStore()
  const range = { fromDay: 1, toDay: 7 }
  check('reverse input is ordered; null respiratory value stays a gap', () => {
    const h = buildMetricHistory('respiratory_rate_bpm', [...store.readings].reverse(), store.journal, range)
    assert.deepEqual(h.series[0].points.map(p => p.day), [1, 2, 3, 4, 5, 6])
    assert.deepEqual(h.missingDays, [7]); assert.equal(h.emptyRecords[0].day, 7)
  })
  check('all four required chart metrics and their cadences have exact counts', () => {
    for (const metric of ['heart_rate_bpm', 'spo2_percent', 'respiratory_rate_bpm', 'sleep_hours_last_night']) {
      const h = buildMetricHistory(metric, store.readings, store.journal, range)
      assert.equal(h.observationCount, metric === 'respiratory_rate_bpm' ? 6 : 7)
      assert.equal(h.series[0].key, metric === 'sleep_hours_last_night' ? 'journal' : 'rest')
    }
  })
  check('absent and single-point histories are explicit, never interpolated', () => {
    const empty = buildMetricHistory('heart_rate_bpm', [], [], range)
    assert.equal(empty.observationCount, 0); assert.equal(empty.missingDays.length, 7)
    const single = buildMetricHistory('heart_rate_bpm', [store.readings[0]], [], range)
    assert.equal(single.observationCount, 1); assert.equal(splitIntoRuns(single.series[0], single.emptyRecords)[0].length, 1)
  })
  check('actual chart component renders empty and single-point histories without invalid numbers', () => {
    for (const records of [[], [store.readings[0]]]) {
      const history = buildMetricHistory('heart_rate_bpm', records, [], range)
      const markup = renderToStaticMarkup(createElement(MetricChart, { history, range, missionStartDate: '2026-11-01' }))
      assert.doesNotMatch(markup, /NaN|Infinity/)
      assert.match(markup, /Show data table/)
      if (!records.length) assert.match(markup, /No heart rate values recorded/)
    }
  })
  check('different contexts do not share a series or bridge missing days', () => {
    const observations = [store.readings[0], { ...store.readings[1], measurement_context: 'exercise' }, store.readings[2]]
    const h = buildMetricHistory('heart_rate_bpm', observations, [], range)
    assert.deepEqual(h.series.map(s => s.key), ['rest', 'exercise'])
    assert.equal(splitIntoRuns(h.series[0], h.emptyRecords).length, 2)
  })
  check('an explicit null between two same-day values breaks the line', () => {
    const observations = ['10:00:00', '11:00:00', '12:00:00'].map((time, i) => ({ ...store.readings[0], reading_id: `R-${i}`, timestamp: `2026-11-01T${time}Z`, heart_rate_bpm: i === 1 ? null : 72 }))
    const h = buildMetricHistory('heart_rate_bpm', observations, [], range)
    assert.equal(splitIntoRuns(h.series[0], h.emptyRecords).length, 2)
  })
  check('range filtering and reported zero sleep preserve exact observations', () => {
    const h = buildMetricHistory('sleep_hours_last_night', [], [{ ...store.journal[0], sleep_hours_last_night: 0 }, store.journal[1]], { fromDay: 1, toDay: 1 })
    assert.equal(h.observationCount, 1); assert.equal(h.series[0].points[0].value, 0)
  })
  check('baseline copy differentiates insufficient and unavailable analysis', () => {
    const b = { status: 'insufficient_data', value: null, sample_count: 1, reference_start: null, reference_end: null, method: null, measurement_context: 'rest' }
    assert.match(describeBaseline('Heart rate', 'beats/min', b), /More observations needed/)
    assert.match(describeBaseline('Heart rate', 'beats/min', { ...b, status: 'not_implemented' }), /not implemented/)
  })
  check('live create defaults are explicit and corrections preserve original source/time', () => {
    const values = { sleep: 0, mood: null, notes: 'test' }
    const defaults = { timeUtc: '09:30:00', sourceId: 'SYN-CONFIGURED' }
    const created = buildJournalInput(store.astronauts[0], 8, null, values, defaults)
    assert.equal(created.timestamp, '2026-11-08T09:30:00Z'); assert.equal(created.source_id, defaults.sourceId)
    const edited = buildJournalInput(store.astronauts[0], 1, store.journal[0], values, defaults)
    assert.equal(edited.timestamp, store.journal[0].timestamp); assert.equal(edited.source_id, store.journal[0].source_id)
  })
  console.log(`\n${checks} series and journal-default checks passed.`)
} finally { await vite.close() }
