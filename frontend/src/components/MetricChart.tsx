import { useId, useMemo, useState } from 'react'
import { Table2 } from 'lucide-react'
import { CartesianGrid, Line, LineChart, ReferenceArea, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { METRICS, describeValue, formatNumber, moodLabel } from '../lib/metrics'
import { formatDayList, splitIntoRuns } from '../lib/series'
import type { DayRange, MetricHistory, SeriesKey } from '../lib/series'
import { formatUtcDateTime, formatUtcShortDate, missionDayStartMs } from '../lib/time'
import type { BaselineMetric } from '../types/health'

type DotProps = { cx?: number; cy?: number; index?: number; value?: unknown }

const DAY_MS = 86_400_000
const HALF_DAY_MS = DAY_MS / 2

/** Color and marker shape both identify a series; neither is a status hue. */
const SERIES_STYLE: Record<SeriesKey, { color: string; shape: 'circle' | 'triangle' | 'diamond' | 'ring' }> = {
  rest: { color: 'var(--ah-series-1)', shape: 'circle' },
  journal: { color: 'var(--ah-series-1)', shape: 'circle' },
  exercise: { color: 'var(--ah-series-2)', shape: 'triangle' },
  sleep: { color: 'var(--ah-series-3)', shape: 'diamond' },
  unknown: { color: 'var(--ah-series-unknown)', shape: 'ring' },
}

/** Round axis bounds and evenly spaced ticks that contain every value, with a little headroom. */
function niceScale(values: number[]): { domain: [number, number]; ticks: number[] } {
  if (values.length === 0) return { domain: [0, 1], ticks: [0, 1] }
  const min = Math.min(...values)
  const max = Math.max(...values)
  const span = Math.max(max - min, 1)
  const step = [0.5, 1, 2, 5, 10, 20, 50, 100].find((candidate) => span / candidate <= 4) ?? 100
  const low = Math.max(0, Math.floor((min - step * 0.25) / step) * step)
  const high = Math.ceil((max + step * 0.25) / step) * step
  const ticks: number[] = []
  for (let tick = low; tick <= high + step / 1000; tick += step) ticks.push(Math.round(tick * 10) / 10)
  return { domain: [low, high], ticks }
}

function Marker({ cx, cy, seriesKey, size = 4.5 }: { cx: number; cy: number; seriesKey: SeriesKey; size?: number }) {
  const { color, shape } = SERIES_STYLE[seriesKey]
  const ring = { stroke: 'var(--ah-page)', strokeWidth: 2 }
  if (shape === 'triangle') {
    const s = size + 1.5
    return <path d={`M${cx} ${cy - s}L${cx + s} ${cy + s * 0.8}L${cx - s} ${cy + s * 0.8}Z`} fill={color} {...ring} />
  }
  if (shape === 'diamond') {
    const s = size + 1.5
    return <path d={`M${cx} ${cy - s}L${cx + s} ${cy}L${cx} ${cy + s}L${cx - s} ${cy}Z`} fill={color} {...ring} />
  }
  if (shape === 'ring') return <circle cx={cx} cy={cy} r={size} fill="var(--ah-page)" stroke={color} strokeWidth={2} />
  return <circle cx={cx} cy={cy} r={size} fill={color} {...ring} />
}

function LegendKey({ seriesKey }: { seriesKey: SeriesKey }) {
  return (
    <svg width="26" height="12" viewBox="0 0 26 12" aria-hidden="true" focusable="false">
      <line x1="1" y1="6" x2="25" y2="6" stroke={SERIES_STYLE[seriesKey].color} strokeWidth="2" strokeLinecap="round" />
      <Marker cx={13} cy={6} seriesKey={seriesKey} size={3.5} />
    </svg>
  )
}

interface MetricChartProps {
  history: MetricHistory
  range: DayRange
  missionStartDate: string
  /** Comparable individual reference, when the data source provides one. */
  baseline?: BaselineMetric | null
  /** Evidence window of an alert, drawn as a band behind the series. */
  highlight?: { start: string; end: string; label: string }
  height?: number
}

export function MetricChart({ history, range, missionStartDate, baseline = null, highlight, height = 220 }: MetricChartProps) {
  const [tableOpen, setTableOpen] = useState(false)
  const tableId = useId()
  const { metric } = history
  const info = METRICS[metric]
  const isMood = metric === 'mood_score'
  const reference = baseline?.status === 'available' && baseline.value !== null ? baseline.value : null

  const model = useMemo(() => {
    const rows = new Map<number, Record<string, number>>()
    const rowAt = (t: number) => {
      const row = rows.get(t) ?? { t }
      rows.set(t, row)
      return row
    }
    // One <Line> per unbroken run: lines never cross a missing day or an empty record.
    const lines = history.series.flatMap((series) =>
      splitIntoRuns(series, history.emptyRecords).map((run, index) => {
        const dataKey = `${series.key}:${index}`
        for (const point of run) rowAt(point.t)[dataKey] = point.value
        return { dataKey, seriesKey: series.key }
      }),
    )
    for (const empty of history.emptyRecords) rowAt(empty.t)
    return { rows: [...rows.values()].sort((a, b) => (a.t ?? 0) - (b.t ?? 0)), lines }
  }, [history])

  const startMs = missionDayStartMs(missionStartDate, range.fromDay)
  const endMs = missionDayStartMs(missionStartDate, range.toDay + 1)
  const dayCount = range.toDay - range.fromDay + 1
  const tickStep = Math.max(1, Math.ceil(dayCount / 8))
  const ticks: number[] = []
  for (let day = range.fromDay; day <= range.toDay; day += tickStep) ticks.push(missionDayStartMs(missionStartDate, day) + HALF_DAY_MS)
  const dayOfMs = (ms: number) => Math.floor((ms - missionDayStartMs(missionStartDate, 1)) / DAY_MS) + 1

  const values = history.series.flatMap((series) => series.points.map((point) => point.value))
  if (reference !== null) values.push(reference)
  const scale = isMood ? { domain: [1, 5] as [number, number], ticks: [1, 2, 3, 4, 5] } : niceScale(values)

  const pointsAt = (t: number) =>
    history.series.flatMap((series) => series.points.filter((point) => point.t === t).map((point) => ({ series, point })))
  const emptyAt = (t: number) => history.emptyRecords.filter((empty) => empty.t === t)
  const seriesLabel = (key: SeriesKey) => history.series.find((series) => series.key === key)?.label ?? (key === 'journal' ? 'Daily entry' : `${key} readings`)
  const showMarkers = history.observationCount <= 45

  const tableRows = [
    ...history.series.flatMap((series) => series.points.map((point) => ({ ...point, label: series.label, text: describeValue(metric, point.value) }))),
    ...history.emptyRecords.map((empty) => ({ ...empty, label: seriesLabel(empty.seriesKey), text: 'Not recorded' })),
  ].sort((a, b) => a.t - b.t)

  return (
    <div className="chart">
      {history.series.length > 1 && (
        <ul className="chart__legend">
          {history.series.map((series) => (
            <li key={series.key}><LegendKey seriesKey={series.key} /> {series.label}</li>
          ))}
        </ul>
      )}

      {history.observationCount === 0 ? (
        <p className="chart__empty">
          No {info.label.toLowerCase()} values recorded from Day {range.fromDay} to Day {range.toDay}.
        </p>
      ) : (
        <div className="chart__plot" style={{ height }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={model.rows} margin={{ top: 14, right: 14, bottom: 4, left: 0 }} accessibilityLayer>
              <CartesianGrid vertical={false} stroke="var(--ah-chart-grid)" />
              {highlight && (
                <ReferenceArea x1={Date.parse(highlight.start) - HALF_DAY_MS / 3} x2={Date.parse(highlight.end) + HALF_DAY_MS / 3} fill="var(--ah-chart-window)" fillOpacity={1} strokeOpacity={0} ifOverflow="hidden" />
              )}
              {history.missingDays.map((day) => (
                <ReferenceArea key={day} x1={missionDayStartMs(missionStartDate, day)} x2={missionDayStartMs(missionStartDate, day + 1)} fill="var(--ah-chart-gap)" fillOpacity={1} strokeOpacity={0} ifOverflow="hidden" />
              ))}
              <XAxis
                dataKey="t"
                type="number"
                scale="time"
                domain={[startMs, endMs]}
                ticks={ticks}
                tickFormatter={(value: number) => String(dayOfMs(value))}
                tickLine={false}
                axisLine={{ stroke: 'var(--ah-chart-axis)' }}
                tick={{ fill: 'var(--ah-ink-3)', fontSize: 12 }}
                height={26}
              />
              <YAxis
                domain={scale.domain}
                ticks={scale.ticks}
                tickFormatter={(value: number) => (isMood ? moodLabel(value) : formatNumber(value))}
                allowDecimals={metric === 'sleep_hours_last_night'}
                width={isMood ? 68 : 40}
                tickLine={false}
                axisLine={false}
                tick={{ fill: 'var(--ah-ink-3)', fontSize: 12 }}
              />
              <Tooltip
                isAnimationActive={false}
                cursor={{ stroke: 'var(--ah-chart-axis)', strokeWidth: 1 }}
                content={({ active, label }) => {
                  const t = Number(label)
                  if (!active || Number.isNaN(t)) return null
                  const found = pointsAt(t)
                  const empty = emptyAt(t)
                  if (found.length === 0 && empty.length === 0) return null
                  return (
                    <div className="chart-tooltip">
                      <p className="chart-tooltip__when">Day {dayOfMs(t)} · {formatUtcDateTime(t)}</p>
                      {found.map(({ series, point }) => (
                        <p key={series.key} className="chart-tooltip__row">
                          <LegendKey seriesKey={series.key} />
                          <strong>{describeValue(metric, point.value)}</strong>
                          <span>{series.label}</span>
                        </p>
                      ))}
                      {empty.map((record) => (
                        <p key={record.recordId} className="chart-tooltip__row"><strong>Not recorded</strong><span>{seriesLabel(record.seriesKey)}</span></p>
                      ))}
                      {reference !== null && <p className="chart-tooltip__ref">Reference {describeValue(metric, reference)}</p>}
                    </div>
                  )
                }}
              />
              {reference !== null && (
                <ReferenceLine
                  y={reference}
                  stroke="var(--ah-chart-reference)"
                  strokeWidth={1.5}
                  strokeDasharray="6 4"
                  label={{ value: `Reference ${formatNumber(reference)}`, position: 'insideBottomRight', fill: 'var(--ah-ink-2)', fontSize: 12 }}
                />
              )}
              {model.lines.map(({ dataKey, seriesKey }) => (
                <Line
                  key={dataKey}
                  dataKey={dataKey}
                  type="linear"
                  stroke={SERIES_STYLE[seriesKey].color}
                  strokeWidth={2}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  connectNulls
                  isAnimationActive={false}
                  dot={(dot: DotProps) =>
                    showMarkers && typeof dot.cx === 'number' && typeof dot.cy === 'number' && typeof dot.value === 'number'
                      ? <Marker key={dot.index} cx={dot.cx} cy={dot.cy} seriesKey={seriesKey} />
                      : <g key={dot.index} />
                  }
                  activeDot={(dot: DotProps) =>
                    typeof dot.cx === 'number' && typeof dot.cy === 'number' && typeof dot.value === 'number'
                      ? <Marker key={dot.index} cx={dot.cx} cy={dot.cy} seriesKey={seriesKey} size={6} />
                      : <g key={dot.index} />
                  }
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {history.observationCount > 0 && (
        <p className="chart__axis-note mono">
          Mission day · {formatUtcShortDate(startMs)} to {formatUtcShortDate(endMs - 1)} (UTC)
        </p>
      )}
      <ul className="chart__notes">
        {highlight && <li><span className="chart__swatch chart__swatch--window" aria-hidden="true" /> {highlight.label}</li>}
        {history.missingDays.length > 0 && history.observationCount > 0 && (
          <li><span className="chart__swatch chart__swatch--gap" aria-hidden="true" /> No value recorded: {formatDayList(history.missingDays)}. The gap is kept, not filled.</li>
        )}
      </ul>

      <button type="button" className="button button--quiet button--small" aria-expanded={tableOpen} aria-controls={tableId} onClick={() => setTableOpen((open) => !open)}>
        <Table2 size={15} aria-hidden="true" /> {tableOpen ? 'Hide data table' : 'Show data table'}
      </button>
      <div id={tableId} hidden={!tableOpen} className="table-scroll">
        {tableOpen && (
          <table className="data-table">
            <caption className="visually-hidden">{info.label}, Day {range.fromDay} to Day {range.toDay}</caption>
            <thead>
              <tr><th scope="col">Day</th><th scope="col">Observed (UTC)</th><th scope="col">Series</th><th scope="col">Value</th></tr>
            </thead>
            <tbody>
              {tableRows.length === 0 && <tr><td colSpan={4}>No records in this period.</td></tr>}
              {tableRows.map((row) => (
                <tr key={`${row.recordId}:${row.label}`}>
                  <td>Day {row.day}</td>
                  <td className="mono">{formatUtcDateTime(row.timestamp)}</td>
                  <td>{row.label}</td>
                  <td>{row.text}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

/** One sentence that says whether a comparable reference exists, and why not when it does not. */
export function describeBaseline(metricLabel: string, unit: string, baseline: BaselineMetric | null): string {
  if (!baseline) return 'No reference: mood is an ordinal self-report and is shown directly.'
  const context = baseline.measurement_context ? `${baseline.measurement_context} ` : ''
  if (baseline.status === 'available' && baseline.value !== null) {
    const window =
      baseline.reference_start && baseline.reference_end
        ? ` from ${formatUtcShortDate(baseline.reference_start)} to ${formatUtcShortDate(baseline.reference_end)}`
        : ''
    return `Individual reference: ${formatNumber(baseline.value)} ${unit}, from ${baseline.sample_count} ${context}observations${window}${baseline.method ? ` (method: ${baseline.method})` : ''}.`
  }
  if (baseline.status === 'insufficient_data') {
    return `More observations needed for a ${metricLabel.toLowerCase()} reference (${baseline.sample_count} so far). Values are shown without comparison.`
  }
  return 'Reference not available: the analysis is not implemented in this data source. Values are shown without comparison.'
}
