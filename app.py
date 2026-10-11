"""
Visarjan Ghat Watch - BMC / MPPCB Water Quality Data Portal
Claude Impact Lab Bhopal - Track 2

Run:  pip install streamlit pandas altair
      streamlit run app.py

Single file. The 120 ghat readings (7 Bhopal ghats, 2023-2025, Ganesh and Durga,
before / during / one week after immersion) were extracted from the MPPCB
idol-immersion reports and are embedded below (DATA_CSV), each with its PDF page.
This is a static MPPCB dataset, NOT a live sensor feed.
"""
import io
import re

import pandas as pd
import streamlit as st

# --------------------------------------------------------------------------
# 1. Embedded data (extracted from MPPCB PDFs; values kept as printed)
#    * = kund not built before immersion, ** = kund dismantled before 1-week sample
# --------------------------------------------------------------------------
DATA_CSV = """Ghat,Year,Festival,Phase,pH,DO (mg/l),BOD (mg/l),Chromium (mg/l),Lead (mg/l),Zinc (mg/l),Copper (mg/l),Report,Page
Khatlapura ghat,2023,Ganesh,pre,6.98,6.4,2.4,BDL,BDL,0.011,BDL,MPPCB 2023 idol immersion report (PDF),26
Khatlapura ghat,2023,Ganesh,during,7.63,6.1,2.8,_,_,_,_,MPPCB 2023 idol immersion report (PDF),26
Khatlapura ghat,2023,Ganesh,post,8.08,7.8,11.2,BDL,BDL,0.019,0.026,MPPCB 2023 idol immersion report (PDF),26
Bairagarh (Sant Hirdaram) kund,2023,Ganesh,pre,7.71,5.6,3.8,BDL,BDL,0.238,BDL,MPPCB 2023 idol immersion report (PDF),26
Bairagarh (Sant Hirdaram) kund,2023,Ganesh,during,7.37,4.5,4.2,BDL,0.101,0.689,0.069,MPPCB 2023 idol immersion report (PDF),26
Bairagarh (Sant Hirdaram) kund,2023,Ganesh,post,7.2,0,10,BDL,BDL,0.023,0.019,MPPCB 2023 idol immersion report (PDF),26
Prempura ghat,2023,Ganesh,pre,7.72,6.2,1.3,BDL,BDL,0.009,BDL,MPPCB 2023 idol immersion report (PDF),26
Prempura ghat,2023,Ganesh,during,8.53,6.7,1.5,BDL,0.076,0.0183,0.066,MPPCB 2023 idol immersion report (PDF),26
Prempura ghat,2023,Ganesh,post,7.44,6.5,2,BDL,BDL,0.015,0.025,MPPCB 2023 idol immersion report (PDF),26
Rani Kamlapati ghat / Kamla Park kund,2023,Ganesh,pre,7.65,6.6,4.2,BDL,BDL,0.012,BDL,MPPCB 2023 idol immersion report (PDF),27
Rani Kamlapati ghat / Kamla Park kund,2023,Ganesh,during,8.35,5.8,4.4,BDL,0.06,0.066,0.074,MPPCB 2023 idol immersion report (PDF),27
Rani Kamlapati ghat / Kamla Park kund,2023,Ganesh,post,8.07,9.5,9.2,BDL,BDL,0.01,0.019,MPPCB 2023 idol immersion report (PDF),27
Hathaikheda dam / kund,2023,Ganesh,pre,8.1,7.9,2.5,BDL,BDL,0.026,BDL,MPPCB 2023 idol immersion report (PDF),27
Hathaikheda dam / kund,2023,Ganesh,during,8.92,6.5,6,BDL,0.08,0.077,0.105,MPPCB 2023 idol immersion report (PDF),27
Hathaikheda dam / kund,2023,Ganesh,post,8.01,5.1,10.8,BDL,BDL,0.008,0.031,MPPCB 2023 idol immersion report (PDF),27
Malikhedi kund,2023,Ganesh,pre,7.65,7.5,1.6,BDL,BDL,0.024,BDL,MPPCB 2023 idol immersion report (PDF),27
Malikhedi kund,2023,Ganesh,during,7.81,7,1.8,BDL,0.145,0.089,0.111,MPPCB 2023 idol immersion report (PDF),27
Malikhedi kund,2023,Ganesh,post,7.11,3.2,16.8,BDL,BDL,0.011,0.026,MPPCB 2023 idol immersion report (PDF),27
Shahpura lake ghat,2023,Ganesh,pre,7.32,5.9,6.4,BDL,BDL,0.009,BDL,MPPCB 2023 idol immersion report (PDF),28
Shahpura lake ghat,2023,Ganesh,during,7.36,5.2,8.4,BDL,BDL,0.021,BDL,MPPCB 2023 idol immersion report (PDF),28
Shahpura lake ghat,2023,Ganesh,post,7.76,5,10.4,BDL,BDL,0.025,0.078,MPPCB 2023 idol immersion report (PDF),28
Hathaikheda dam / kund,2023,Durga,pre,8.02,6.5,4,BDL,BDL,0.025,BDL,MPPCB 2023 idol immersion report (PDF),59
Hathaikheda dam / kund,2023,Durga,during,8.02,10.2,8.8,BDL,0.11,0.286,0.052,MPPCB 2023 idol immersion report (PDF),59
Hathaikheda dam / kund,2023,Durga,post,8.15,8.6,2.4,BDL,0.1,0.135,0.16,MPPCB 2023 idol immersion report (PDF),59
Rani Kamlapati ghat / Kamla Park kund,2023,Durga,pre,8.07,6.2,8.8,BDL,BDL,0.068,0.048,MPPCB 2023 idol immersion report (PDF),59
Rani Kamlapati ghat / Kamla Park kund,2023,Durga,during,7.63,6,8.4,BDL,BDL,0.063,0.038,MPPCB 2023 idol immersion report (PDF),59
Rani Kamlapati ghat / Kamla Park kund,2023,Durga,post,7.54,6.5,8.6,BDL,BDL,0.013,0.008,MPPCB 2023 idol immersion report (PDF),59
Khatlapura ghat,2023,Durga,pre,7.87,4.5,6.4,BDL,BDL,0.027,BDL,MPPCB 2023 idol immersion report (PDF),59
Khatlapura ghat,2023,Durga,during,8.2,4.2,_,BDL,BDL,0.068,BDL,MPPCB 2023 idol immersion report (PDF),59
Khatlapura ghat,2023,Durga,post,7.46,4.4,7.8,BDL,BDL,0.015,BDL,MPPCB 2023 idol immersion report (PDF),59
Bairagarh (Sant Hirdaram) kund,2023,Durga,pre,7.32,0,9.2,BDL,0.16,0.03,BDL,MPPCB 2023 idol immersion report (PDF),60
Bairagarh (Sant Hirdaram) kund,2023,Durga,during,7.55,0,9,BDL,0.11,0.103,0.053,MPPCB 2023 idol immersion report (PDF),60
Bairagarh (Sant Hirdaram) kund,2023,Durga,post,7.81,4.2,9.4,BDL,BDL,0.063,0.074,MPPCB 2023 idol immersion report (PDF),60
Prempura ghat,2023,Durga,pre,7.66,5.4,_,BDL,BDL,0.02,BDL,MPPCB 2023 idol immersion report (PDF),60
Prempura ghat,2023,Durga,during,_,5,_,BDL,0.06,0.074,0.075,MPPCB 2023 idol immersion report (PDF),60
Prempura ghat,2023,Durga,post,7.39,5.7,_,BDL,BDL,0.013,0.009,MPPCB 2023 idol immersion report (PDF),60
Shahpura lake ghat,2023,Durga,pre,7.35,4.5,6.4,BDL,BDL,0.056,0.047,MPPCB 2023 idol immersion report (PDF),60
Shahpura lake ghat,2023,Durga,during,7.73,4,6.8,BDL,0.14,0.363,0.121,MPPCB 2023 idol immersion report (PDF),60
Shahpura lake ghat,2023,Durga,post,7.76,5,7.8,BDL,BDL,0.068,0.081,MPPCB 2023 idol immersion report (PDF),60
Malikhedi kund,2023,Durga,pre,7.57,4.6,6.8,BDL,BDL,0.024,BDL,MPPCB 2023 idol immersion report (PDF),61
Malikhedi kund,2023,Durga,during,7.37,4.3,6.8,BDL,0.14,0.064,0.058,MPPCB 2023 idol immersion report (PDF),61
Malikhedi kund,2023,Durga,post,7.81,10.4,6.6,BDL,BDL,0.063,0.059,MPPCB 2023 idol immersion report (PDF),61
Hathaikheda dam / kund,2024,Durga,pre,9.2,8.6,7.4,BDL,BDL,BDL,BDL,MPPCB 2024 idol immersion report (PDF),23
Hathaikheda dam / kund,2024,Durga,during,7.7,5.9,4.4,BDL,BDL,BDL,BDL,MPPCB 2024 idol immersion report (PDF),23
Hathaikheda dam / kund,2024,Durga,post,7.7,5.7,4.6,BDL,BDL,BDL,BDL,MPPCB 2024 idol immersion report (PDF),23
Rani Kamlapati ghat / Kamla Park kund,2024,Durga,pre,7.48,7.5,5.6,BDL,BDL,BDL,BDL,MPPCB 2024 idol immersion report (PDF),24
Rani Kamlapati ghat / Kamla Park kund,2024,Durga,during,7.7,6.4,5.8,BDL,BDL,BDL,BDL,MPPCB 2024 idol immersion report (PDF),24
Rani Kamlapati ghat / Kamla Park kund,2024,Durga,post,7.75,6.5,6,BDL,BDL,BDL,BDL,MPPCB 2024 idol immersion report (PDF),24
Khatlapura ghat,2024,Durga,pre,8,6.6,7.8,BDL,BDL,BDL,BDL,MPPCB 2024 idol immersion report (PDF),24
Khatlapura ghat,2024,Durga,during,7.57,4.5,8,BDL,BDL,BDL,BDL,MPPCB 2024 idol immersion report (PDF),24
Khatlapura ghat,2024,Durga,post,7.4,4.4,8.4,BDL,BDL,BDL,BDL,MPPCB 2024 idol immersion report (PDF),24
Bairagarh (Sant Hirdaram) kund,2024,Durga,pre,7.03,4.2,6,BDL,BDL,BDL,BDL,MPPCB 2024 idol immersion report (PDF),25
Bairagarh (Sant Hirdaram) kund,2024,Durga,during,6.87,2.2,8,BDL,BDL,BDL,BDL,MPPCB 2024 idol immersion report (PDF),25
Bairagarh (Sant Hirdaram) kund,2024,Durga,post,7.24,2.4,8.2,BDL,BDL,BDL,BDL,MPPCB 2024 idol immersion report (PDF),25
Prempura ghat,2024,Durga,pre,8.22,7.6,2.4,BDL,BDL,BDL,BDL,MPPCB 2024 idol immersion report (PDF),25
Prempura ghat,2024,Durga,during,8.02,6.4,2.6,BDL,BDL,BDL,BDL,MPPCB 2024 idol immersion report (PDF),25
Prempura ghat,2024,Durga,post,8.11,7.6,3.4,BDL,BDL,BDL,BDL,MPPCB 2024 idol immersion report (PDF),25
Shahpura lake ghat,2024,Durga,pre,7.36,6.8,10.8,BDL,BDL,BDL,BDL,MPPCB 2024 idol immersion report (PDF),26
Shahpura lake ghat,2024,Durga,during,7.35,5.4,11.2,BDL,BDL,BDL,BDL,MPPCB 2024 idol immersion report (PDF),26
Shahpura lake ghat,2024,Durga,post,7.53,3.8,11.6,BDL,BDL,BDL,BDL,MPPCB 2024 idol immersion report (PDF),26
Malikhedi kund,2024,Durga,pre,7.29,4.5,6.8,BDL,BDL,BDL,BDL,MPPCB 2024 idol immersion report (PDF),26
Malikhedi kund,2024,Durga,during,7.3,4.1,5,BDL,BDL,BDL,BDL,MPPCB 2024 idol immersion report (PDF),26
Malikhedi kund,2024,Durga,post,7.01,4,5.2,BDL,BDL,BDL,BDL,MPPCB 2024 idol immersion report (PDF),26
Khatlapura ghat,2024,Ganesh,pre,8.07,4.3,6.8,0.09,0.279,0.431,0.081,MPPCB 2024 idol immersion report (PDF),69
Khatlapura ghat,2024,Ganesh,during,6.49,4,7.2,1.98,0.485,1.96,2.66,MPPCB 2024 idol immersion report (PDF),69
Khatlapura ghat,2024,Ganesh,post,7.95,4.6,6.2,0.232,1.266,1.04,0.653,MPPCB 2024 idol immersion report (PDF),69
Bairagarh (Sant Hirdaram) kund,2024,Ganesh,pre,7.27,5.2,4.2,0.095,0.02,0.356,0.054,MPPCB 2024 idol immersion report (PDF),69
Bairagarh (Sant Hirdaram) kund,2024,Ganesh,during,7.36,4.1,13.2,0.21,0.4,1.02,1.311,MPPCB 2024 idol immersion report (PDF),69
Bairagarh (Sant Hirdaram) kund,2024,Ganesh,post,7.22,4.2,14,0.238,1.77,1.219,0.796,MPPCB 2024 idol immersion report (PDF),69
Prempura ghat,2024,Ganesh,pre,8.02,4.3,3.2,0.102,0.107,1.299,0.0274,MPPCB 2024 idol immersion report (PDF),70
Prempura ghat,2024,Ganesh,during,8.55,3.9,6.8,0.206,0.171,0.756,0.444,MPPCB 2024 idol immersion report (PDF),70
Prempura ghat,2024,Ganesh,post,8.05,6.3,5.2,0.32,0.347,1.031,0.151,MPPCB 2024 idol immersion report (PDF),70
Rani Kamlapati ghat / Kamla Park kund,2024,Ganesh,pre,7.35,4.8,4.8,0.095,0.205,0.535,0.076,MPPCB 2024 idol immersion report (PDF),70
Rani Kamlapati ghat / Kamla Park kund,2024,Ganesh,during,7.31,4.3,5,0.204,0.336,0.976,1.042,MPPCB 2024 idol immersion report (PDF),70
Rani Kamlapati ghat / Kamla Park kund,2024,Ganesh,post,7.63,3.6,6.4,0.31,0.395,1.54,0.19,MPPCB 2024 idol immersion report (PDF),70
Hathaikheda dam / kund,2024,Ganesh,pre,7.93,9,7.2,0.136,BDL,0.198,0.054,MPPCB 2024 idol immersion report (PDF),71
Hathaikheda dam / kund,2024,Ganesh,during,7.29,5.3,13.2,0.313,0.537,1.023,1.499,MPPCB 2024 idol immersion report (PDF),71
Hathaikheda dam / kund,2024,Ganesh,post,7.38,11,22,0.219,0.454,2.67,0.388,MPPCB 2024 idol immersion report (PDF),71
Malikhedi kund,2024,Ganesh,pre,7.48,4.8,6.6,0.118,0.166,0.399,0.085,MPPCB 2024 idol immersion report (PDF),71
Malikhedi kund,2024,Ganesh,during,7.38,3.8,6.8,0.245,0.292,0.69,1.05,MPPCB 2024 idol immersion report (PDF),71
Malikhedi kund,2024,Ganesh,post,7.38,6.5,8.4,0.393,0.287,0.761,0.117,MPPCB 2024 idol immersion report (PDF),71
Shahpura lake ghat,2024,Ganesh,pre,7.88,7.4,5.8,0.077,BDL,0.358,0.061,MPPCB 2024 idol immersion report (PDF),72
Shahpura lake ghat,2024,Ganesh,during,7.61,6.8,10,0.164,0.282,0.612,0.752,MPPCB 2024 idol immersion report (PDF),72
Shahpura lake ghat,2024,Ganesh,post,7.92,6.3,6.8,0.359,0.413,1.323,1.638,MPPCB 2024 idol immersion report (PDF),72
Khatlapura ghat,2025,Ganesh,pre,7.34,7.3,4.4,0.03,0.031,0.082,0.138,MPPCB 2025 idol immersion report (PDF),1
Khatlapura ghat,2025,Ganesh,during,8,6,5.4,0.03,0.031,0.013,0.018,MPPCB 2025 idol immersion report (PDF),1
Khatlapura ghat,2025,Ganesh,post,7.76,6.5,5.2,0.03,0.031,0.04,0.08,MPPCB 2025 idol immersion report (PDF),1
Bairagarh (Sant Hirdaram) kund,2025,Ganesh,pre,*,,,,,,,MPPCB 2025 idol immersion report (PDF),1
Bairagarh (Sant Hirdaram) kund,2025,Ganesh,during,7.36,0,8,0.03,0.031,0.074,0.125,MPPCB 2025 idol immersion report (PDF),1
Bairagarh (Sant Hirdaram) kund,2025,Ganesh,post,**,,,,,,,MPPCB 2025 idol immersion report (PDF),1
Prempura ghat,2025,Ganesh,pre,7.41,6.5,4.8,0.03,0.031,0.03,0.133,MPPCB 2025 idol immersion report (PDF),1
Prempura ghat,2025,Ganesh,during,8.01,5.6,4.8,0.03,0.031,0.009,0.018,MPPCB 2025 idol immersion report (PDF),1
Prempura ghat,2025,Ganesh,post,7.92,6,3,0.03,0.031,0.06,0.13,MPPCB 2025 idol immersion report (PDF),1
Rani Kamlapati ghat / Kamla Park kund,2025,Ganesh,pre,7.46,6.9,3.8,0.03,0.031,0.014,0.102,MPPCB 2025 idol immersion report (PDF),2
Rani Kamlapati ghat / Kamla Park kund,2025,Ganesh,during,7.7,6.9,6.9,0.03,0.031,0.51,0.018,MPPCB 2025 idol immersion report (PDF),2
Rani Kamlapati ghat / Kamla Park kund,2025,Ganesh,post,7.62,6.2,4.8,0.03,0.031,0.009,0.018,MPPCB 2025 idol immersion report (PDF),2
Hathaikheda dam / kund,2025,Ganesh,pre,8.23,5.6,5.2,0.03,0.031,0.077,0.156,MPPCB 2025 idol immersion report (PDF),2
Hathaikheda dam / kund,2025,Ganesh,during,8.71,7,10,0.03,0.031,0.327,0.018,MPPCB 2025 idol immersion report (PDF),2
Hathaikheda dam / kund,2025,Ganesh,post,8.44,6.4,5.2,0.03,0.031,0.02,0.03,MPPCB 2025 idol immersion report (PDF),2
Malikhedi kund,2025,Ganesh,pre,*,,,,,,,MPPCB 2025 idol immersion report (PDF),2
Malikhedi kund,2025,Ganesh,during,7.53,0.6,5.8,0.03,0.031,0.022,0.018,MPPCB 2025 idol immersion report (PDF),2
Malikhedi kund,2025,Ganesh,post,**,,,,,,,MPPCB 2025 idol immersion report (PDF),2
Shahpura lake ghat,2025,Ganesh,pre,7.7,7,4.2,0.03,0.031,0.091,0.137,MPPCB 2025 idol immersion report (PDF),3
Shahpura lake ghat,2025,Ganesh,during,7.82,6,5,0.03,0.031,0.085,0.013,MPPCB 2025 idol immersion report (PDF),3
Shahpura lake ghat,2025,Ganesh,post,7.84,6.5,4.8,0.03,0.031,0.07,0.13,MPPCB 2025 idol immersion report (PDF),3
Hathaikheda dam / kund,2025,Durga,pre,8.14,8.5,6.8,0.03,0.03,0.06,0.018,MPPCB 2025 idol immersion report (PDF),37
Hathaikheda dam / kund,2025,Durga,during,8.37,8.5,8,BDL,0.21,0.17,0.28,MPPCB 2025 idol immersion report (PDF),37
Hathaikheda dam / kund,2025,Durga,post,8.44,10.8,6.4,0.03,0.03,0.06,0.018,MPPCB 2025 idol immersion report (PDF),37
Rani Kamlapati ghat / Kamla Park kund,2025,Durga,pre,7.92,2.5,6.8,0.03,0.06,0.12,0.09,MPPCB 2025 idol immersion report (PDF),37
Rani Kamlapati ghat / Kamla Park kund,2025,Durga,during,7.85,2.4,8.8,BDL,0.09,0.12,0.05,MPPCB 2025 idol immersion report (PDF),37
Rani Kamlapati ghat / Kamla Park kund,2025,Durga,post,7.38,2.6,4.8,0.03,0.06,0.12,0.09,MPPCB 2025 idol immersion report (PDF),37
Khatlapura ghat,2025,Durga,pre,8.17,7.1,4.4,0.03,0.05,0.05,0.018,MPPCB 2025 idol immersion report (PDF),37
Khatlapura ghat,2025,Durga,during,7.72,6.2,4.6,BDL,0.14,0.14,0.16,MPPCB 2025 idol immersion report (PDF),37
Khatlapura ghat,2025,Durga,post,7.81,6.6,3.1,0.03,0.05,0.05,0.018,MPPCB 2025 idol immersion report (PDF),37
Prempura ghat,2025,Durga,pre,8.25,6.6,4.4,0.03,0.09,0.17,0.16,MPPCB 2025 idol immersion report (PDF),38
Prempura ghat,2025,Durga,during,8.24,4.9,4.8,0.03,0.09,0.17,0.18,MPPCB 2025 idol immersion report (PDF),38
Prempura ghat,2025,Durga,post,8.29,8.2,3.2,0.03,0.09,0.17,0.16,MPPCB 2025 idol immersion report (PDF),38
Shahpura lake ghat,2025,Durga,pre,7.88,2.5,6.8,0.03,0.06,0.6,0.018,MPPCB 2025 idol immersion report (PDF),38
Shahpura lake ghat,2025,Durga,during,7.36,2.8,11.4,0.03,0.07,0.03,0.018,MPPCB 2025 idol immersion report (PDF),38
Shahpura lake ghat,2025,Durga,post,7.35,7.4,10.4,0.03,0.06,0.6,0.018,MPPCB 2025 idol immersion report (PDF),38"""

