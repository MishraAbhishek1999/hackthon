#!/usr/bin/env python3
"""
Visarjan Ghat Watch - Bhopal (Claude Impact Lab, Track 2)

Reads MPPCB water-quality readings for the 7 Bhopal ghats, scores each ghat
against CPCB Class B (outdoor bathing) limits, and writes:
  - ghat_risk_ranking.csv   ranked table (machine readable)
  - ghat_risk_report.md     ranked table + plain-word reasons + trace refs
  - brief_en.txt / brief_hi.txt   forwardable one-page briefs

Usage:
  python ghat_watch.py --data data/bhopal_ghats_2023_2025.csv --out outputs
  python ghat_watch.py --data data/sample_bhopal_2025.csv --demo-date "20 October 2026"

The script auto-detects column names (wide format: one column per parameter,
or long format: 'parameter' + 'value' columns). Run with --show-columns to see
what it detected. If a column is missed, add an alias in COLUMN_PATTERNS.

Missing-data rules (strictly enforced):
  blank / not sampled / _ / - / NA  -> MISSING. Never counted as clean.
  BDL / '<x'                        -> below detection limit: very low, valid
                                       and compliant, but NOT zero.
  ND                                -> not detected: very low, valid, compliant.
  (BDL/ND for pH or DO is physically implausible, so it is treated as MISSING.)
"""
import argparse
import math
import os
import re
import sys

import pandas as pd

# --------------------------------------------------------------------------
# 1. Standards and configuration
# --------------------------------------------------------------------------
CPCB_B = {            # CPCB Class B: outdoor bathing (organised)
    "pH": (6.5, 8.5),   # acceptable range
    "DO": 5.0,          # mg/l, minimum
    "BOD": 3.0,         # mg/l, maximum
    "TC": 500.0,        # MPN/100 ml, maximum
}

# CPCB Class B has NO heavy-metal limits. To flag metals we use a configurable
# reference (BIS IS 10500 drinking-water acceptable limits, mg/l). Change here
# if the department prefers another reference. This is an ASSUMPTION - the
# reports are only evidence of presence, not a CPCB Class B exceedance.
METAL_REF = {"Cr": 0.05, "Pb": 0.01, "Zn": 5.0, "Cu": 0.05}
# MPPCB's own detection limits (the Upper Lake 2025-26 report prints them as
# "<0.03", "<0.031", "<0.018", "<0.009"). The 2025 idol reports print exactly
# these numbers again and again (e.g. Chromium 0.03, Lead 0.031 at every site),
# so a value at or below the limit is treated as BDL, not as a real detection.
DETECTION_LIMIT = {"Cr": 0.03, "Pb": 0.031, "Cu": 0.018, "Zn": 0.009}
METAL_NAMES = {
    "en": {"Cr": "Chromium", "Pb": "Lead", "Zn": "Zinc", "Cu": "Copper"},
    "hi": {"Cr": "क्रोमियम", "Pb": "सीसा (लेड)", "Zn": "जिंक", "Cu": "कॉपर"},
}

# Score weights (sum = 1.0). Per the brief: DO, BOD and metals matter most.
WEIGHTS = {"DO": 0.30, "BOD": 0.25, "TC": 0.15, "pH": 0.05,
           "METALS": 0.15, "IMMERSION": 0.10}
# Recency weights: the officer is planning on the latest picture.
YEAR_WEIGHT = {2023: 0.5, 2024: 0.75, 2025: 1.0}
MAX_GAP_PENALTY = 10.0   # points added when many readings are missing
HIGH, MEDIUM = 60.0, 35.0

