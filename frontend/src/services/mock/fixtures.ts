/** Copied from docs/examples/api_examples.json (contract v0.1.0). Update with the shared fixtures. */
import type { ApiResponse, Astronaut, HealthSummary, PaginatedResponse } from '../../types/health'

export const profilesFixture = {
  "data": [
    {
      "astronaut_id": "AST-001",
      "name": "Demo Astronaut 1",
      "is_fictional": true,
      "mission_start_date": "2026-11-01",
      "planned_duration_days": 30
    },
    {
      "astronaut_id": "AST-002",
      "name": "Demo Astronaut 2",
      "is_fictional": true,
      "mission_start_date": "2026-11-01",
      "planned_duration_days": 30
    }
  ],
  "meta": {
    "schema_version": "0.1.0",
    "as_of": null,
    "total": 2,
    "limit": 100,
    "offset": 0
  }
} satisfies PaginatedResponse<Astronaut>

export const summaryFixture = {
  "data": {
    "astronaut": {
      "astronaut_id": "AST-001",
      "name": "Demo Astronaut 1",
      "is_fictional": true,
      "mission_start_date": "2026-11-01",
      "planned_duration_days": 30
    },
    "mission_day": 7,
    "latest_reading": {
      "reading_id": "READING-0007",
      "astronaut_id": "AST-001",
      "timestamp": "2026-11-07T12:00:00Z",
      "mission_day": 7,
      "heart_rate_bpm": 84,
      "spo2_percent": 97,
      "respiratory_rate_bpm": null,
      "measurement_context": "rest",
      "source_type": "synthetic",
      "source_id": "SYN-CORE-001"
    },
    "latest_journal": {
      "journal_id": "JOURNAL-0007",
      "astronaut_id": "AST-001",
      "timestamp": "2026-11-07T08:00:00Z",
      "mission_day": 7,
      "sleep_hours_last_night": 5.5,
      "mood_score": 2,
      "notes": null,
      "source_type": "synthetic",
      "source_id": "SYN-CORE-001"
    },
    "latest_metrics": {
      "heart_rate_bpm": {
        "value": 84,
        "unit": "beats/min",
        "timestamp": "2026-11-07T12:00:00Z",
        "mission_day": 7,
        "measurement_context": "rest",
        "source_type": "synthetic",
        "source_id": "SYN-CORE-001",
        "record_id": "READING-0007"
      },
      "spo2_percent": {
        "value": 97,
        "unit": "%",
        "timestamp": "2026-11-07T12:00:00Z",
        "mission_day": 7,
        "measurement_context": "rest",
        "source_type": "synthetic",
        "source_id": "SYN-CORE-001",
        "record_id": "READING-0007"
      },
      "respiratory_rate_bpm": {
        "value": 16,
        "unit": "breaths/min",
        "timestamp": "2026-11-06T12:00:00Z",
        "mission_day": 6,
        "measurement_context": "rest",
        "source_type": "synthetic",
        "source_id": "SYN-CORE-001",
        "record_id": "READING-0006"
      },
      "sleep_hours_last_night": {
        "value": 5.5,
        "unit": "hours",
        "timestamp": "2026-11-07T08:00:00Z",
        "mission_day": 7,
        "measurement_context": null,
        "source_type": "synthetic",
        "source_id": "SYN-CORE-001",
        "record_id": "JOURNAL-0007"
      },
      "mood_score": {
        "value": 2,
        "unit": "score",
        "timestamp": "2026-11-07T08:00:00Z",
        "mission_day": 7,
        "measurement_context": null,
        "source_type": "synthetic",
        "source_id": "SYN-CORE-001",
        "record_id": "JOURNAL-0007"
      }
    },
    "baselines": {
      "heart_rate_bpm": {
        "status": "available",
        "value": 72,
        "sample_count": 5,
        "reference_start": "2026-11-01T00:00:00Z",
        "reference_end": "2026-11-05T23:59:59Z",
        "measurement_context": "rest",
        "method": "fixture_reference_mean"
      },
      "spo2_percent": {
        "status": "available",
        "value": 98,
        "sample_count": 5,
        "reference_start": "2026-11-01T00:00:00Z",
        "reference_end": "2026-11-05T23:59:59Z",
        "measurement_context": "rest",
        "method": "fixture_reference_mean"
      },
      "respiratory_rate_bpm": {
        "status": "available",
        "value": 16,
        "sample_count": 5,
        "reference_start": "2026-11-01T00:00:00Z",
        "reference_end": "2026-11-05T23:59:59Z",
        "measurement_context": "rest",
        "method": "fixture_reference_mean"
      },
      "sleep_hours_last_night": {
        "status": "available",
        "value": 7.5,
        "sample_count": 5,
        "reference_start": "2026-11-01T00:00:00Z",
        "reference_end": "2026-11-05T23:59:59Z",
        "measurement_context": null,
        "method": "fixture_reference_mean"
      }
    },
    "alert_summary": {
      "evaluation_status": "available",
      "active_count": 1,
      "highest_severity": "warning",
      "recent": [
        {
          "alert_id": "ALERT-0001",
          "astronaut_id": "AST-001",
          "timestamp": "2026-11-07T12:00:00Z",
          "mission_day": 7,
          "indicator": "heart_rate_bpm",
          "severity": "warning",
          "status": "active",
          "description": "Introduced synthetic resting heart-rate change.",
          "explanation": "Fixture days 6-7 have a resting mean of 81 beats/min; the synthetic days 1-5 reference mean is 72. This controlled example illustrates explanation fields, not a validated medical threshold.",
          "rule_id": "DEMO-HR-CHANGE",
          "rule_version": "fixture-1",
          "observed_value": 81,
          "baseline_value": 72,
          "unit": "beats/min",
          "window_start": "2026-11-06T12:00:00Z",
          "window_end": "2026-11-07T12:00:00Z",
          "resolved_at": null,
          "source_type": "synthetic",
          "source_id": "SYN-CORE-001"
        }
      ]
    }
  },
  "meta": {
    "schema_version": "0.1.0",
    "as_of": "2026-11-07T23:59:59Z"
  }
} satisfies ApiResponse<HealthSummary>

