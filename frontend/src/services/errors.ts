import type { ApiErrorDetail } from '../types/health'

/**
 * Transport-independent failure categories. Views decide what to show from `kind`,
 * `code`, and `details[].field`, never from the English wording of a server message.
 */
export type HealthDataErrorKind = 'not_found' | 'validation' | 'conflict' | 'server' | 'network' | 'timeout'

interface HealthDataErrorInit {
  kind: HealthDataErrorKind
  message: string
  status?: number | null
  code?: string | null
  details?: ApiErrorDetail[]
}

export class HealthDataError extends Error {
  readonly kind: HealthDataErrorKind
  readonly status: number | null
  readonly code: string | null
  readonly details: ApiErrorDetail[]

  constructor(init: HealthDataErrorInit) {
    super(init.message)
    this.name = 'HealthDataError'
    this.kind = init.kind
    this.status = init.status ?? null
    this.code = init.code ?? null
    this.details = init.details ?? []
  }
}

export function toHealthDataError(error: unknown): HealthDataError {
  if (error instanceof HealthDataError) return error
  return new HealthDataError({
    kind: 'server',
    message: error instanceof Error ? error.message : 'Unexpected data source failure.',
  })
}