GHATS = {  # canonical name -> (waterbody, mapping confidence)
    "Bairagarh (Sant Hirdaram) kund": ("Upper Lake", "High"),
    "Khatlapura ghat": ("Lower Lake", "High"),
    "Prempura ghat": ("Upper Lake", "High"),
    "Rani Kamlapati ghat / Kamla Park kund": ("Lower Lake", "Medium"),
    "Hathaikheda dam / kund": ("Hathaikheda dam", "High"),
    "Malikhedi kund": ("Kund", "High"),
    "Shahpura lake ghat": ("Shahpura Lake", "High"),
}
GHAT_HI = {
    "Bairagarh (Sant Hirdaram) kund": "बैरागढ़ (संत हिरदाराम) कुंड",
    "Khatlapura ghat": "खटलापुरा घाट",
    "Prempura ghat": "प्रेमपुरा घाट",
    "Rani Kamlapati ghat / Kamla Park kund": "रानी कमलापति घाट / कमला पार्क कुंड",
    "Hathaikheda dam / kund": "हथाईखेड़ा डैम / कुंड",
    "Malikhedi kund": "मालीखेड़ी कुंड",
    "Shahpura lake ghat": "शाहपुरा लेक घाट",
}

GHAT_KEYWORDS = [  # order matters: specific names before 'lower lake'
    ("bairagarh", "Bairagarh (Sant Hirdaram) kund"),
    ("hirdaram", "Bairagarh (Sant Hirdaram) kund"),
    ("hirdaram", "Bairagarh (Sant Hirdaram) kund"),
    ("khatlapura", "Khatlapura ghat"),
    ("prempura", "Prempura ghat"),
    ("kamlapati", "Rani Kamlapati ghat / Kamla Park kund"),
    ("kamla", "Rani Kamlapati ghat / Kamla Park kund"),
    ("hathai", "Hathaikheda dam / kund"),
    ("malikhed", "Malikhedi kund"),
    ("maalikhed", "Malikhedi kund"),
    ("malikhedi", "Malikhedi kund"),
    ("shahpura", "Shahpura lake ghat"),
    ("lower lake", "Rani Kamlapati ghat / Kamla Park kund"),  # Durga-table label
]

# --------------------------------------------------------------------------
# 2. Column detection
# --------------------------------------------------------------------------
PARAM_PATTERNS = {
    "pH": r"^ph\b|\bph\b",
    "DO": r"dissolved oxygen|^do\b|\bdo\b",
    "BOD": r"\bbod\b|biochemical",
    "TC": r"total coliform|^tc\b|\btc\b|coliform|mpn",
    "Cr": r"chromium|^cr\b|\bcr\b",
    "Pb": r"\blead\b|^pb\b|\bpb\b",
    "Zn": r"\bzinc\b|^zn\b|\bzn\b",
    "Cu": r"\bcopper\b|^cu\b|\bcu\b",
}
COLUMN_PATTERNS = {
    "ghat": r"ghat|location|site|station|sampling point|name",
    "year": r"\byear\b|^yr\b",
    "festival": r"festival|event",
    "phase": r"phase|stage|period|immersion|when",
    "page": r"page|pg\b",
    "report": r"report|source|file|pdf",
    "date": r"date",
}
CORE = ["DO", "BOD", "TC", "pH"]
METALS = ["Cr", "Pb", "Zn", "Cu"]


def norm(s):
    return re.sub(r"[^a-z0-9<]+", " ", str(s).lower()).strip()


def param_of(text):
    t = norm(text)
    if re.search(r"faecal|fecal", t) and "total" not in t:
        return None
    for p, pat in PARAM_PATTERNS.items():
        if re.search(pat, t):
            return p
    return None


def detect_columns(df):
    """Return (meta_map, param_columns, long_format)."""
    cols = list(df.columns)
    meta = {}
    long_fmt = False
    pcol = next((c for c in cols if norm(c) in ("parameter", "param", "test",
                                                "parameter name")), None)
    vcol = next((c for c in cols if norm(c) in ("value", "result", "reading",
                                                "observed value")), None)
    if pcol and vcol:
        long_fmt = True
        meta["parameter"], meta["value"] = pcol, vcol
    used = set(meta.values())
    for key, pat in COLUMN_PATTERNS.items():
        for c in cols:
            if c in used or (not long_fmt and param_of(c)):
                continue
            if re.search(pat, norm(c)):
                meta[key] = c
                used.add(c)
                break
    pcols = {}
    if not long_fmt:
        for c in cols:
            p = param_of(c)
            if p and c not in used and p not in pcols:
                pcols[p] = c
    return meta, pcols, long_fmt


