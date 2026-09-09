# Null Handling Report — v5

| Table | Column | Null Count | Strategy | Justification |
|---|---|---|---|---|
| `fact_risk_behaviour` | `daily_productivity` | 34 | group_median | Ordinal numeric; program_stream is the best group proxy |
| `fact_risk_behaviour` | `energy_level` | 28 | group_median | Energy correlates with academic year/workload |
| `fact_risk_behaviour` | `stress_level` | 35 | group_median | Stress directly predicts risk level; best grouping |
| `fact_risk_behaviour` | `routine_rating` | 41 | group_median | Routine patterns differ by program |
| `fact_risk_behaviour` | `revision_frequency` | 34 | group_mode | Revision patterns differ by program |
| `fact_risk_behaviour` | `focus_duration` | 43 | group_mode | Focus spans differ by program intensity |
| `fact_risk_behaviour` | `sleep_hours` | 55 | group_mode | Sleep patterns correlate with age |
| `fact_risk_behaviour` | `screen_time_non_study` | 32 | fill_with_unknown | Cannot be safely inferred from available features |
| `fact_risk_behaviour` | `online_courses` | 36 | fill_with_not_available | Binary-type field — cannot impute without risk of bias |
| `fact_risk_behaviour` | `programming_foundation` | 41 | fill_with_not_available | Skill level — imputing would fabricate student ability |
| `fact_risk_behaviour` | `events_participation` | 58 | fill_with_unknown | Participation data — cannot infer absence/presence |
| `fact_risk_behaviour` | `external_resources` | 45 | fill_with_unknown | Context-dependent — cannot safely infer |
| `fact_risk_behaviour` | `external_pressure` | 29 | fill_with_unknown | Subjective — cannot safely infer |