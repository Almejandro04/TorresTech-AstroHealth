/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string
  readonly VITE_DATA_SOURCE?: 'mock' | 'api'
  readonly VITE_API_TIMEOUT_MS?: string
  readonly VITE_JOURNAL_SOURCE_ID?: string
  readonly VITE_JOURNAL_TIME_UTC?: string
}