# --------------------------------------------------------------------------
# 3. Value parsing (the missing-data rules live here)
# --------------------------------------------------------------------------
MISSING_TOKENS = {"", "_", "-", "--", "—", "–", "na", "n/a", "nan", "none",
                  "null", "not sampled", "ns", "not tested", "nt"}


def parse_value(raw, param):
    """Return (status, number). status in {'value','low','missing'}.
    'low' = BDL/ND: very low, valid, compliant, and NOT zero."""
    if raw is None or (isinstance(raw, float) and math.isnan(raw)):
        return "missing", None
    s = str(raw).strip()
    low = s.lower()
    if low in MISSING_TOKENS:
        return "missing", None
    if low in ("bdl", "nd") or low.startswith("<"):
        if param in ("pH", "DO"):          # implausible -> do not assume clean
            return "missing", None
        return "low", None
    m = re.search(r"-?\d+(?:[.,]\d+)?(?:e[+-]?\d+)?", low.replace(",", ""))
    if not m:
        return "missing", None
    try:
        v = float(m.group(0))
    except ValueError:
        return "missing", None
    if param in DETECTION_LIMIT and v <= DETECTION_LIMIT[param] + 1e-9:
        return "low", None          # at/below MPPCB detection limit = BDL
    return "value", v


def canon_ghat(text):
    t = norm(text)
    for kw, name in GHAT_KEYWORDS:
        if kw in t:
            return name
    return None


def canon_phase(text):
    t = norm(text)
    if re.search(r"\bpre\b|before", t):
        return "pre"
    if re.search(r"post|after", t):
        return "post"
    if re.search(r"during|immers|\bdur\b", t):
        return "during"
    return "unknown"


def canon_festival(text):
    t = norm(text)
    if "durga" in t or "navratri" in t or "dussehra" in t:
        return "Durga"
    if "ganesh" in t or "ganpati" in t:
        return "Ganesh"
    return str(text).strip() or "unknown"


# --------------------------------------------------------------------------
# 4. Load -> tidy long table
# --------------------------------------------------------------------------
def load(paths):
    frames, unmapped = [], set()
    for path in paths:
        df = pd.read_csv(path, dtype=str, keep_default_na=False,
                         encoding="utf-8-sig")
        meta, pcols, long_fmt = detect_columns(df)
        if "ghat" not in meta:
            sys.exit(f"[{path}] cannot find a ghat/location column. "
                     f"Columns: {list(df.columns)}")
        recs = []
        for i, row in df.iterrows():
            g = canon_ghat(row[meta["ghat"]])
            if g is None:
                unmapped.add(row[meta["ghat"]])
                continue
            base = {
                "ghat": g,
                "year": pd.to_numeric(row.get(meta.get("year", ""), None),
                                      errors="coerce"),
                "festival": canon_festival(row.get(meta.get("festival", ""), "")),
                "phase": canon_phase(row.get(meta.get("phase", ""), "")),
                "page": str(row.get(meta.get("page", ""), "")).strip(),
                "report": str(row.get(meta.get("report", ""), "")).strip(),
                "src_file": os.path.basename(path),
                "src_row": i + 2,   # +2 = header + 1-based -> spreadsheet row
            }
            if long_fmt:
                p = param_of(row[meta["parameter"]])
                items = [(p, row[meta["value"]])] if p else []
            else:
                items = [(p, row[c]) for p, c in pcols.items()]
            for p, raw in items:
                status, num = parse_value(raw, p)
                recs.append({**base, "param": p, "raw": str(raw).strip(),
                             "status": status, "num": num})
        frames.append(pd.DataFrame(recs))
    tidy = pd.concat(frames, ignore_index=True)
    if tidy["year"].isna().all():
        tidy["year"] = 0
    tidy["w"] = tidy["year"].map(lambda y: YEAR_WEIGHT.get(int(y), 0.75)
                                 if pd.notna(y) else 0.75)
    return tidy, unmapped


def trace(r):
    """Human-checkable pointer back to the source report/page."""
    bits = []
    if pd.notna(r["year"]) and r["year"]:
        bits.append(f"{int(r['year'])} {r['festival']}")
    if r["phase"] != "unknown":
        bits.append(f"{r['phase']}-immersion")
    ref = []
    if r["report"]:
        ref.append(r["report"])
    if r["page"]:
        ref.append(f"p.{r['page']}")
    ref.append(f"{r['src_file']} row {r['src_row']}")
    return ", ".join(bits + ["[" + " ".join(ref) + "]"])