GHATS = {  # canonical name -> (Hindi, water body, mapping confidence)
    "Bairagarh (Sant Hirdaram) kund": ("बैरागढ़ (संत हिरदाराम) कुंड", "Upper Lake", "High"),
    "Khatlapura ghat": ("खटलापुरा घाट", "Lower Lake", "High"),
    "Prempura ghat": ("प्रेमपुरा घाट", "Upper Lake", "High"),
    "Rani Kamlapati ghat / Kamla Park kund": ("रानी कमलापति घाट / कमला पार्क कुंड", "Lower Lake", "Medium"),
    "Hathaikheda dam / kund": ("हथाईखेड़ा डैम / कुंड", "Hathaikheda dam", "High"),
    "Malikhedi kund": ("मालीखेड़ी कुंड", "Kund", "High"),
    "Shahpura lake ghat": ("शाहपुरा लेक घाट", "Shahpura Lake", "High"),
}
PHASES = ["pre", "during", "post"]
PHASE_LABEL = {"pre": "Pre-immersion", "during": "During immersion", "post": "After 1 week"}
PHASE_LABEL_HI = {"pre": "विसर्जन से पहले", "during": "विसर्जन के दौरान", "post": "एक सप्ताह बाद"}
PARAMS = {  # display name -> CSV column
    "DO": "DO (mg/l)", "BOD": "BOD (mg/l)", "pH": "pH",
    "Chromium": "Chromium (mg/l)", "Lead": "Lead (mg/l)",
    "Zinc": "Zinc (mg/l)", "Copper": "Copper (mg/l)",
}
PARAM_HI = {"DO": "घुली ऑक्सीजन", "BOD": "बीओडी (प्रदूषण भार)", "pH": "पीएच",
            "Chromium": "क्रोमियम", "Lead": "सीसा (लेड)", "Zinc": "जिंक", "Copper": "कॉपर"}
