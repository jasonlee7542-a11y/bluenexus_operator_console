# BlueNexus Operator Console

A Streamlit decision-support dashboard for Challenge 1, built around a plant-status table, prioritized investigation queue and a staged verification workflow. It combines a clear performance overview with traceable cleaning, engineering review rules and an investigation handoff. It uses historical daily CSVs, not a live plant connection. There are no verified equipment-failure labels.

## Deploy from your GitHub repository

1. Extract this ZIP on your computer.
2. Upload **all Python files**, `settings.json`, `requirements.txt`, and the `.streamlit/config.toml` file to your repository. Keep the Python files together in the same folder. This is a complete replacement app; replacing only `app2.py` is insufficient.
3. Keep your original three CSVs in that same folder, with these exact names:
   - `plant_A_equipment_daily.csv`
   - `plant_B_equipment_daily.csv`
   - `plant_daily_performance.csv`
4. In Streamlit Community Cloud, select your repository/branch and set the main file to **app2.py** (or its folder-relative path).
5. Use Python 3.12 if choosing a runtime. Redeploy or reboot after committing the complete update.
6. Open Overview. If a file is missing, the app explains which one. You can alternatively supply all three files using the sidebar's Data inputs controls.

The source CSVs are deliberately not included in this code ZIP. Retain the challenge's confidentiality restrictions when choosing repository and app access. This app has no built-in authentication; use deployment access controls appropriate to your data. Do not rely on a password embedded in source code.

## Run in VS Code

Open this extracted folder using File → Open Folder. Put the three CSVs beside app2.py. Open Terminal → New Terminal, then run:

```bash
python -m pip install -r requirements.txt
python -m streamlit run app2.py
```

The terminal prints the browser address. Leave the terminal running while using the app. To stop it, press Ctrl+C.

## Files

| File | Purpose |
|---|---|
| app2.py | App entry point, navigation, data loading and detailed methods |
| operator_ui.py | Operator overview, energy/water screens, incident queue and staged checks |
| dashboard.css | Compact visual layout, typography and status styling |
| pipeline.py | CSV parsing, audit, ratios and prior-only energy comparisons |
| detector.py | Prior rolling IQR screening with explicit unscored states |
| rules.py | Engineering review rules and grouped incidents |
| tags.py | Inferred tag meanings, units and confidence |
| ranking.py | Consistent background statistical ranking |
| playbooks.py | Remote checks, inspection guidance and attendance routing |
| settings.json | Provisional assessment thresholds |
| requirements.txt | Dependencies installed by Streamlit |
| .streamlit/config.toml | Visual theme |
| OPERATOR_GUIDE.md | Step-by-step operation |
| ENGINEERING_NOTES.md | Rule basis, scope and limitations |
| test_core.py | Synthetic regression checks; no confidential data needed |
| VALIDATION.md | Checks performed on this release |

`action_ui.py` and `review_core.py` from earlier versions are not imported by this build. You may leave old files in your repository; ensure Streamlit runs the new app2.py with every new dependency above.

## Test the logic

```bash
python -m unittest -v test_core.py
```

## What this product does not claim

It screens possible inefficiency and supplies evidence-based investigation steps. It does not predict confirmed equipment failures, certify water quality, diagnose a particular mechanical fault or execute AquaxGo/PLC commands. Inferred tags and provisional thresholds are visible for engineering review. Operator notes and attendance answers are session-local; download the handoff to retain them. This is a challenge prototype, not a production incident-management system.

## Update from the previous package

Upload these three files together: `app2.py`, `operator_ui.py` and `dashboard.css`. All must be beside the existing analysis modules and CSVs. Keeping the supplied `.streamlit/config.toml` is recommended. The complete ZIP also includes all dependencies for a fresh deployment. Do not replace only app2.py.

The first page now shows a latest-reported plant table and prioritized episodes. Selecting a circle previews the next check; Open investigation opens that exact case. The incident page keeps the case queue beside the evidence and offers three steps: Verify, Remote checks, Site decision. Verification answers remain in the browser session across steps/pages; download the handoff for a lasting record.