# --------------------------------------------------------------------------
# 5. Exceedance + severity (0..1) per reading
# --------------------------------------------------------------------------
def exceed(param, v):
    """Return (exceeds: bool, severity 0..1) for a numeric reading."""
    if param == "DO":
        return v < CPCB_B["DO"], min(1.0, (CPCB_B["DO"] - v) / CPCB_B["DO"])
    if param == "BOD":
        return v > CPCB_B["BOD"], min(1.0, (v - CPCB_B["BOD"]) / (3 * CPCB_B["BOD"]))
    if param == "TC":
        if v <= CPCB_B["TC"]:
            return False, 0.0
        return True, min(1.0, math.log10(v / CPCB_B["TC"]) / 2)
    if param == "pH":
        lo, hi = CPCB_B["pH"]
        d = lo - v if v < lo else v - hi
        return d > 0, min(1.0, max(d, 0) / 1.5)
    ref = METAL_REF[param]
    return v > ref, min(1.0, math.log10(max(v / ref, 1)) / 1.0)


def wmean(vals, ws):
    sw = sum(ws)
    return sum(v * w for v, w in zip(vals, ws)) / sw if sw else 0.0


# --------------------------------------------------------------------------
# 6. Score one ghat
# --------------------------------------------------------------------------
def score_ghat(g):
    out = {"comp": {}, "facts": {}}
    nums = g[g["status"] == "value"]

    # core parameters ----------------------------------------------------
    for p in CORE:
        sub = nums[nums["param"] == p]
        if sub.empty:
            out["comp"][p] = 0.0
            out["facts"][p] = {"n": 0}
            continue
        flags = [exceed(p, v) for v in sub["num"]]
        exc = [f[0] for f in flags]
        sev = [f[1] for f in flags]
        rate = wmean([1.0 if e else 0.0 for e in exc], sub["w"])
        ex_sev = [s for e, s in zip(exc, sev) if e]
        mean_sev = sum(ex_sev) / len(ex_sev) if ex_sev else 0.0
        out["comp"][p] = rate * (0.5 + 0.5 * mean_sev)
        worst_i = (sub["num"].idxmin() if p == "DO" else
                   sub["num"].idxmax() if p != "pH" else
                   (sub["num"] - 7.5).abs().idxmax())
        out["facts"][p] = {
            "n": len(sub), "k": sum(exc),
            "worst": sub.loc[worst_i, "num"], "trace": trace(sub.loc[worst_i]),
            "zero": int((sub["num"] == 0).sum()) if p == "DO" else 0,
        }

    # heavy metals -------------------------------------------------------
    m_valid = g[(g["param"].isin(METALS)) & (g["status"].isin(["value", "low"]))]
    m_num = m_valid[m_valid["status"] == "value"]
    if len(m_valid):
        det = wmean([1.0 if (s == "value" and v > 0) else 0.0
                     for s, v in zip(m_valid["status"],
                                     m_valid["num"].fillna(0))], m_valid["w"])
        exc_flags = [exceed(p, v)[0] for p, v in zip(m_num["param"], m_num["num"])]
        exr = wmean([1.0 if e else 0.0 for e in exc_flags], m_num["w"]) if len(m_num) else 0.0
        out["comp"]["METALS"] = 0.5 * det + 0.5 * exr
    else:
        out["comp"]["METALS"] = 0.0
    det_by_metal = {m: int(((m_num["param"] == m) & (m_num["num"] > 0)).sum())
                    for m in METALS}
    exc_by_metal = {m: sum(exceed(m, v)[0] for v in m_num[m_num["param"] == m]["num"])
                    for m in METALS}
    out["facts"]["METALS"] = {"n": len(m_valid), "detected": det_by_metal,
                              "exceed": exc_by_metal}
    if len(m_num):
        wi = m_num["num"].idxmax()
        out["facts"]["METALS"]["worst_trace"] = trace(m_num.loc[wi])

    # immersion deterioration (pre vs during/post) -------------------------
    det_parts, imm = [], {}
    for p, fn in (("DO", lambda a, b: max(0, a - b) / CPCB_B["DO"]),
                  ("BOD", lambda a, b: max(0, b - a) / CPCB_B["BOD"])):
        sub = nums[nums["param"] == p]
        pre = sub[sub["phase"] == "pre"]["num"]
        dp = sub[sub["phase"].isin(["during", "post"])]["num"]
        if len(pre) and len(dp):
            det_parts.append(min(1.0, fn(pre.mean(), dp.mean())))
            imm[p] = (pre.mean(), dp.mean())
    out["comp"]["IMMERSION"] = sum(det_parts) / len(det_parts) if det_parts else 0.0
    out["facts"]["IMMERSION"] = imm

    # data coverage: missing is NOT clean ---------------------------------
    core_rows = g[g["param"].isin(CORE)]
    out["coverage"] = ((core_rows["status"] != "missing").mean()
                       if len(core_rows) else 0.0)
    out["n_rows"] = g[["src_file", "src_row"]].drop_duplicates().shape[0]

    base = sum(WEIGHTS[k] * out["comp"][k] for k in WEIGHTS) * 100
    penalty = (1 - out["coverage"]) * MAX_GAP_PENALTY
    out["score"] = min(100.0, base + penalty)
    out["gap_penalty"] = penalty
    out["band"] = ("HIGH" if out["score"] >= HIGH else
                   "MEDIUM" if out["score"] >= MEDIUM else "LOWER")
    return out


