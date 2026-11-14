import type { HealthDataSource } from './healthDataSource'
import { profilesFixture, summaryFixture, emptySummaryFixture } from './mock/fixtures'

export const mockHealthDataSource: HealthDataSource = {
  async getAstronauts() {
    return structuredClone(profilesFixture)
  },
  async getSummary(astronautId) {
    const fixture = [summaryFixture, emptySummaryFixture].find(
      (response) => response.data.astronaut.astronaut_id === astronautId,
    )
    if (!fixture) throw new Error('The selected mission profile could not be found.')
    return structuredClone(fixture)
  },
}
