const apiBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim() || 'http://localhost:8000'

const parsed = new URL(apiBaseUrl)
if (!['http:', 'https:'].includes(parsed.protocol) || parsed.search || parsed.hash) {
  throw new Error('VITE_API_BASE_URL must be an HTTP(S) base URL without a query or fragment.')
}

export const appConfig = {
  apiBaseUrl: apiBaseUrl.replace(/\/+$/, ''),
  dataSource: 'mock' as const,
}

/** Prepared for the live API integration in FRONTEND-06; never used for mock reads. */
export function buildApiUrl(path: `/api/${string}`): string {
  return `${appConfig.apiBaseUrl}${path}`
}