# --------------------------------------------------------------------------
# 7. Plain-word reasons (English + Hindi)
# --------------------------------------------------------------------------
def fmt(x):
    return f"{x:g}" if x is not None else "-"


def reasons(res, lang):
    f, R = res["facts"], []
    en = lang == "en"
    d = f.get("DO", {"n": 0})
    if d.get("n") and d["k"]:
        R.append((f"Oxygen (DO) was below the safe 5 mg/l in {d['k']} of {d['n']} readings; "
                  f"lowest {fmt(d['worst'])} mg/l ({d['trace']}).") if en else
                 (f"घुली ऑक्सीजन (DO) {d['n']} में से {d['k']} जाँच में सुरक्षित सीमा 5 mg/l से कम रही; "
                  f"सबसे कम {fmt(d['worst'])} mg/l ({d['trace']})।"))
        if d["zero"]:
            R.append((f"DO hit 0 mg/l on {d['zero']} occasion(s) - no fish can survive."
                      ) if en else
                     f"DO {d['zero']} बार शून्य (0 mg/l) दर्ज हुई - मछलियाँ जीवित नहीं रह सकतीं।")
    b = f.get("BOD", {"n": 0})
    if b.get("n") and b["k"]:
        R.append((f"BOD (pollution load) above the 3 mg/l limit in {b['k']} of {b['n']} readings; "
                  f"highest {fmt(b['worst'])} mg/l ({b['trace']}).") if en else
                 (f"BOD (प्रदूषण भार) {b['n']} में से {b['k']} जाँच में 3 mg/l की सीमा से अधिक; "
                  f"सर्वाधिक {fmt(b['worst'])} mg/l ({b['trace']})।"))
    t = f.get("TC", {"n": 0})
    if t.get("n") and t["k"]:
        R.append((f"Total coliform (sewage bacteria) above 500 MPN/100 ml in {t['k']} of {t['n']} readings; "
                  f"highest {fmt(t['worst'])} ({t['trace']}).") if en else
                 (f"कुल कोलीफॉर्म (सीवेज बैक्टीरिया) {t['n']} में से {t['k']} जाँच में 500 MPN/100 ml से अधिक; "
                  f"सर्वाधिक {fmt(t['worst'])} ({t['trace']})।"))
    p = f.get("pH", {"n": 0})
    if p.get("n") and p["k"]:
        R.append((f"pH outside 6.5-8.5 in {p['k']} of {p['n']} readings (worst {fmt(p['worst'])})."
                  ) if en else
                 f"pH {p['n']} में से {p['k']} जाँच में 6.5-8.5 के बाहर (सबसे अधिक विचलन {fmt(p['worst'])})।")
    m = f.get("METALS", {"n": 0})
    if m.get("n"):
        found = [k for k, v in m["detected"].items() if v]
        if found:
            names = ", ".join(METAL_NAMES[lang][k] for k in found)
            over = [k for k, v in m["exceed"].items() if v]
            over_txt_en = (f" Above the reference level for: "
                           f"{', '.join(METAL_NAMES['en'][k] for k in over)}." if over else "")
            over_txt_hi = (f" संदर्भ सीमा से अधिक: "
                           f"{', '.join(METAL_NAMES['hi'][k] for k in over)}।" if over else "")
            R.append((f"Heavy metals detected: {names} - often from idol paints.{over_txt_en}"
                      f" ({m.get('worst_trace', '')})") if en else
                     (f"भारी धातुएँ मिलीं: {names} - अक्सर मूर्तियों के रंगों से।{over_txt_hi}"
                      f" ({m.get('worst_trace', '')})"))
    im = f.get("IMMERSION", {})
    if "DO" in im and im["DO"][1] < im["DO"][0] - 0.5:
        R.append((f"Immersion makes it worse: average DO fell from {im['DO'][0]:.1f} before to "
                  f"{im['DO'][1]:.1f} mg/l during/after.") if en else
                 (f"विसर्जन से स्थिति बिगड़ती है: औसत DO पहले {im['DO'][0]:.1f} से घटकर "
                  f"विसर्जन के दौरान/बाद में {im['DO'][1]:.1f} mg/l रही।"))
    if "BOD" in im and im["BOD"][1] > im["BOD"][0] + 0.5:
        R.append((f"Average BOD rose from {im['BOD'][0]:.1f} to {im['BOD'][1]:.1f} mg/l during/after immersion."
                  ) if en else
                 f"औसत BOD विसर्जन के दौरान/बाद में {im['BOD'][0]:.1f} से बढ़कर {im['BOD'][1]:.1f} mg/l हुई।")
    cov = res["coverage"]
    if cov < 0.85:
        R.append((f"DATA GAP: only {cov:.0%} of required readings exist. Blanks are NOT treated as clean; "
                  f"re-test before immersion.") if en else
                 (f"डेटा की कमी: आवश्यक रीडिंग में से केवल {cov:.0%} उपलब्ध हैं। खाली को साफ़ नहीं माना गया; "
                  f"विसर्जन से पहले दोबारा जाँच कराएँ।"))
    if not R:
        R.append("No Class B exceedances found in the available readings."
                 if en else "उपलब्ध रीडिंग में Class B की कोई सीमा पार नहीं हुई।")
    return R


