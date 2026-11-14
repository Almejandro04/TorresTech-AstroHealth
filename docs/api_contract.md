# AstroHealth API and Data Contract

Version: **0.1.0**  
Status: **Contract prepared; product decisions recorded; pull request peer review pending.**  
Tracking issue: [CORE-01 / #1](https://github.com/Almejandro04/TorresTech-AstroHealth/issues/1)

This specification defines the MVP interface between the React frontend, FastAPI backend, and data preparation work. It specifies behavior; it does not implement the application. Changes to field names, units, enum values, or response shapes require updates to this document and its fixtures in the same pull request before dependent work merges.

## 1. Decisions and implementation conventions

| Decision | Proposed v0.1.0 behavior | Reason / review owner |
| --- | --- | --- |
| Mission profiles | Fictional astronauts; demonstration endpoints accept synthetic observations only | All three: avoid presenting terrestrial subjects as astronauts |
| Mission day | Day 1 is `mission_start_date`, using UTC calendar dates | Jorge + Jhonatan: identical labels on cards, charts, and imports |
| Daily information | Journal entries are separate from point-in-time vital readings | All three: different observation cadence |
| Dashboard values | Latest non-null value per indicator, with that value's own timestamp and provenance | Confirmed product decision in the working session |
| Mood | Integer 1–5: very low, low, neutral, high, very high | Confirmed; a product self-report scale, not a validated clinical score |
| Fatigue | Deferred from the v0.1.0 wire format | Confirmed; keep sleep, mood, and notes in the initial journal |
| Interface language | English labels, help, feedback, and error recovery instructions | Confirmed; API identifiers and technical documentation remain English |
| Journal corrections | Edit the existing daily entry, retain its ID, and save explicitly | Confirmed; preserve a single entry per astronaut/day |
| Journal history | Add `GET /api/astronauts/{id}/journal` | Jorge: sleep charts need daily history; summary alone is insufficient |
| Missing data | Explicit JSON `null`; never substitute zero, normal, or a previous measurement | All three |
| Alert availability | Distinguish `not_implemented`, `insufficient_data`, and `available` | Jhonatan: an empty list must not imply successful analysis |
| Alert interaction | Consult and understand; read-only API; engine maintains `active` / `resolved` | Confirmed; no reviewed/acknowledged state or manual resolution action in this MVP |
| Replay | Observation-time cutoff `as_of`, also returned in responses | Jhonatan: later observations must not leak into an earlier demo day |
| Write retries | Exact reading retry returns existing record; conflicting duplicate returns 409; journal is one updatable entry per day | Jhonatan + Ismael |

The six rows marked confirmed record decisions supplied during the working session. Other rows are documented engineering conventions for peer review, not a claim that every line has already been approved. No application implementation, scientific validation, or clinical endorsement is implied. Further product changes are discussed before changing their wire format; ordinary implementation choices follow this contract.

## 2. Conventions and validation

- JSON property names use `snake_case`. JSON numbers must be finite; `NaN` and infinity are invalid.
- IDs are opaque, case-sensitive, nonempty strings of at most 64 characters. The URL's `{id}` identifies the astronaut. Request bodies do not repeat `astronaut_id`; stored/output records do.
- Timestamps are UTC strings ending in `Z`, with seconds and optional fractional seconds, e.g. `2026-11-07T12:00:00Z`. Offset-free timestamps are rejected. Exports always use this UTC form.
- `mission_start_date` is an ISO calendar date. `mission_day = (UTC date(timestamp) - mission_start_date).days + 1`. Day numbers start at 1; a supplied day must match the timestamp and be within the profile's planned duration.
- The journal timestamp is the effective observation time attributed to that day's self-report. It is not a server audit timestamp. Sleep refers to the previous sleep period ending on that mission day. This MVP defines day boundaries in UTC, not Ecuador local time.
- Request fields listed below are required even when nullable. Unknown body fields and wrong primitive types are rejected; strings such as `"83"` do not count as JSON numbers. Booleans do not count as integers.
- All CSV/JSON import records retain `source_type` and `source_id`. For the fictional mission API, `source_type` is exactly `synthetic`. `source_id` resolves to a source manifest.
- Schema/scale constraints are data-shape checks, not medical normal ranges. An unusual but structurally valid observation is not rejected just because an analysis rule might flag it.

## 3. Shared models

### 3.1 Astronaut

| Field | JSON type | Rule |
| --- | --- | --- |
| `astronaut_id` | string | Stable fictional profile ID |
| `name` | string | Nonempty display name |
| `is_fictional` | boolean | Always `true` for this MVP |
| `mission_start_date` | string | ISO date, UTC calendar boundary |
| `planned_duration_days` | integer | Positive; demonstration scenario is approximately 30 days |

Profiles are seeded locally. Profile creation/editing endpoints are outside this contract. The current mission day belongs to the summary and is derived from the selected data cutoff, not the computer's current date.

### 3.2 HealthReadingInput / HealthReading

| Input field | JSON type | Rule / unit |
| --- | --- | --- |
| `timestamp` | string | Effective UTC observation time |
| `mission_day` | integer | Positive and consistent with the profile and timestamp |
| `heart_rate_bpm` | number or null | Greater than 0 when present; beats/min |
| `spo2_percent` | number or null | 0–100 inclusive; percent |
| `respiratory_rate_bpm` | number or null | Greater than 0 when present; breaths/min |
| `measurement_context` | string | `rest`, `exercise`, `sleep`, or `unknown` |
| `source_type` | string | `synthetic` |
| `source_id` | string | Manifest identifier |

At least one of the three vital measurements must be non-null. A missing observation is absent; a partially observed record uses null for the missing metrics. Sleep and mood do not appear in a vital reading.

The output `HealthReading` contains every input field plus server-generated `reading_id` and the URL's `astronaut_id`. The latest raw record retains its explicit missing fields. Dashboard cards instead use the per-indicator `latest_metrics` snapshots in section 3.5. An older non-null value retains its original observation time and must not be relabeled as a new measurement. Charts keep missing values as gaps.

### 3.3 HealthJournalInput / HealthJournal

| Input field | JSON type | Rule / unit |
| --- | --- | --- |
| `timestamp` | string | Effective self-report time in UTC |
| `mission_day` | integer | Must match timestamp/profile |
| `sleep_hours_last_night` | number or null | 0–24 inclusive; hours |
| `mood_score` | integer or null | 1 very low; 2 low; 3 neutral; 4 high; 5 very high |
| `notes` | string or null | Trimmed, at most 2,000 characters; display as plain text |
| `source_type` | string | `synthetic` |
| `source_id` | string | Manifest identifier |

At least one of sleep, mood, or a nonblank note must be present. Sleep `0` is a reported value, not missing. The output adds `journal_id` and `astronaut_id`. A profile has at most one entry per mission day. Reposting the day updates that entry, retains its ID, and returns 200; first creation returns 201. The frontend preserves failed input and shows whether a write succeeded. Revision history/concurrent editing is deferred.

### 3.4 HealthAlert

Alerts are generated by the backend, not posted by the frontend. All fields below are present in responses.

| Field | JSON type | Rule |
| --- | --- | --- |
| `alert_id`, `astronaut_id` | string | Stable IDs |
| `timestamp`, `mission_day` | string, integer | Detection observation time and matching day |
| `indicator` | string | One of the five metric field names defined above |
| `severity` | string | `info`, `warning`, or `critical`; experimental attention level |
| `status` | string | `active` or `resolved` |
| `description`, `explanation` | string | Nonempty observational wording; explain the detected pattern |
| `rule_id`, `rule_version` | string | Traceable experimental rule or explicitly synthetic scenario rule |
| `observed_value` | number | Value/statistic described by the rule |
| `baseline_value` | number or null | Reference value, when applicable |
| `unit` | string | `beats/min`, `%`, `breaths/min`, `hours`, or `score`, matching indicator |
| `window_start`, `window_end` | string | UTC evidence window; start <= end <= detection timestamp |
| `resolved_at` | string or null | Null while active; UTC time >= detection when resolved |
| `source_type`, `source_id` | string | `synthetic` and traceable manifest ID |

Return only alerts whose detection time is at or before `as_of`. An alert resolved after that cutoff appears active with `resolved_at: null` in that earlier observation view. Deduplicate a rule event using its documented event key; replay must not create unlimited copies. No lifecycle mutation endpoint is included. Actual thresholds, formulas, minimum-history policies, and rule validation belong to BACKEND-04/05 and DATA-06; this contract does not declare them medically valid.

### 3.5 MetricSnapshot, BaselineMetric, and HealthSummary

Each dashboard indicator uses a `MetricSnapshot`. Select its most recent non-null observation at or before `as_of`, independently of the other indicators. Vital indicators come from readings; sleep and mood come from journal entries. Break timestamp ties deterministically by record ID. Every snapshot includes all these fields:

| Field | JSON type | Rule |
| --- | --- | --- |
| `value` | number or null | Same type/scale as the indicator; mood remains an integer |
| `unit` | string | `beats/min`, `%`, `breaths/min`, `hours`, or `score`, matching the indicator |
| `timestamp` | string or null | Actual UTC time of the selected non-null observation |
| `mission_day` | integer or null | Day of that observation, not the current summary day |
| `measurement_context` | string or null | Original vital context; null for sleep/mood |
| `source_type`, `source_id` | string or null | Original provenance, not a new synthetic observation |
| `record_id` | string or null | Corresponding reading/journal ID for traceability |

If no non-null observation exists, `value` and every metadata field except `unit` are null. Keep the known unit. If the selected value predates the latest raw record or selected mission day, display its own day/time visibly. Do not claim it was freshly measured or assign an invented clinical freshness threshold. History endpoints and charts must not forward-fill gaps just because cards show a prior observed value.

`BaselineMetric` has these required fields:

| Field | JSON type | Rule |
| --- | --- | --- |
| `status` | string | `available`, `insufficient_data`, or `not_implemented` |
| `value` | number or null | Non-null only when available; same unit as metric |
| `sample_count` | integer | Nonnegative count of observations used; 0 when not implemented |
| `reference_start`, `reference_end` | string or null | UTC window, both present when available and never beyond `as_of` |
| `measurement_context` | string or null | Comparable reading context; null for daily sleep |
| `method` | string or null | Named/documented method; null before implementation |

Missing baseline values must not imply zero. Baselines for distinct astronauts, contexts, or units must not be combined. The four baseline keys are `heart_rate_bpm`, `spo2_percent`, `respiratory_rate_bpm`, and `sleep_hours_last_night`. Mood is an ordinal self-report displayed directly; arithmetic mood baselines are deferred.

`HealthSummary` contains:

| Field | JSON type | Meaning |
| --- | --- | --- |
| `astronaut` | Astronaut | Selected fictional profile |
| `mission_day` | integer or null | Day at `as_of`; null when no observations and no explicit cutoff |
| `latest_reading` | HealthReading or null | Latest record at/before cutoff |
| `latest_journal` | HealthJournal or null | Latest daily entry at/before cutoff; keep its own day visible |
| `latest_metrics` | object | Five MetricSnapshot keys: the three vital metric names, `sleep_hours_last_night`, and `mood_score`; dashboard cards consume these |
| `baselines` | object | The four keys above, each a BaselineMetric |
| `alert_summary` | object | `evaluation_status`, `active_count`, `highest_severity`, and `recent` |

`evaluation_status` is `not_implemented`, `insufficient_data`, or `available`. The first two return `active_count: null`, `highest_severity: null`, and `recent: []`. When available, `active_count` is a nonnegative integer, `highest_severity` is the highest active severity or null, and `recent` contains at most three active alerts sorted newest first. Only `available` plus count 0 means that an evaluation completed without an active alert; it is not a claim of good health. A baseline being unavailable does not prevent raw readings/history from being shown.

## 4. HTTP interface

Local proposed defaults: API `http://localhost:8000`; frontend `http://localhost:5173`; frontend config `VITE_API_BASE_URL=http://localhost:8000`. The client appends `/api/...`. Backend CORS allows the exact configured frontend origin; add `http://127.0.0.1:5173` explicitly if used. OpenAPI/Swagger are expected at `/openapi.json` and `/docs` after BACKEND-01. Authentication and cloud deployment are outside this fictitious-data MVP.

| Method | Endpoint | Success `data` | HTTP success |
| --- | --- | --- | --- |
| GET | `/api/health` | `{ "status": "ok", "service": "astrohealth-api" }` | 200 |
| GET | `/api/astronauts` | Astronaut array | 200 |
| GET | `/api/astronauts/{id}/readings` | HealthReading array | 200 |
| POST | `/api/astronauts/{id}/readings` | HealthReading | 201 new; 200 exact retry |
| GET | `/api/astronauts/{id}/journal` | HealthJournal array | 200 |
| POST | `/api/astronauts/{id}/journal` | HealthJournal | 201 new; 200 update/retry |
| GET | `/api/astronauts/{id}/summary` | HealthSummary | 200 |
| GET | `/api/astronauts/{id}/alerts` | HealthAlert array | 200 |

The new journal GET is the only addition to the original endpoint list. It gives the sleep chart a dedicated history source. It must be implemented with BACKEND-03 and consumed by FRONTEND-03/06.

### Query parameters and cutoff

- Lists use `limit` (integer 1–1,000; default 100) and `offset` (integer >= 0; default 0). Profiles sort by ID. Readings/journals sort by `(timestamp, ID)` ascending; alerts sort by `(timestamp descending, alert_id ascending)`.
- Readings, journal, and alert lists accept `from_day` and `to_day` (inclusive valid mission days; omitted means no bound). Reversed or out-of-mission bounds return 422.
- Those lists and summary accept `as_of` (UTC timestamp). Records after it must not influence data, baselines, or alert evaluation. If absent, resolve it to the latest persisted reading/journal timestamp for the selected profile; if none exist, return null. Explicit cutoffs outside the mission return 422.
- Alerts additionally accept `status=active|resolved`; absent means both. Counts in list metadata are after filters, before pagination.
- An empty list is HTTP 200 with `data: []` and `total: 0`. A nonexistent astronaut is 404, not an empty list. Empty histories must not require implemented analysis.
- `as_of` is an observation cutoff, not a historical database revision query: journal corrections replace the day's entry. Full edit-history reconstruction is not in the MVP. No future observation, baseline window, or resolved state may be included in a replay view.

### Response envelopes

Every success response has `data` and `meta`. Every meta contains `schema_version: "0.1.0"` and `as_of` (UTC timestamp or null). Health and profile-list responses use `as_of: null`. Lists additionally include `total`, `limit`, and `offset`. Alert-list meta additionally includes `evaluation_status`, so `data: []` is not ambiguous.

Every error has `error` and `meta` instead of `data`:

```json
{
  "error": {
    "code": "ASTRONAUT_NOT_FOUND",
    "message": "Astronaut AST-999 was not found.",
    "details": []
  },
  "meta": { "schema_version": "0.1.0", "as_of": null }
}
```

| HTTP | `error.code` | Expected behavior |
| --- | --- | --- |
| 404 | `ASTRONAUT_NOT_FOUND` | Unknown profile ID |
| 409 | `READING_CONFLICT` | Same reading key with different measurement/provenance values |
| 422 | `VALIDATION_ERROR` | Wrong types, bad/null-only record, out-of-scale value, timestamp/day mismatch, malformed JSON, invalid filters, or unsupported body fields |
| 500 | `INTERNAL_ERROR` | Generic error message; do not return stack traces |

`details` is always an array of `{ "field": "body.spo2_percent", "message": "Must be between 0 and 100." }` objects, or empty when not field-specific. Frontend logic relies on status/code/field, not exact English message wording. BACKEND-03 must normalize FastAPI HTTP and request-validation errors into this envelope rather than exposing two different response shapes. Network failure is a client state, not a JSON response from this API.

### Write identity and update behavior

- A reading is unique on `(astronaut_id, timestamp, measurement_context)` after canonical timestamp normalization. Same key and identical remaining normalized fields: return the existing record and 200. Same key and different fields: 409; no overwrite or new row.
- Journal uniqueness is `(astronaut_id, mission_day)`. Upsert as described in section 3.3; keep a stable journal ID. Entries cannot be moved to a different day by reusing an ID.
- Backend generates reading/journal/alert IDs. Do not treat fixture IDs as an implementation requirement.
- Refresh summary/history/alerts after a successful write or replay. Do not present an old analysis result as current while reevaluation is pending; use an unavailable analysis status until the cutoff-consistent result is ready.

## 5. Shared data files and provenance

`examples/mission_seed.json` is the small import/mock fixture. It contains `schema_version`, a source manifest, fictional `astronauts`, and `readings` / `journal` arrays. Import records contain the corresponding Input fields plus `astronaut_id`; the backend assigns record IDs. Its seven days are contract examples, not the approximately 30-day deliverable of DATA-04.

CSV alternatives use UTF-8, the exact headers in `examples/readings.csv` and `examples/journal.csv`, and an empty cell for null. A numeric `0` remains zero; the strings `null`, `NaN`, and `N/A` are not accepted as substitute missing values. Convert cells to the declared JSON types before validation. Reject unknown headers. A surrounding manifest supplies the schema version, profiles, and source references.

Import validation checks types, provenance, units, matching day/time, profile references, and duplicates before writing. The proposed MVP policy is atomic per file/bundle: report invalid row numbers/fields and commit no rows from that invalid unit. This does not require a public bulk-upload endpoint.

For real biomedical work in DATA-03, retain original population, subject IDs, source type, units, context, and dataset identifiers in a separate processed-data manifest. Terrestrial records use `source_type: "terrestrial_biomedical"` and `subject_id`, not invented astronaut IDs. They are not directly loaded into these synthetic-only astronaut routes. Any later derivative used for a fictional mission is separately labeled synthetic and cites its source transformation; it is never renamed into real astronaut data.

Preserve the real dataset's original timebase. If it only provides elapsed seconds, record that timebase and its units in the processed-data manifest; do not invent UTC dates or mission days to force it into the mission schema. DATA-03 documents its dataset-specific normalization separately.

## 6. Fixtures and audit checklist

- [API request/response cases](examples/api_examples.json): endpoint shapes, pagination, no observations, null values, normal/alert states, unavailable analysis, and error cases.
- [Synthetic import bundle](examples/mission_seed.json): two fictitious profiles, seven days for one profile, no records for the other.
- [Readings CSV](examples/readings.csv) and [journal CSV](examples/journal.csv): equivalent small import examples.

Fixtures are hand-authored interface examples. Alert/baseline values illustrate response shapes and controlled scenarios; they do not specify medically validated rules. Their synthetic reference method is explicitly identified as `fixture_reference_mean`.

| Audit item | Review owner | Status |
| --- | --- | --- |
| Dashboard can map every indicator and timestamp | Jorge | Pending review |
| Sleep chart has daily history and null handling | Jorge | Pending review |
| Types, envelopes, endpoints, duplicates, and cutoff can be implemented | Jhonatan | Pending review |
| Units, mood scale, missing values, source manifest, and import mapping | Ismael | Pending review |
| Accept proposed choices in section 1; revise conflicting assumptions | Jorge + Jhonatan, with Ismael's input | Pending review |
| Fixture syntax, CSV/JSON parity, day mapping, and response invariants | Preparation validation | See pull request validation record |

CORE-01 remains open until the contract is reviewed, agreed, and merged through its documentation pull request. No application feature is completed by this document alone.

## 7. Usability requirements linked to this contract

See [UX requirements and acceptance scenarios](ux_requirements.md). That document applies the user-supplied Nielsen heuristics and Laws of UX references to AstroHealth's own interaction requirements. It is a specification for subsequent frontend/integration issues, not a claim that a UI has been implemented or tested.

- The demo interface is English. Stable API codes and `details[].field` support clear field-specific messages rather than displaying raw exceptions or wire-format names.
- Each indicator shows the selected value's unit, observation day/time, and provenance. Missing values, missing history, unavailable analysis, and request errors have distinct states.
- Editing a journal uses prefilled values with explicit Save changes and Cancel actions. Success is shown only after a successful response; failure preserves input and offers retry. Cancellation of unsaved edits does not undo a previous server save.
- Alerts expose their explanation and evidence with text/icon severity cues. User controls do not resolve, acknowledge, hide, or delete the engine's alert condition.

## 8. Implementation references

- [FastAPI error handling and custom validation handlers](https://fastapi.tiangolo.com/tutorial/handling-errors/)
- [RFC 3339 timestamp format](https://www.rfc-editor.org/rfc/rfc3339)

These references explain implementation formats/mechanisms, not astronaut medical thresholds. Scientific selection and validation remain owned by DATA-01/02/06.