METALS = ["Chromium", "Lead", "Zinc", "Copper"]
CORE = ["DO", "BOD", "pH"]
# MPPCB's own detection limits; the 2025 reports print exactly these numbers at
# nearly every site, so a value at/below them is treated as BDL (our inference).
DETECTION_LIMIT = {"Chromium": 0.03, "Lead": 0.031, "Copper": 0.018, "Zinc": 0.009}
# CPCB Class B has no metal limits; BIS IS 10500 drinking-water values are a stand-in.
METAL_REF = {"Chromium": 0.05, "Lead": 0.01, "Zinc": 5.0, "Copper": 0.05}
WEIGHTS = {"DO": 0.30, "BOD": 0.25, "pH": 0.05, "METALS": 0.15, "IMMERSION": 0.10}  # coliform (0.15) not available
YEAR_WEIGHT = {2023: 0.5, 2024: 0.75, 2025: 1.0}
MAX_GAP_PENALTY = 10.0
CPCB_DEFAULT = {"ph_lo": 6.5, "ph_hi": 8.5, "do_min": 5.0, "bod_max": 3.0}
STATUS_ORDER = ["CRITICAL", "HIGH", "MODERATE", "LOW"]
STATUS_ICON = {"CRITICAL": "🔴 CRITICAL", "HIGH": "🟠 HIGH", "MODERATE": "🟡 MODERATE", "LOW": "🟢 LOW"}
STATUS_HI = {"CRITICAL": "गंभीर", "HIGH": "उच्च", "MODERATE": "मध्यम", "LOW": "कम"}
MISSING_TOKENS = {"", "_", "-", "--", "na", "n/a", "nan", "none", "not sampled", "*", "**"}


