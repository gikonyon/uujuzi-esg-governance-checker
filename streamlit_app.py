"""
Uujuzi ESG & Governance Assurance Checker
=========================================
Working prototype with:
  - PDF / TXT report ingestion
  - Claim extraction + Claim Verifiability Map
  - Real GIS verification via Global Forest Watch
  - Governance corroboration tiering
  - Evidence ledger + assurance result

Principle: never present a reported claim as a verified outcome.
Every synthetic figure is labelled. Real integrations marked TODO_LIVE.
"""

import io
import json
import math
import re
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="Uujuzi ESG & Governance Assurance",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .main-header {font-size: 2.2rem; font-weight: 700; margin-bottom: 0.2rem;}
    .sub-header  {font-size: 1.05rem; color: #666; margin-bottom: 1.2rem;}
    .verdict-card {padding: 1rem 1.2rem; border-radius: 10px;
                   border-left: 6px solid #888; background: #fafafa; margin: 0.6rem 0;}
    .verdict-corroborated  {border-left-color:#1a7f37; background:#f2fbf3;}
    .verdict-partial       {border-left-color:#bf8700; background:#fffaf0;}
    .verdict-contradicted  {border-left-color:#cf222e; background:#fff5f5;}
    .verdict-unverifiable  {border-left-color:#57606a; background:#f6f8fa;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# STATIC REFERENCE DATA
# ============================================================
STANDARDS = {
    "IFRS S1":   {"description": "Sustainability-related Financial Disclosures",
                  "keywords": ["governance", "strategy", "risk", "material", "sustainability", "financial"],
                  "areas": ["Governance", "Strategy", "Risk", "Metrics"]},
    "IFRS S2":   {"description": "Climate-related Disclosures",
                  "keywords": ["climate", "carbon", "emission", "ghg", "net zero", "scope"],
                  "areas": ["Climate Governance", "Climate Risks", "Metrics"]},
    "ISO 14001": {"description": "Environmental Management Systems",
                  "keywords": ["environment", "water", "air", "waste", "pollution", "tree", "forest", "emission"],
                  "areas": ["Env Management", "Compliance", "Objectives", "Monitoring"]},
    "ISO 26000": {"description": "Social Responsibility Guidance",
                  "keywords": ["community", "social", "human rights", "labour", "stakeholder", "employment"],
                  "areas": ["Governance", "Human Rights", "Community", "Environment"]},
    "ISO 45001": {"description": "Occupational Health & Safety",
                  "keywords": ["safety", "worker", "occupational", "incident", "injury"],
                  "areas": ["Worker Safety", "Risk", "Incidents", "Performance"]},
    "UN SDGs":   {"description": "UN Sustainable Development Goals",
                  "keywords": ["poverty", "health", "water", "energy", "jobs",
                               "infrastructure", "climate", "forest", "community"],
                  "areas": ["Climate", "Water", "Jobs", "Communities"]},
    "UN Global Compact": {"description": "Principles for Responsible Business",
                          "keywords": ["human rights", "labour", "environment",
                                       "corruption", "governance"],
                          "areas": ["Human Rights", "Labour", "Environment", "Anti-Corruption"]},
}

EVIDENCE_TIERS = {
    "Tier 1": "Multiple independent sources including an institutional source.",
    "Tier 2": "Two or more reasonably independent credible sources.",
    "Tier 3": "Single-source reporting — requires additional corroboration.",
    "Tier 4": "Unverifiable — insufficient evidence to establish the claim.",
}

VERDICTS = {
    "Corroborated":           {"css": "verdict-corroborated", "score": 1.00},
    "Partially corroborated": {"css": "verdict-partial",      "score": 0.60},
    "Requires evidence":      {"css": "verdict-partial",      "score": 0.35},
    "Contradicted":           {"css": "verdict-contradicted", "score": 0.00},
    "Unverifiable":           {"css": "verdict-unverifiable", "score": 0.20},
    "Not assessed":           {"css": "verdict-unverifiable", "score": 0.00},
}

AREA_TO_STANDARD_HINTS = {
    "Environment": ["ISO 14001", "UN SDGs", "IFRS S2"],
    "Climate":     ["IFRS S2", "UN SDGs"],
    "Community":   ["ISO 26000", "UN SDGs"],
    "Governance":  ["IFRS S1", "UN Global Compact"],
    "Social":      ["ISO 26000", "UN SDGs"],
    "Safety":      ["ISO 45001"],
    "Finance":     ["IFRS S1", "UN SDGs"],
}

# ============================================================
# VERIFIABILITY CATEGORIES
# ============================================================
VERIFIABILITY_LABELS = {
    "SPATIALLY_VERIFIABLE":     "Spatially verifiable",
    "FINANCIALLY_VERIFIABLE":   "Financially verifiable",
    "DOCUMENTARILY_VERIFIABLE": "Documentarily verifiable",
    "FORWARD_LOOKING_TARGET":   "Forward-looking target",
    "UNVERIFIABLE":             "Unverifiable as stated",
}

VERIFIABILITY_EXPLANATIONS = {
    "SPATIALLY_VERIFIABLE":     "Cross-checkable with public satellite / archive data if an AOI is supplied.",
    "FINANCIALLY_VERIFIABLE":   "Verifiable from the client's audited financial records, not from GIS.",
    "DOCUMENTARILY_VERIFIABLE": "Verifiable from the client's internal records (HR, procurement, board minutes).",
    "FORWARD_LOOKING_TARGET":   "A target or intention, not a realised outcome. Assessed on consistency, not verified.",
    "UNVERIFIABLE":             "Contains no measurable, directional, time-bounded assertion. Requires restatement.",
}

# ============================================================
# SESSION STATE
# ============================================================
def _new_assessment(org, sector, year):
    return {
        "meta": {"organization": org, "sector": sector, "report_year": year},
        "raw_report_text": "",
        "source_filename": "",
        "parsed_tables": [],
        "claims": [],
        "standards_matches": {},
        "spatial": {},
        "governance": [],
        "evidence_ledger": [],
    }

if "assessment" not in st.session_state:
    st.session_state["assessment"] = _new_assessment("Demo Organization", "Agriculture", 2026)

def A():
    return st.session_state["assessment"]

def add_ledger(module, item, verdict, tier, source, synthetic=False):
    A()["evidence_ledger"].append({
        "module": module, "item": item, "verdict": verdict, "tier": tier,
        "source": source, "synthetic": synthetic,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    })

# ============================================================
# SIDEBAR
# ============================================================
st.sidebar.title("🌍 Uujuzi")
st.sidebar.markdown("### Assurance Workspace")

organization = st.sidebar.text_input("Organization / Project", A()["meta"]["organization"])

SECTORS = ["Agriculture", "Banking & Finance", "Energy", "Manufacturing", "Mining",
           "Telecommunications", "Infrastructure", "NGO / Development", "Government", "Other"]
sec_idx = SECTORS.index(A()["meta"]["sector"]) if A()["meta"]["sector"] in SECTORS else 0
sector = st.sidebar.selectbox("Sector", SECTORS, index=sec_idx)

YEARS = [2026, 2025, 2024, 2023, 2022]
yr_idx = YEARS.index(A()["meta"]["report_year"]) if A()["meta"]["report_year"] in YEARS else 0
report_year = st.sidebar.selectbox("ESG Report Year", YEARS, index=yr_idx)

A()["meta"]["organization"] = organization
A()["meta"]["sector"] = sector
A()["meta"]["report_year"] = report_year

st.sidebar.markdown("---")
st.sidebar.caption("Real GIS verification via Global Forest Watch tree-cover archive.")

page = st.sidebar.radio(
    "Navigate",
    ["📊 Dashboard", "📄 Report & Claims", "📚 Standards",
     "🛰️ GIS Archive Verification", "🏛️ Governance",
     "📋 Assurance Result", "🗂️ Evidence Ledger"],
)

# ============================================================
# HEADER
# ============================================================
st.markdown('<div class="main-header">🌍 Uujuzi ESG & Governance Assurance</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">From reported ESG claims to evidence-based impact validation.</div>', unsafe_allow_html=True)

# ============================================================
# DOCUMENT INGESTION — PDF / TXT
# ============================================================
@st.cache_data(ttl=3600, show_spinner=False)
def extract_pdf_text(file_bytes: bytes, max_pages: int = 60):
    """Extract text and tables from a PDF using pdfplumber.
    Never fabricates content — errors are recorded per page."""
    try:
        import pdfplumber
    except ImportError:
        return {"text": "", "tables": [], "pages_processed": 0, "pages_total": 0,
                "errors": ["pdfplumber is not installed. Add it to requirements.txt."]}

    text_chunks, tables, errors = [], [], []
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            total = len(pdf.pages)
            limit = min(total, max_pages)
            for i, page in enumerate(pdf.pages[:limit]):
                try:
                    pt = page.extract_text() or ""
                    if pt.strip():
                        text_chunks.append(f"\n===== Page {i+1} =====\n{pt}")
                    for t in (page.extract_tables() or []):
                        try:
                            df = pd.DataFrame(t)
                            if not df.empty:
                                tables.append({"page": i + 1, "table": df})
                        except Exception as e:
                            errors.append(f"Page {i+1} table parse: {e}")
                except Exception as e:
                    errors.append(f"Page {i+1}: {e}")
    except Exception as e:
        return {"text": "", "tables": [], "pages_processed": 0, "pages_total": 0,
                "errors": [f"Could not open PDF: {e}"]}

    return {"text": "\n".join(text_chunks), "tables": tables,
            "pages_processed": limit, "pages_total": total, "errors": errors}

# ============================================================
# CLAIM EXTRACTION
# ============================================================
CLAIM_PATTERNS = [
    (r"(\d[\d,]*)\s*(?:trees|seedlings)\s*(?:were\s*)?plant(?:ed)?", "Environment", "trees"),
    (r"water\s*(?:quality|clarity|turbidity)\s*(?:improved|increased|better)\s*(?:by\s*)?(\d+(?:\.\d+)?)\s*%", "Environment", "%"),
    (r"(?:air|emissions?)\s*(?:quality\s*)?(?:improved|reduced|decreased)\s*(?:by\s*)?(\d+(?:\.\d+)?)\s*%", "Climate", "%"),
    (r"(\d[\d,]*)\s*(?:jobs|employment|positions)\s*(?:created|supported|generated)", "Community", "jobs"),
    (r"(?:board|governance)\s*(?:oversight|committee|safeguards?)\s*(?:established|implemented|in place)", "Governance", "boolean"),
    (r"(\d[\d,]*)\s*employees?\b", "Social", "employees"),
    (r"(\d[\d,]*)\s*(?:mentees|students|scholarships?)", "Community", "beneficiaries"),
]

def extract_claims(text):
    if not text or not text.strip():
        return []
    claims = []
    for i, (pattern, area, unit) in enumerate(CLAIM_PATTERNS, start=1):
        for m in re.finditer(pattern, text, flags=re.IGNORECASE):
            raw = m.group(1) if m.groups() else None
            mag = None
            if raw:
                try:
                    mag = float(raw.replace(",", ""))
                except ValueError:
                    mag = None
            claims.append({
                "id": f"{area[:3].upper()}-{i:03d}-{len(claims)+1:02d}",
                "area": area, "claim": m.group(0).strip(),
                "magnitude": mag, "unit": unit,
            })
    if not claims:
        for sent in re.split(r"(?<=[.!?])\s+", text):
            if re.search(r"\d", sent) and len(sent) > 20:
                claims.append({"id": f"GEN-{len(claims)+1:03d}", "area": "Environment",
                               "claim": sent.strip(), "magnitude": None, "unit": ""})
                if len(claims) >= 8:
                    break
    return claims

def match_standards(claim_text, area):
    text = (claim_text or "").lower()
    out = []
    for name, meta in STANDARDS.items():
        hits = [k for k in meta["keywords"] if k in text]
        if hits:
            out.append({"standard": name, "why": ", ".join(hits)})
    if not out:
        for name in AREA_TO_STANDARD_HINTS.get(area, []):
            out.append({"standard": name, "why": f"area default ({area})"})
    return out

def classify_claim_verifiability(claim_text: str):
    t = (claim_text or "").lower()

    if re.search(r"\b(by\s+20\d{2}|target|intend|plan|will\s+report|aim|goal)\b", t):
        return "FORWARD_LOOKING_TARGET", "Annual milestones + external verification pathway"

    spatial_terms = [
        "tree", "trees", "forest", "deforest", "reforest", "canopy",
        "vegetation", "ndvi", "land use", "land-use",
        "water quality", "turbidity", "effluent", "river", "watershed",
        "air quality", "pm2.5", "emission", "emissions", "scope 1", "scope 2",
        "biodiversity", "habitat", "wetland", "mangrove",
    ]
    if any(term in t for term in spatial_terms):
        return "SPATIALLY_VERIFIABLE", "Area of interest (coordinates, place name, or project boundary)"

    financial_terms = [
        "kes", "usd", "$", "billion", "million", "financ", "disburse",
        "loan", "portfolio", "revenue", "procurement spend", "investment",
        "scholarship", "capital", "credit",
    ]
    if any(term in t for term in financial_terms):
        return "FINANCIALLY_VERIFIABLE", "Audited financial records / loan book / procurement ledger"

    doc_terms = [
        "employee", "employees", "employment", "jobs", "staff", "retention",
        "trained", "training", "mentee", "mentees", "women", "gender",
        "board", "governance", "managerial", "leadership", "oversight",
        "policy", "committee", "whistleblower", "diversity",
    ]
    if any(term in t for term in doc_terms):
        return "DOCUMENTARILY_VERIFIABLE", "HR records / board minutes / training registers"

    return "UNVERIFIABLE", "A measurable, time-bounded indicator"

# ============================================================
# GEOCODING (OpenStreetMap Nominatim)
# ============================================================
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "UujuziESGAssurance/1.0 (prototype)"

@st.cache_data(ttl=86400, show_spinner=False)
def geocode_place(place_name):
    if not place_name or not place_name.strip():
        return None
    try:
        r = requests.get(
            NOMINATIM_URL,
            params={"q": place_name, "format": "json", "limit": 1},
            headers={"User-Agent": USER_AGENT},
            timeout=15,
        )
        if r.status_code != 200:
            return None
        data = r.json()
        if not data:
            return None
        top = data[0]
        return {"lat": float(top["lat"]), "lon": float(top["lon"]),
                "display_name": top.get("display_name", place_name),
                "source": "Nominatim / OpenStreetMap"}
    except Exception:
        return None

# ============================================================
# GFW TREE-COVER — best-effort with manual fallback
# ============================================================
def _circle_geojson(lat, lon, radius_km, n=32):
    dlat = radius_km / 111.0
    coslat = math.cos(math.radians(lat))
    dlon = radius_km / (111.0 * coslat) if coslat != 0 else radius_km / 111.0
    coords = []
    for i in range(n + 1):
        th = 2 * math.pi * i / n
        coords.append([lon + dlon * math.cos(th), lat + dlat * math.sin(th)])
    return {"type": "Polygon", "coordinates": [coords]}

@st.cache_data(ttl=21600, show_spinner=False)
def gfw_tree_cover_loss(lat, lon, radius_km, start_year, end_year):
    """Best-effort GFW query. Returns DataFrame(year, loss_ha) or None."""
    try:
        geom = _circle_geojson(lat, lon, radius_km)
        url = "https://data-api.globalforestwatch.org/dataset/umd_tree_cover_loss/latest/query"
        headers = {"Content-Type": "application/json"}
        try:
            if "GFW_API_KEY" in st.secrets:
                headers["x-api-key"] = st.secrets["GFW_API_KEY"]
        except Exception:
            pass
        payload = {"geometry": geom, "start_year": int(start_year), "end_year": int(end_year)}
        r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=20)
        if r.status_code != 200:
            return None
        rows = r.json().get("data", [])
        if not rows:
            return None
        df = pd.DataFrame(rows)
        rename = {}
        for col in df.columns:
            cl = col.lower()
            if "year" in cl:
                rename[col] = "year"
            elif "ha" in cl and "loss" in cl:
                rename[col] = "loss_ha"
        df = df.rename(columns=rename)
        if "year" not in df.columns or "loss_ha" not in df.columns:
            return None
        return df[["year", "loss_ha"]].sort_values("year").reset_index(drop=True)
    except Exception:
        return None

# ============================================================
# TREND + VERDICT
# ============================================================
def slope_and_r2(years, values):
    x = np.asarray(list(years), dtype=float)
    y = np.asarray(list(values), dtype=float)
    mask = ~np.isnan(y)
    x, y = x[mask], y[mask]
    if len(x) < 2:
        return 0.0, 0.0
    slope, intercept = np.polyfit(x, y, 1)
    fitted = slope * x + intercept
    ss_res = float(np.sum((y - fitted) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
    return float(slope), float(r2)

def spatial_verdict(claim_direction, slope, r2, n_years):
    if n_years < 3:
        return "Unverifiable", "Tier 4", (
            f"Only {n_years} year(s) of archive data available. "
            "At least 3 are needed for a defensible trend claim."
        )
    observed = "increase" if slope > 0.001 else "decline" if slope < -0.001 else "flat"
    if claim_direction is None:
        return "Unverifiable", "Tier 4", "No directional claim supplied."
    if claim_direction == observed and r2 >= 0.5:
        return "Corroborated", "Tier 2", (
            f"Archive trend is {observed} (slope {slope:+.4f}/yr, R²={r2:.2f}), "
            "consistent with the reported direction."
        )
    if claim_direction == observed:
        return "Partially corroborated", "Tier 3", (
            f"Direction matches ({observed}) but the fit is weak (R²={r2:.2f})."
        )
    return "Contradicted", "Tier 4", (
        f"Archive trend is {observed} (slope {slope:+.4f}/yr), "
        f"opposite to the reported {claim_direction}."
    )

# ============================================================
# DASHBOARD
# ============================================================
if page == "📊 Dashboard":
    st.header("📊 ESG Assurance Dashboard")
    st.write(f"**{organization}** · {sector} · ESG report year **{report_year}**")

    ledger = A()["evidence_ledger"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Claims extracted", len(A()["claims"]))
    c2.metric("Evidence items logged", len(ledger))
    c3.metric("Standards matched", len(A()["standards_matches"]))
    c4.metric("GIS verifications run", sum(1 for e in ledger if e["module"] == "Spatial"))

    if A().get("source_filename"):
        st.caption(f"Loaded report: **{A()['source_filename']}**")

    st.markdown("---")
    st.subheader("Pipeline status")
    st.dataframe(pd.DataFrame([
        {"Stage": "Report ingested", "Done": bool(A()["raw_report_text"]), "Go to": "📄 Report & Claims"},
        {"Stage": "Claims extracted", "Done": bool(A()["claims"]), "Go to": "📄 Report & Claims"},
        {"Stage": "Standards mapped", "Done": bool(A()["standards_matches"]), "Go to": "📚 Standards"},
        {"Stage": "GIS verification run", "Done": bool(A()["spatial"]), "Go to": "🛰️ GIS Archive Verification"},
        {"Stage": "Governance evidence logged", "Done": bool(A()["governance"]), "Go to": "🏛️ Governance"},
    ]), use_container_width=True, hide_index=True)

# ============================================================
# REPORT & CLAIMS  (PDF + TXT ingestion)
# ============================================================
elif page == "📄 Report & Claims":
    st.header("📄 Report & Claims")
    st.caption(
        "Upload an ESG / SDID / sustainability report as **PDF** or **TXT**. "
        "PDF extraction happens locally in the browser session."
    )

    st.subheader("1. Upload the report")
    uploaded = st.file_uploader("Choose a PDF or TXT file", type=["pdf", "txt"])

    if uploaded is not None:
        file_bytes = uploaded.read()
        size_kb = len(file_bytes) / 1024

        if uploaded.name.lower().endswith(".pdf"):
            with st.spinner(f"Extracting text and tables from {uploaded.name}…"):
                parsed = extract_pdf_text(file_bytes, max_pages=60)

            if parsed["errors"]:
                with st.expander(f"Extraction notes ({len(parsed['errors'])})"):
                    for e in parsed["errors"]:
                        st.caption(f"• {e}")

            st.success(
                f"Parsed **{parsed['pages_processed']} of {parsed['pages_total']} pages** · "
                f"{len(parsed['text']):,} characters · {len(parsed['tables'])} tables · "
                f"{size_kb:,.0f} KB"
            )

            if parsed["pages_total"] > parsed["pages_processed"]:
                st.warning(
                    f"Only the first {parsed['pages_processed']} of {parsed['pages_total']} "
                    "pages were processed in this demo."
                )

            A()["raw_report_text"] = parsed["text"]
            A()["parsed_tables"] = parsed["tables"]
            A()["source_filename"] = uploaded.name

        else:
            try:
                text = file_bytes.decode("utf-8", errors="ignore")
                A()["raw_report_text"] = text
                A()["parsed_tables"] = []
                A()["source_filename"] = uploaded.name
                st.success(f"Loaded **{uploaded.name}** · {len(text):,} chars · {size_kb:,.0f} KB")
            except Exception as e:
                st.error(f"Could not read file: {e}")

    if A().get("raw_report_text"):
        st.markdown("---")
        st.subheader("2. Extracted content preview")
        with st.expander("First 3,000 characters of extracted text", expanded=False):
            st.text(A()["raw_report_text"][:3000])

        tables = A().get("parsed_tables", [])
        if tables:
            st.markdown(f"**Tables detected: {len(tables)}**")
            opts = [f"Page {t['page']} — {t['table'].shape[0]}×{t['table'].shape[1]}"
                    for t in tables]
            choice = st.selectbox("Preview a table", opts)
            idx = opts.index(choice)
            st.dataframe(tables[idx]["table"], use_container_width=True)

    st.markdown("---")
    st.subheader("3. Confirm text and extract claims")
    text = st.text_area(
        "Report text (editable — fix any extraction issues here)",
        value=A().get("raw_report_text", "") or (
            "In 2026 the company reported that 100,000 trees were planted at its "
            "Kakuzi estate operations between 2024 and 2026. Water quality around "
            "the project area improved by 15%. 340 jobs were created."
        ),
        height=240,
    )
    A()["raw_report_text"] = text

    if st.button("Extract claims", type="primary"):
        A()["claims"] = extract_claims(text)
        A()["standards_matches"] = {
            c["id"]: match_standards(c["claim"], c["area"]) for c in A()["claims"]
        }
        for c in A()["claims"]:
            cat, missing = classify_claim_verifiability(c["claim"])
            c["verifiability"] = cat
            c["missing_evidence"] = missing
        st.success(f"Extracted {len(A()['claims'])} claim(s).")

    if A()["claims"]:
        st.markdown("---")
        st.subheader("4. Claim Verifiability Map")
        st.caption(
            "Each claim is classified by **what kind of evidence can actually verify it**. "
            "This is what tells a client which claims will survive external scrutiny."
        )
        rows = []
        for c in A()["claims"]:
            cat = c.get("verifiability", "UNVERIFIABLE")
            rows.append({
                "ID": c["id"], "Area": c["area"], "Claim": c["claim"],
                "Category": VERIFIABILITY_LABELS[cat],
                "Missing evidence": c.get("missing_evidence", ""),
            })
        vmap = pd.DataFrame(rows)
        st.dataframe(vmap, use_container_width=True, hide_index=True)

        counts = vmap["Category"].value_counts().to_dict()
        cols = st.columns(5)
        for i, key in enumerate(VERIFIABILITY_LABELS.values()):
            cols[i].metric(key, counts.get(key, 0))

        st.markdown("**What each category means**")
        for key, label in VERIFIABILITY_LABELS.items():
            st.markdown(f"- **{label}** — {VERIFIABILITY_EXPLANATIONS[key]}")

        st.download_button(
            "Download Claim Verifiability Map (CSV)",
            vmap.to_csv(index=False).encode("utf-8"),
            file_name=f"uujuzi_claims_{datetime.now():%Y%m%d_%H%M}.csv",
            mime="text/csv",
        )

# ============================================================
# STANDARDS
# ============================================================
elif page == "📚 Standards":
    st.header("📚 Standards Cross-Reference")
    if not A()["claims"]:
        st.warning("Extract claims first on the Report & Claims tab.")
    else:
        for c in A()["claims"]:
            with st.expander(f"{c['id']} — {c['claim'][:90]}"):
                matches = A()["standards_matches"].get(c["id"], [])
                if not matches:
                    st.write("No standards matched.")
                    continue
                st.dataframe(pd.DataFrame([
                    {"Standard": m["standard"],
                     "Description": STANDARDS[m["standard"]]["description"],
                     "Matched on": m["why"]}
                    for m in matches
                ]), use_container_width=True, hide_index=True)

# ============================================================
# GIS ARCHIVE VERIFICATION
# ============================================================
elif page == "🛰️ GIS Archive Verification":
    st.header("🛰️ GIS Archive Verification")
    st.caption(
        "Verifies a spatially-verifiable claim against public tree-cover archive data "
        "for the reporting period."
    )

    spatial_claims = [c for c in A().get("claims", [])
                      if c.get("verifiability") == "SPATIALLY_VERIFIABLE"]
    if not spatial_claims:
        st.warning(
            "No spatially-verifiable claims have been extracted yet. "
            "Load a report on the 📄 Report & Claims tab."
        )

    st.subheader("1. Reported claim")
    default_claim = spatial_claims[0]["claim"] if spatial_claims else "100,000 trees planted 2024–2026"
    claim_text = st.text_input("Claim", default_claim)

    c1, c2, c3 = st.columns(3)
    baseline_year = c1.selectbox("Baseline year", [2023, 2024, 2025], index=1)
    reporting_year = c2.selectbox("Reporting year", [2026, 2025], index=0)
    claim_direction = c3.selectbox("Claimed direction", ["increase", "decline", "unspecified"])

    st.subheader("2. Location of the claim")
    loc_method = st.radio(
        "Specify location",
        ["Type a place name (auto-geocode)", "Enter coordinates manually"],
        horizontal=True,
    )

    lat = lon = None
    place_label = ""
    geocode_ok = False

    if loc_method.startswith("Type"):
        place_name = st.text_input("Place name", "Kakuzi estate, Murang'a County, Kenya")
        if st.button("Geocode location"):
            with st.spinner("Geocoding via OpenStreetMap…"):
                g = geocode_place(place_name)
            if g:
                st.session_state["geo"] = g
                st.success(f"Resolved to: {g['display_name']}")
            else:
                st.warning(
                    "Geocoding failed. Enter coordinates manually below. "
                    "The app will not fake a location."
                )
        g = st.session_state.get("geo")
        if g:
            lat, lon = g["lat"], g["lon"]
            place_label = g["display_name"]
            geocode_ok = True

    if not geocode_ok:
        c1, c2 = st.columns(2)
        lat = c1.number_input("Latitude", value=-0.850000, format="%.6f")
        lon = c2.number_input("Longitude", value=37.150000, format="%.6f")
        place_label = place_label or f"{lat:.4f}, {lon:.4f}"

    radius_km = st.slider("AOI radius (km)", 1.0, 25.0, 5.0, step=1.0)

    def circle_polygon(la, lo, r_km, n=48):
        dlat = r_km / 111.0
        coslat = math.cos(math.radians(la)) if la else 1
        dlon = r_km / (111.0 * coslat) if coslat else r_km / 111.0
        th = np.linspace(0, 2 * math.pi, n)
        return (la + dlat * np.sin(th)).tolist(), (lo + dlon * np.cos(th)).tolist()

    plat, plon = circle_polygon(lat, lon, radius_km)
    fmap = go.Figure()
    fmap.add_trace(go.Scattermapbox(
        lat=plat, lon=plon, mode="lines", fill="toself",
        line=dict(color="#cf222e", width=2), fillcolor="rgba(207,34,46,0.15)",
        name="AOI",
    ))
    fmap.add_trace(go.Scattermapbox(
        lat=[lat], lon=[lon], mode="markers",
        marker=dict(size=10, color="#cf222e"), name="Centre",
    ))
    fmap.update_layout(
        mapbox=dict(style="open-street-map",
                    center=dict(lat=lat, lon=lon),
                    zoom=int(max(4, 11 -
