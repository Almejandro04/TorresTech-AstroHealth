# Validation review / Revisión de validación

Issue: DATA-06 / #20. Evidence: `scripts/validate_mission_rules.py` →
[`data/synthetic/validation_result.json`](../../data/synthetic/validation_result.json),
plus `data/tests/`. Results below are the script's actual output on the default
mission (seed 2026). Labels as in [health_indicators.md](health_indicators.md).

- [English](#english)
- [Español](#español)

## English

| Component | Check | Result | Evidence / source or assumption | Severity | Owner | Recommended correction |
| --- | --- | --- | --- | --- | --- | --- |
| Names, units, scales | Bundle fields vs contract v0.1.0 | Pass: every bundle validates with the backend import model; import committed 63 readings, 32 journal entries | `test_synthetic_mission.py`; `import_committed` | — | Ismael | None |
| Timestamps and `mission_day` | UTC `Z`; day = (UTC date − start) + 1 | Pass for all records | `test_thirty_days_and_consistent_mission_day` | — | Ismael | None |
| Missing values | Nulls stay null; absent journal stays absent | Pass: day 12 HR null, day 13 RR null, no day-14 journal | `test_scenario_nulls_and_absences` | — | Ismael | None |
| Contexts | `rest` baseline excludes sleep/exercise | Pass: baseline 72.2 (rest only) vs 77.56 if contexts were mixed | `exercise_and_sleep_excluded_from_baseline` | — | Jhonatan | None |
| Provenance | `source_type`/`source_id` on every record | Pass: `synthetic` / `SYN-AH-MISSION-001`; BIDMC stays `terrestrial_biomedical` | `test_provenance_and_ids`; `test_mapping_identity_and_no_mission_columns` | — | Ismael | None |
| Recalculated baseline | API value vs hand mean of days 1–5 rest HR | Pass: 72.2 = 72.2, 5 samples, from day 6 (`insufficient_data` at end of day 5) | `baseline_available_from_day_6_matches_hand_mean` | — | Jhonatan | None |
| Normal scenario | Normal days stay below threshold (77.2) | Pass: only days 9 and 18–21 reach it | `test_scenario_values_exercise_the_rule` | — | Ismael | None |
| Isolated spike | Day 9 alone does not alert | Pass: `available`, 0 active alerts at end of day 9 | `isolated_spike_day_9_no_alert` | — | Jhonatan | None |
| Sustained deviation | Days 18–19 trigger one warning | Pass: one `DEMO-HR-CHANGE` warning, window 2026-11-18T12:00:00Z → 2026-11-19T12:00:00Z, observed 80, baseline 72.2; resolved at 2026-11-22T12:00:00Z | `sustained_change_day_19_one_warning`; `resolved_on_day_22` | — | Jhonatan | None |
| Insufficient data | AST-102 is never an all-clear | Pass: summary and alerts `insufficient_data`, no active count | `ast102_insufficient_data_never_all_clear` | — | Jhonatan | None |
| Deduplication | Re-evaluating does not copy alerts | Pass: 3 evaluations at day 25 → 1 stored alert, same ID | `no_duplicates_after_three_evaluations` | — | Jhonatan | None |
| Non-diagnostic text | No diagnosis/treatment words; experimental nature stated | Pass: no forbidden words; "controlled example", "not a validated medical threshold" present | `alert_text_is_observational_and_experimental` | — | Jhonatan | None |
| Explanation wording | Text fits a non-fixture mission | Finding: the text says "Fixture days 18-19 …" for the synthetic mission | Backend template `backend/app/services/alert_rules.py` (#15), written to match the contract fixture | Low | Jhonatan | Consider "Synthetic days …" in a later rule version; that changes the `explainable_synthetic_alert` fixture match, so it needs a contract decision |
| Rule `DEMO-HR-CHANGE` | Source for +5 beats/min on 2 consecutive days | No source: `[SIMULATION-ASSUMPTION]`. S13 defines no on-board alert threshold; S4/S5 report HR unchanged in flight | `docs/architecture/alert_rules.md` | Medium (interpretation) | Jhonatan / Ismael | Keep the explicit limit: demo rule, not a medical or validated criterion |
| Contract fixture vs policy | When the baseline becomes available | Known difference: the fixture shows it available at the end of day 5; the implementation makes it available from day 6 (validated above) | `summary_normal_reference_fixture` (strict xfail in backend tests) | Medium (consistency) | Jhonatan | Proposal: decide as a team which one is authoritative and update either the fixture or the policy with the contract process; no code change here |

## Español

| Componente | Verificación | Resultado | Evidencia/fuente o supuesto | Severidad | Responsable | Corrección recomendada |
| --- | --- | --- | --- | --- | --- | --- |
| Nombres, unidades, escalas | Campos del bundle vs contrato v0.1.0 | Pasa: todos los bundles validan con el modelo de importación del backend; se importaron 63 lecturas y 32 diarios | `test_synthetic_mission.py`; `import_committed` | — | Ismael | Ninguna |
| Timestamps y `mission_day` | UTC `Z`; día = (fecha UTC − inicio) + 1 | Pasa en todos los registros | `test_thirty_days_and_consistent_mission_day` | — | Ismael | Ninguna |
| Faltantes | Los null siguen null; el diario ausente sigue ausente | Pasa: FC null día 12, FR null día 13, sin diario el día 14 | `test_scenario_nulls_and_absences` | — | Ismael | Ninguna |
| Contextos | El baseline `rest` excluye sueño/ejercicio | Pasa: baseline 72.2 (solo reposo) frente a 77.56 si se mezclaran contextos | `exercise_and_sleep_excluded_from_baseline` | — | Jhonatan | Ninguna |
| Procedencia | `source_type`/`source_id` en cada registro | Pasa: `synthetic` / `SYN-AH-MISSION-001`; BIDMC sigue `terrestrial_biomedical` | `test_provenance_and_ids`; `test_mapping_identity_and_no_mission_columns` | — | Ismael | Ninguna |
| Baseline recalculado | Valor de la API vs media a mano de la FC en reposo días 1–5 | Pasa: 72.2 = 72.2, 5 muestras, desde el día 6 (`insufficient_data` al final del día 5) | `baseline_available_from_day_6_matches_hand_mean` | — | Jhonatan | Ninguna |
| Escenario normal | Los días normales quedan bajo el umbral (77.2) | Pasa: solo los días 9 y 18–21 lo alcanzan | `test_scenario_values_exercise_the_rule` | — | Ismael | Ninguna |
| Pico aislado | El día 9 solo no genera alerta | Pasa: `available`, 0 alertas activas al final del día 9 | `isolated_spike_day_9_no_alert` | — | Jhonatan | Ninguna |
| Desviación sostenida | Los días 18–19 generan un warning | Pasa: un warning `DEMO-HR-CHANGE`, ventana 2026-11-18T12:00:00Z → 2026-11-19T12:00:00Z, observado 80, baseline 72.2; resuelta en 2026-11-22T12:00:00Z | `sustained_change_day_19_one_warning`; `resolved_on_day_22` | — | Jhonatan | Ninguna |
| Datos insuficientes | AST-102 nunca equivale a "sin alertas" | Pasa: summary y alertas `insufficient_data`, sin conteo activo | `ast102_insufficient_data_never_all_clear` | — | Jhonatan | Ninguna |
| Deduplicación | Reevaluar no copia alertas | Pasa: 3 evaluaciones en el día 25 → 1 alerta guardada, mismo ID | `no_duplicates_after_three_evaluations` | — | Jhonatan | Ninguna |
| Textos no diagnósticos | Sin palabras de diagnóstico/tratamiento; naturaleza experimental explícita | Pasa: sin palabras prohibidas; contiene "controlled example" y "not a validated medical threshold" | `alert_text_is_observational_and_experimental` | — | Jhonatan | Ninguna |
| Redacción de la explicación | El texto encaja con una misión que no es fixture | Hallazgo: el texto dice "Fixture days 18-19 …" para la misión sintética | Plantilla del backend `backend/app/services/alert_rules.py` (#15), escrita para coincidir con el fixture del contrato | Baja | Jhonatan | Considerar "Synthetic days …" en una versión posterior de la regla; eso cambia la coincidencia con `explainable_synthetic_alert`, así que requiere decisión de contrato |
| Regla `DEMO-HR-CHANGE` | Fuente para +5 beats/min en 2 días consecutivos | Sin fuente: `[SIMULATION-ASSUMPTION]`. S13 no define umbrales de alerta a bordo; S4/S5 informan FC sin cambio en vuelo | `docs/architecture/alert_rules.md` | Media (interpretación) | Jhonatan / Ismael | Mantener el límite explícito: regla de demo, no criterio médico ni validado |
| Fixture del contrato vs política | Cuándo pasa a estar disponible el baseline | Diferencia conocida: el fixture lo muestra disponible al final del día 5; la implementación lo hace disponible desde el día 6 (validado arriba) | `summary_normal_reference_fixture` (xfail estricto en las pruebas del backend) | Media (consistencia) | Jhonatan | Propuesta: decidir en equipo cuál es la referencia y actualizar el fixture o la política con el proceso de contrato; sin cambio de código aquí |
