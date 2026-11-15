/**
 * Verifies the WCAG 2.2 contrast of the color pairs the interface really uses.
 * Reads src/styles/tokens.css, so the report cannot drift from the shipped values.
 *
 *   npm run check:contrast
 *
 * Thresholds: 4.5:1 for normal text (SC 1.4.3) and 3:1 for the non-text parts needed to
 * identify a control or a state (SC 1.4.11).
 */
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

const css = readFileSync(fileURLToPath(new URL('../src/styles/tokens.css', import.meta.url)), 'utf8')

function readBlock(selector) {
  const start = css.indexOf(`${selector} {`)
  if (start === -1) throw new Error(`Token block not found: ${selector}`)
  const body = css.slice(start, css.indexOf('\n}', start))
  const tokens = {}
  for (const match of body.matchAll(/(--ah-[\w-]+):\s*(#[0-9a-fA-F]{6})\s*;/g)) tokens[match[1]] = match[2].toUpperCase()
  return tokens
}

const light = readBlock(':root')
const themes = { light, dark: { ...light, ...readBlock(':root[data-theme="dark"]') } }

const channel = (value) => {
  const v = value / 255
  return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4
}
const luminance = (hex) => {
  const n = parseInt(hex.slice(1), 16)
  return 0.2126 * channel((n >> 16) & 255) + 0.7152 * channel((n >> 8) & 255) + 0.0722 * channel(n & 255)
}
const ratio = (a, b) => {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x)
  return (hi + 0.05) / (lo + 0.05)
}

const TEXT = 4.5
const NON_TEXT = 3

/** [use in the interface, foreground token, background token, minimum ratio] */
const pairs = [
  // Text
  ['Body text on page', 'ink', 'page', TEXT],
  ['Body text on context bar and table header', 'ink', 'surface-2', TEXT],
  ['Body text on pressed or skeleton surface', 'ink', 'surface-3', TEXT],
  ['Secondary text on page', 'ink-2', 'page', TEXT],
  ['Secondary text on context bar', 'ink-2', 'surface-2', TEXT],
  ['Muted labels and timestamps on page', 'ink-3', 'page', TEXT],
  ['Muted labels on context bar', 'ink-3', 'surface-2', TEXT],
  ['Muted labels on selected row', 'ink-3', 'selected', TEXT],
  ['Link on page', 'link', 'page', TEXT],
  ['Link on context bar', 'link', 'surface-2', TEXT],

  // Masthead (brand band)
  ['Wordmark and active controls on masthead', 'masthead-ink', 'masthead', TEXT],
  ['Inactive tab label on masthead', 'masthead-ink-2', 'masthead', TEXT],
  ['Active tab label (tab joined to the context bar)', 'selected-ink', 'surface-2', TEXT],
  ['Focus ring on masthead', 'masthead-ink', 'masthead', NON_TEXT],

  // Actions and selection
  ['Primary button label', 'action-ink', 'action', TEXT],
  ['Primary button label, hover', 'action-ink', 'action-hover', TEXT],
  ['Primary button fill against page', 'action', 'page', NON_TEXT],
  ['Secondary button and input border on page', 'control-border', 'page', NON_TEXT],
  ['Input border on context bar', 'control-border', 'surface-2', NON_TEXT],
  ['Selected item label (bottom navigation, lists, segments)', 'selected-ink', 'selected', TEXT],
  ['Selected item text', 'ink', 'selected', TEXT],
  ['Focus ring on page', 'focus', 'page', NON_TEXT],
  ['Focus ring on context bar', 'focus', 'surface-2', NON_TEXT],

  // Semantic states (always paired with an icon and a label)
  ['Critical text on critical tint', 'critical', 'critical-bg', TEXT],
  ['Critical text and icon on page', 'critical', 'page', TEXT],
  ['Critical badge label (solid)', 'critical-solid-ink', 'critical-solid', TEXT],
  ['Critical badge fill against page', 'critical-solid', 'page', NON_TEXT],
  ['Field error text on page', 'critical', 'page', TEXT],
  ['Warning text on warning tint', 'warning', 'warning-bg', TEXT],
  ['Warning text and icon on page', 'warning', 'page', TEXT],
  ['Warning border against page', 'warning-line', 'page', NON_TEXT],
  ['Success text on success tint', 'success', 'success-bg', TEXT],
  ['Success text and icon on page', 'success', 'page', TEXT],
  ['Information text on information tint', 'info', 'info-bg', TEXT],
  ['Information text and icon on page', 'info', 'page', TEXT],
  ['Unknown / pending text on neutral tint', 'neutral', 'neutral-bg', TEXT],
  ['Unknown / pending text on page', 'neutral', 'page', TEXT],

  // Mission timeline
  ['Timeline: days in view against context bar', 'action', 'surface-2', NON_TEXT],
  ['Timeline: planned-day outline against context bar', 'control-border', 'surface-2', NON_TEXT],

  // Charts
  ['Series 1 (rest readings, journal) against page', 'series-1', 'page', NON_TEXT],
  ['Series 2 (exercise readings) against page', 'series-2', 'page', NON_TEXT],
  ['Series 3 (sleep-context readings) against page', 'series-3', 'page', NON_TEXT],
  ['Unknown-context series against page', 'series-unknown', 'page', NON_TEXT],
  ['Reference line against page', 'chart-reference', 'page', NON_TEXT],
  ['Axis and tick labels on page', 'ink-3', 'page', TEXT],
  ['Value labels over a gap band', 'ink-2', 'chart-gap', TEXT],
  ['Series 1 over the evidence-window band', 'series-1', 'chart-window', NON_TEXT],
]

/** Constraints the design deliberately respects instead of trying to pass. */
const constraints = [
  ['NASA Red on the NASA Blue band (never used to carry meaning)', '#E4002B', '#0032A0'],
  ['NASA Blue as a control color on the dark page (replaced by the action tint)', '#0032A0', themes.dark['--ah-page']],
]

let failures = 0
for (const [name, tokens] of Object.entries(themes)) {
  console.log(`\n${name.toUpperCase()} THEME`)
  console.log('  ratio  min  result  use')
  for (const [use, fg, bg, min] of pairs) {
    const fgHex = tokens[`--ah-${fg}`]
    const bgHex = tokens[`--ah-${bg}`]
    if (!fgHex || !bgHex) throw new Error(`Unknown token in pair "${use}": ${fg} / ${bg}`)
    const value = ratio(fgHex, bgHex)
    const pass = value >= min
    if (!pass) failures += 1
    console.log(`  ${value.toFixed(2).padStart(5)}  ${String(min).padEnd(3)}  ${pass ? 'pass  ' : 'FAIL  '}  ${use}  (${fgHex} on ${bgHex})`)
  }
}

console.log('\nDOCUMENTED CONSTRAINTS (expected to stay below 3:1, therefore avoided by the design)')
for (const [use, fg, bg] of constraints) console.log(`  ${ratio(fg, bg).toFixed(2).padStart(5)}  ${use}`)

if (failures > 0) {
  console.error(`\n${failures} contrast pair(s) below the required ratio.`)
  process.exit(1)
}
console.log(`\nAll ${pairs.length * 2} checked pairs meet their required ratio.`)
