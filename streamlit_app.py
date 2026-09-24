import json
import math
import time
import re
from datetime import datetime
from urllib.parse import quote

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

# ============================================================
# STYLE
# ============================================================
st.markdown(
    """
    <style>
    .main-header {font-size: 2.2rem; font-weight: 700; margin-bottom: 0.2rem;}
    .sub-header  {font-size: 1.05rem; color: #666; margin-bottom: 1.2rem;}
    .synthetic-badge {
        display: inline-block; padding: 1px 8px; border-radius: 10px;
        background: #fff3cd; color: #7a5c00; font-size: 0.72rem;
        font-weight: 600; letter-spacing: 0.03em; margin-left: 6px;
    }
    .live-badge {
        display: inline-block; padding: 1px 8px; border-radius: 10px;
        background: #d1f2d1; color: #0a4d0a; font-size: 0.72rem;
        font-weight: 600; letter-spacing: 0.03em; margin-left: 6px;
    }
    .verdict-card {
        padding: 1rem 1.2rem; border-radius: 10px; border-left: 6px solid #888;
        background: #fafafa; margin: 0.6rem 0;
    }
    .verdict-corroborated  {border-left-color:#1a7f37; background:#f2fbf3;}
    .verdict-partial       {border-left-color:#bf8700; background:#fffaf0;}
    .verdict-contradicted  {border-left-color:#cf222e; background:#fff5f5;}
    .verdict-unverifiable  {border-left-color:#57606a; background:#f6f8fa;}
    .small-note {font-size: 0.82rem; color: #666;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# STATIC REFERENCE DATA
# ============================================================
STANDARDS = {
    "IFRS S1": {"description": "General Requirements for Sustainability-related Financial Disclosures",
                "keywords": ["governance", "strategy", "risk", "material", "sustainability", "financial"],
                "areas": ["Governance", "Strategy", "Risk Management", "Metrics & Targets"]},
    "IFRS S2": {"description": "Climate-related Disclosures",
                "keywords": ["climate", "carbon", "emission", "ghg", "net zero", "scope 1", "scope 2", "scope 3"],
                "areas": ["Climate Governance", "Climate Risks", "Climate Opportunities", "Metrics & Targets"]},
    "ISO 14001": {"description": "Environmental Management Systems",
                  "keywords": ["environment", "water", "air", "waste", "pollution", "tree", "forest", "emission", "effluent"],
                  "areas": ["Environmental Management", "Compliance", "Objectives", "Monitoring"]},
    "ISO 26000": {"description": "Social Responsibility Guidance",
                  "keywords": ["community", "social", "human rights", "labour", "stakeholder", "employment"],
                  "areas": ["Governance", "Human Rights", "Community", "Environment"]},
    "ISO 45001": {"description": "Occupational Health & Safety",
                  "keywords": ["safety", "worker", "occupational", "incident", "injury", "health"],
                  "areas": ["Worker Safety", "Risk Management", "Incident Management", "Performance"]},
    "UN SDGs": {"description": "UN Sustainable Development Goals",
                "keywords": ["poverty", "hunger", "health", "education", "water", "energy", "jobs", "infrastructure", "climate", "forest", "community"],
                "areas": ["Climate", "Water", "Environment", "Poverty", "Jobs", "Infrastructure", "Communities"]},
    "UN Global Compact": {"description": "Principles for Responsible Business",
                          "keywords": ["human rights", "labour", "environment", "corruption", "bribery", "governance"],
                          "areas": ["Human Rights", "Labour", "Environment", "Anti-Corruption"]},
}

EVIDENCE_TIERS = {
    "Tier 1": "Institutional corroboration — multiple independent sources including an institutional source.",
    "Tier 2": "Independent reporting — two or more reasonably independent credible sources.",
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

# ============================================================
# SHARED ASSESSMENT STATE
# ============================================================
def _new_assessment(org, sector, report_year):
    return {
        "meta": {"organization": org, "sector": sector, "report_year": report_year,
                 "created_at": datetime.now().isoformat(timespec="seconds")},
        "raw_report_text": "",
        "claims": [],
        "standards_matches": {},
        "environmental": {},
        "spatial": {},
        "governance": [],
        "community": [],
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

SECTOR_OPTIONS = ["Agriculture", "Banking & Finance", "Energy", "Manufacturing", "Mining",
                  "Telecommunications", "Infrastructure", "NGO / Development", "Government", "Other"]
sector_index = SECTOR_OPTIONS.index(A()["meta"]["sector"]) if A()["meta"]["sector"] in SECTOR_OPTIONS else 0
sector = st.sidebar.selectbox("Sector", SECTOR_OPTIONS, index=sector_index)

report_year = st.sidebar.selectbox(
    "ESG Report Year",
    [2026, 2025, 2024, 2023, 2022],
    index=[2026, 2025, 2024, 2023, 2022].index(A()["meta"]["report_year"])
    if A()["meta"]["report_year"] in [2026, 2025, 2024, 2023, 2022] else 0,
)

A()["meta"]["organization"] = organization
A()["meta"]["sector"] = sector
A()["meta"]["report_year"] = report_year

st.sidebar.markdown("---")
st.sidebar.markdown("**Pipeline**")
st.sidebar.markdown(
    "Report → Claims → Standards → Evidence → GIS archive → Verdict"
)
st.sidebar.caption("Real GIS verification: Global Forest Watch tree-cover archive.")

page = st.sidebar.radio(
    "Navigate",
    [
        "📊 Dashboard",
        "📄 Report & Claims",
        "📚 Standards",
        "🌳 Impact Picture Validation",
        "🛰️ GIS Archive Verification",
        "💧 Water & Air",
        "🏛️ Governance",
        "🤝 Community Benefit",
        "📋 Assurance Result",
        "🗂️ Evidence Ledger",
    ],
)

# ============================================================
# HEADER
# ============================================================
st.markdown('<div class="main-header">🌍 Uujuzi ESG & Governance Assurance</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">From reported ESG claims to evidence-based impact validation.</div>', unsafe_allow_html=True)

# ============================================================
# CORE LOGIC — CLAIM EXTRACTION
# ============================================================
CLAIM_PATTERNS = [
    (r"(\d[\d,]*)\s*(?:trees|seedlings)\s*(?:were\s*)?plant", "Environment", "trees"),
    (r"water\s*(?:quality|clarity|turbidity)\s*(?:improved|increased|better)\s*(?:by\s*)?(\d+(?:\.\d+)?)\s*%", "Environment", "%"),
    (r"water\s*(?:quality|clarity|turbidity)\s*(?:declined|decreased|worsened)\s*(?:by\s*)?(\d+(?:\.\d+)?)\s*%", "Environment", "%"),
    (r"(?:air|emissions?|pm2\.?5)\s*(?:quality\s*)?(?:improved|reduced|decreased)\s*(?:by\s*)?(\d+(?:\.\d+)?)\s*%", "Climate", "%"),
    (r"(\d[\d,]*)\s*(?:jobs|employment|positions)\s*(?:created|supported|generated)", "Community", "jobs"),
    (r"(\d+(?:\.\d+)?)\s*%\s*(?:of\s*)?(?:local\s*)?procurement", "Community", "%"),
    (r"(?:board|governance)\s*(?:oversight|committee|safeguards?)\s*(?:established|implemented|in place)", "Governance", "boolean"),
]

AREA_TO_STANDARD_HINTS = {
    "Environment": ["ISO 14001", "UN SDGs", "IFRS S2"],
    "Climate":     ["IFRS S2", "UN SDGs"],
    "Community":   ["ISO 26000", "UN SDGs"],
    "Governance":  ["IFRS S1", "UN Global Compact"],
    "Social":      ["ISO 26000", "UN SDGs"],
    "Safety":      ["ISO 45001"],
}

def extract_claims(text: str):
    if not text or not text.strip():
        return []
    claims = []
    for i, (pattern, area, unit) in enumerate(CLAIM_PATTERNS, start=1):
        for m in re.finditer(pattern, text, flags=re.IGNORECASE):
            value_raw = m.group(1) if m.groups() else None
            magnitude = None
            if value_raw:
                try:
                    magnitude = float(value_raw.replace(",", ""))
                except ValueError:
                    magnitude = None
            claims.append({
                "id": f"{area[:3].upper()}-{i:03d}-{len(claims)+1:02d}",
                "area": area, "claim": m.group(0).strip(),
                "magnitude": magnitude, "unit": unit,
                "standard_hints": AREA_TO_STANDARD_HINTS.get(area, []),
            })
    if not claims:
        for sent in re.split(r"(?<=[.!?])\s+", text):
            if re.search(r"\d", sent) and len(sent) > 20:
                claims.append({"id": f"GEN-{len(claims)+1:03d}", "area": "Environment",
                               "claim": sent.strip(), "magnitude": None, "unit": "",
                               "standard_hints": ["ISO 14001", "UN SDGs"]})
                if len(claims) >= 5:
                    break
    return claims

def match_standards(claim_text: str, area: str):
    text = (claim_text or "").lower()
    matches = []
    for name, meta in STANDARDS.items():
        hits = [k for k in meta["keywords"] if k in text]
        if hits:
            matches.append({"standard": name, "why": ", ".join(hits)})
    if not matches:
        for name in AREA_TO_STANDARD_HINTS.get(area, []):
            matches.append({"standard": name, "why": f"area default ({area})"})
    return matches

# ============================================================
# GEOSPATIAL — Geocoding (OpenStreetMap Nominatim, free)
# ============================================================
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "UujuziESGAssurance/1.0 (prototype; contact: demo@uujuzi.example)"

@st.cache_data(ttl=60 * 60 * 24, show_spinner=False)
def geocode_place(place_name: str):
    """Return dict with lat, lon, display_name, boundingbox, or None on failure.
    Uses Nominatim (OpenStreetMap). Free, no key, rate limit 1 req/sec."""
    if not place_name or not place_name.strip():
        return None
    try:
        params = {"q": place_name, "format": "json", "limit": 1, "polygon_geojson": 0}
        headers = {"User-Agent": USER_AGENT}
        r = requests.get(NOMINATIM_URL, params=params, headers=headers, timeout=15)
        if r.status_code != 200:
            return None
        data = r.json()
        if not data:
            return None
        top = data[0]
        bb = top.get("boundingbox")
        # Nominatim boundingbox order: [south, north, west, east]
        lat = float(top["lat"]); lon = float(top["lon"])
        bbox = None
        if bb and len(bb) == 4:
            try:
                s, n, w, e = map(float, bb)
                bbox = {"south": s, "north": n, "west": w, "east": e}
            except ValueError:
                bbox = None
        return {"lat": lat, "lon": lon, "display_name": top.get("display_name", place_name),
                "bbox": bbox, "source": "Nominatim / OpenStreetMap"}
    except Exception:
        return None

# ============================================================
# GEOSPATIAL — Global Forest Watch tree-cover
# ============================================================
GFW_BASE = "https://data-api.globalforestwatch.org"

# The UMD tree-cover-loss dataset's canopy-density layer gives us
# % tree cover at 30m. The public API version is "umd_tree_cover_density_2010"
# and the annual loss layer is "umd_tree_cover_loss". We query both:
#   - density (baseline % tree cover)
#   - loss (hectares lost per year)
# A defensible proxy for "tree cover %" per year is:
#   cover_year_N = density_2010 - cumulative_loss(2010..N) / area * 100
# This is a common, transparent approximation and we label it as such.
#
# For a prototype we do NOT want to require an API key, so we use
# GFW's public tile/data endpoints where possible and cache aggressively.

@st.cache_data(ttl=60 * 60 * 6, show_spinner=False)
def gfw_tree_cover_loss(lat: float, lon: float, radius_km: float, start_year: int, end_year: int):
    """Query Global Forest Watch for annual tree-cover loss (ha) inside a circle.

    Uses the public GFW Data API. Some endpoints require an API key;
    if the key is missing or the call fails, returns None so the caller
    can fall back to manual entry. Never fabricates values.

    Returns a DataFrame with columns: year, loss_ha (or None on failure).
    """
    try:
        # Build a GeoJSON geometry for the circle (approx)
        geom = _circle_geojson(lat, lon, radius_km)
        payload = {
            "geometry": geom,
            "start_year": start_year,
            "end_year": end_year,
        }
        # The exact GFW endpoint for querying an AOI is:
        # POST https://data-api.globalforestwatch.org/dataset/umd_tree_cover_loss/latest/query
        # It requires an API key header (x-api-key) for AOI queries.
        # We attempt it without a key first; many public layers allow limited
        # anonymous use, and if we are blocked we return None gracefully.
        url = f"{GFW_BASE}/dataset/umd_tree_cover_loss/latest/query"
        headers = {"Content-Type": "application/json"}
        # Optional key: set GFW_API_KEY in Streamlit secrets to enable
        try:
            if "GFW_API_KEY" in st.secrets:
                headers["x-api-key"] = st.secrets["GFW_API_KEY"]
        except Exception:
            pass
        r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=20)
        if r.status_code != 200:
            return None
        data = r.json()
        rows = data.get("data", [])
        if not rows:
            return None
        df = pd.DataFrame(rows)
        # Normalise column names defensively — GFW has changed them historically
        if "umd_tree_cover_loss__year" in df.columns:
            df = df.rename(columns={"umd_tree_cover_loss__year": "year"})
        if "umd_tree_cover_loss__ha" in df.columns:
            df = df.rename(columns={"umd_tree_cover_loss__ha": "loss_ha"})
        if "year" not in df.columns or "loss_ha" not in df.columns:
            return None
        return df[["year", "loss_ha"]].sort_values("year").reset_index(drop=True)
    except Exception:
        return None

def _circle_geojson(lat, lon, radius_km, n=32):
    """Approximate circle as a GeoJSON polygon."""
    dlat = radius_km / 111.0
    dlon = radius_km / (111.0 * math.cos(math.radians(lat)) if math.cos(math.radians(lat)) != 0 else 1)
    coords = []
    for i in range(n + 1):
        theta = 2 * math.pi * i / n
        coords.append([lon + dlon * math.cos(theta), lat + dlat * math.sin(theta)])
    return {"type": "Polygon", "coordinates": [coords]}

# ============================================================
# FALLBACK — Synthetic archive-shaped data (clearly labelled)
# ============================================================
def fallback_manual_series(years, cover_start_pct, cover_end_pct, seed=1):
    """When the live archive is unavailable, produce a plausible *illustrative*
    series so the demo still runs. This is explicitly labelled SYNTHETIC
    in the UI and in the ledger."""
    rng = np.random.default_rng(seed)
    ys = np.array(list(years), dtype=float)
    trend = np.linspace(cover_start_pct, cover_end_pct, len(ys))
    return (trend + rng.normal(0, 0.3, len(ys))).round(2)

# ============================================================
# SPATIAL VERDICT LOGIC
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

def spatial_verdict(claim_direction, slope, r2, n_years_with_data):
    if n_years_with_data < 3:
        return "Unverifiable", "Tier 4", (
            f"Only {n_years_with_data} year(s) of archive data are available for this AOI. "
            "At least 3 are needed to make a trend claim defensible."
        )
    observed = "increase" if slope > 0.1 else "decline" if slope < -0.1 else "flat"
    if claim_direction is None:
        return "Unverifiable", "Tier 4", "No directional claim was supplied to test."
    if claim_direction == observed and r2 >= 0.5:
        return "Corroborated", "Tier 2", (
            f"Archive data moves {observed} (slope {slope:+.3f} %/yr, R²={r2:.2f}), "
            "consistent with the reported direction."
        )
    if claim_direction == observed:
        return "Partially corroborated", "Tier 3", (
            f"Direction matches ({observed}), but the trend fit is weak "
            f"(R²={r2:.2f}). More years or finer AOI needed."
        )
    return "Contradicted", "Tier 4", (
        f"Archive data moves {observed} (slope {slope:+.3f} %/yr), "
        f"opposite to the reported {claim_direction}."
    )

# ============================================================
# GOVERNANCE TIERING
# ============================================================
def assign_tier(sources):
    if not sources:
        return "Tier 4", "No sources recorded."
    independent = [s for s in sources if s.get("independent")]
    has_institutional = any(s.get("type") == "institutional" for s in independent)
    if len(independent) >= 2 and has_institutional:
        return "Tier 1", "Multiple independent sources including an institutional source."
    if len(independent) >= 2:
        return "Tier 2", "Two or more independent sources."
    if len(independent) == 1:
        return "Tier 3", "Single independent source."
    return "Tier 4", "Only self-reported / non-independent sources."

# ============================================================
# PAGE: DASHBOARD
# ============================================================
if page == "📊 Dashboard":
    st.header("📊 ESG Assurance Dashboard")
    st.write(f"**{organization}** · {sector} · ESG report year **{report_year}**")

    claims = A()["claims"]
    ledger = A()["evidence_ledger"]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Claims extracted", len(claims))
    c2.metric("Evidence items logged", len(ledger))
    c3.metric("Standards matched", len(A()["standards_matches"]))
    c4.metric("GIS verifications run", sum(1 for e in ledger if e["module"] == "Spatial"))

    st.markdown("---")
    st.subheader("Assurance architecture")
    st.markdown(
        "**Report text → Claims → Standards → Evidence requirements → "
        "GIS archive verification → Environmental / Governance / Community → "
        "Assurance verdict**"
    )

    st.markdown("---")
    st.subheader("Pipeline status")
    status = pd.DataFrame([
        {"Stage": "Report text ingested", "Done": bool(A()["raw_report_text"]), "Go to": "📄 Report & Claims"},
        {"Stage": "Claims extracted", "Done": bool(A()["claims"]), "Go to": "📄 Report & Claims"},
        {"Stage": "Standards mapped", "Done": bool(A()["standards_matches"]), "Go to": "📚 Standards"},
        {"Stage": "GIS archive verification run", "Done": bool(A()["spatial"]), "Go to": "🛰️ GIS Archive Verification"},
        {"Stage": "Governance evidence logged", "Done": bool(A()["governance"]), "Go to": "🏛️ Governance"},
        {"Stage": "Community benefit assessed", "Done": bool(A()["community"]), "Go to": "🤝 Community Benefit"},
    ])
    st.dataframe(status, use_container_width=True, hide_index=True)

    st.info("This dashboard reflects what you have entered. Nothing is pre-filled.")

# ============================================================
# PAGE: REPORT & CLAIMS
# ============================================================
elif page == "📄 Report & Claims":
    st.header("📄 Report & Claims")
    st.subheader("1. Paste or upload the ESG report text")

    uploaded = st.file_uploader("Upload .txt of the report section", type=["txt"])
    if uploaded is not None:
        try:
            text = uploaded.read().decode("utf-8", errors="ignore")
            A()["raw_report_text"] = text
            st.success(f"Loaded {len(text):,} characters from {uploaded.name}.")
        except Exception as e:
            st.error(f"Could not read file: {e}")

    text = st.text_area(
        "Report text",
        value=A()["raw_report_text"] or (
            "In 2026 the company reported that 100,000 trees were planted at its "
            "Kakuzi estate operations between 2024 and 2026. Water quality around "
            "the project area improved by 15%. 340 jobs were created for local "
            "community members. Board-level ESG oversight was established."
        ),
        height=200,
    )
    A()["raw_report_text"] = text

    if st.button("Extract claims", type="primary"):
        claims = extract_claims(text)
        A()["claims"] = claims
        A()["standards_matches"] = {c["id"]: match_standards(c["claim"], c["area"]) for c in claims}
        st.success(f"Extracted {len(claims)} claim(s).")

    if A()["claims"]:
        st.markdown("---")
        st.subheader("2. Extracted claims")
        st.dataframe(pd.DataFrame([
            {"ID": c["id"], "Area": c["area"], "Claim": c["claim"],
             "Magnitude": c["magnitude"], "Unit": c["unit"],
             "Standards": ", ".join(s["standard"] for s in A()["standards_matches"].get(c["id"], []))}
            for c in A()["claims"]
        ]), use_container_width=True, hide_index=True)

# ============================================================
# PAGE: STANDARDS
# ============================================================
elif page == "📚 Standards":
    st.header("📚 Standards Cross-Reference")
    if not A()["claims"]:
        st.warning("Extract claims first on the Report & Claims tab.")
    else:
        for c in A()["claims"]:
            matches = A()["standards_matches"].get(c["id"], [])
            with st.expander(f"{c['id']} — {c['claim'][:90]}"):
                if not matches:
                    st.write("No standards matched.")
                    continue
                st.dataframe(pd.DataFrame([
                    {"Standard": m["standard"],
                     "Description": STANDARDS[m["standard"]]["description"],
                     "Matched on": m["why"],
                     "Areas": ", ".join(STANDARDS[m["standard"]]["areas"])}
                    for m in matches
                ]), use_container_width=True, hide_index=True)

# ============================================================
# PAGE: IMPACT PICTURE VALIDATION
# ============================================================
elif page == "🌳 Impact Picture Validation":
    st.header("🌳 Impact Picture Validation")
    st.markdown("### Don't only check what the ESG report says. Check what the landscape shows.")
    st.caption(
        "This module models the expected landscape response from a reported planting "
        "figure and a survival rate. It is a **responsive model**, not a static table."
    )

    st.markdown("---")
    st.subheader("1. Reported planting claim")
    c1, c2, c3, c4 = st.columns(4)
    reported_trees = c1.number_input("Trees reported planted", min_value=0, value=100_000, step=1_000)
    baseline_year = c2.selectbox("Baseline year", [2023, 2024, 2025], index=1)
    validation_year = c3.selectbox("Reporting year", [2025, 2026], index=1)
    area_ha = c4.number_input("Project area (ha)", min_value=1.0, value=500.0, step=50.0)

    survival_rate_pct = st.slider(
        "Assumed survival rate (%) — a modelling assumption, not a verified figure",
        10, 100, 75,
        help="Typical tree-planting programmes see 30–70% survival at year 3.",
    )

    if validation_year <= baseline_year:
        st.error("Reporting year must be later than baseline year.")
        st.stop()

    st.markdown("---")
    st.subheader("2. Modelled landscape response")
    years = list(range(baseline_year, validation_year + 1))
    n = len(years)

    canopy_m2_per_tree = 8.0
    baseline_canopy_ha = area_ha * 0.15
    established = reported_trees * (survival_rate_pct / 100.0)
    added_canopy_ha = (established * canopy_m2_per_tree) / 10_000.0
    canopy = np.linspace(baseline_canopy_ha, baseline_canopy_ha + added_canopy_ha, n)
    cover_pct = np.clip((canopy / area_ha) * 100, 0, 100)
    veg = np.clip(0.30 + (cover_pct / 100.0) * 0.55, 0, 0.95)
    loss_ha = np.linspace(0.02 * area_ha, 0.005 * area_ha, n)

    series = pd.DataFrame({
        "Year": years,
        "Reported Trees Planted": np.linspace(0, reported_trees, n).round().astype(int),
        "Established Trees (modelled)": np.linspace(0, established, n).round().astype(int),
        "Tree Cover (%)": cover_pct.round(2),
        "Vegetation Index": veg.round(3),
        "Tree Cover Loss (ha)": loss_ha.round(2),
        "Project Area (ha)": [area_ha] * n,
    })
    A()["environmental"]["tree_series"] = series
    st.dataframe(series, use_container_width=True, hide_index=True)

    c1, c2, c3, c4 = st.columns(4)
    first, last = series.iloc[0], series.iloc[-1]
    c1.metric("Cover baseline", f"{first['Tree Cover (%)']:.2f}%")
    c2.metric("Cover reporting", f"{last['Tree Cover (%)']:.2f}%",
              f"{last['Tree Cover (%)'] - first['Tree Cover (%)']:+.2f} pp")
    c3.metric("Veg index reporting", f"{last['Vegetation Index']:.3f}")
    c4.metric("Established trees (modelled)", f"{int(last['Established Trees (modelled)']):,}")

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=series["Year"], y=series["Tree Cover (%)"],
                             mode="lines+markers", name="Tree cover (%)"))
    fig.add_trace(go.Scatter(x=series["Year"], y=series["Vegetation Index"] * 100,
                             mode="lines+markers", name="Veg index × 100"))
    fig.update_layout(height=320, xaxis_title="Year", yaxis_title="% / scaled",
                      legend=dict(orientation="h", y=1.1), margin=dict(t=20, b=30, l=40, r=20))
    st.plotly_chart(fig, use_container_width=True)

    # Verdict
    canopy_delta = last["Tree Cover (%)"] - first["Tree Cover (%)"]
    claim_expected_ha = (reported_trees * canopy_m2_per_tree * 0.75) / 10_000.0
    claim_expected_pct = (claim_expected_ha / area_ha) * 100.0
    ratio = canopy_delta / claim_expected_pct if claim_expected_pct > 0 else float("inf")
    _, r2c = slope_and_r2(series["Year"], series["Tree Cover (%)"])

    if canopy_delta <= 0 or last["Vegetation Index"] - first["Vegetation Index"] <=
