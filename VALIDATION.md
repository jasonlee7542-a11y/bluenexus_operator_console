# Release validation

## Automated logic checks

`python -m unittest -v test_core.py`: **11 tests passed**.

Covered exact duplicates, conflicting daily keys, ambiguous dates, invalid numeric logging, preserved missing/zero/extreme values, valid ratio denominators, prior-only statistical and peer references, flat-baseline unscored status, high/low temperature rules, episode gaps, and attendance routing.

## Streamlit execution checks

Streamlit AppTest ran all six pages for All plants, Plant A and Plant B: **18 combinations without app exceptions**. The full-history Plant A incident view was also exercised.

These are programmatic UI execution tests, not a browser pixel-layout certification or a test of live AquaxGo integration. No live plant integration is present.

## Supplied-data checks

- Plant A high-temperature rule preserved and flagged all 27 extreme-temperature days; these form one consecutive episode.
- Plant A 31 August SEC remains an investigation lead with only two similar-output peers, below the five-peer minimum.
- Plant B 11 August supply/customer discrepancy remains visible as a reconciliation issue rather than a confirmed leak.
- Prepared source values are not imputed or scrubbed to conceal extreme readings.

There are no verified failure labels, so accuracy, sensitivity, false-alarm rate and failure-prediction lead time cannot be honestly claimed from these checks. The tests validate implemented behavior, not diagnostic ground truth.

## Branded design update

After moving navigation to the sidebar and replacing the Overview layout, all six pages were rerun for All plants, Plant A and Plant B: 18 combinations without app exceptions. Analysis modules were unchanged. Browser screenshot verification was unavailable in this session; the validation is programmatic.

## Operator-console rebuild

Fourteen automated tests passed: eleven core-logic checks and three UI tests. The UI tests cover all 18 plant/page combinations, exact opening of an earlier temperature episode, and persistence of verification/remote-check answers through the three-stage workflow and page navigation. No browser pixel/layout certification is claimed.
