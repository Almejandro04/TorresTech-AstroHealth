/** Validate 30-day mission views of a running FastAPI server with the real frontend guards.
 * Node 22.13+; read-only; loads the unchanged frontend responseValidation.ts in memory.
 * Usage: node backend/scripts/check_mission_views.mjs http://127.0.0.1:PORT AST-101 2026-11-19T23:59:59Z [...]
 */
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { stripTypeScriptTypes } from 'node:module'

const [baseUrl, astronautId, ...cutoffs] = process.argv.slice(2)
assert.ok(baseUrl && astronautId && cutoffs.length, 'Usage: node check_mission_views.mjs URL ASTRONAUT_ID CUTOFF [CUTOFF...]')
const source = readFileSync(new URL('../../frontend/src/services/responseValidation.ts', import.meta.url), 'utf8')
const guards = await import(`data:text/javascript;base64,${Buffer.from(stripTypeScriptTypes(source)).toString('base64')}`)
const { responses, matchesView } = guards

const views = { summary: responses.summary, readings: responses.readings, journal: responses.journal, alerts: responses.alerts }
let count = 0
for (const cutoff of cutoffs) {
  for (const [view, guard] of Object.entries(views)) {
    const url = new URL(`${baseUrl}/api/astronauts/${encodeURIComponent(astronautId)}/${view}`)
    url.searchParams.set('as_of', cutoff)
    if (view !== 'summary') url.searchParams.set('limit', '1000')
    const response = await fetch(url, { headers: { Accept: 'application/json' } })
    assert.equal(response.status, 200, `${view} at ${cutoff}: HTTP ${response.status}`)
    const body = await response.json()
    assert.ok(guard(body), `${view} at ${cutoff}: responses.${view} guard rejected the body`)
    assert.ok(matchesView(body, astronautId, cutoff), `${view} at ${cutoff}: matchesView rejected the body`)
    count++
  }
}
console.log(`${count} mission views passed responses.* and matchesView for ${astronautId}.`)
