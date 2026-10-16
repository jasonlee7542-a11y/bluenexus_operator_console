# Engineering and design notes

## Design judgment

The groupmate's useful strength was immediate visibility of production, energy, water and quality. The earlier operator workflow's useful strength was traceable preparation, independent engineering checks and an explanation of what to investigate. This edition combines those approaches. It is a new implementation based on the reviewed interfaces and supplied data; it is not a source-code merge of the groupmate's app.

An overall plant health score was omitted because detector coverage differs between plants and no verified failure outcomes support calibrated scoring. Every conclusion instead shows its measurement, comparison, confidence and next check. Statistical ranking prioritizes review workload, while engineering priority is handled separately.

## Implemented rules

| Check | Default | Meaning and limitation |
|---|---|---|
| Temperature high | >120°C, immediately | Provisional investigation threshold under assumed Celsius units; not a physical impossibility or verified bearing limit |
| Temperature low | <0°C, immediately | Context-dependent unusual reading; cold conditions may be real |
| Absolute-zero check | <−273.15°C | Inconsistent with the assumed Celsius scale |
| Persistent rise | Above prior Q3 + 1.5×IQR for ≥3 consecutive days | Temperature, vibration or turbidity; operating mode remains unconfirmed |
| Daily SEC rise | >20% above prior median or comparable-output median | Possible energy-intensity change, not proven pump or membrane deterioration |
| Comparable-output history | Prior 60 days, output ±20%, minimum 5 peers | Controls for volume only; no future data |
| Electricity with zero product | Positive electricity, zero product | Cleaning/standby/meter issue possible; no division by epsilon |
| Delivery discrepancy | Absolute gap >10% of supply; >50% prompt verification | Reconcile meters, storage and time boundaries before diagnosing losses |
| Recovery consistency | Outside 0–100% | Check definition, storage and reporting periods |
| Plant B whole-plant recovery change | >10 percentage points from prior median | Investigation threshold; not a universally optimal RO range |
| Product pH | Outside 6.5–8.5 | Provisional review range, not a compliance specification |
| pH plausibility | Outside 0–14 | Unusual for this application; not universally physically impossible |
| Frequency/electrical mismatch | Zero frequency with positive paired electrical reading | Tag/aggregation consistency check, not proof of a motor fault |
| Counter decrease | Current < preceding observed reading | Reset/rollover/data issue; no consumption inferred across the decrease |
| Other consistency | Negative magnitudes, invalid binary states, power-factor magnitude >1 | Conditional on correct tag mapping, units and conventions |

Thresholds are in settings.json. Changing them requires engineering review; they are assessment settings, not manufacturer-certified limits. Equipment-page IQR controls affect exploratory ranking only. Incidents use settings.json consistently across the dashboard.

## Preparation and reproducibility

Read source values as strings, remove exact duplicate rows, standardize missing tokens, validate unambiguous year-first dates, coerce numeric values with an error log, and sort dates. Conflicting daily keys stop processing instead of being silently averaged. Keep all-null, all-zero and constant columns in the audit. Do not interpolate, clip, overwrite source files or convert missing readings to zero. Derived ratios reject invalid denominators and negative consumed/produced totals.

Statistical comparisons use prior calendar days. Missing dates reduce coverage and break consecutive runs. Flat baselines are unscored. Independent engineering limits still apply to constant extreme readings. Daily events are grouped by plant, rule and signal over consecutive calendar dates. An incident's final flagged date is not a confirmed repair date.

The downloadable analysis bundle includes prepared tables, audits, parsing logs, inferred tag definitions, rule coverage, settings, view dates and SHA-256 source fingerprints. Different source files or settings can produce different results; the fingerprints make that explicit.

## Indicators and sources

SEC (kWh/m³), recovery, conductivity and flow/quality trends are relevant process-monitoring concepts. However, whole-plant daily recovery is not automatically RO membrane recovery, conductivity is not a full water-safety assessment, and unnormalized SEC cannot isolate membrane fouling.

General diagnostic guidance is informed by:

- [DuPont FilmTec RO/NF technical manual](https://www.dupont.com/content/dam/dupont/amer/us/en/water-solutions/public/documents/en/RO-NF-FilmTec-Manual-45-D01504-en.pdf): use normalized membrane performance and appropriate operating measurements when investigating deterioration.
- [SKF bearing troubleshooting guidance](https://cdn.skfmediahub.skf.com/api/public/0901d1968024f02a/pdf_preview_medium/0901d1968024f02a_pdf_preview_medium.pdf): temperature/vibration symptoms have multiple possible mechanical, lubrication and operating causes.

These references support investigation concepts, not this prototype's exact numerical thresholds. The supplied BlueNexus descriptions do not establish a verified asset-specific sensor dictionary, alarm setpoints or remotely executable control contract. Chinese tag interpretations are hypotheses with confidence annotations. Plant A electrical scaling remains uncertain, so its raw power/current traces are not used to calculate whole-plant SEC; performance-file totals are used instead.

## Important remaining gaps

- Verified equipment IDs, sensor locations, units, scaling and RMS/peak conventions.
- Approved OEM/site limits and product-quality specifications.
- Running, cleaning and standby states, operating hours and maintenance outcomes.
- Aligned pressure/flow/temperature/feed-quality measurements for normalized RO performance.
- Current telemetry and authorized AquaxGo actions for an actual remote-control integration.
- Persistent user authentication, incident ownership/history and work-order integration for production deployment.

The app supplies useful, reproducible investigation leads now. These gaps prevent verified fault diagnosis, automatic repair and a validated failure-prediction claim.