export const emptySummaryFixture = {
  "data": {
    "astronaut": {
      "astronaut_id": "AST-002",
      "name": "Demo Astronaut 2",
      "is_fictional": true,
      "mission_start_date": "2026-11-01",
      "planned_duration_days": 30
    },
    "mission_day": null,
    "latest_reading": null,
    "latest_journal": null,
    "latest_metrics": {
      "heart_rate_bpm": {
        "value": null,
        "unit": "beats/min",
        "timestamp": null,
        "mission_day": null,
        "measurement_context": null,
        "source_type": null,
        "source_id": null,
        "record_id": null
      },
      "spo2_percent": {
        "value": null,
        "unit": "%",
        "timestamp": null,
        "mission_day": null,
        "measurement_context": null,
        "source_type": null,
        "source_id": null,
        "record_id": null
      },
      "respiratory_rate_bpm": {
        "value": null,
        "unit": "breaths/min",
        "timestamp": null,
        "mission_day": null,
        "measurement_context": null,
        "source_type": null,
        "source_id": null,
        "record_id": null
      },
      "sleep_hours_last_night": {
        "value": null,
        "unit": "hours",
        "timestamp": null,
        "mission_day": null,
        "measurement_context": null,
        "source_type": null,
        "source_id": null,
        "record_id": null
      },
      "mood_score": {
        "value": null,
        "unit": "score",
        "timestamp": null,
        "mission_day": null,
        "measurement_context": null,
        "source_type": null,
        "source_id": null,
        "record_id": null
      }
    },
    "baselines": {
      "heart_rate_bpm": {
        "status": "insufficient_data",
        "value": null,
        "sample_count": 0,
        "reference_start": null,
        "reference_end": null,
        "measurement_context": "rest",
        "method": null
      },
      "spo2_percent": {
        "status": "insufficient_data",
        "value": null,
        "sample_count": 0,
        "reference_start": null,
        "reference_end": null,
        "measurement_context": "rest",
        "method": null
      },
      "respiratory_rate_bpm": {
        "status": "insufficient_data",
        "value": null,
        "sample_count": 0,
        "reference_start": null,
        "reference_end": null,
        "measurement_context": "rest",
        "method": null
      },
      "sleep_hours_last_night": {
        "status": "insufficient_data",
        "value": null,
        "sample_count": 0,
        "reference_start": null,
        "reference_end": null,
        "measurement_context": null,
        "method": null
      }
    },
    "alert_summary": {
      "evaluation_status": "insufficient_data",
      "active_count": null,
      "highest_severity": null,
      "recent": []
    }
  },
  "meta": {
    "schema_version": "0.1.0",
    "as_of": null
  }
} satisfies ApiResponse<HealthSummary>