# --------------------------------------------------------------------------
# 2. Cleaning rules (pure functions - no Streamlit)
# --------------------------------------------------------------------------
def parse_cell(raw, param):
    """Return (status, number). status: 'value' | 'low' (BDL/ND) | 'missing'."""
    s = str(raw).strip().lower()
    if s in MISSING_TOKENS:
        return "missing", None
    if s in ("bdl", "nd") or s.startswith("<"):
        # BDL/ND on pH or DO is physically impossible -> never assume clean.
        return ("missing", None) if param in ("pH", "DO") else ("low", None)
    m = re.search(r"-?\d+(?:\.\d+)?", s.replace(",", ""))
    if not m:
        return "missing", None
    v = float(m.group(0))
    if param in DETECTION_LIMIT and v <= DETECTION_LIMIT[param] + 1e-9:
        return "low", None
    return "value", v


def load_data():
    raw = pd.read_csv(io.StringIO(DATA_CSV), dtype=str, keep_default_na=False)
    out = raw[["Ghat", "Year", "Festival", "Phase", "Report", "Page"]].copy()
    out["Year"] = out["Year"].astype(int)
    out["Page"] = out["Page"].astype(int)
    for p, col in PARAMS.items():
        parsed = [parse_cell(v, p) for v in raw[col]]
        out[p] = [n for _, n in parsed]
        out[p + "_status"] = [s for s, _ in parsed]
    out["w"] = out["Year"].map(lambda y: YEAR_WEIGHT.get(y, 0.75))
    out["Trace"] = (out["Year"].astype(str) + " " + out["Festival"] + ", " + out["Phase"] +
                    "-immersion [" + out["Report"] + " p." + out["Page"].astype(str) + "]")
    return out


