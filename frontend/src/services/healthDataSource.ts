import type { ApiResponse, HealthSummary, PaginatedResponse, Astronaut } from '../types/health'

/** Implement this same boundary for FastAPI in FRONTEND-06; views do not own data transport. */
export interface HealthDataSource {
  getAstronauts(): Promise<PaginatedResponse<Astronaut>>
  getSummary(astronautId: string): Promise<ApiResponse<HealthSummary>>
}
