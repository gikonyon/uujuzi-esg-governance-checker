"""
Uujuzi ESG & Governance Assurance Checker — Streamlit UI.
Logic lives in uujuzi_core.py so this file stays readable.
"""

from datetime import datetime

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import uujuzi_core as core

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
# SESSION STATE
# ============================================================
if "assessment" not in st.session_state:
    st.session_state["assessment"] = core.new_assessment(
        "Demo Organization", "Agriculture", 2026
    )

def A():
    return st.session_state["assessment"]

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
# REPORT & CLAIMS
# ============================================================
elif page == "📄 Report & Claims":
    st.header("📄 Report & Claims")
    st.caption("Upload an ESG / SDID report as PDF or TXT. Extraction happens locally.")

    st.subheader("1. Upload the report")
    uploaded = st.file_uploader("Choose a PDF or TXT file", type=["pdf", "txt"])

    if uploaded is not None:
        file_bytes = uploaded.read()
        size_kb = len(file_bytes) / 1024

        if uploaded.name.lower().endswith(".pdf"):
            with st.spinner(f"Extracting from {uploaded.name}…"):
                parsed = core.extract_pdf_text(file_bytes, max_pages=60)

            if parsed["errors"]:
                with st.expander(f"Extraction notes ({len(parsed['errors'])})"):
                    for e in parsed["errors"]:
                        st.caption(f"• {e}")

            st.success(
                f"Parsed **{parsed['pages_processed']} of {parsed['pages_total']} pages** · "
                f"{len(parsed['text']):,} chars · {len(parsed['tables'])} tables · {size_kb:,.0f} KB"
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
        with st.expander("First 3,000 characters", expanded=False):
            st.text(A()["raw_report_text"][:3000])

        tables = A().get("parsed_tables", [])
        if tables:
            st.markdown(f"**Tables detected: {len(tables)}**")
            opts = [f"Page {t['page']} — {t['table'].shape[0]}×{t['table'].shape[1]}" for t in tables]
            choice = st.selectbox("Preview a table", opts)
            st.dataframe(tables[opts.index(choice)]["table"], use_container_width=True)

    st.markdown("---")
    st.subheader("3. Confirm text and extract claims")
    text = st.text_area(
        "Report text (editable)",
        value=A().get("raw_report_text", "") or (
            "In 2026 the company reported that 100,000 trees were planted at its "
            "Kakuzi estate operations between 2024 and 2026. Water quality around "
            "the project area improved by 15%. 340 jobs were created."
        ),
        height=240,
    )
    A()["raw_report_text"] = text

    if st.button("Extract claims", type="primary"):
        A()["claims"] = core.extract_claims(text)
        A()["standards_matches"] = {
            c["id"]: core.match_standards(c["claim"], c["area"]) for c in A()["claims"]
        }
        for c in A()["claims"]:
            cat, missing = core.classify_claim_verifiability(c["claim"])
            c["verifiability"] = cat
            c["missing_evidence"] = missing
        st.success(f"Extracted {len(A()['claims'])} claim(s).")

    if A()["claims"]:
        st.markdown("---")
        st.subheader("4. Claim Verifiability Map")
        rows = []
        for c in A()["claims"]:
            cat = c.get("verifiability", "UNVERIFIABLE")
            rows.append({
                "ID": c["id"], "Area": c["area"], "Claim": c["claim"],
                "Category": core.VERIFIABILITY_LABELS[cat],
                "Missing evidence": c.get("missing_evidence", ""),
            })
        vmap = pd.DataFrame(rows)
        st.dataframe(vmap, use_container_width=True, hide_index=True)

        counts = vmap["Category"].value_counts().to_dict()
        cols = st.columns(5)
        for i, key in enumerate(core.VERIFIABILITY_LABELS.values()):
            cols[i].metric(key, counts.get(key, 0))

        st.markdown("**What each category means**")
        for key, label in core.VERIFIABILITY_LABELS.items():
            st.markdown(f"- **{label}** — {core.VERIFIABILITY_EXPLANATIONS[key]}")

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
                     "Description": core.STANDARDS[m["standard"]]["description"],
                     "Matched on": m["why"]}
                    for m in matches
                ]), use_container_width=True, hide_index=True)

