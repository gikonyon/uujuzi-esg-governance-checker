"""
Uujuzi ESG & Governance Assurance Checker
Working prototype with real GIS verification.

Cross-checks a client report against public Global Forest Watch
tree-cover data for the reporting period and shows a year-by-year
table with source attribution and per-year confidence.
"""

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
                  "keywords": ["poverty", "health", "water", "energy", "jobs", "infrastructure", "climate", "forest", "community"],
                  "areas": ["Climate", "Water", "Jobs", "Communities"]},
    "UN Global Compact": {"description": "Principles for Responsible Business",
                          "keywords": ["human rights", "labour", "environment", "corruption", "governance"],
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
}

# ============================================================
# SESSION STATE
# ============================================================
def _new_assessment(org, sector, year):
    return {
        "meta": {"organization": org, "sector": sector, "report_year": year},
        "raw_report_text": "",
        "claims": [],
        "standards_matches": {},
        "spatial": {},
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
# CLAIM EXTRACTION
# ============================================================
CLAIM_PATTERNS = [
    (r"(\d[\d,]*)\s*(?:trees|seedlings)\s*(?:were\s*)?plant", "Environment", "trees"),
    (r"water\s*(?:quality|clarity|turbidity)\s*(?:improved|increased|better)\s*(?:by\s*)?(\d+(?:\.\d+)?)\s*%", "Environment", "%"),
    (r"(?:air|emissions?)\s*(?:quality\s*)?(?:improved|reduced|decreased)\s*(?:by\s*)?(\d+(?:\.\d+)?)\s*%", "Climate", "%"),
    (r"(\d[\d,]*)\s*(?:jobs|employment|positions)\s*(?:created|supported|generated)", "Community", "jobs"),
    (r"(?:board|governance)\s*(?:oversight|committee|safeguards?)\s*(?:established|implemented|in place)", "Governance", "boolean"),
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
                if len(claims) >= 5:
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

# ============================================================
# GEOCODING (OpenStreetMap Nominatim — free, no key)
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
        return {
            "lat": float(top["lat"]),
            "lon": float(top["lon"]),
            "display_name": top.get("display_name", place_name),
            "source": "Nominatim / OpenStreetMap",
        }
    except Exception:
        return None

# ============================================================
# GFW TREE COVER — best-effort, falls back to manual
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
    """Best-effort query to GFW public data API. Returns DataFrame(year, loss_ha)
    or None on any failure. Never fabricates values."""
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
    observed = "increase" if slope > 0.1 else "decline" if slope < -0.1 else "flat"
    if claim_direction is None:
        return "Unverifiable", "Tier 4", "No directional claim supplied."
    if claim_direction == observed and r2 >= 0.5:
        return "Corroborated", "Tier 2", (
            f"Archive trend is {observed} (slope {slope:+.3f}/yr, R²={r2:.2f}), "
            "consistent with the reported direction."
        )
    if claim_direction == observed:
        return "Partially corroborated", "Tier 3", (
            f"Direction matches ({observed}) but the fit is weak (R²={r2:.2f})."
        )
    return "Contradicted", "Tier 4", (
        f"Archive trend is {observed} (slope {slope:+.3f}/yr), "
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

    st.markdown("---")
    st.subheader("Pipeline status")
    st.dataframe(pd.DataFrame([
        {"Stage": "Report text ingested", "Done": bool(A()["raw_report_text"]), "Go to": "📄 Report & Claims"},
        {"Stage": "Claims extracted", "Done": bool(A()["claims"]), "Go to": "📄 Report & Claims"},
        {"Stage": "Standards mapped", "Done": bool(A()["standards_matches"]), "Go to": "📚 Standards"},
        {"Stage": "GIS verification run", "Done": bool(A()["spatial"]), "Go to": "🛰️ GIS Archive Verification"},
    ]), use_container_width=True, hide_index=True)

# ============================================================
# REPORT & CLAIMS
# ============================================================
elif page == "📄 Report & Claims":
    st.header("📄 Report & Claims")

    uploaded = st.file_uploader("Upload .txt of the report section", type=["txt"])
    if uploaded is not None:
        try:
            A()["raw_report_text"] = uploaded.read().decode("utf-8", errors="ignore")
            st.success(f"Loaded {len(A()['raw_report_text']):,} characters.")
        except Exception as e:
            st.error(f"Could not read file: {e}")

    text = st.text_area(
        "Report text",
        value=A()["raw_report_text"] or (
            "In 2026 the company reported that 100,000 trees were planted at its "
            "Kakuzi estate operations between 2024 and 2026. Water quality around "
            "the project area improved by 15%. 340 jobs were created."
        ),
        height=180,
    )
    A()["raw_report_text"] = text

    if st.button("Extract claims", type="primary"):
        A()["claims"] = extract_claims(text)
        A()["standards_matches"] = {c["id"]: match_standards(c["claim"], c["area"]) for c in A()["claims"]}
        st.success(f"Extracted {len(A()['claims'])} claim(s).")

    if A()["claims"]:
        st.markdown("---")
        st.dataframe(pd.DataFrame([
            {"ID": c["id"], "Area": c["area"], "Claim": c["claim"],
             "Magnitude": c["magnitude"], "Unit": c["unit"],
             "Standards": ", ".join(s["standard"] for s in A()["standards_matches"].get(c["id"], []))}
            for c in A()["claims"]
        ]), use_container_width=True, hide_index=True)

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
                st.dataframe(pd.DataFrame([
                    {"Standard": m["standard"],
                     "Description": STANDARDS[m["standard"]]["description"],
                     "Matched on": m["why"]}
                    for m in A()["standards_matches"].get(c["id"], [])
                ]), use_container_width=True, hide_index=True)

# ============================================================
# GIS ARCHIVE VERIFICATION  ← the new flagship tab
# ============================================================
elif page == "🛰️ GIS Archive Verification":
    st.header("🛰️ GIS Archive Verification")
    st.caption(
        "Verifies a reported claim against real public tree-cover archive data for "
        "the reporting period. For a 2026 report, this covers 2024, 2025 and 2026."
    )

    st.subheader("1. Reported claim")
    c1, c2, c3 = st.columns(3)
    claim_text = c1.text_input("Claim (short)", "100,000 trees planted 2024–2026")
    baseline_year = c2.selectbox("Baseline year", [2023, 2024, 2025], index=1)
    reporting_year = c3.selectbox("Reporting year", [2026, 2025], index=0)

    claim_direction = st.selectbox(
        "Claimed direction (from the report text)",
        ["increase", "decline", "unspecified"],
    )

    st.subheader("2. Location of the claim")
    loc_method = st.radio(
        "How do you want to specify the location?",
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
                geocode_ok = True
            else:
                st.warning(
                    "Geocoding failed. You can enter coordinates manually below. "
                    "The app will not fake a location."
                )
        g = st.session_state.get("geo")
        if g and g.get("display_name", "").lower().find(place_name.split(",")[0].lower()) >= 0:
            lat, lon = g["lat"], g["lon"]
            place_label = g["display_name"]
            geocode_ok = True

    if not geocode_ok or loc_method.startswith("Enter"):
        c1, c2 = st.columns(2)
        lat = c1.number_input("Latitude", value=-0.850000, format="%.6f")
        lon = c2.number_input("Longitude", value=37.150000, format="%.6f")
        place_label = place_label or f"{lat:.4f}, {lon:.4f}"

    radius_km = st.slider("AOI radius (km)", 1.0, 25.0, 5.0, step=1.0)

    # Show AOI on map
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
                    zoom=int(max(4, 11 - math.log2(radius_km + 1)))),
        height=360, margin=dict(t=0, b=0, l=0, r=0),
        legend=dict(orientation="h", y=1.02),
    )
    st.plotly_chart(fmap, use_container_width=True)
    st.caption(f"AOI centred on **{place_label}**. Radius {radius_km:.1f} km.")

    st.subheader("3. Archive verification")
    st.caption(
        "Queries Global Forest Watch for annual tree-cover loss inside the AOI. "
        "If the public archive is unavailable, you will see a warning and can "
        "supply figures manually — the app will not invent data."
    )

    years = list(range(baseline_year, reporting_year + 1))
    gfw_df = None
    with st.spinner("Querying Global Forest Watch archive…"):
        gfw_df = gfw_tree_cover_loss(lat, lon, radius_km, baseline_year, reporting_year)

    if gfw_df is not None and not gfw_df.empty:
        st.success(f"Retrieved {len(gfw_df)} year(s) from Global Forest Watch.")
        series_df = gfw_df.copy()
        series_df["source"] = "Global Forest Watch — UMD tree-cover loss"
        series_df["synthetic"] = False
    else:
        st.warning(
            "Global Forest Watch did not return data for this AOI (this is common "
            "if the AOI is outside forest cover, or if the public API is rate-limited). "
            "Below is a **manual-entry fallback**. Any numbers you enter here are "
            "labelled as user-supplied — the app does not silently substitute synthetic values."
        )
        manual = st.data_editor(
            pd.DataFrame({
                "year": years,
                "loss_ha": [0.0] * len(years),
            }),
            num_rows="fixed", use_container_width=True, key="manual_gfw",
        )
        series_df = manual.copy()
        series_df["source"] = "User-supplied"
        series_df["synthetic"] = True

    st.dataframe(series_df, use_container_width=True, hide_index=True)

    # Compute trend on loss (a decline in loss per year = improvement)
    if "loss_ha" in series_df.columns and len(series_df) >= 3:
        slope, r2 = slope_and_r2(series_df["year"], series_df["loss_ha"])
        # If loss is decreasing, that's an improvement.
        observed_direction = (
            "increase" if slope > 0.001 else "decline" if slope < -0.001 else "flat"
        )
        verdict, tier, rationale = spatial_verdict(
            None if claim_direction == "unspecified" else claim_direction,
            -slope,  # negative loss slope = positive vegetation trend
            r2,
            len(series_df),
        )
        st.markdown(
            f'<div class="verdict-card {VERDICTS[verdict]["css"]}">'
            f'<b>Verdict:</b> {verdict} &nbsp;·&nbsp; <b>{tier}</b><br>{rationale}</div>',
            unsafe_allow_html=True,
        )
        st.caption(
            f"Slope of loss = {slope:+.4f} ha/yr · R² = {r2:.2f}. "
            "A declining loss slope is treated as a positive vegetation trend."
        )
        add_ledger(
            "Spatial",
            f"AOI verification at {place_label} ({baseline_year}–{reporting_year})",
            verdict, tier,
            source="Global Forest Watch" if not series_df["synthetic"].iloc[0] else "User-supplied",
            synthetic=bool(series_df["synthetic"].iloc[0]),
        )
        A()["spatial"] = {"lat": lat, "lon": lon, "radius_km": radius_km,
                          "series": series_df, "verdict": verdict, "tier": tier}
    else:
        st.info("Add at least 3 years of data to compute a trend.")

    st.markdown("---")
    st.warning(
        "**What this verdict does and does not mean.** Tree-cover change can be "
        "caused by planting, natural regrowth, fire, logging, or land-use change. "
        "Consistency between archive data and a reported claim is evidence that "
        "the claim *can* be true, not proof of the number of trees planted. "
        "Exact counts still require planting registers, GPS plots and survival surveys."
    )

# ============================================================
# GOVERNANCE
# ============================================================
elif page == "🏛️ Governance":
    st.header("🏛️ Governance Evidence & Corroboration")
    gov_claim = st.text_input(
        "Claim or issue to assess",
        "Board-level ESG oversight is functioning effectively.",
    )

    if "gov_sources" not in st.session_state:
        st.session_state["gov_sources"] = [
            {"source": "Board minutes (self)", "type": "self", "independent": False},
            {"source": "Independent governance review", "type": "institutional", "independent": True},
        ]

    edited = st.data_editor(
        pd.DataFrame(st.session_state["gov_sources"]),
        num_rows="dynamic", use_container_width=True, key="gov_editor",
    )
    st.session_state["gov_sources"] = edited.to_dict("records")

    sources = st.session_state["gov_sources"]
    independent = [s for s in sources if s.get("independent")]
    has_inst = any(s.get("type") == "institutional" for s in independent)
    if len(independent) >= 2 and has_inst:
        tier, reason = "Tier 1", "Multiple independent sources including an institutional source."
    elif len(independent) >= 2:
        tier, reason = "Tier 2", "Two or more independent sources."
    elif len(independent) == 1:
        tier, reason = "Tier 3", "Single independent source."
    else:
        tier, reason = "Tier 4", "Only self-reported / non-independent sources."

    verdict = {"Tier 1": "Corroborated", "Tier 2": "Corroborated",
               "Tier 3": "Partially corroborated", "Tier 4": "Unverifiable"}[tier]

    st.markdown(
        f'<div class="verdict-card {VERDICTS[verdict]["css"]}">'
        f'<b>Tier:</b> {tier}<br>{reason}<br><b>Verdict:</b> {verdict}</div>',
        unsafe_allow_html=True,
    )
    A()["governance"] = {"claim": gov_claim, "sources": sources, "tier": tier, "verdict": verdict}
    add_ledger("Governance", gov_claim, verdict, tier, source="see sources", synthetic=False)

# ============================================================
# ASSURANCE RESULT
# ============================================================
elif page == "📋 Assurance Result":
    st.header("📋 Overall Assurance Result")
    ledger = A()["evidence_ledger"]
    if not ledger:
        st.warning("No evidence logged yet. Run through the pipeline tabs first.")
        st.stop()

    df = pd.DataFrame(ledger)
    df["score"] = df["verdict"].map(lambda v: VERDICTS.get(v, {}).get("score", 0.0))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Evidence items", len(df))
    c2.metric("Synthetic items", int(df["synthetic"].sum()))
    c3.metric("Real-source items", int((~df["synthetic"]).sum()))
    overall = df["score"].mean() * 100
    c4.metric("Assurance indicator", f"{overall:.0f}%")
    st.progress(min(overall / 100.0, 1.0))

    st.markdown("---")
    st.subheader("Evidence by module")
    by_mod = df.groupby("module").agg(
        items=("item", "count"),
        mean_score=("score", "mean"),
    ).reset_index()
    by_mod["mean_score"] = (by_mod["mean_score"] * 100).round(0).astype(int).astype(str) + "%"
    st.dataframe(by_mod, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("Full evidence ledger")
    st.dataframe(df[["module", "item", "verdict", "tier", "source", "synthetic", "timestamp"]],
                 use_container_width=True, hide_index=True)

    st.download_button(
        "Download evidence ledger (CSV)",
        df.to_csv(index=False).encode("utf-8"),
        file_name=f"uujuzi_evidence_ledger_{datetime.now():%Y%m%d_%H%M}.csv",
        mime="text/csv",
    )

    st.warning(
        "This indicator is the mean of per-item verdict scores. It is a convenience "
        "summary, not an audit opinion. Any row marked `synthetic = True` is illustrative "
        "and must be replaced with real evidence before external use."
    )

# ============================================================
# EVIDENCE LEDGER
# ============================================================
elif page == "🗂️ Evidence Ledger":
    st.header("🗂️ Evidence Ledger")
    if A()["evidence_ledger"]:
        st.dataframe(pd.DataFrame(A()["evidence_ledger"]),
                     use_container_width=True, hide_index=True)
    else:
        st.info("Nothing logged yet.")

# ============================================================
# FOOTER
# ============================================================
st.markdown("---")
st.caption(
    f"Uujuzi ESG & Governance Assurance · prototype · "
    f"{datetime.now():%Y-%m-%d %H:%M} · {organization}"
)
