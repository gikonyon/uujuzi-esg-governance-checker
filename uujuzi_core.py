"""
Uujuzi core — shared logic for the ESG & Governance Assurance Checker.
Kept separate from streamlit_app.py so the app file stays readable.

Contains:
  - Reference data (standards, tiers, verdicts)
  - Session state shape
  - PDF / TXT ingestion
  - Claim extraction
  - Claim verifiability classifier
  - Standards matching
  - Geocoding (OpenStreetMap / Nominatim)
  - Global Forest Watch query
  - Trend maths + verdict logic
"""

import io
import json
import math
import re
from datetime import datetime

import numpy as np
import pandas as pd
import requests

# ============================================================
# REFERENCE DATA
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
# SESSION STATE SHAPE
# ============================================================
def new_assessment(org, sector, year):
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

def add_ledger(assessment, module, item, verdict, tier, source, synthetic=False):
    assessment["evidence_ledger"].append({
        "module": module, "item": item, "verdict": verdict, "tier": tier,
        "source": source, "synthetic": synthetic,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    })

# ============================================================
# PDF / TXT INGESTION
# ============================================================
def extract_pdf_text(file_bytes, max_pages=60):
    """Extract text and tables from a PDF. Never fabricates content."""
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

# ============================================================
# VERIFIABILITY CLASSIFIER
# ============================================================
def classify_claim_verifiability(claim_text):
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
# STANDARDS MATCHING
# ============================================================
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

# ============================================================
# GEOCODING
# ============================================================
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "UujuziESGAssurance/1.0 (prototype)"

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
# GLOBAL FOREST WATCH
# ============================================================
def circle_geojson(lat, lon, radius_km, n=32):
    dlat = radius_km / 111.0
    coslat = math.cos(math.radians(lat))
    dlon = radius_km / (111.0 * coslat) if coslat != 0 else radius_km / 111.0
    coords = []
    for i in range(n + 1):
        th = 2 * math.pi * i / n
        coords.append([lon + dlon * math.cos(th), lat + dlat * math.sin(th)])
    return {"type": "Polygon", "coordinates": [coords]}

def gfw_tree_cover_loss(lat, lon, radius_km, start_year, end_year):
    """Best-effort GFW query. Returns DataFrame(year, loss_ha) or None."""
    try:
        geom = circle_geojson(lat, lon, radius_km)
        url = "https://data-api.globalforestwatch.org/dataset/umd_tree_cover_loss/latest/query"
        headers = {"Content-Type": "application/json"}
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
            f"Archive trend is {observed} (slope {slope:+.4f}/yr, R2={r2:.2f}), "
            "consistent with the reported direction."
        )
    if claim_direction == observed:
        return "Partially corroborated", "Tier 3", (
            f"Direction matches ({observed}) but the fit is weak (R2={r2:.2f})."
        )
    return "Contradicted", "Tier 4", (
        f"Archive trend is {observed} (slope {slope:+.4f}/yr), "
        f"opposite to the reported {claim_direction}."
    )

def circle_polygon(la, lo, r_km, n=48):
    dlat = r_km / 111.0
    coslat = math.cos(math.radians(la)) if la else 1
    dlon = r_km / (111.0 * coslat) if coslat else r_km / 111.0
    th = np.linspace(0, 2 * math.pi, n)
    return (la + dlat * np.sin(th)).tolist(), (lo + dlon * np.cos(th)).tolist()

def assign_governance_tier(sources):
    if not sources:
        return "Tier 4", "No sources recorded."
    independent = [s for s in sources if s.get("independent")]
    has_inst = any(s.get("type") == "institutional" for s in independent)
    if len(independent) >= 2 and has_inst:
        return "Tier 1", "Multiple independent sources including an institutional source."
    if len(independent) >= 2:
        return "Tier 2", "Two or more independent sources."
    if len(independent) == 1:
        return "Tier 3", "Single independent source."
    return "Tier 4", "Only self-reported / non-independent sources."