# --------------------------------------------------------------------------
# 8. Outputs
# --------------------------------------------------------------------------
ACTIONS = {
    "en": {
        "HIGH": "Re-test 7-10 days before; prefer artificial tank/alternate site; ask for clay, natural-colour idols; "
                "sample again right after immersion; arrange debris removal.",
        "MEDIUM": "Re-test before immersion; push eco-friendly idols; keep watch on DO and BOD; sample after immersion.",
        "LOWER": "Routine monitoring; confirm with a pre-immersion sample.",
    },
    "hi": {
        "HIGH": "विसर्जन से 7-10 दिन पहले दोबारा जाँच; कृत्रिम कुंड/वैकल्पिक स्थल को प्राथमिकता; मिट्टी व प्राकृतिक रंगों की "
                "मूर्तियों का आग्रह; विसर्जन के तुरंत बाद फिर नमूना; मलबा हटाने की व्यवस्था।",
        "MEDIUM": "विसर्जन से पहले दोबारा जाँच; पर्यावरण-अनुकूल मूर्तियों का आग्रह; DO व BOD पर नज़र; विसर्जन के बाद नमूना।",
        "LOWER": "नियमित निगरानी; विसर्जन से पहले एक नमूने से पुष्टि करें।",
    },
}
BAND_HI = {"HIGH": "उच्च जोखिम", "MEDIUM": "मध्यम जोखिम", "LOWER": "अपेक्षाकृत कम जोखिम"}