# --------------------------------------------------------------------------
# 3. Scoring (same method as ghat_watch.py, limits adjustable)
# --------------------------------------------------------------------------
def _component(vals, ws, exceeds, severity):
    if not len(vals):
        return 0.0, 0.0, 0
    ex = [exceeds(v) for v in vals]
    rate = sum(w for w, e in zip(ws, ex) if e) / sum(ws)
    sev = [severity(v) for v, e in zip(vals, ex) if e]
    mean_sev = sum(sev) / len(sev) if sev else 0.0
    return rate * (0.5 + 0.5 * mean_sev), rate, sum(ex)


def score_ghat(g, lim):
    do_min, bod_max = lim["do_min"], lim["bod_max"]
    lo, hi = lim["ph_lo"], lim["ph_hi"]
    res = {}
    d = g[g["DO_status"] == "value"]
    b = g[g["BOD_status"] == "value"]
    p = g[g["pH_status"] == "value"]
    c_do, r_do, k_do = _component(list(d["DO"]), list(d["w"]), lambda v: v < do_min,
                                  lambda v: min(1.0, (do_min - v) / do_min))
    c_bod, r_bod, k_bod = _component(list(b["BOD"]), list(b["w"]), lambda v: v > bod_max,
                                     lambda v: min(1.0, (v - bod_max) / (3 * bod_max)))
    c_ph, _, k_ph = _component(list(p["pH"]), list(p["w"]), lambda v: v < lo or v > hi,
                               lambda v: min(1.0, (lo - v if v < lo else v - hi) / 1.5))
    # heavy metals: detection rate + exceedance of reference (readings that are values or BDL/ND)
    det, ex, det_w, ex_w, n_det = [], [], [], [], 0
    for m in METALS:
        valid = g[g[m + "_status"].isin(["value", "low"])]
        for _, r in valid.iterrows():
            is_val = r[m + "_status"] == "value"
            det.append(1.0 if is_val else 0.0)
            det_w.append(r["w"])
            n_det += int(is_val)
            if is_val:
                ex.append(1.0 if r[m] > METAL_REF[m] else 0.0)
                ex_w.append(r["w"])
    det_rate = sum(a * w for a, w in zip(det, det_w)) / sum(det_w) if det_w else 0.0
    ex_rate = sum(a * w for a, w in zip(ex, ex_w)) / sum(ex_w) if ex_w else 0.0
    c_met = 0.5 * det_rate + 0.5 * ex_rate
    # worsening during/after immersion vs before
    parts = []
    for par, fn in (("DO", lambda a, z: max(0, a - z) / do_min), ("BOD", lambda a, z: max(0, z - a) / bod_max)):
        sub = g[g[par + "_status"] == "value"]
        pre = sub[sub["Phase"] == "pre"][par]
        dp = sub[sub["Phase"].isin(["during", "post"])][par]
        if len(pre) and len(dp):
            parts.append(min(1.0, fn(pre.mean(), dp.mean())))
    c_imm = sum(parts) / len(parts) if parts else 0.0
    cells = g[[x + "_status" for x in CORE]]
    coverage = float((cells != "missing").to_numpy().mean()) if cells.size else 0.0
    base = (WEIGHTS["DO"] * c_do + WEIGHTS["BOD"] * c_bod + WEIGHTS["pH"] * c_ph +
            WEIGHTS["METALS"] * c_met + WEIGHTS["IMMERSION"] * c_imm) * 100
    score = min(100.0, base + (1 - coverage) * MAX_GAP_PENALTY)
    res.update(score=score, coverage=coverage, do_rate=r_do, bod_rate=r_bod,
               n_do=len(d), k_do=k_do, n_bod=len(b), k_bod=k_bod, n_ph=len(p), k_ph=k_ph,
               n_metal_det=n_det, n_metal_valid=len(det),
               metals_found=[m for m in METALS if (g[m + "_status"] == "value").any()],
               min_do=float(d["DO"].min()) if len(d) else None,
               max_bod=float(b["BOD"].max()) if len(b) else None,
               min_do_trace=d.loc[d["DO"].idxmin(), "Trace"] if len(d) else "",
               max_bod_trace=b.loc[b["BOD"].idxmax(), "Trace"] if len(b) else "",
               zero_do=int((d["DO"] == 0).sum()),
               imm=c_imm)
    return res


def status_of(r):
    """Transparent rule: near-anoxic water or very high score = CRITICAL."""
    if (r["min_do"] is not None and r["min_do"] <= 1.0) or r["score"] >= 60:
        return "CRITICAL"
    if r["score"] >= 45 or (r["do_rate"] >= 0.5 and r["bod_rate"] >= 0.5):
        return "HIGH"
    if r["score"] >= 25:
        return "MODERATE"
    return "LOW"


