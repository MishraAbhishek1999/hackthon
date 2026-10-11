#!/usr/bin/env python3
"""
Extract the 7 Bhopal ghat tables from the MPPCB idol-immersion PDFs into one
CSV that ghat_watch.py can read.

Requires poppler's `pdftotext` on PATH.
Usage: python extract_idol_reports.py --pdf-dir resources --out data/bhopal_ghats_extracted.csv

Values are kept as printed ('BDL', 'ND', '_', '*', '**', blank) so that
ghat_watch.py applies the missing-data rules, not this script.
'*'  = temporary kund not built before immersion (no sample)
'**' = kund dismantled before the one-week sample (no sample)
"""
import argparse
import csv
import os
import re
import subprocess

from ghat_watch import canon_ghat

# (file, year, {pdf page: festival}). Pages were located by searching for the
# seven Bhopal ghat names; the 2023 and 2024 PDFs hold one table block per festival.
SOURCES = [
    ("Idol_immer__Report_23_CPCB.pdf", 2023,
     {**{p: "Ganesh" for p in range(26, 30)}, **{p: "Durga" for p in range(58, 62)}}),
    ("Ganesh_and_Durga_visarjan_report-2024.pdf", 2024,
     {**{p: "Durga" for p in range(23, 27)}, **{p: "Ganesh" for p in range(69, 73)}}),
    ("Ganesh_and_Durga_visarjan_report-2025.pdf", 2025,
     {**{p: "Ganesh" for p in range(1, 4)}, **{p: "Durga" for p in range(37, 39)}}),
]
PARAMS = {"pH": r"^ph$", "DO": r"oxygen", "BOD": r"^bod$",
          "Chromium": r"^chromium$", "Lead": r"^lead$",
          "Zinc": r"^zinc$", "Copper": r"^copper$"}
PHASES = ["pre", "during", "post"]
ROW = re.compile(r"^\s*(\d+)\s+([A-Za-z][A-Za-z.\- ]*?)(?=\s{2,}|\s+[-\d_*<]|$)")


def param_key(label):
    for k, pat in PARAMS.items():
        if re.search(pat, label.strip().lower()):
            return k
    return None


def parse_page(text):
    """Yield (title_text, {param: [pre, during, post]}) for each table on a page."""
    centers, title, buf, cur, tables = None, "", [], None, []
    for line in text.splitlines():
        if "Pre Immersion" in line:
            a, b, c = (line.index(s) + len(s) / 2 for s in
                       ("Pre Immersion", "During Immersion", "After one week"))
            centers, title = (a, b, c), " ".join(buf)
            cur = {}
            tables.append((title, cur))
            buf = []
            continue
        m = ROW.match(line)
        if m and cur is not None:
            key = param_key(m.group(2))
            if key:
                vals = ["", "", ""]
                for t in re.finditer(r"\S+", line[m.end():]):
                    mid = m.end() + (t.start() + t.end()) / 2
                    i = min(range(3), key=lambda j: abs(centers[j] - mid))
                    vals[i] = t.group(0)
                cur[key] = vals
            buf = []
        elif line.strip():
            buf.append(line.strip())
    return tables


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf-dir", default="resources")
    ap.add_argument("--out", default="data/bhopal_ghats_extracted.csv")
    a = ap.parse_args()
    rows = []
    for fname, year, pages in SOURCES:
        path = os.path.join(a.pdf_dir, fname)
        txt = subprocess.run(["pdftotext", "-layout", path, "-"], capture_output=True,
                             text=True, errors="ignore").stdout.split("\f")
        for pg, fest in pages.items():
            for title, tab in parse_page(txt[pg - 1]):
                ghat = canon_ghat(title)
                if not ghat or not tab:
                    continue
                for i, ph in enumerate(PHASES):
                    rows.append({
                        "Ghat": ghat, "Year": year, "Festival": fest, "Phase": ph,
                        "pH": tab.get("pH", ["", "", ""])[i],
                        "DO (mg/l)": tab.get("DO", ["", "", ""])[i],
                        "BOD (mg/l)": tab.get("BOD", ["", "", ""])[i],
                        "Chromium (mg/l)": tab.get("Chromium", ["", "", ""])[i],
                        "Lead (mg/l)": tab.get("Lead", ["", "", ""])[i],
                        "Zinc (mg/l)": tab.get("Zinc", ["", "", ""])[i],
                        "Copper (mg/l)": tab.get("Copper", ["", "", ""])[i],
                        "Report": f"MPPCB {year} idol immersion report (PDF)",
                        "Page": pg, "Source title": title[-80:]})
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} rows -> {a.out}")


if __name__ == "__main__":
    main()
