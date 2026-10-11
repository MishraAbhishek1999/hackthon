# Visarjan Ghat Watch - Bhopal Water Quality Portal

**Claude Impact Lab Bhopal - Track 2: Visarjan Ghat Watch**

| | |
|---|---|
| **Team name** | _(edit this line before submitting)_ |
| **Members** | _(edit this line before submitting)_ |
| **Track** | Track 2 - Visarjan Ghat Watch |

## Target users

Officers of the **Bhopal Municipal Corporation (BMC)** and the **MP Pollution Control Board (MPPCB)** planning
the Durga Visarjan on **20 October 2026**. The test results sit in 90-to-120-page PDF reports and decisions
are made from memory. This project turns them into:

1. a **web dashboard** (`app.py`, Streamlit) where officers filter limits, see trends for 2023-2025 and
   download the ranked table, and
2. a **command-line pipeline** (`ghat_watch.py`) that writes the ranking, a report and one-page
   English and Hindi briefs.

## Install and run (3 steps)

1. `pip install -r requirements.txt` (Python 3.9+)
2. `streamlit run app.py` - opens the dashboard at http://localhost:8501. The data is built into `app.py`; no extra files are needed.
3. Optional, for the briefs: `python ghat_watch.py --data data/bhopal_ghats_extracted.csv --out outputs`

To rebuild the dataset from the MPPCB PDFs (needs poppler's `pdftotext`):
`python extract_idol_reports.py --pdf-dir resources --out data/bhopal_ghats_extracted.csv`

## Track requirements met

| Requirement | Where |
|---|---|
| Ranked list of the 7 Bhopal ghats by risk | Dashboard "Ranking & export"; `outputs/ghat_risk_ranking.csv` |
| Plain-word reasons | "Why" column in English and Hindi |
| Traceable report/page numbers | Source traces (report + PDF page) for the lowest DO and highest BOD of each ghat |
| Forwardable briefs in Hindi and English | `outputs/brief_en.txt`, `outputs/brief_hi.txt` |
| CPCB Class B limits | pH 6.5-8.5, DO >= 5, BOD <= 3 mg/l (adjustable sliders; coliform not available at ghat level) |
| Missing-data rules | Blanks, `_`, `-`, `NA`, `*`, `**` = missing, never clean; BDL/ND = very low, not zero; BDL/ND on pH or DO = missing |
| Filters, trends, export | Sidebar sliders and selectors; phase and 2023-2025 charts; `bmc_ghat_emergency_report.csv` download |

## Dashboard features

- Cards: critical ghats, average DO, active warnings (readings breaching the chosen limits), ghats with data gaps.
- Sliders for pH range, minimum DO and maximum BOD; festival, year, status and ghat filters. The table re-ranks automatically.
- Charts: before / during / one-week-after change per ghat, and year-by-year trends, with the limit drawn as a red dashed line.
- Plain English with Hindi sub-captions throughout.

## How the score works

0-100 per ghat: DO shortfall 30%, BOD exceedance 25%, heavy metals 15%, worsening during/after immersion 10%,
pH 5%. Coliform (15%) is not scored because the ghat-level reports contain no coliform results. Newer years
count more (2025 = 1.0, 2024 = 0.75, 2023 = 0.5). Missing data adds up to 10 penalty points, so a gap never
makes a ghat look safer. **Status** is derived, not typed in: CRITICAL if DO <= 1 mg/l at any time or score >= 60;
HIGH if score >= 45 or DO and BOD both breached in at least half the readings; MODERATE if score >= 25.
Weights and thresholds are our own judgement, not an official standard.

## What works and what doesn't

**Works**
- `app.py` compiles and its data cleaning, scoring, ranking, breach counting and reasons logic was tested
  outside Streamlit on the embedded data. Scores match the command-line pipeline (e.g. Bairagarh 54.9).
- The 120 readings (7 ghats, 2023-2025, Ganesh and Durga, before/during/after) were extracted from three MPPCB
  idol-immersion PDFs with their page numbers.
- Changing a limit slider re-scores and re-ranks every ghat.

**Doesn't work / limitations**
- **The Streamlit interface itself has not been run in a browser by us.** The build environment could not
  install Streamlit. Run it once and check the layout before presenting; if a widget argument fails on your
  Streamlit version, upgrade with `pip install -U streamlit`.
- **It is not live.** There is no sensor feed. The data is static MPPCB reports, so "live" would be inaccurate.
- **The official project CSVs were never loaded.** Everything comes from our own PDF extraction, which was
  spot-checked rather than verified table by table.
- Total coliform is not scored for ghats. Coliform exists only for lake gauging stations in other reports.
- 2025 gaps: no Durga table for Bairagarh or Malikhedi; their 2025 Ganesh tables have no before/after sample
  (temporary kund not built, or dismantled). They are scored on less data and flagged.
- A metal reading equal to MPPCB's detection limit (Cr 0.03, Pb 0.031, Cu 0.018, Zn 0.009) is treated as BDL.
  This is our inference from repeated identical values and should be confirmed with MPPCB.
- CPCB Class B has no metal limits; BIS drinking-water values are used as a stand-in reference.
- Rani Kamlapati is "Kamla Park kund" in Ganesh tables and "Lower Lake ghat" in Durga tables (medium-confidence match).
- Hindi text has not been reviewed by a native speaker.
- Scores are relative planning priorities, not a legal or regulatory finding.

## Files

| File | Purpose |
|---|---|
| `app.py` | Streamlit dashboard, self-contained with embedded data |
| `ghat_watch.py` | Command-line pipeline: scoring, report, EN/HI briefs |
| `extract_idol_reports.py` | Builds the ghat CSV from the MPPCB PDFs |
| `data/bhopal_ghats_extracted.csv` | Extracted readings (120 rows) |
| `outputs/` | Ranking CSV, report, `brief_en.txt`, `brief_hi.txt` |
| `LICENSE` | MIT |
