import type { DayRange, MetricSeries, EmptyRecord } from '../lib/series'
import { splitIntoRuns } from '../lib/series'

const WIDTH = 132
const HEIGHT = 36
const PAD = 5

interface SparklineProps {
  series: MetricSeries | undefined
  emptyRecords: EmptyRecord[]
  range: DayRange
  missionStartMs: number
}

/**
 * Trend glyph for one comparable series. Decorative: its values are stated in text beside it
 * and charted with axes in Analytics. Missing days stay empty; no line crosses them.
 */
export function Sparkline({ series, emptyRecords, range, missionStartMs }: SparklineProps) {
  if (!series || series.points.length === 0) return null
  const dayMs = 86_400_000
  const start = missionStartMs + (range.fromDay - 1) * dayMs
  const span = (range.toDay - range.fromDay + 1) * dayMs
  const values = series.points.map((point) => point.value)
  const min = Math.min(...values)
  const max = Math.max(...values)
  const x = (t: number) => PAD + ((t - start) / span) * (WIDTH - PAD * 2)
  const y = (value: number) => (max === min ? HEIGHT / 2 : HEIGHT - PAD - ((value - min) / (max - min)) * (HEIGHT - PAD * 2))
  const last = series.points.at(-1)

  return (
    <svg className="sparkline" width={WIDTH} height={HEIGHT} viewBox={`0 0 ${WIDTH} ${HEIGHT}`} aria-hidden="true" focusable="false">
      {splitIntoRuns(series, emptyRecords).map((run) =>
        run.length === 1 ? (
          run[0] && <circle key={run[0].t} className="sparkline__dot" cx={x(run[0].t)} cy={y(run[0].value)} r={1.75} />
        ) : (
          <polyline key={run[0]?.t} className="sparkline__line" points={run.map((point) => `${x(point.t).toFixed(1)},${y(point.value).toFixed(1)}`).join(' ')} />
        ),
      )}
      {last && <circle className="sparkline__last" cx={x(last.t)} cy={y(last.value)} r={3.5} />}
    </svg>
  )
}