def brief(ranked, lang, date_txt, top_n=3):
    en = lang == "en"
    has_tc = any(r["facts"]["TC"]["n"] for _, r in ranked)
    tc_en = ", Total Coliform <= 500 MPN/100 ml" if has_tc else ""
    tc_hi = ", कुल कोलीफॉर्म <= 500 MPN/100 ml" if has_tc else ""
    no_tc_en = "" if has_tc else (" Coliform was not scored: the ghat-level reports contain no coliform "
                                  "results.")
    no_tc_hi = "" if has_tc else (" कोलीफॉर्म का आकलन नहीं हुआ: घाट-स्तर की रिपोर्टों में कोलीफॉर्म "
                                  "के परिणाम नहीं हैं।")
    L = []
    if en:
        L += [f"TO: BMC Officer, Durga Visarjan {date_txt}",
              "SUBJECT: Ghat Watch - which Bhopal ghats need attention first", "",
              "Based on MPPCB readings 2023-2025 measured against CPCB Class B bathing limits "
              f"(DO >= 5 mg/l, BOD <= 3 mg/l{tc_en}, pH 6.5-8.5).{no_tc_en}", ""]
    else:
        L += [f"प्रति: नगर निगम अधिकारी, दुर्गा विसर्जन {date_txt}",
              "विषय: घाट वॉच - भोपाल के किन घाटों पर पहले ध्यान दें", "",
              "आधार: MPPCB की 2023-2025 की जाँच रिपोर्टें, CPCB क्लास B (बाहरी स्नान) की सीमाओं के विरुद्ध "
              f"(DO >= 5 mg/l, BOD <= 3 mg/l{tc_hi}, pH 6.5-8.5)।{no_tc_hi}", ""]
    L.append("PRIORITY ORDER:" if en else "प्राथमिकता क्रम:")
    for i, (name, res) in enumerate(ranked, 1):
        nm = name if en else GHAT_HI[name]
        band = res["band"] if en else BAND_HI[res["band"]]
        L.append(f"{i}. {nm} - {band} ({res['score']:.0f}/100)")
    L.append("")
    for i, (name, res) in enumerate(ranked[:top_n], 1):
        nm = name if en else GHAT_HI[name]
        L.append(f"{i}. {nm} ({GHATS[name][0]})")
        for r in reasons(res, lang)[:4]:
            L.append(f"   - {r}")
        L.append(f"   {'Action' if en else 'कार्रवाई'}: {ACTIONS[lang][res['band']]}")
        L.append("")
    gaps = [n for n, r in ranked if r["coverage"] < 0.85]
    if gaps:
        L.append(("Data gaps (blank is not clean): " if en else "डेटा में कमी (खाली = साफ़ नहीं): ")
                 + ", ".join(g if en else GHAT_HI[g] for g in gaps))
    if GHATS and any(GHATS[n][1] == "Medium" for n, _ in ranked):
        L.append("Note: Rani Kamlapati ghat is 'Kamla Park kund' in Ganesh tables and 'Lower Lake ghat' in "
                 "Durga tables; the match is medium-confidence." if en else
                 "टिप्पणी: रानी कमलापति घाट, गणेश तालिकाओं में 'कमला पार्क कुंड' और दुर्गा तालिकाओं में "
                 "'लोअर लेक घाट' है; मिलान मध्यम विश्वसनीयता का है।")
    L.append("Scores are relative priorities, not a legal finding. Every figure is traceable to the "
             "source file/page shown in brackets." if en else
             "स्कोर प्राथमिकता तय करने के लिए हैं, कानूनी निष्कर्ष नहीं। हर आँकड़ा कोष्ठक में दिए स्रोत "
             "फ़ाइल/पेज से जाँचा जा सकता है।")
    return "\n".join(L)