# ============================================================
# GIS ARCHIVE VERIFICATION
# ============================================================
elif page == "🛰️ GIS Archive Verification":
    st.header("🛰️ GIS Archive Verification")
    st.caption("Verifies a spatially-verifiable claim against public archive data.")

    spatial_claims = [c for c in A().get("claims", [])
                      if c.get("verifiability") == "SPATIALLY_VERIFIABLE"]
    if spatial_claims:
        st.info(f"{len(spatial_claims)} spatially-verifiable claim(s) available from the report.")
    else:
        st.warning("No spatially-verifiable claims yet. Load a report first.")

    default_claim = spatial_claims[0]["claim"] if spatial_claims else "100,000 trees planted 2024–2026"
    claim_text = st.text_input("Claim", default_claim)

    c1, c2, c3 = st.columns(3)
    baseline_year = c1.selectbox("Baseline year", [2023, 2024, 2025], index=1)
    reporting_year = c2.selectbox("Reporting year", [2026, 2025], index=0)
    claim_direction = c3.selectbox("Claimed direction", ["increase", "decline", "unspecified"])

    st.subheader("Location")
    loc_method = st.radio(
        "Specify location",
        ["Type a place name", "Enter coordinates manually"],
        horizontal=True,
    )

    lat = lon = None
    place_label = ""
    geocode_ok = False

    if loc_method == "Type a place name":
        place_name = st.text_input("Place name", "Kakuzi estate, Murang'a County, Kenya")
        if st.button("Geocode location"):
            with st.spinner("Geocoding via OpenStreetMap…"):
                g = core.geocode_place(place_name)
            if g:
                st.session_state["geo"] = g
                st.success(f"Resolved to: {g['display_name']}")
            else:
                st.warning("Geocoding failed — enter coordinates manually below.")
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

    plat, plon = core.circle_polygon(lat, lon, radius_km)
    fmap = go.Figure()
    fmap.add_trace(go.Scattermapbox(
        lat=plat, lon=plon, mode="lines", fill="toself",
        line=dict(color="#cf222e", width=2),
        fillcolor="rgba(207,34,46,0.15)", name="AOI",
    ))
    fmap.add_trace(go.Scattermapbox(
        lat=[lat], lon=[lon], mode="markers",
        marker=dict(size=10, color="#cf222e"), name="Centre",
    ))
    fmap.update_layout(
        mapbox=dict(
            style="open-street-map",
            center=dict(lat=lat, lon=lon),
            zoom=int(max(4, 11 - np.log2(radius_km + 1))),
        ),
        height=360, margin=dict(t=0, b=0, l=0, r=0),
        legend=dict(orientation="h", y=1.02),
    )
    st.plotly_chart(fmap, use_container_width=True)
    st.caption(f"AOI centred on **{place_label}**. Radius {radius_km:.1f} km.")

    st.subheader("Archive verification")
    years = list(range(baseline_year, reporting_year + 1))

    with st.spinner("Querying Global Forest Watch archive…"):
        gfw_df = core.gfw_tree_cover_loss(lat, lon, radius_km, baseline_year, reporting_year)

    if gfw_df is not None and not gfw_df.empty:
        st.success(f"Retrieved {len(gfw_df)} year(s) from Global Forest Watch.")
        series_df = gfw_df.copy()
        series_df["source"] = "Global Forest Watch — UMD tree-cover loss"
        series_df["synthetic"] = False
    else:
        st.warning(
            "Global Forest Watch returned no data for this AOI. Enter figures manually "
            "below — the app will not invent values."
        )
        manual = st.data_editor(
            pd.DataFrame({"year": years, "loss_ha": [0.0] * len(years)}),
            num_rows="fixed", use_container_width=True, key="manual_gfw",
        )
        series_df = manual.copy()
        series_df["source"] = "User-supplied"
        series_df["synthetic"] = True

    st.dataframe(series_df, use_container_width=True, hide_index=True)

    if "loss_ha" in series_df.columns and len(series_df) >= 3:
        slope, r2 = core.slope_and_r2(series_df["year"], series_df["loss_ha"])
        verdict, tier, rationale = core.spatial_verdict(
            None if claim_direction == "unspecified" else claim_direction,
            -slope,
            r2,
            len(series_df),
        )
        css = core.VERDICTS[verdict]["css"]
        st.markdown(
            f'<div class="verdict-card {css}">'
            f'<b>Verdict:</b> {verdict} &nbsp;·&nbsp; <b>{tier}</b><br>{rationale}</div>',
            unsafe_allow_html=True,
        )
        st.caption(
            f"Slope of loss = {slope:+.4f} ha/yr · R² = {r2:.2f}. "
            "A declining loss slope is treated as a positive vegetation trend."
        )
        core.add_ledger(
            A(), "Spatial",
            f"AOI verification at {place_label} ({baseline_year}–{reporting_year})",
            verdict, tier,
            source="Global Forest Watch" if not series_df["synthetic"].iloc[0] else "User-supplied",
            synthetic=bool(series_df["synthetic"].iloc[0]),
        )
        A()["spatial"] = {
            "lat": lat, "lon": lon, "radius_km": radius_km,
            "series": series_df, "verdict": verdict, "tier": tier,
        }
    else:
        st.info("Add at least 3 years of data to compute a trend.")

    st.markdown("---")
    st.warning(
        "**What this verdict does and does not mean.** Tree-cover change can be caused by "
        "planting, natural regrowth, fire, logging, or land-use change. Consistency between "
        "archive data and a reported claim is evidence the claim *can* be true, not proof "
        "of the number of trees planted."
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

    tier, reason = core.assign_governance_tier(sources)
    verdict = {"Tier 1": "Corroborated", "Tier 2": "Corroborated",
               "Tier 3": "Partially corroborated", "Tier 4": "Unverifiable"}[tier]

    css = core.VERDICTS[verdict]["css"]
    st.markdown(
        f'<div class="verdict-card {css}">'
        f'<b>Tier:</b> {tier}<br>{reason}<br><b>Verdict:</b> {verdict}</div>',
        unsafe_allow_html=True,
    )
    A()["governance"] = {"claim": gov_claim, "sources": sources, "tier": tier, "verdict": verdict}
    core.add_ledger(A(), "Governance", gov_claim, verdict, tier,
                    source="see sources", synthetic=False)

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
    df["score"] = df["verdict"].map(lambda v: core.VERDICTS.get(v, {}).get("score", 0.0))

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
    st.dataframe(
        df[["module", "item", "verdict", "tier", "source", "synthetic", "timestamp"]],
        use_container_width=True, hide_index=True,
    )

    st.download_button(
        "Download evidence ledger (CSV)",
        df.to_csv(index=False).encode("utf-8"),
        file_name=f"uujuzi_evidence_ledger_{datetime.now():%Y%m%d_%H%M}.csv",
        mime="text/csv",
    )

    st.warning(
        "This indicator is the mean of per-item verdict scores. It is a convenience "
        "summary, not an audit opinion. Any row marked `synthetic = True` must be "
        "replaced with real evidence before external use."
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