def reasons(r, lim):
    en, hi = [], []
    if r["n_do"] and r["k_do"]:
        en.append(f"Oxygen (DO) fell below {lim['do_min']:g} mg/l in {r['k_do']} of {r['n_do']} readings "
                  f"(lowest {r['min_do']:g} mg/l).")
        hi.append(f"घुली ऑक्सीजन {r['n_do']} में से {r['k_do']} जाँच में {lim['do_min']:g} mg/l से कम "
                  f"(न्यूनतम {r['min_do']:g} mg/l)।")
        if r["zero_do"]:
            en.append(f"DO reached 0 mg/l {r['zero_do']} time(s): no fish can survive.")
            hi.append(f"DO {r['zero_do']} बार शून्य रही: मछलियाँ जीवित नहीं रह सकतीं।")
    if r["n_bod"] and r["k_bod"]:
        en.append(f"BOD (pollution load) exceeded {lim['bod_max']:g} mg/l in {r['k_bod']} of {r['n_bod']} "
                  f"readings (highest {r['max_bod']:g} mg/l).")
        hi.append(f"बीओडी {r['n_bod']} में से {r['k_bod']} जाँच में {lim['bod_max']:g} mg/l से अधिक "
                  f"(सर्वाधिक {r['max_bod']:g} mg/l)।")
    if r["n_ph"] and r["k_ph"]:
        en.append(f"pH was outside {lim['ph_lo']:g}-{lim['ph_hi']:g} in {r['k_ph']} of {r['n_ph']} readings.")
        hi.append(f"पीएच {r['n_ph']} में से {r['k_ph']} जाँच में {lim['ph_lo']:g}-{lim['ph_hi']:g} के बाहर।")
    if r["metals_found"]:
        en.append("Heavy metals detected: " + ", ".join(r["metals_found"]) + " (often from idol paints).")
        hi.append("भारी धातुएँ मिलीं: " + ", ".join(r["metals_found"]) + " (अक्सर मूर्तियों के रंगों से)।")
    if r["imm"] > 0.15:
        en.append("Water gets worse during/after immersion compared with before.")
        hi.append("विसर्जन के दौरान/बाद में पानी की गुणवत्ता पहले से बिगड़ती है।")
    if r["coverage"] < 0.85:
        en.append(f"DATA GAP: only {r['coverage']:.0%} of readings exist; blanks are never treated as clean.")
        hi.append(f"डेटा की कमी: केवल {r['coverage']:.0%} रीडिंग उपलब्ध; खाली को साफ़ नहीं माना गया।")
    if not en:
        en.append("No breach of the selected limits in the selected data.")
        hi.append("चुने गए डेटा में चुनी गई सीमाओं का उल्लंघन नहीं।")
    return " ".join(en), " ".join(hi)


def rank_table(df, lim):
    rows = []
    for ghat, (hindi, body, conf) in GHATS.items():
        g = df[df["Ghat"] == ghat]
        if g.empty:
            continue
        r = score_ghat(g, lim)
        st_ = status_of(r)
        why_en, why_hi = reasons(r, lim)
        rows.append({
            "Ghat": ghat, "Ghat (Hindi)": hindi, "Water body": body, "Mapping confidence": conf,
            "Status": STATUS_ICON[st_], "Status key": st_,
            "Risk score": round(r["score"], 1),
            "Lowest DO (mg/l)": r["min_do"], "Highest BOD (mg/l)": r["max_bod"],
            "DO breaches": f"{r['k_do']}/{r['n_do']}", "BOD breaches": f"{r['k_bod']}/{r['n_bod']}",
            "Data coverage %": round(r["coverage"] * 100),
            "Why (English)": why_en, "कारण (हिंदी)": why_hi,
            "Source: lowest DO": r["min_do_trace"], "Source: highest BOD": r["max_bod_trace"],
            "Limits applied": (f"pH {lim['ph_lo']:g}-{lim['ph_hi']:g}; DO >= {lim['do_min']:g} mg/l; "
                               f"BOD <= {lim['bod_max']:g} mg/l"),
        })
    t = pd.DataFrame(rows).sort_values("Risk score", ascending=False).reset_index(drop=True)
    t.insert(0, "Rank", t.index + 1)
    return t


def breach_mask(df, lim):
    """Boolean Series: reading breaches a selected limit (only real values count)."""
    do_b = (df["DO_status"] == "value") & (df["DO"] < lim["do_min"])
    bod_b = (df["BOD_status"] == "value") & (df["BOD"] > lim["bod_max"])
    ph_b = (df["pH_status"] == "value") & ((df["pH"] < lim["ph_lo"]) | (df["pH"] > lim["ph_hi"]))
    return do_b | bod_b | ph_b


def missing_tables(df):
    """Expected ghat x year x festival tables that do not exist in the data."""
    have = set(zip(df["Ghat"], df["Year"], df["Festival"]))
    gaps = []
    for g in GHATS:
        for y in (2023, 2024, 2025):
            for f in ("Ganesh", "Durga"):
                if (g, y, f) not in have:
                    gaps.append(f"{g} - {y} {f}: no table in the MPPCB report")
    return gaps


# --------------------------------------------------------------------------
# 4. UI
# --------------------------------------------------------------------------
CSS = """
<style>
.block-container {padding-top: 1.2rem;}
.gw-banner {background: linear-gradient(90deg,#0b3d91 0%,#124a9e 100%); color:#fff; padding:18px 24px;
  border-radius:10px; border-bottom:6px solid; border-image: linear-gradient(90deg,#ff9933 33%,#ffffff 33% 66%,#138808 66%) 1;}
.gw-banner h1 {color:#fff; margin:0; font-size:1.7rem;}
.gw-banner p {color:#dbe7ff; margin:4px 0 0 0; font-size:0.95rem;}
section[data-testid="stSidebar"] {background: linear-gradient(180deg,#0b2a5b 0%,#123f7a 100%);}
section[data-testid="stSidebar"] * {color:#f0f6ff !important;}
section[data-testid="stSidebar"] .stSlider [data-baseweb="slider"] div {color:#f0f6ff !important;}
div[data-testid="stMetric"] {background:#ffffff; border:1px solid #d9e2ec; border-left:6px solid #0b3d91;
  padding:12px 16px; border-radius:8px; box-shadow:0 1px 3px rgba(16,42,67,.08);}
div[data-testid="stMetric"] * {color:#102a43 !important;}
.gw-note {font-size:0.85rem; color:#52667a;}
</style>
"""


