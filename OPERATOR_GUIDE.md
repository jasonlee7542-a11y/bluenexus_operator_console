# Operator guide

## Start here

1. Choose the plant and review dates in the sidebar. These are historical daily records.
2. Read **Plant status** for the latest reported production and SEC in that window.
3. In **Investigation queue**, click the circle beside an episode. P1 means verify promptly; P2 means review. Data-quality issues have their own queue category.
4. Read **Next action** beside the queue. Click **Open investigation** to open that exact case.
5. Use **earlier priority episodes** to inspect high-priority records outside the selected dates.

## Complete an investigation

The queue stays on the left; the selected case stays on the right. The panel shows the flagged reading, review trigger and trend. The shaded dates are the historical episode. A past episode is not evidence of a current fault.

1. **Verify:** check current readings, timestamp, unit and asset identity. Record Confirmed, Not confirmed or Not checked.
2. **Remote checks:** work through the three numbered checks. Record whether the issue remains unexplained or was independently explained.
3. **Site decision:** read the attendance recommendation. Expand Technician handoff for the inspection location and tasks. AI scope explains what remote assistance could do; no controls are connected.
4. Add notes and download the handoff. The app sends no dispatch or plant command. Follow site procedures for escalation and any physical work.

Your answers stay in this browser session when changing steps or pages. They are not inferred from the CSV and are not saved to a shared incident database.

## Each page

| Page | What to look at | What to do next |
|---|---|---|
| Overview | Production, energy intensity, priority incidents, missing coverage | Open the first relevant incident; check older-history warning |
| Energy | SEC trend, similar-output reference, production/energy relationship, plan gaps | Investigate elevated SEC; if comparable history is insufficient, collect more context instead of concluding pump inefficiency |
| Water & Quality | Recovery, supply/customer discrepancy, pH/conductivity and chemical-data availability | Reconcile meters/storage first for volume gaps; verify quality readings and approved specifications |
| Equipment | Automatically ranked signals, statistical and engineering markers, aligned trend overlay | Start at the top of the ranking, then confirm the corresponding engineering incident and operating context |
| Incidents | Evidence, remote steps, technician location, attendance decision | Complete verification and download a handoff |
| Data & Methods | Missing/zero/constant channels, cleaning decisions, assumed units, rules | Resolve coverage and mapping problems; download the reproducible analysis bundle |

## Understand the indicators

- **SEC:** electricity divided by product volume, in kWh/m³. The whole-period figure uses total valid electricity divided by total product on matching days, not the mean of daily ratios.
- **Similar-output reference:** earlier days with production within ±20% of the current day, looking back up to 60 days. At least five prior days are required. This adjusts only for output, not feedwater or operating mode.
- **Prior baseline:** earlier observations only. The current day cannot move its own threshold. Fourteen calendar days and 80% coverage require twelve prior readings by default.
- **IQR multiplier:** controls the width of the statistical comparison band. A larger value flags fewer unusual observations. It does not change the engineering temperature threshold. Equipment-page sensitivity controls affect exploration, not the fixed incident rules in settings.json.
- **Statistical marker:** an unusual observation relative to its prior history, not a diagnosed fault.
- **Engineering marker:** a separately triggered engineering review rule. It can flag a consistently extreme reading that statistical comparisons miss.
- **Consecutive flagged days:** adjacent calendar days qualifying for that rule. Missing calendar days break a run. For persistent trend rules, the first incident date is the first day meeting the persistence requirement.
- **No flags / unavailable:** not the same as healthy. A flat, missing or unmapped channel may be unscored.

## Three examples in the supplied data

1. **Plant A, January temperature:** select All available history → Incidents. The approximately 212°C assumed front-bearing signal is preserved and flagged over 27 days. First verify units, scaling and the current sensor reading; the historical values alone do not prove bearing failure.
2. **Plant A, 31 August SEC:** the high daily SEC is a review lead. Comparable-output history has only two earlier peers, so the app explicitly avoids concluding unusually high consumption at the same production level.
3. **Plant B, 11 August delivery:** supply and customer totals differ by approximately 95.4%. Start with time boundaries, storage and meter records. This is not proof of a leak.

## Remote AI versus a site visit

AI-assisted work can help compare records, check calculations and prepare a work order. Physical measurement, instrument calibration and equipment repair require the appropriate people and procedures. This release contains deterministic analysis and guidance; it has no connected AI service, AquaxGo control or dispatch API.