def write_outputs(ranked, outdir, date_txt):
    os.makedirs(outdir, exist_ok=True)
    rows = []
    for i, (name, r) in enumerate(ranked, 1):
        rows.append({
            "rank": i, "ghat": name, "ghat_hindi": GHAT_HI[name],
            "water_body": GHATS[name][0], "mapping_confidence": GHATS[name][1],
            "risk_score": round(r["score"], 1), "band": r["band"],
            "DO_score": round(r["comp"]["DO"], 3), "BOD_score": round(r["comp"]["BOD"], 3),
            "coliform_score": round(r["comp"]["TC"], 3), "pH_score": round(r["comp"]["pH"], 3),
            "metals_score": round(r["comp"]["METALS"], 3),
            "immersion_worsening": round(r["comp"]["IMMERSION"], 3),
            "data_coverage_pct": round(r["coverage"] * 100),
            "gap_penalty_pts": round(r["gap_penalty"], 1),
            "main_reasons_en": " | ".join(reasons(r, "en")),
            "main_reasons_hi": " | ".join(reasons(r, "hi")),
        })
    pd.DataFrame(rows).to_csv(os.path.join(outdir, "ghat_risk_ranking.csv"),
                              index=False, encoding="utf-8-sig")

    md = ["# Visarjan Ghat Watch - Bhopal risk ranking", "",
          "| Rank | Ghat | Water body | Score | Band | Data coverage |",
          "|---|---|---|---|---|---|"]
    for i, (n, r) in enumerate(ranked, 1):
        md.append(f"| {i} | {n} | {GHATS[n][0]} | {r['score']:.0f} | {r['band']} | {r['coverage']:.0%} |")
    md += ["", "## Why each ghat ranks where it does", ""]
    for i, (n, r) in enumerate(ranked, 1):
        md.append(f"### {i}. {n} - {r['band']} ({r['score']:.0f}/100)")
        md += [f"- {x}" for x in reasons(r, "en")]
        md.append("")
    md += ["## Method", "",
           f"Weights: {WEIGHTS}. Year weights: {YEAR_WEIGHT}. Gap penalty up to {MAX_GAP_PENALTY} pts. "
           f"Metal reference limits (NOT CPCB Class B, which has none): {METAL_REF} mg/l."]
    with open(os.path.join(outdir, "ghat_risk_report.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(md))
    for lang in ("en", "hi"):
        with open(os.path.join(outdir, f"brief_{lang}.txt"), "w", encoding="utf-8") as fh:
            fh.write(brief(ranked, lang, date_txt))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", nargs="+", default=["data/bhopal_ghats_2023_2025.csv"])
    ap.add_argument("--out", default="outputs")
    ap.add_argument("--festival", choices=["Durga", "Ganesh", "all"], default="all",
                    help="restrict to one festival's readings (default: all)")
    ap.add_argument("--date", default="20 October 2026")
    ap.add_argument("--show-columns", action="store_true")
    a = ap.parse_args()

    if a.show_columns:
        for p in a.data:
            df = pd.read_csv(p, dtype=str, nrows=5, encoding="utf-8-sig")
            print(p, detect_columns(df))
        return

    missing = [p for p in a.data if not os.path.isfile(p)]
    if missing:
        sys.exit(f"Data file not found: {missing}. Put the project CSV at that path, or run "
                 "`python extract_idol_reports.py --pdf-dir resources` to build "
                 "data/bhopal_ghats_extracted.csv from the MPPCB PDFs and pass that to --data.")
    tidy, unmapped = load(a.data)
    if unmapped:
        print("WARNING - rows with unrecognised ghat names were skipped:", sorted(unmapped))
    if a.festival != "all":
        tidy = tidy[tidy["festival"] == a.festival]

    ranked = []
    for name in GHATS:
        g = tidy[tidy["ghat"] == name]
        if g.empty:
            print(f"WARNING - no rows found for {name}")
            continue
        ranked.append((name, score_ghat(g)))
    ranked.sort(key=lambda x: -x[1]["score"])
    write_outputs(ranked, a.out, a.date)

    print(f"\n{'#':<3}{'Ghat':<40}{'Score':>6}  {'Band':<7}{'Cover':>6}")
    for i, (n, r) in enumerate(ranked, 1):
        print(f"{i:<3}{n:<40}{r['score']:>6.0f}  {r['band']:<7}{r['coverage']:>6.0%}")
    print(f"\nWrote ranking, report and EN/HI briefs to ./{a.out}/")


if __name__ == "__main__":
    main()