def main():
    import altair as alt

    st.set_page_config(page_title="Visarjan Ghat Watch - Bhopal", page_icon="💧", layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(
        "<div class='gw-banner'><h1>💧 Visarjan Ghat Watch - Bhopal Water Quality Portal</h1>"
        "<p>For BMC and MP Pollution Control Board officers planning Durga Visarjan, 20 October 2026 &nbsp;|&nbsp; "
        "विसर्जन घाट वॉच - भोपाल जल गुणवत्ता पोर्टल</p></div>", unsafe_allow_html=True)
    st.write("")

    df_all = st.cache_data(load_data)()

    # ---- Sidebar filters -------------------------------------------------
    sb = st.sidebar
    sb.markdown("## 🎛️ Filters")
    sb.caption("फ़िल्टर - सीमाएँ बदलने पर रैंकिंग अपने आप बदलती है")
    sb.markdown("**CPCB Class B limits (outdoor bathing)**")
    sb.caption("CPCB क्लास B सीमाएँ (बाहरी स्नान)")
    ph_lo, ph_hi = sb.slider("pH range / पीएच सीमा", 4.0, 10.0, (CPCB_DEFAULT["ph_lo"], CPCB_DEFAULT["ph_hi"]), 0.1)
    do_min = sb.slider("Minimum DO, mg/l / न्यूनतम घुली ऑक्सीजन", 0.0, 10.0, CPCB_DEFAULT["do_min"], 0.5)
    bod_max = sb.slider("Maximum BOD, mg/l / अधिकतम बीओडी", 1.0, 15.0, CPCB_DEFAULT["bod_max"], 0.5)
    lim = {"ph_lo": ph_lo, "ph_hi": ph_hi, "do_min": do_min, "bod_max": bod_max}
    if lim != CPCB_DEFAULT:
        sb.warning("Limits differ from CPCB Class B (pH 6.5-8.5, DO >= 5, BOD <= 3).")
    sb.markdown("---")
    sb.markdown("**Data selection / डेटा चयन**")
    festivals = sb.multiselect("Festival / त्योहार", ["Durga", "Ganesh"], default=["Durga", "Ganesh"])
    years = sb.multiselect("Year / वर्ष", [2023, 2024, 2025], default=[2023, 2024, 2025])
    status_pick = sb.multiselect("Show status / स्थिति", STATUS_ORDER, default=STATUS_ORDER)
    ghat_pick = sb.multiselect("Ghats / घाट", list(GHATS), default=list(GHATS))
    sb.markdown("---")
    sb.caption("Static MPPCB data 2023-2025 (extracted from the idol-immersion reports). "
               "Not a live sensor feed. / स्थिर MPPCB डेटा, लाइव सेंसर नहीं।")

    df = df_all[df_all["Festival"].isin(festivals) & df_all["Year"].isin(years) & df_all["Ghat"].isin(ghat_pick)]
    if df.empty:
        st.warning("No data for this selection. Choose at least one festival, year and ghat. "
                   "इस चयन के लिए डेटा नहीं है।")
        st.stop()

    table = rank_table(df, lim)
    shown = table[table["Status key"].isin(status_pick)].reset_index(drop=True)
    shown["Rank"] = shown.index + 1

    # ---- Metric cards ----------------------------------------------------
    n_crit = int((table["Status key"] == "CRITICAL").sum())
    avg_do = df.loc[df["DO_status"] == "value", "DO"].mean()
    warnings_n = int(breach_mask(df, lim).sum())
    gaps_n = int((table["Data coverage %"] < 85).sum())
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Critical ghats", f"{n_crit} of {len(table)}", help="Near-anoxic water (DO <= 1 mg/l) or risk score >= 60")
    c1.caption("गंभीर घाट")
    c2.metric("Average DO (mg/l)", f"{avg_do:.1f}", delta=f"{avg_do - do_min:+.1f} vs limit",
              delta_color="normal", help="Mean of all valid DO readings in the selection")
    c2.caption("औसत घुली ऑक्सीजन")
    c3.metric("Active warnings", f"{warnings_n}", help="Readings that breach the limits set in the sidebar")
    c3.caption("सक्रिय चेतावनियाँ (सीमा पार रीडिंग)")
    c4.metric("Ghats with data gaps", f"{gaps_n}", help="Less than 85% of pH/DO/BOD cells available")
    c4.caption("डेटा-कमी वाले घाट")

    crit_names = table.loc[table["Status key"] == "CRITICAL", "Ghat"].tolist()
    if crit_names:
        st.error("**CRITICAL:** " + "; ".join(crit_names) + ". Plan alternative arrangements and repeat testing "
                 "before immersion. / गंभीर: विसर्जन से पहले वैकल्पिक व्यवस्था और दोबारा जाँच करें।")
    if gaps_n:
        st.warning(f"{gaps_n} ghat(s) are scored on incomplete data. Blank cells are never treated as clean. "
                   "कुछ घाटों का आकलन अधूरे डेटा पर है।")

    tab1, tab2, tab3, tab4 = st.tabs(["📋 Ranking & export", "📉 Phase trends", "📅 Year trends 2023-2025",
                                      "🗂️ Data & method"])

    # ---- Tab 1: ranking + export ----------------------------------------
    with tab1:
        st.subheader("Ghat risk ranking")
        st.caption("घाट जोखिम रैंकिंग - सीमा या चयन बदलने पर स्वतः पुनः क्रमबद्ध")
        cols = ["Rank", "Ghat", "Water body", "Status", "Risk score", "Lowest DO (mg/l)", "Highest BOD (mg/l)",
                "DO breaches", "BOD breaches", "Data coverage %", "Why (English)", "कारण (हिंदी)"]
        st.dataframe(shown[cols], use_container_width=True, hide_index=True, column_config={
            "Risk score": st.column_config.ProgressColumn("Risk score", min_value=0, max_value=100, format="%.0f"),
            "Why (English)": st.column_config.TextColumn(width="large"),
            "कारण (हिंदी)": st.column_config.TextColumn(width="large"),
        })
        st.markdown("<p class='gw-note'>Risk score is a relative planning priority (0-100), not a legal finding. "
                    "Coliform is not scored: the ghat-level reports contain no coliform results. "
                    "Status rule: CRITICAL = DO &lt;= 1 mg/l at any time or score &gt;= 60; HIGH = score &gt;= 45 or "
                    "both DO and BOD breached in at least half of readings; MODERATE = score &gt;= 25.</p>",
                    unsafe_allow_html=True)
        export = shown.drop(columns=["Status key"])
        export.insert(1, "Status (plain)", shown["Status key"])
        st.download_button("⬇️ Download report (CSV) / रिपोर्ट डाउनलोड करें",
                           data=export.to_csv(index=False).encode("utf-8-sig"),
                           file_name="bmc_ghat_emergency_report.csv", mime="text/csv", type="primary")
        with st.expander("Source traces (report and page for the worst readings) / स्रोत"):
            st.dataframe(shown[["Rank", "Ghat", "Source: lowest DO", "Source: highest BOD"]],
                         use_container_width=True, hide_index=True)

    # ---- Tab 2: phase trends --------------------------------------------
    with tab2:
        st.subheader("How water quality changes around immersion")
        st.caption("विसर्जन से पहले, दौरान और एक सप्ताह बाद जल गुणवत्ता में बदलाव")
        a, b = st.columns([1, 3])
        param = a.selectbox("Parameter / पैरामीटर", list(PARAMS), index=1,
                            format_func=lambda k: f"{k} ({PARAM_HI[k]})")
        default_g = table["Ghat"].head(3).tolist()
        pick = b.multiselect("Compare ghats / घाट चुनें", table["Ghat"].tolist(), default=default_g)
        d2 = df[(df["Ghat"].isin(pick)) & (df[param + "_status"] == "value")]
        if d2.empty:
            st.info("No detected values for this parameter/selection (BDL/ND or missing).")
        else:
            agg = d2.groupby(["Ghat", "Phase"], as_index=False)[param].mean()
            agg["Phase label"] = agg["Phase"].map(PHASE_LABEL)
            order = [PHASE_LABEL[p] for p in PHASES]
            line = alt.Chart(agg).mark_line(point=alt.OverlayMarkDef(size=90)).encode(
                x=alt.X("Phase label:N", sort=order, title=None),
                y=alt.Y(f"{param}:Q", title=PARAMS[param]),
                color=alt.Color("Ghat:N", legend=alt.Legend(orient="bottom")),
                tooltip=["Ghat", "Phase label", alt.Tooltip(f"{param}:Q", format=".2f")])
            layers = [line]
            rules = {"DO": [do_min], "BOD": [bod_max], "pH": [ph_lo, ph_hi]}.get(param, [])
            if rules:
                layers.append(alt.Chart(pd.DataFrame({"y": rules})).mark_rule(
                    color="#c92a2a", strokeDash=[6, 4]).encode(y="y:Q"))
            st.altair_chart(alt.layer(*layers).properties(height=380), use_container_width=True)
            st.caption("Average over the selected years/festivals; red dashed line = selected limit. "
                       "चयनित वर्षों/त्योहारों का औसत; लाल रेखा = चयनित सीमा।")
            piv = agg.pivot(index="Ghat", columns="Phase label", values=param)[
                [c for c in order if c in agg["Phase label"].unique()]].round(2)
            st.dataframe(piv, use_container_width=True)

    # ---- Tab 3: year trends ---------------------------------------------
    with tab3:
        st.subheader("Historical trend, 2023-2025")
        st.caption("ऐतिहासिक रुझान 2023-2025 (केवल त्योहार फ़िल्टर लागू; वर्ष फ़िल्टर नहीं)")
        a, b, c = st.columns(3)
        param3 = a.selectbox("Parameter / पैरामीटर ", list(PARAMS), index=0, key="p3",
                             format_func=lambda k: f"{k} ({PARAM_HI[k]})")
        phase3 = b.selectbox("Phase / चरण", PHASES, index=1, format_func=lambda k: f"{PHASE_LABEL[k]} ({PHASE_LABEL_HI[k]})")
        pick3 = c.multiselect("Ghats / घाट ", list(GHATS), default=table["Ghat"].head(3).tolist(), key="g3")
        d3 = df_all[(df_all["Festival"].isin(festivals)) & (df_all["Phase"] == phase3) &
                    (df_all["Ghat"].isin(pick3)) & (df_all[param3 + "_status"] == "value")]
        if d3.empty:
            st.info("No detected values for this selection.")
        else:
            agg3 = d3.groupby(["Ghat", "Year"], as_index=False)[param3].mean()
            ch = alt.Chart(agg3).mark_line(point=alt.OverlayMarkDef(size=90)).encode(
                x=alt.X("Year:O", title=None), y=alt.Y(f"{param3}:Q", title=PARAMS[param3]),
                color=alt.Color("Ghat:N", legend=alt.Legend(orient="bottom")),
                tooltip=["Ghat", "Year", alt.Tooltip(f"{param3}:Q", format=".2f")])
            rules3 = {"DO": [do_min], "BOD": [bod_max], "pH": [ph_lo, ph_hi]}.get(param3, [])
            layers3 = [ch]
            if rules3:
                layers3.append(alt.Chart(pd.DataFrame({"y": rules3})).mark_rule(
                    color="#c92a2a", strokeDash=[6, 4]).encode(y="y:Q"))
            st.altair_chart(alt.layer(*layers3).properties(height=380), use_container_width=True)
            bar = alt.Chart(agg3).mark_bar().encode(
                x=alt.X("Year:O", title=None), y=alt.Y(f"{param3}:Q", title=PARAMS[param3]),
                color="Ghat:N", xOffset="Ghat:N", tooltip=["Ghat", "Year", alt.Tooltip(f"{param3}:Q", format=".2f")])
            st.altair_chart(bar.properties(height=300), use_container_width=True)
            st.caption("Years with no table or no detected value for a ghat are simply absent. "
                       "जिन वर्षों में तालिका या मान नहीं है, वे नहीं दिखते।")

    # ---- Tab 4: data & method -------------------------------------------
    with tab4:
        st.subheader("Data, gaps and method")
        st.caption("डेटा, कमियाँ और विधि")
        gaps = missing_tables(df_all)
        if gaps:
            st.warning("**Tables absent from the MPPCB reports (not treated as clean):**\n\n" +
                       "\n".join(f"- {g}" for g in gaps))
        miss = df.groupby("Ghat")[[c + "_status" for c in CORE]].agg(lambda s: int((s == "missing").sum()))
        miss.columns = [f"{c} cells missing" for c in CORE]
        st.markdown("**Missing cells in the current selection** (`*`, `**`, `_`, `-`, blank, or BDL/ND on pH/DO)")
        st.dataframe(miss, use_container_width=True)
        st.markdown("**Readings in the current selection (with source page)**")
        raw_cols = ["Ghat", "Year", "Festival", "Phase", "pH", "DO", "BOD", "Chromium", "Lead", "Zinc", "Copper",
                    "Report", "Page"]
        st.dataframe(df[raw_cols].reset_index(drop=True), use_container_width=True, hide_index=True)
        st.download_button("⬇️ Download readings (CSV)", df[raw_cols].to_csv(index=False).encode("utf-8-sig"),
                           file_name="bhopal_ghat_readings_selection.csv", mime="text/csv")
        with st.expander("Method and data rules / विधि और नियम", expanded=False):
            st.markdown(
                "- **Limits (CPCB Class B):** pH 6.5-8.5, DO >= 5 mg/l, BOD <= 3 mg/l (adjustable in the sidebar).\n"
                "- **Missing:** blank, `not sampled`, `_`, `-`, `NA`, `*`, `**` are missing and never counted as clean.\n"
                "- **BDL / ND:** very low and compliant, but not zero. BDL/ND on pH or DO is impossible, so it is treated as missing.\n"
                "- **Metals:** Chromium, Lead, Zinc, Copper. Values at or below MPPCB's detection limits "
                "(0.03, 0.031, 0.009, 0.018 mg/l) are treated as BDL. CPCB Class B has no metal limits, so BIS "
                "drinking-water values are used as a stand-in reference.\n"
                "- **Score weights:** DO 30%, BOD 25%, heavy metals 15%, worsening during/after immersion 10%, "
                "pH 5%. Coliform (15%) is not available at ghat level so it is not scored. Newer years weigh more "
                "(2025 = 1.0, 2024 = 0.75, 2023 = 0.5). Missing data adds up to 10 points.\n"
                "- **Rani Kamlapati ghat** is 'Kamla Park kund' in Ganesh tables and 'Lower Lake ghat' in Durga tables "
                "(medium-confidence match).")


if __name__ == "__main__":
    main()
