/** Mission time is UTC throughout (contract v0.1.0): day 1 is `mission_start_date`. */
const DAY_MS = 86_400_000
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
const pad = (value: number) => String(value).padStart(2, '0')

type Instant = string | number

export function formatUtcShortDate(instant: Instant): string {
  const date = new Date(instant)
  return `${date.getUTCDate()} ${MONTHS[date.getUTCMonth()]}`
}

export function formatUtcDate(instant: Instant): string {
  return `${formatUtcShortDate(instant)} ${new Date(instant).getUTCFullYear()}`
}

export function formatUtcTime(instant: Instant): string {
  const date = new Date(instant)
  return `${pad(date.getUTCHours())}:${pad(date.getUTCMinutes())} UTC`
}

export function formatUtcDateTime(instant: Instant): string {
  return `${formatUtcDate(instant)}, ${formatUtcTime(instant)}`
}

export function missionDayStartMs(missionStartDate: string, day: number): number {
  return Date.parse(`${missionStartDate}T00:00:00Z`) + (day - 1) * DAY_MS
}

export function missionDayOf(missionStartDate: string, instant: Instant): number {
  return Math.floor((new Date(instant).getTime() - missionDayStartMs(missionStartDate, 1)) / DAY_MS) + 1
}

/** `YYYY-MM-DD` of a mission day. */
export function missionDayIsoDate(missionStartDate: string, day: number): string {
  return new Date(missionDayStartMs(missionStartDate, day)).toISOString().slice(0, 10)
}

/** Last second of a mission day: the cutoff used to view the mission "as of" that day. */
export function missionDayEndIso(missionStartDate: string, day: number): string {
  return `${missionDayIsoDate(missionStartDate, day)}T23:59:59Z`
}

/** "Day 7 · 7 Nov 2026, 12:00 UTC" */
export function formatObservation(day: number, timestamp: string): string {
  return `Day ${day} · ${formatUtcDateTime(timestamp)}`
}
