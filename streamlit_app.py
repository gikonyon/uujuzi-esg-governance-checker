import re
import math
import hashlib
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ============================================================
# UUJUZI ESG & GOVERNANCE ASSURANCE CHECKER
# ============================================================
# A working prototype that reconciles reported ESG claims
# against standards, documentary evidence, environmental
# indicators, spatial evidence, governance corroboration and
# community-benefit evidence.
#
# Core principle:
#   Do not treat a reported claim as a verified outcome.
#   Reconcile it against independent, tiered evidence.
#
# All synthetic figures are explicitly labelled SYNTHETIC
# inline. Real integrations are marked TODO_LIVE.
# ============================================================

st.set_page_config(
    page_title="Uujuzi ESG & Governance Assurance",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ------------------------------------------------------------
# STYLE
# ------------------------------------------------------------
st.markdown(
    """
    <style>
    .main-header {font-size: 2.2rem; font-weight: 700; margin-bottom: 0.2rem;}
    .sub-header  {font-size: 1.05rem; color: #666; margin-bottom: 1.2rem;}
    .synthetic-badge {
        display: inline-block; padding: 1px 8px; border-radius: 10px;
        background: #fff3cd; color: #7a5c00; font-size: 0.72rem;
        font-weight: 600; letter-spacing: 0.03em; margin-left: 6px;
        vertical-align: middle;
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
    "IFRS S1": {
        "description": "General Requirements for Disclosure of Sustainability-related Financial Information",
        "keywords": ["governance", "strategy", "risk", "material", "sustainability", "financial"],
        "areas": ["Governance", "Strategy", "Risk Management", "Metrics & Targets"],
    },
    "IFRS S2": {
        "description": "Climate-related Disclosures",
        "keywords": ["climate", "carbon", "emission", "ghg", "net zero", "scope 1", "scope 2", "scope 3"],
        "areas": ["Climate Governance", "Climate Risks", "Climate Opportunities", "Metrics & Targets"],
    },
    "ISO 14001": {
        "description": "Environmental Management Systems",
        "keywords": ["environment", "water", "air", "waste", "pollution", "tree", "forest", "emission", "effluent"],
        "areas": ["Environmental Management", "Compliance", "Objectives", "Monitoring"],
    },
    "ISO 26000": {
        "description": "Social Responsibility Guidance",
        "keywords": ["community", "social", "human rights", "labour", "stakeholder", "employment"],
        "areas": ["Governance", "Human Rights", "Community", "Environment"],
    },
    "ISO 45001": {
        "description": "Occupational Health & Safety",
        "keywords": ["safety", "worker", "occupational", "incident", "injury", "health"],
        "areas": ["Worker Safety", "Risk Management", "Incident Management", "Performance"],
    },
    "UN SDGs": {
        "description": "UN Sustainable Development Goals",
        "keywords": ["poverty", "hunger", "health", "education", "water", "energy", "jobs", "infrastructure", "climate", "forest", "community"],
        "areas": ["Climate", "Water", "Environment", "Poverty", "Jobs", "Infrastructure", "Communities"],
    },
    "UN Global Compact": {
        "description": "Principles for Responsible Business",
        "keywords": ["human rights", "labour", "environment", "corruption", "bribery", "governance"],
        "areas": ["Human Rights", "Labour", "Environment", "Anti-Corruption"],
    },
}

# Evidence tier definitions used across all modules.
EVIDENCE_TIERS = {
    "Tier 1": "Institutional corroboration — multiple independent sources including an institutional source.",
    "Tier 2": "Independent reporting — two or more reasonably independent credible sources.",
    "Tier 3": "Single-source reporting — requires additional corroboration.",
    "Tier 4": "Unverifiable — insufficient evidence to establish the claim.",
}

# Verdict vocabulary — used everywhere.
VERDICTS = {
    "Corroborated":             {"css": "verdict-corroborated", "score": 1.00},
    "Partially corroborated":   {"css": "verdict-partial",      "score": 0.60},
    "Requires evidence":        {"css": "verdict-partial",      "score": 0.35},
    "Contradicted":             {"css": "verdict-contradicted", "score": 0.00},
    "Unverifiable":             {"css": "verdict-unverifiable", "score": 0.20},
    "Not assessed":             {"css": "verdict-unverifiable", "score": 0.00},
}


# ============================================================
# SHARED ASSESSMENT STATE
# ============================================================
# Everything flows through this object. Tabs read from it and
# write to it. That is what turns eight screens into one pipeline.

def _new_assessment(org, sector, report_year):
    return {
        "meta": {
            "organization": org,
            "sector": sector,
            "report_year": report_year,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        },
        "raw_report_text": "",
        "claims": [],           # list of dicts
        "standards_matches": {},# claim_id -> [standard names]
        "environmental": {},    # indicator -> series + verdict
        "spatial": {},          # aoi, series, verdict
        "governance": [],       # list of evidence rows
        "community": [],        # list of evidence rows
        "evidence_ledger": [],  # every evidence item in one place
    }


if "assessment" not in st.session_state:
    st.session_state["assessment"] = _new_assessment(
        "Demo Organization", "Agriculture", 2025
    )


def A():
    """Shortcut to the shared assessment."""
    return st.session_state["assessment"]


def add_ledger(module, item, verdict, tier, synthetic=True):
    """Every piece of evidence used anywhere gets written here."""
    A()["evidence_ledger"].append({
        "module": module,
        "item": item,
        "verdict": verdict,
        "tier": tier,
        "synthetic": synthetic,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    })


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("🌍 Uujuzi")
st.sidebar.markdown("### Assurance Workspace")

organization = st.sidebar.text_input("Organization / Project", A()["meta"]["organization"])
sector = st.sidebar.selectbox(
    "Sector",
    ["Agriculture", "Banking & Finance", "Energy", "Manufacturing", "Mining",
     "Telecommunications", "Infrastructure", "NGO / Development", "Government", "Other"],
    index=["Agriculture", "Banking & Finance", "Energy", "Manufacturing", "Mining",
           "Telecommunications", "Infrastructure", "NGO / Development", "Government", "Other"].index(A()["meta"]["sector"])
    if A()["meta"]["sector"] in ["Agriculture", "Banking & Finance", "Energy", "Manufacturing", "Mining",
                                  "Telecommunications", "Infrastructure", "NGO / Development", "Government", "Other"] else 0,
)
report_year = st.sidebar.selectbox("ESG Report Year", [2025, 2024, 2023, 2022, 2021], index=0)

# Persist meta every render so downstream tabs always see current values.
A()["meta"]["organization"] = organization
A()["meta"]["sector"] = sector
A()["meta"]["report_year"] = report_year

st.sidebar.markdown("---")
st.sidebar.markdown(
    """
    **Pipeline**

    Report text → Claims → Standards → Evidence requirements →
    Environmental / Spatial / Governance / Community checks →
    Assurance verdict
    """
)
st.sidebar.caption(
    "All synthetic figures are labelled inline. Real integrations are marked TODO_LIVE."
)

page = st.sidebar.radio(
    "Navigate",
    [
        "📊 Dashboard",
        "📄 Report & Claims",
        "📚 Standards",
        "🌳 Impact Picture Validation",
        "🛰️ Spatial Audit",
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
st.markdown(
    '<div class="sub-header">From reported ESG claims to evidence-based impact validation.</div>',
    unsafe_allow_html=True,
)


# ============================================================
# CORE LOGIC — CLAIM EXTRACTION
# ============================================================

CLAIM_PATTERNS = [
    # (regex, area, unit_label)
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
    """Extract structured claims from report text.

    Rule-based for the prototype. TODO_LIVE: replace with the NLP /
    LLM extraction step once claim text is coming from the ingestion
    pipeline. The output contract (list of dicts with id, area,
    claim, magnitude, unit, standard_hints) is what downstream
    modules depend on, so keep that shape when you swap it out.
    """
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
                "area": area,
                "claim": m.group(0).strip(),
                "magnitude": magnitude,
                "unit": unit,
                "standard_hints": AREA_TO_STANDARD_HINTS.get(area, []),
            })

    # Fallback: if nothing matched, look for sentences with % or numbers
    if not claims:
        for sent in re.split(r"(?<=[.!?])\s+", text):
            if re.search(r"\d", sent) and len(sent) > 20:
                claims.append({
                    "id": f"GEN-{len(claims)+1:03d}",
                    "area": "Environment",
                    "claim": sent.strip(),
                    "magnitude": None,
                    "unit": "",
                    "standard_hints": ["ISO 14001", "UN SDGs"],
                })
                if len(claims) >= 5:
                    break

    return claims


def match_standards(claim_text: str, area: str):
    """Return the standards whose keywords fire on this claim,
    with the specific keyword that fired (so the reasoning is auditable)."""
    text = (claim_text or "").lower()
    matches = []
    for name, meta in STANDARDS.items():
        hits = [k for k in meta["keywords"] if k in text]
        if hits:
            matches.append({"standard": name, "why": ", ".join(hits)})
    # Always include the area's default hints if nothing matched
    if not matches:
        for name in AREA_TO_STANDARD_HINTS.get(area, []):
            matches.append({"standard": name, "why": f"area default ({area})"})
    return matches


# ============================================================
# CORE LOGIC — TREE PLANTING MODEL
# ============================================================
# This is what makes the Impact Picture tab responsive. The user
# supplies planting parameters, and the tree cover / vegetation
# series responds. It's still a MODEL (synthetic), but it is a
# responsive model, not a fixed table.

def tree_model(reported_trees, area_ha, baseline_year, validation_year,
               survival_rate_pct, natural_regrowth_baseline=0.15):
    """Return a year-by-year synthetic series where tree cover and
    vegetation genuinely respond to the input parameters.

    Approach:
      - baseline canopy cover for the site is a fraction of area
        (natural_regrowth_baseline accounts for pre-existing cover)
      - each planted tree contributes an assumed canopy area once
        established; survival_rate_pct discounts the planted count
      - loss from natural disturbance is modelled as a small
        declining series
      - years between baseline and reporting are interpolated
    """
    years = list(range(baseline_year, validation_year + 1))
    n = len(years)
    if n < 2:
        years = [baseline_year, baseline_year + 1]
        n = 2

    # Assumed canopy per established tree in m^2 (species- and age-dependent).
    # 8 m² is a defensible middle for mixed indigenous / agroforestry at year 3.
    canopy_m2_per_tree = 8.0
    ha_to_m2 = 10_000.0

    baseline_canopy_ha = area_ha * natural_regrowth_baseline
    established_trees = reported_trees * (survival_rate_pct / 100.0)
    added_canopy_ha = (established_trees * canopy_m2_per_tree) / ha_to_m2

    # Natural disturbance loss declines slightly over time as canopy closes.
    baseline_loss_ha = 0.02 * area_ha
    final_loss_ha = 0.005 * area_ha
    loss_series = np.linspace(baseline_loss_ha, final_loss_ha, n)

    # Net canopy trajectory
    canopy = np.linspace(baseline_canopy_ha, baseline_canopy_ha + added_canopy_ha, n)
    tree_cover_pct = np.clip((canopy / area_ha) * 100.0, 0, 100)

    # Vegetation index loosely follows canopy but compressed (0.3–0.9 range)
    veg_base = 0.30 + (tree_cover_pct / 100.0) * 0.55
    veg = np.clip(veg_base, 0, 0.95)

    return pd.DataFrame({
        "Year": years,
        "Reported Trees Planted": np.linspace(0, reported_trees, n).round().astype(int),
        "Established Trees (modelled)": np.linspace(0, established_trees, n).round().astype(int),
        "Tree Cover (%)": tree_cover_pct.round(2),
        "Vegetation Index": veg.round(3),
        "Tree Cover Loss (ha)": loss_series.round(2),
        "Project Area (ha)": [area_ha] * n,
    })


def slope_and_r2(years, values):
    x = np.asarray(years, dtype=float)
    y = np.asarray(values, dtype=float)
    if len(x) < 2:
        return 0.0, 0.0
    slope, intercept = np.polyfit(x, y, 1)
    fitted = slope * x + intercept
    ss_res = float(np.sum((y - fitted) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
    return float(slope), float(r2)


def assess_tree_claim(series, reported_trees):
    """Derive a verdict from the modelled series AND the reported figure."""
    baseline = series.iloc[0]
    final = series.iloc[-1]
    canopy_delta = final["Tree Cover (%)"] - baseline["Tree Cover (%)"]
    veg_delta = final["Vegetation Index"] - baseline["Vegetation Index"]
    slope_canopy, r2_canopy = slope_and_r2(series["Year"], series["Tree Cover (%)"])

    # Expected canopy gain from the claim alone
    claim_expected_ha = (reported_trees * 8.0 * 0.75) / 10_000.0  # 75% survival assumed for expectation
    claim_expected_pct = (claim_expected_ha / final["Project Area (ha)"]) * 100.0
    observed_pct = canopy_delta

    ratio = (observed_pct / claim_expected_pct) if claim_expected_pct > 0 else float("inf")

    if canopy_delta <= 0 or veg_delta <= 0:
        return ("Contradicted", "Tier 4",
                "The modelled landscape response does not show the canopy or vegetation "
                "gain that the reported planting would require. Under the supplied parameters "
                "the claim is not supported by the spatial evidence.")

    if ratio >= 0.75 and r2_canopy >= 0.6:
        return ("Corroborated", "Tier 2",
                f"Under the supplied planting and survival parameters the modelled canopy "
                f"gain ({observed_pct:.2f} pp over {int(series['Year'].iloc[-1]) - int(series['Year'].iloc[0])} years) "
                f"is broadly consistent with the reported figure. Ground verification of "
                f"planting registers and survival plots is still required to close this out.")

    if ratio >= 0.35:
        return ("Partially corroborated", "Tier 3",
                f"The modelled canopy gain ({observed_pct:.2f} pp) is directionally "
                f"consistent with the claim but smaller than the reported figure would imply "
                f"({claim_expected_pct:.2f} pp expected). Survival, species mix, or "
                f"disturbance losses may explain the gap.")

    return ("Requires evidence", "Tier 3",
            f"Only a small fraction of the expected canopy response is modelled "
            f"({observed_pct:.2f} pp observed vs {claim_expected_pct:.2f} pp expected). "
            f"Additional ground evidence is required before this claim can be read as supported.")


# ============================================================
# CORE LOGIC — SPATIAL AUDIT
# ============================================================

def make_synthetic_ndvi(years, trend_start, trend_end, noise=0.02, seed=42):
    """Yearly NDVI samples with a linear trend plus noise.
    SYNTHETIC — placeholder for a Sentinel-2 NDVI time series."""
    rng = np.random.default_rng(seed)
    ys = np.array(years, dtype=float)
    trend = np.linspace(trend_start, trend_end, len(ys))
    return (trend + rng.normal(0, noise, len(ys))).round(3)


def spatial_change_verdict(claim_direction, slope, r2):
    """Turn a slope and R² into a verdict on the reported direction."""
    observed_direction = "increase" if slope > 0 else "decline" if slope < 0 else "flat"
    if claim_direction == observed_direction and r2 >= 0.5:
        return "Corroborated", "Tier 2", (
            f"Independent spatial series moves {observed_direction} (slope {slope:+.3f}/yr, "
            f"R²={r2:.2f}), consistent with the reported direction."
        )
    if claim_direction == observed_direction:
        return "Partially corroborated", "Tier 3", (
            f"Direction matches ({observed_direction}), but the trend fit is weak "
            f"(R²={r2:.2f}). More samples or a longer window are needed."
        )
    if claim_direction is None:
        return "Unverifiable", "Tier 4", "No directional claim was supplied to test."
    return "Contradicted", "Tier 4", (
        f"Spatial series moves {observed_direction} (slope {slope:+.3f}/yr), "
        f"opposite to the reported {claim_direction}."
    )


# ============================================================
# CORE LOGIC — GOVERNANCE TIERING
# ============================================================

def assign_tier(sources):
    """Assign a corroboration tier from a list of source dicts:
       {"source": str, "type": "institutional|ngo|media|government|self", "independent": bool}
    Rules:
       Tier 1: >=2 independent sources incl. at least one institutional
       Tier 2: >=2 independent sources
       Tier 3: exactly 1 independent source
       Tier 4: none, or only self-reported
    """
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
# DASHBOARD
# ============================================================
if page == "📊 Dashboard":
    st.header("📊 ESG Assurance Dashboard")
    st.write(f"**{organization}** · {sector} · ESG report year **{report_year}**")

    claims = A()["claims"]
    ledger = A()["evidence_ledger"]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Claims extracted", len(claims))
    col2.metric("Evidence items logged", len(ledger))
    col3.metric("Standards matched", len(A()["standards_matches"]))
    col4.metric("Modules with evidence", len({e["module"] for e in ledger}))

    st.markdown("---")
    st.subheader("Assurance Architecture")
    st.markdown(
        "**Report text → Claims → Standards → Evidence requirements → "
        "Environmental / Spatial / Governance / Community checks → Assurance verdict**"
    )

    st.markdown("---")
    st.subheader("Pipeline status")
    pipeline_status = pd.DataFrame([
        {"Stage": "Report text ingested", "Done": bool(A()["raw_report_text"]), "Go to": "📄 Report & Claims"},
        {"Stage": "Claims extracted", "Done": bool(A()["claims"]), "Go to": "📄 Report & Claims"},
        {"Stage": "Standards mapped", "Done": bool(A()["standards_matches"]), "Go to": "📚 Standards"},
        {"Stage": "Impact picture assessed", "Done": bool(A()["environmental"] or A()["spatial"]), "Go to": "🌳 Impact Picture Validation"},
        {"Stage": "Spatial audit run", "Done": bool(A()["spatial"]), "Go to": "🛰️ Spatial Audit"},
        {"Stage": "Governance evidence logged", "Done": bool(A()["governance"]), "Go to": "🏛️ Governance"},
        {"Stage": "Community benefit assessed", "Done": bool(A()["community"]), "Go to": "🤝 Community Benefit"},
    ])
    st.dataframe(pipeline_status, use_container_width=True, hide_index=True)

    st.info(
        "This dashboard reflects **what you have actually entered**. "
        "Nothing is pre-filled. Run through the pipeline stages in the sidebar."
    )


# ============================================================
# REPORT & CLAIMS
# ============================================================
elif page == "📄 Report & Claims":
    st.header("📄 Report & Claims")

    st.subheader("1. Paste or upload the ESG report text")
    st.caption(
        "Prototype: paste the section of the report you want to audit. "
        "TODO_LIVE: wire this to PDF/HTML ingestion."
    )

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
            "In 2025 the company reported that 100,000 trees were planted between "
            "2023 and 2025. Water quality around the project area improved by 15%. "
            "Air emissions were reduced by 20%. 340 jobs were created for local "
            "community members. Board-level ESG oversight was established."
        ),
        height=200,
    )
    A()["raw_report_text"] = text

    if st.button("Extract claims", type="primary"):
        claims = extract_claims(text)
        A()["claims"] = claims
        A()["standards_matches"] = {
            c["id"]: match_standards(c["claim"], c["area"]) for c in claims
        }
        st.success(f"Extracted {len(claims)} claim(s).")

    if A()["claims"]:
        st.markdown("---")
        st.subheader("2. Extracted claims")
        claims_df = pd.DataFrame([
            {
                "ID": c["id"],
                "Area": c["area"],
                "Claim": c["claim"],
                "Magnitude": c["magnitude"],
                "Unit": c["unit"],
                "Standards": ", ".join(s["standard"] for s in A()["standards_matches"].get(c["id"], [])),
            }
            for c in A()["claims"]
        ])
        st.dataframe(claims_df, use_container_width=True, hide_index=True)


# ============================================================
# STANDARDS
# ============================================================
elif page == "📚 Standards":
    st.header("📚 Standards Cross-Reference")

    if not A()["claims"]:
        st.warning("Extract claims first on the **Report & Claims** tab.")
    else:
        st.subheader("Claim → Standard mapping (with the keyword that fired)")
        for c in A()["claims"]:
            matches = A()["standards_matches"].get(c["id"], [])
            with st.expander(f"{c['id']} — {c['claim'][:90]}"):
                if not matches:
                    st.write("No standards matched. Consider adding an explicit area tag.")
                    continue
                rows = []
                for m in matches:
                    rows.append({
                        "Standard": m["standard"],
                        "Description": STANDARDS[m["standard"]]["description"],
                        "Matched on": m["why"],
                        "Assurance areas": ", ".join(STANDARDS[m["standard"]]["areas"]),
                    })
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("Standards registry")
    reg = pd.DataFrame([
        {"Standard": k, "Description": v["description"], "Keywords": ", ".join(v["keywords"])}
        for k, v in STANDARDS.items()
    ])
    st.dataframe(reg, use_container_width=True, hide_index=True)


# ============================================================
# IMPACT PICTURE VALIDATION
# ============================================================
elif page == "🌳 Impact Picture Validation":
    st.header("🌳 Impact Picture Validation")
    st.markdown("### Don't only check what the ESG report says. Check what the landscape shows.")
    st.caption(
        "This module is **a responsive model**, not a fixed table. Change the planting or "
        "survival parameters below and the tree-cover trajectory — and the verdict — will move."
    )

    st.markdown("---")
    st.subheader("1. Reported planting claim")

    c1, c2, c3, c4 = st.columns(4)
    reported_trees = c1.number_input("Trees reported planted", min_value=0, value=100_000, step=1_000)
    baseline_year = c2.selectbox("Baseline year", [2021, 2022, 2023, 2024], index=2)
    validation_year = c3.selectbox("Reporting year", [2023, 2024, 2025], index=2)
    area_ha = c4.number_input("Project area (ha)", min_value=1.0, value=500.0, step=50.0)

    survival_rate_pct = st.slider(
        "Assumed survival rate (%) — this is a modelling assumption, not a verified figure",
        10, 100, 75,
        help="Silvicultural reality: many tree-planting programmes see 30–70% survival at year 3. "
             "The model uses this to convert reported planting into established canopy.",
    )

    if validation_year <= baseline_year:
        st.error("Reporting year must be later than baseline year.")
        st.stop()

    st.markdown("---")
    st.subheader("2. Modelled landscape response")

    series = tree_model(reported_trees, area_ha, baseline_year, validation_year, survival_rate_pct)
    A()["environmental"]["tree_series"] = series

    st.dataframe(series, use_container_width=True, hide_index=True)

    col1, col2, col3, col4 = st.columns(4)
    first, last = series.iloc[0], series.iloc[-1]
    col1.metric("Tree cover (baseline)", f"{first['Tree Cover (%)']:.2f}%")
    col2.metric("Tree cover (reporting)", f"{last['Tree Cover (%)']:.2f}%",
                f"{last['Tree Cover (%)'] - first['Tree Cover (%)']:+.2f} pp")
    col3.metric("Vegetation index (reporting)", f"{last['Vegetation Index']:.3f}",
                f"{last['Vegetation Index'] - first['Vegetation Index']:+.3f}")
    col4.metric("Trees established (modelled)", f"{int(last['Established Trees (modelled)']):,}")

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=series["Year"], y=series["Tree Cover (%)"],
                             mode="lines+markers", name="Tree Cover (%)"))
    fig.add_trace(go.Scatter(x=series["Year"], y=series["Vegetation Index"] * 100,
                             mode="lines+markers", name="Vegetation Index × 100"))
    fig.update_layout(height=340, xaxis_title="Year", yaxis_title="% / scaled index",
                      legend=dict(orientation="h", y=1.1),
                      margin=dict(t=20, b=30, l=40, r=20))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.subheader("3. Impact picture verdict")
    verdict, tier, rationale = assess_tree_claim(series, reported_trees)

    st.markdown(
        f'<div class="verdict-card {VERDICTS[verdict]["css"]}">'
        f'<b>Verdict:</b> {verdict} &nbsp;·&nbsp; <b>{tier}</b><br>{rationale}</div>',
        unsafe_allow_html=True,
    )
    st.caption(EVIDENCE_TIERS[tier])

    add_ledger("Impact Picture", f"Tree planting claim ({reported_trees:,} trees)",
               verdict, tier, synthetic=True)

    st.markdown("---")
    st.warning(
        "**Assurance limitation.** An increase in modelled or satellite-detected canopy does "
        "**not** prove that the exact number of reported trees was planted. Exact counts require "
        "planting registers, GPS plots, survival surveys, nursery records and/or independent "
        "field verification. This model is a decision-support tool, not an audit."
    )


# ============================================================
# SPATIAL AUDIT
# ============================================================
elif page == "🛰️ Spatial Audit":
    st.header("🛰️ Spatial Audit")
    st.caption(
        "Interactive AOI map and a change-detection calculation on an NDVI-style series. "
        "**The series is synthetic** — the calculation and verdict logic are real."
    )

    st.subheader("1. Area of interest")

    c1, c2, c3, c4 = st.columns(4)
    lat = c1.number_input("Latitude", value=-0.850000, format="%.6f")
    lon = c2.number_input("Longitude", value=37.150000, format="%.6f")
    radius_km = c3.number_input("AOI radius (km)", min_value=0.5, value=5.0, step=0.5)
    claim_direction = c4.selectbox("Claimed direction", ["increase", "decline", "unspecified"])

    # Build an AOI polygon (approximate — good enough for a prototype map)
    def circle_polygon(lat0, lon0, r_km, n=64):
        dlat = r_km / 111.0
        dlon = r_km / (111.0 * math.cos(math.radians(lat0)))
        theta = np.linspace(0, 2 * math.pi, n)
        return (lat0 + dlat * np.sin(theta)).tolist(), (lon0 + dlon * np.cos(theta)).tolist()

    poly_lat, poly_lon = circle_polygon(lat, lon, radius_km)

    fig_map = go.Figure()
    fig_map.add_trace(go.Scattermapbox(
        lat=poly_lat, lon=poly_lon, mode="lines", fill="toself",
        name="AOI", line=dict(color="#cf222e", width=2),
        fillcolor="rgba(207,34,46,0.15)",
    ))
    fig_map.add_trace(go.Scattermapbox(
        lat=[lat], lon=[lon], mode="markers",
        marker=dict(size=10, color="#cf222e"), name="Centre",
    ))
    fig_map.update_layout(
        mapbox=dict(style="open-street-map", center=dict(lat=lat, lon=lon),
                    zoom=int(max(4, 11 - math.log2(radius_km + 1)))),
        height=380, margin=dict(t=0, b=0, l=0, r=0),
        legend=dict(orientation="h", y=1.02),
    )
    st.plotly_chart(fig_map, use_container_width=True)

    st.caption(
        "TODO_LIVE: replace the base map with a Sentinel-2 / GEE tile layer and clip to the "
        "supplied GeoJSON project boundary. The AOI here is a generated circle — real projects "
        "should supply an actual polygon."
    )

    st.markdown("---")
    st.subheader("2. NDVI-style change detection")

    c1, c2, c3 = st.columns(3)
    start_year = c1.number_input("Series start year", value=2019, step=1)
    end_year = c2.number_input("Series end year", value=2025, step=1)
    noise = c3.slider("Synthetic noise", 0.0, 0.08, 0.02, step=0.005)

    years = list(range(int(start_year), int(end_year) + 1))
    if len(years) < 3:
        st.warning("Need at least 3 years for a trend fit.")
        st.stop()

    ndvi = make_synthetic_ndvi(years, 0.62, 0.51, noise=noise, seed=abs(hash((lat, lon))) % 2**32)

    df = pd.DataFrame({"Year": years, "NDVI (synthetic)": ndvi})
    st.dataframe(df, use_container_width=True, hide_index=True)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=years, y=ndvi, mode="markers+lines", name="NDVI (synthetic)"))
    slope, intercept = np.polyfit(years, ndvi, 1)
    fig.add_trace(go.Scatter(x=years, y=slope * np.array(years) + intercept,
                             mode="lines", name=f"Trend ({slope:+.4f}/yr)", line=dict(dash="dash")))
    fig.update_layout(height=320, xaxis_title="Year", yaxis_title="NDVI",
                      legend=dict(orientation="h", y=1.1),
                      margin=dict(t=20, b=30, l=40, r=20))
    st.plotly_chart(fig, use_container_width=True)

    _, r2 = slope_and_r2(years, ndvi)
    verdict, tier, rationale = spatial_change_verdict(
        None if claim_direction == "unspecified" else claim_direction, slope, r2
    )

    st.markdown(
        f'<div class="verdict-card {VERDICTS[verdict]["css"]}">'
        f'<b>Verdict:</b> {verdict} &nbsp;·&nbsp; <b>{tier}</b><br>{rationale}</div>',
        unsafe_allow_html=True,
    )
    st.caption(
        f"Slope = {slope:+.4f}/yr · R² = {r2:.2f}. "
        "R² measures the fit of a straight line to the synthetic series — "
        "**not** the confidence of the underlying observation. A real "
        "implementation must weight confidence by data density and cloud cover."
    )

    A()["spatial"] = {"lat": lat, "lon": lon, "radius_km": radius_km,
                      "series": df, "slope": slope, "r2": r2,
                      "verdict": verdict, "tier": tier}
    add_ledger("Spatial", f"AOI NDVI trend at ({lat:.3f},{lon:.3f})",
               verdict, tier, synthetic=True)


# ============================================================
# WATER & AIR
# ============================================================
elif page == "💧 Water & Air":
    st.header("💧 Water & Air Environmental Validation")
    st.caption(
        "Enter or upload monitoring data. The prototype accepts typed values so you can "
        "see the trend logic run on your own numbers. **TODO_LIVE**: wire to OpenAQ / "
        "national monitoring APIs."
    )

    st.subheader("Water clarity (turbidity index — lower = clearer)")
    water_df = st.data_editor(
        pd.DataFrame({"Year": [2021, 2022, 2023, 2024, 2025],
                      "Turbidity index": [0.44, 0.42, 0.41, 0.39, 0.39]}),
        num_rows="dynamic", use_container_width=True, key="water_editor",
    )

    st.subheader("Air quality (PM2.5 µg/m³ — lower = cleaner)")
    air_df = st.data_editor(
        pd.DataFrame({"Year": [2021, 2022, 2023, 2024, 2025],
                      "PM2.5": [42, 41, 39, 40, 38]}),
        num_rows="dynamic", use_container_width=True, key="air_editor",
    )

    for name, df, value_col, improvement in [
        ("Water clarity", water_df, "Turbidity index", "decrease"),
        ("Air quality", air_df, "PM2.5", "decrease"),
    ]:
        if len(df) < 2:
            continue
        slope, r2 = slope_and_r2(df["Year"], df[value_col])
        improved = (slope < 0 and improvement == "decrease") or (slope > 0 and improvement == "increase")
        verdict = "Corroborated" if (improved and r2 >= 0.5) else \
                  "Partially corroborated" if improved else "Contradicted"
        tier = "Tier 2" if r2 >= 0.5 else "Tier 3"
        st.markdown(f"**{name}** — slope {slope:+.4f}/yr, R²={r2:.2f}")
        st.markdown(
            f'<div class="verdict-card {VERDICTS[verdict]["css"]}">'
            f'Verdict: <b>{verdict}</b> · {tier}</div>',
            unsafe_allow_html=True,
        )
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["Year"], y=df[value_col], mode="markers+lines"))
        fig.update_layout(height=240, margin=dict(t=10, b=20, l=40, r=20))
        st.plotly_chart(fig, use_container_width=True)
        add_ledger(name, f"{value_col} trend", verdict, tier, synthetic=True)

    st.warning(
        "Values shown are your typed inputs and are **not** independently sourced. "
        "Wire to a monitoring feed before using for anything other than a demonstration."
    )


# ============================================================
# GOVERNANCE
# ============================================================
elif page == "🏛️ Governance":
    st.header("🏛️ Governance Evidence & Corroboration")

    st.write(
        "Record the sources for a governance claim. The tier is **derived from the sources**, "
        "not assigned by hand."
    )

    st.subheader("Governance claim / issue")
    gov_claim = st.text_input(
        "Claim or issue to assess",
        value="Board-level ESG oversight is functioning effectively.",
    )

    st.subheader("Sources")
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

    tier, reason = assign_tier(st.session_state["gov_sources"])
    verdict = {"Tier 1": "Corroborated",
               "Tier 2": "Corroborated",
               "Tier 3": "Partially corroborated",
               "Tier 4": "Unverifiable"}[tier]

    st.markdown("---")
    st.markdown(
        f'<div class="verdict-card {VERDICTS[verdict]["css"]}">'
        f'<b>Corroboration tier:</b> {tier}<br>{reason}<br>'
        f'<b>Verdict:</b> {verdict}</div>',
        unsafe_allow_html=True,
    )

    A()["governance"] = {"claim": gov_claim, "sources": st.session_state["gov_sources"],
                         "tier": tier, "verdict": verdict}
    add_ledger("Governance", gov_claim, verdict, tier, synthetic=False)

    st.info(
        "Governance claims — especially ones touching human rights or allegations — "
        "should **never** be presented as established fact from a single source. The tier "
        "logic above encodes that discipline."
    )


# ============================================================
# COMMUNITY BENEFIT
# ============================================================
elif page == "🤝 Community Benefit":
    st.header("🤝 Community Benefit")

    st.write(
        "Record each reported community benefit and the strongest evidence class you hold for it."
    )

    evidence_classes = [
        "None",
        "Self-reported",
        "Photographs",
        "Community meeting minutes",
        "Third-party survey",
        "Payroll / audited records",
        "Government statistics",
    ]
    class_to_verdict = {
        "None": "Unverifiable",
        "Self-reported": "Requires evidence",
        "Photographs": "Partially corroborated",
        "Community meeting minutes": "Partially corroborated",
        "Third-party survey": "Partially corroborated",
        "Payroll / audited records": "Corroborated",
        "Government statistics": "Corroborated",
    }
    class_to_tier = {
        "None": "Tier 4", "Self-reported": "Tier 4",
        "Photographs": "Tier 3", "Community meeting minutes": "Tier 3",
        "Third-party survey": "Tier 2", "Payroll / audited records": "Tier 1",
        "Government statistics": "Tier 1",
    }

    if "comm_rows" not in st.session_state:
        st.session_state["comm_rows"] = [
            {"Benefit": "Local employment", "Reported": True, "Evidence class": "Payroll / audited records"},
            {"Benefit": "Local procurement", "Reported": True, "Evidence class": "Self-reported"},
            {"Benefit": "Community infrastructure", "Reported": True, "Evidence class": "Photographs"},
            {"Benefit": "Training", "Reported": True, "Evidence class": "Community meeting minutes"},
        ]

    edited = st.data_editor(
        pd.DataFrame(st.session_state["comm_rows"]),
        num_rows="dynamic", use_container_width=True, key="comm_editor",
        column_config={
            "Evidence class": st.column_config.SelectboxColumn(options=evidence_classes)
        },
    )
    st.session_state["comm_rows"] = edited.to_dict("records")

    rows = []
    for r in st.session_state["comm_rows"]:
        cls = r.get("Evidence class", "None")
        v = class_to_verdict.get(cls, "Unverifiable")
        t = class_to_tier.get(cls, "Tier 4")
        rows.append({"Benefit": r["Benefit"], "Reported": r["Reported"],
                     "Evidence class": cls, "Verdict": v, "Tier": t})
        add_ledger("Community", r["Benefit"], v, t, synthetic=False)

    st.markdown("---")
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    A()["community"] = rows


# ============================================================
# ASSURANCE RESULT
# ============================================================
elif page == "📋 Assurance Result":
    st.header("📋 Overall Assurance Result")

    ledger = A()["evidence_ledger"]
    if not ledger:
        st.warning("No evidence has been logged yet. Run through the pipeline tabs first.")
        st.stop()

    df = pd.DataFrame(ledger)
    df["score"] = df["verdict"].map(lambda v: VERDICTS.get(v, {}).get("score", 0.0))

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Evidence items", len(df))
    col2.metric("Synthetic items", int(df["synthetic"].sum()))
    col3.metric("Independent items", int((~df["synthetic"]).sum()))
    overall = df["score"].mean() * 100
    col4.metric("Assurance indicator", f"{overall:.0f}%")

    st.progress(min(overall / 100.0, 1.0))

    st.markdown("---")
    st.subheader("Evidence-by-module breakdown")
    by_module = df.groupby("module").agg(
        items=("item", "count"),
        mean_score=("score", "mean"),
    ).reset_index()
    by_module["mean_score"] = (by_module["mean_score"] * 100).round(0).astype(int).astype(str) + "%"
    st.dataframe(by_module, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("Full evidence ledger")
    st.dataframe(df[["module", "item", "verdict", "tier", "synthetic", "timestamp"]],
                 use_container_width=True, hide_index=True)

    st.markdown("---")
    st.warning(
        "The assurance indicator is the **mean of per-item verdict scores** across everything "
        "you have logged. It is a convenience summary, not an audit opinion, certification or "
        "legal conclusion. Any item marked `synthetic = True` is a modelled or demonstration "
        "figure and must be replaced with real evidence before this is used externally."
    )

    st.download_button(
        "Download evidence ledger (CSV)",
        df.to_csv(index=False).encode("utf-8"),
        file_name=f"uujuzi_evidence_ledger_{datetime.now():%Y%m%d_%H%M}.csv",
        mime="text/csv",
    )


# ============================================================
# EVIDENCE LEDGER (raw view)
# ============================================================
elif page == "🗂️ Evidence Ledger":
    st.header("🗂️ Evidence Ledger")
    st.caption(
        "Single source of truth. Every verdict anywhere in the app is written here with its "
        "module, tier, and whether it came from synthetic or user-supplied evidence."
    )
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
    f"Uujuzi ESG & Governance Assurance Checker · prototype · "
    f"{datetime.now():%Y-%m-%d %H:%M} · {organization}"
)
st.caption(
    "Every synthetic figure is labelled inline. Real integrations are marked TODO_LIVE. "
    "GIS and satellite evidence must be interpreted according to spatial resolution, "
    "temporal coverage and methodology."
)
