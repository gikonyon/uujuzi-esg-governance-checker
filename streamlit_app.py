import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

# ============================================================
# UUJUZI ESG & GOVERNANCE ASSURANCE CHECKER
# ============================================================
# Purpose:
#   Compare ESG claims against:
#   1. ESG / sustainability reports
#   2. International standards
#   3. Environmental indicators
#   4. GIS / satellite evidence
#   5. Governance evidence
#   6. Community benefit evidence
#
# FLAGSHIP FEATURE:
#   IMPACT PICTURE VALIDATION
#
# Example:
#   Company reports:
#       "100,000 trees planted between 2023 and 2025."
#
#   Uujuzi compares:
#       2023 baseline
#       2024 progress
#       2025 reporting year
#
#   Against:
#       tree cover
#       vegetation index
#       tree-cover loss
#       project area
#       evidence supplied by organization
#
# IMPORTANT:
#   Satellite/GIS evidence can support detectable landscape
#   change but should NOT be interpreted as an exact tree count.
# ============================================================


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Uujuzi ESG & Governance Assurance",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>

    .main-header {
        font-size: 2.4rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
    }

    .sub-header {
        font-size: 1.1rem;
        color: #666;
        margin-bottom: 1.5rem;
    }

    .impact-box {
        padding: 1.2rem;
        border-radius: 12px;
        border: 1px solid #ddd;
        margin-bottom: 1rem;
    }

    .metric-card {
        padding: 1rem;
        border-radius: 10px;
        border: 1px solid #ddd;
        text-align: center;
    }

    .small-note {
        font-size: 0.85rem;
        color: #666;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="main-header">🌍 UUJUZI ESG & Governance Assurance Checker</div>',
    unsafe_allow_html=True
)

st.markdown(
    """
    <div class="sub-header">
    From reported ESG claims to evidence-based impact validation.
    </div>
    """,
    unsafe_allow_html=True
)

st.info(
    "Core principle: Don't only check what the ESG report says. "
    "Check what the evidence and landscape show."
)


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("🌍 Uujuzi")

st.sidebar.markdown("### Assurance Workspace")

organization = st.sidebar.text_input(
    "Organization / Project",
    "Demo Organization"
)

sector = st.sidebar.selectbox(
    "Sector",
    [
        "Agriculture",
        "Banking & Finance",
        "Energy",
        "Manufacturing",
        "Mining",
        "Telecommunications",
        "Infrastructure",
        "NGO / Development",
        "Government",
        "Other"
    ]
)

report_year = st.sidebar.selectbox(
    "ESG Report Year",
    [2025, 2024, 2023, 2022, 2021],
    index=0
)

mode = st.sidebar.selectbox(
    "Assessment Mode",
    [
        "Demo Data",
        "Upload Evidence"
    ]
)

st.sidebar.markdown("---")

st.sidebar.markdown(
    """
    ### Evidence Philosophy

    Uujuzi separates:

    - Reported claims
    - Documentary evidence
    - GIS evidence
    - Satellite evidence
    - Governance evidence
    - Community evidence

    A reported claim is not automatically treated as a verified outcome.
    """
)


# ============================================================
# STANDARDS DATABASE
# ============================================================

STANDARDS = {
    "IFRS S1": {
        "name": "IFRS S1",
        "description": "General Requirements for Disclosure of Sustainability-related Financial Information",
        "areas": [
            "Governance",
            "Strategy",
            "Risk Management",
            "Metrics and Targets"
        ]
    },

    "IFRS S2": {
        "name": "IFRS S2",
        "description": "Climate-related disclosures",
        "areas": [
            "Climate Governance",
            "Climate Risks",
            "Climate Opportunities",
            "Metrics and Targets"
        ]
    },

    "ISO 14001": {
        "name": "ISO 14001",
        "description": "Environmental Management Systems",
        "areas": [
            "Environmental Management",
            "Compliance",
            "Environmental Objectives",
            "Monitoring"
        ]
    },

    "ISO 26000": {
        "name": "ISO 26000",
        "description": "Social Responsibility Guidance",
        "areas": [
            "Governance",
            "Human Rights",
            "Community",
            "Environment"
        ]
    },

    "ISO 45001": {
        "name": "ISO 45001",
        "description": "Occupational Health and Safety",
        "areas": [
            "Worker Safety",
            "Risk Management",
            "Incident Management",
            "Performance"
        ]
    },

    "UN SDGs": {
        "name": "UN Sustainable Development Goals",
        "description": "Global Sustainable Development Framework",
        "areas": [
            "Climate",
            "Water",
            "Environment",
            "Poverty",
            "Jobs",
            "Infrastructure",
            "Communities"
        ]
    },

    "UN Global Compact": {
        "name": "UN Global Compact",
        "description": "Principles for responsible business",
        "areas": [
            "Human Rights",
            "Labour",
            "Environment",
            "Anti-Corruption"
        ]
    }
}


# ============================================================
# DEMO ESG CLAIMS
# ============================================================

DEMO_CLAIMS = pd.DataFrame(
    {
        "Claim ID": [
            "ENV-001",
            "ENV-002",
            "SOC-001",
            "GOV-001",
            "CLM-001"
        ],

        "ESG Area": [
            "Environment",
            "Environment",
            "Community",
            "Governance",
            "Climate"
        ],

        "Claim": [
            "100,000 trees planted between 2023 and 2025",
            "Water quality improved around project area",
            "Local communities benefited from project employment",
            "Board-level ESG oversight established",
            "Company reduced environmental footprint"
        ],

        "Evidence Provided": [
            "ESG Report + planting records",
            "Water monitoring report",
            "Community impact report",
            "Board minutes",
            "ESG report"
        ],

        "Status": [
            "Requires GIS validation",
            "Requires environmental validation",
            "Document review",
            "Document review",
            "Requires environmental validation"
        ]
    }
)


# ============================================================
# UPLOAD DATA
# ============================================================

uploaded_file = None

if mode == "Upload Evidence":

    st.sidebar.markdown("### Upload Evidence")

    uploaded_file = st.sidebar.file_uploader(
        "Upload CSV evidence",
        type=["csv"]
    )


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def standard_match(claim):

    text = str(claim).lower()

    matches = []

    if any(
        x in text
        for x in [
            "environment",
            "tree",
            "water",
            "climate",
            "emission",
            "carbon"
        ]
    ):
        matches.extend(
            [
                "IFRS S2",
                "ISO 14001",
                "UN SDGs"
            ]
        )

    if any(
        x in text
        for x in [
            "community",
            "employment",
            "social"
        ]
    ):
        matches.extend(
            [
                "ISO 26000",
                "UN SDGs"
            ]
        )

    if any(
        x in text
        for x in [
            "board",
            "governance",
            "oversight"
        ]
    ):
        matches.extend(
            [
                "IFRS S1",
                "ISO 26000"
            ]
        )

    return list(dict.fromkeys(matches))


def classify_result(status):

    status = str(status).lower()

    if "validated" in status:
        return "Validated / Supported"

    if "partial" in status:
        return "Partially Supported"

    if "requires" in status:
        return "Requires Additional Evidence"

    if "document" in status:
        return "Documentary Review"

    return "Not Yet Assessed"


def generate_environmental_data():

    years = [2023, 2024, 2025]

    data = pd.DataFrame(
        {
            "Year": years,

            "Water Quality Index": [
                58,
                64,
                71
            ],

            "Air Quality Index": [
                61,
                65,
                69
            ],

            "Vegetation Index": [
                0.42,
                0.48,
                0.55
            ],

            "Tree Cover (%)": [
                31.2,
                33.7,
                36.1
            ],

            "Tree Cover Loss (ha)": [
                4.8,
                2.7,
                1.4
            ]
        }
    )

    return data


def generate_tree_validation_data():

    return pd.DataFrame(
        {
            "Year": [
                2023,
                2024,
                2025
            ],

            "Reported Trees Planted": [
                0,
                45000,
                100000
            ],

            "Tree Cover (%)": [
                31.2,
                33.7,
                36.1
            ],

            "Vegetation Index": [
                0.42,
                0.48,
                0.55
            ],

            "Tree Cover Loss (ha)": [
                4.8,
                2.7,
                1.4
            ],

            "Project Area (ha)": [
                500,
                500,
                500
            ]
        }
    )


def calculate_percentage_change(start, end):

    if start == 0:
        return np.nan

    return ((end - start) / start) * 100


def assess_tree_claim(
    reported_trees,
    baseline_tree_cover,
    final_tree_cover,
    baseline_vegetation,
    final_vegetation,
    tree_cover_loss
):

    tree_cover_change = final_tree_cover - baseline_tree_cover

    vegetation_change = final_vegetation - baseline_vegetation

    if tree_cover_change > 0 and vegetation_change > 0:

        if tree_cover_loss <= 2:

            return (
                "Positive spatial/environmental signal",
                "The available indicators show an increase in tree cover and vegetation "
                "between the baseline and reporting year, with relatively low reported "
                "tree-cover loss. This supports further verification of the planting claim."
            )

        return (
            "Mixed environmental signal",
            "Tree cover and vegetation increased, but tree-cover loss is also present. "
            "Additional project-level evidence is recommended."
        )

    if tree_cover_change > 0:

        return (
            "Partial spatial signal",
            "Tree cover increased, but vegetation evidence is less conclusive."
        )

    if vegetation_change > 0:

        return (
            "Partial vegetation signal",
            "Vegetation increased, but detectable tree-cover change is not sufficient "
            "to support the planting claim on its own."
        )

    return (
        "Insufficient spatial signal",
        "The supplied indicators do not show a clear positive change between "
        "the baseline and reporting year."
    )


def calculate_assurance_score(
    standards_score,
    environmental_score,
    governance_score,
    community_score,
    evidence_score
):

    score = (
        standards_score
        + environmental_score
        + governance_score
        + community_score
        + evidence_score
    ) / 5

    return round(score, 1)


# ============================================================
# LOAD TREE VALIDATION DATA
# ============================================================

if uploaded_file is not None:

    try:

        uploaded_data = pd.read_csv(uploaded_file)

        st.sidebar.success(
            f"Loaded {len(uploaded_data)} evidence records."
        )

    except Exception as e:

        st.sidebar.error(
            f"Could not read CSV: {e}"
        )

        uploaded_data = None

else:

    uploaded_data = None


# ============================================================
# NAVIGATION
# ============================================================

page = st.sidebar.radio(
    "Navigate",
    [
        "📊 Dashboard",
        "📄 Report Claims",
        "📚 Standards Checker",
        "🌳 Impact Picture Validation",
        "🛰️ GIS Change Detection",
        "💧 Water & Air",
        "🏛️ Governance",
        "🤝 Community Benefit",
        "📋 Assurance Result"
    ]
)


# ============================================================
# DASHBOARD
# ============================================================

if page == "📊 Dashboard":

    st.header("📊 ESG Assurance Dashboard")

    st.write(
        f"Organization: **{organization}**"
    )

    st.write(
        f"Sector: **{sector}** | ESG reporting year: **{report_year}**"
    )

    claims = DEMO_CLAIMS.copy()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "ESG Claims",
            len(claims)
        )

    with col2:
        st.metric(
            "Environmental Claims",
            len(
                claims[
                    claims["ESG Area"] == "Environment"
                ]
            )
        )

    with col3:
        st.metric(
            "GIS Validation",
            "Required"
        )

    with col4:
        st.metric(
            "Assurance Status",
            "Prototype"
        )

    st.markdown("---")

    st.subheader("Assurance Architecture")

    st.markdown(
        """
        **Report Claim → Standard → Evidence → GIS / Environmental Data
        → Governance → Community Outcome → Assurance Conclusion**
        """
    )

    st.markdown("---")

    st.subheader("🌳 Flagship Impact Picture")

    st.info(
        "Example: If an organization reports 100,000 trees planted between "
        "2023 and 2025, Uujuzi compares the reported claim with the "
        "2023 baseline, 2024 progress and 2025 landscape evidence."
    )

    st.write(
        "The objective is not simply to count what the report says. "
        "The objective is to establish whether independent evidence is "
        "consistent with the reported impact."
    )


# ============================================================
# REPORT CLAIMS
# ============================================================

elif page == "📄 Report Claims":

    st.header("📄 ESG Report Claims")

    st.write(
        "Enter or review the organization's reported ESG claims."
    )

    claims = DEMO_CLAIMS.copy()

    st.dataframe(
        claims,
        use_container_width=True,
        hide_index=True
    )

    st.markdown("---")

    st.subheader("Claim-to-Standard Mapping")

    for _, row in claims.iterrows():

        matched = standard_match(row["Claim"])

        st.markdown(
            f"**{row['Claim ID']} — {row['Claim']}**"
        )

        if matched:

            st.write(
                "Potential standards:",
                ", ".join(matched)
            )

        else:

            st.write(
                "No automatic standard match."
            )


# ============================================================
# STANDARDS CHECKER
# ============================================================

elif page == "📚 Standards Checker":

    st.header("📚 Standards Cross-Reference")

    selected_standard = st.selectbox(
        "Select Standard",
        list(STANDARDS.keys())
    )

    standard = STANDARDS[selected_standard]

    st.subheader(
        standard["name"]
    )

    st.write(
        standard["description"]
    )

    st.markdown("### Relevant assurance areas")

    for area in standard["areas"]:

        st.checkbox(
            area,
            value=False
        )

    st.markdown("---")

    st.subheader("ESG Claims Against Standards")

    claims = DEMO_CLAIMS.copy()

    results = []

    for _, row in claims.iterrows():

        matched = standard_match(row["Claim"])

        results.append(
            {
                "Claim ID": row["Claim ID"],
                "Claim": row["Claim"],
                "Potential Standards": ", ".join(matched)
            }
        )

    st.dataframe(
        pd.DataFrame(results),
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# 🌳 IMPACT PICTURE VALIDATION
# ============================================================

elif page == "🌳 Impact Picture Validation":

    st.header("🌳 Impact Picture Validation")

    st.markdown(
        """
        ### Don't only check what the ESG report says.
        ### Check what the landscape shows.
        """
    )

    st.write(
        """
        This module compares an organization's reported environmental
        intervention with a time series of spatial/environmental indicators.
        """
    )

    # --------------------------------------------------------
    # CLAIM INPUT
    # --------------------------------------------------------

    st.subheader("1. Reported Tree Planting Claim")

    col1, col2, col3 = st.columns(3)

    with col1:

        reported_trees = st.number_input(
            "Trees reported planted",
            min_value=0,
            value=100000,
            step=1000
        )

    with col2:

        baseline_year = st.selectbox(
            "Baseline year",
            [2023, 2022, 2021],
            index=0
        )

    with col3:

        validation_year = st.selectbox(
            "Reporting year",
            [2025, 2024, 2023],
            index=0
        )

    st.text_area(
        "Reported claim",
        value=(
            f"{reported_trees:,} trees planted between "
            f"{baseline_year} and {validation_year}."
        )
    )

    # --------------------------------------------------------
    # PROJECT LOCATION
    # --------------------------------------------------------

    st.subheader("2. Project Location")

    col1, col2, col3 = st.columns(3)

    with col1:

        latitude = st.number_input(
            "Latitude",
            value=-1.286389,
            format="%.6f"
        )

    with col2:

        longitude = st.number_input(
            "Longitude",
            value=36.817223,
            format="%.6f"
        )

    with col3:

        project_area = st.number_input(
            "Project area (ha)",
            min_value=1.0,
            value=500.0
        )

    location_df = pd.DataFrame(
        {
            "latitude": [latitude],
            "longitude": [longitude]
        }
    )

    st.map(
        location_df,
        latitude="latitude",
        longitude="longitude",
        zoom=8
    )

    st.caption(
        "Prototype project location. Future versions can accept "
        "GeoJSON/shapefiles defining the complete project boundary."
    )

    # --------------------------------------------------------
    # DATA
    # --------------------------------------------------------

    st.subheader("3. 2023 → 2025 Landscape Evidence")

    tree_data = generate_tree_validation_data()

    # Adjust reported claim to user's input
    tree_data.loc[
        tree_data["Year"] == validation_year,
        "Reported Trees Planted"
    ] = reported_trees

    st.dataframe(
        tree_data,
        use_container_width=True,
        hide_index=True
    )

    # --------------------------------------------------------
    # CHANGES
    # --------------------------------------------------------

    baseline = tree_data[
        tree_data["Year"] == baseline_year
    ].iloc[0]

    final = tree_data[
        tree_data["Year"] == validation_year
    ].iloc[0]

    tree_cover_change = (
        final["Tree Cover (%)"]
        - baseline["Tree Cover (%)"]
    )

    vegetation_change = (
        final["Vegetation Index"]
        - baseline["Vegetation Index"]
    )

    tree_cover_percent_change = calculate_percentage_change(
        baseline["Tree Cover (%)"],
        final["Tree Cover (%)"]
    )

    vegetation_percent_change = calculate_percentage_change(
        baseline["Vegetation Index"],
        final["Vegetation Index"]
    )

    # --------------------------------------------------------
    # METRICS
    # --------------------------------------------------------

    st.subheader("4. Landscape Change")

    col1, col2, col3, col4 = st.columns(4)

    with col1:

        st.metric(
            "Tree Cover",
            f"{final['Tree Cover (%)']:.1f}%",
            f"{tree_cover_change:+.1f} pp"
        )

    with col2:

        st.metric(
            "Vegetation Index",
            f"{final['Vegetation Index']:.2f}",
            f"{vegetation_change:+.2f}"
        )

    with col3:

        st.metric(
            "Tree Cover Loss",
            f"{final['Tree Cover Loss (ha)']:.1f} ha"
        )

    with col4:

        st.metric(
            "Reported Trees",
            f"{reported_trees:,}"
        )

    # --------------------------------------------------------
    # CHART
    # --------------------------------------------------------

    st.subheader("5. Visual Time Series")

    chart_data = tree_data.set_index("Year")

    st.line_chart(
        chart_data[
            [
                "Tree Cover (%)",
                "Vegetation Index"
            ]
        ]
    )

    st.caption(
        "Prototype visualization. Production implementation should "
        "replace synthetic values with project-specific GIS/satellite data."
    )

    # --------------------------------------------------------
    # ASSESSMENT
    # --------------------------------------------------------

    assessment, explanation = assess_tree_claim(
        reported_trees,
        baseline["Tree Cover (%)"],
        final["Tree Cover (%)"],
        baseline["Vegetation Index"],
        final["Vegetation Index"],
        final["Tree Cover Loss (ha)"]
    )

    st.subheader("6. Impact Picture Assessment")

    if assessment == "Positive spatial/environmental signal":

        st.success(
            f"🌳 {assessment}"
        )

    elif assessment == "Mixed environmental signal":

        st.warning(
            f"⚠️ {assessment}"
        )

    else:

        st.info(
            f"ℹ️ {assessment}"
        )

    st.write(explanation)

    # --------------------------------------------------------
    # IMPORTANT LIMITATION
    # --------------------------------------------------------

    st.warning(
        """
        IMPORTANT ASSURANCE LIMITATION:

        An increase in satellite-detected tree cover or vegetation does
        NOT prove that exactly the reported number of trees was planted.

        For example, 100,000 reported trees cannot be converted directly
        into "100,000 trees verified" using satellite imagery alone.

        GIS evidence should instead be interpreted as evidence of:

        • detectable vegetation change
        • tree-cover change
        • project-area consistency
        • persistence over time
        • possible disturbance/loss
        • spatial consistency with the reported intervention

        Exact tree counts require additional ground-level evidence such
        as planting registers, GPS plots, survival surveys, photographs,
        nursery records and/or independent field verification.
        """
    )

    # --------------------------------------------------------
    # EVIDENCE MATRIX
    # --------------------------------------------------------

    st.subheader("7. Evidence Matrix")

    evidence_matrix = pd.DataFrame(
        {
            "Evidence": [
                "ESG report claim",
                "Planting records",
                "Project GPS boundary",
                "2023 baseline imagery",
                "2024 progress imagery",
                "2025 reporting-year imagery",
                "Tree-cover change",
                "Vegetation change",
                "Tree-cover loss",
                "Ground verification"
            ],

            "Available": [
                "Yes",
                "Required",
                "Required",
                "Required",
                "Recommended",
                "Required",
                "Prototype",
                "Prototype",
                "Prototype",
                "Required"
            ],

            "Purpose": [
                "Defines the reported claim",
                "Supports reported planting numbers",
                "Defines the analysis area",
                "Establishes baseline",
                "Shows intermediate change",
                "Shows reporting-year condition",
                "Detects spatial change",
                "Supports vegetation assessment",
                "Checks possible disturbance",
                "Supports physical verification"
            ]
        }
    )

    st.dataframe(
        evidence_matrix,
        use_container_width=True,
        hide_index=True
    )

    # --------------------------------------------------------
    # CLAIM LANGUAGE
    # --------------------------------------------------------

    st.subheader("8. Recommended Assurance Language")

    st.code(
        f"""
Reported claim:
{reported_trees:,} trees planted between {baseline_year} and {validation_year}.

Spatial evidence:
The available landscape indicators show a change in tree cover
and vegetation between the baseline and reporting year.

Assurance interpretation:
Spatial evidence is CONSISTENT WITH a detectable environmental
change, subject to verification of the project boundary and
supporting ground-level evidence.

The spatial analysis DOES NOT independently verify the exact number
of trees planted.

Additional evidence required:
- planting registers
- GPS/project boundaries
- survival data
- field photographs
- independent verification
- project-level planting records
        """
    )


# ============================================================
# 🛰️ GIS CHANGE DETECTION
# ============================================================

elif page == "🛰️ GIS Change Detection":

    st.header("🛰️ GIS Change Detection")

    st.write(
        """
        This module is designed to move Uujuzi from document-only ESG
        checking toward spatial evidence validation.
        """
    )

    st.subheader("Proposed 2023 → 2025 workflow")

    workflow = pd.DataFrame(
        {
            "Stage": [
                1,
                2,
                3,
                4,
                5,
                6
            ],

            "Activity": [
                "Extract ESG claim",
                "Define project boundary",
                "Establish 2023 baseline",
                "Analyze 2024 change",
                "Analyze 2025 reporting year",
                "Compare evidence with claim"
            ],

            "Output": [
                "Structured claim",
                "GPS / GeoJSON polygon",
                "Baseline map",
                "Progress map",
                "Reporting-year map",
                "Assurance finding"
            ]
        }
    )

    st.dataframe(
        workflow,
        use_container_width=True,
        hide_index=True
    )

    st.markdown("---")

    st.subheader("GIS Evidence Layers")

    layers = [
        "🌳 Tree cover",
        "🌱 Vegetation",
        "🛰️ Satellite imagery",
        "📍 Project boundary",
        "🔥 Tree-cover loss / disturbance",
        "🌲 Planted-tree areas",
        "💧 Water",
        "🏘️ Settlements / land use",
        "📸 Ground photographs"
    ]

    for layer in layers:

        st.checkbox(
            layer,
            value=False
        )

    st.markdown("---")

    st.subheader("Future GIS Data Architecture")

    st.code(
        """
        ESG Report
             ↓
        Extract Claim
             ↓
        Project GPS / GeoJSON
             ↓
        ┌─────────────────────────────┐
        │ 2023 Baseline               │
        │ 2024 Progress               │
        │ 2025 Reporting Year         │
        └─────────────────────────────┘
             ↓
        Satellite / GIS Data
             ↓
        ┌─────────────────────────────┐
        │ Tree Cover                  │
        │ Vegetation                  │
        │ Tree Loss                   │
        │ Land Use                    │
        │ Planted Trees               │
        └─────────────────────────────┘
             ↓
        Spatial Comparison
             ↓
        Evidence Matrix
             ↓
        ESG Assurance Finding
        """
    )

    st.info(
        """
        Production roadmap:

        1. GeoJSON project boundaries
        2. Sentinel-2 imagery
        3. Google Earth Engine processing
        4. Global Forest Watch layers
        5. Time-series change detection
        6. Automated evidence report
        """
    )

    st.markdown(
        """
        Global Forest Watch provides tree-cover-loss data at 30m resolution
        and has spatial datasets for planted trees/tree plantations. These
        can become important external evidence layers in the production
        architecture. :contentReference[oaicite:1]{index=1}
        """
    )


# ============================================================
# 💧 WATER & AIR
# ============================================================

elif page == "💧 Water & Air":

    st.header("💧 Water & Air Environmental Validation")

    environmental_data = generate_environmental_data()

    st.dataframe(
        environmental_data,
        use_container_width=True,
        hide_index=True
    )

    st.subheader("Water Quality")

    st.line_chart(
        environmental_data.set_index("Year")[
            ["Water Quality Index"]
        ]
    )

    st.subheader("Air Quality")

    st.line_chart(
        environmental_data.set_index("Year")[
            ["Air Quality Index"]
        ]
    )

    st.subheader("Vegetation")

    st.line_chart(
        environmental_data.set_index("Year")[
            ["Vegetation Index"]
        ]
    )

    st.warning(
        """
        Current values are synthetic demonstration data.

        Production implementation should connect to appropriate
        environmental monitoring datasets and document the source,
        spatial resolution, time period and limitations of each dataset.
        """
    )


# ============================================================
# 🏛️ GOVERNANCE
# ============================================================

elif page == "🏛️ Governance":

    st.header("🏛️ Governance Evidence")

    governance_data = pd.DataFrame(
        {
            "Evidence": [
                "Board ESG oversight",
                "ESG policy",
                "Risk management framework",
                "Stakeholder engagement",
                "Whistleblowing mechanism",
                "Anti-corruption controls"
            ],

            "Evidence Type": [
                "Board minutes",
                "Policy document",
                "Risk register",
                "Consultation records",
                "Whistleblower policy",
                "Control documentation"
            ],

            "Status": [
                "Available",
                "Available",
                "Requires review",
                "Requires review",
                "Available",
                "Available"
            ],

            "Corroboration": [
                "Tier 2",
                "Tier 2",
                "Tier 1",
                "Tier 1",
                "Tier 2",
                "Tier 2"
            ]
        }
    )

    st.dataframe(
        governance_data,
        use_container_width=True,
        hide_index=True
    )

    st.info(
        """
        Governance allegations or single-source claims should not be
        presented as established facts without appropriate corroboration.
        """
    )


# ============================================================
# 🤝 COMMUNITY BENEFIT
# ============================================================

elif page == "🤝 Community Benefit":

    st.header("🤝 Community Benefit")

    community_data = pd.DataFrame(
        {
            "Indicator": [
                "Local employment",
                "Local procurement",
                "Community infrastructure",
                "Training",
                "Small business participation",
                "Community consultation"
            ],

            "Reported": [
                True,
                True,
                True,
                True,
                False,
                True
            ],

            "Evidence": [
                "Payroll records",
                "Supplier records",
                "Project records",
                "Training registers",
                "Not provided",
                "Meeting records"
            ],

            "Verification Status": [
                "Review",
                "Review",
                "Review",
                "Review",
                "Missing",
                "Review"
            ]
        }
    )

    st.dataframe(
        community_data,
        use_container_width=True,
        hide_index=True
    )

    st.markdown(
        """
        Uujuzi should distinguish between:

        **Reported benefit**
        → what the organization says happened.

        **Documented benefit**
        → what supporting records demonstrate.

        **Observed benefit**
        → what independent data or field evidence indicates.

        **Verified benefit**
        → evidence that has passed the defined assurance process.
        """
    )


# ============================================================
# 📋 ASSURANCE RESULT
# ============================================================

elif page == "📋 Assurance Result":

    st.header("📋 Overall Assurance Result")

    standards_score = 75
    environmental_score = 70
    governance_score = 65
    community_score = 70
    evidence_score = 60

    assurance_score = calculate_assurance_score(
        standards_score,
        environmental_score,
        governance_score,
        community_score,
        evidence_score
    )

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            "Standards",
            f"{standards_score}%"
        )

    with col2:
        st.metric(
            "Environmental",
            f"{environmental_score}%"
        )

    with col3:
        st.metric(
            "Governance",
            f"{governance_score}%"
        )

    with col4:
        st.metric(
            "Community",
            f"{community_score}%"
        )

    with col5:
        st.metric(
            "Evidence",
            f"{evidence_score}%"
        )

    st.markdown("---")

    st.metric(
        "Prototype Assurance Indicator",
        f"{assurance_score}%"
    )

    st.warning(
        """
        This is a prototype analytical indicator, not an audit opinion,
        certification, legal conclusion or formal assurance engagement.

        A production Uujuzi system should define a documented methodology,
        evidence thresholds, source hierarchy, reviewer controls and
        sector-specific assurance rules.
        """
    )

    st.subheader("Assurance Findings")

    findings = pd.DataFrame(
        {
            "Area": [
                "ESG Claims",
                "Standards",
                "Impact Picture",
                "GIS",
                "Governance",
                "Community Benefit"
            ],

            "Finding": [
                "Claims identified",
                "Potential standards mapped",
                "Spatial validation required",
                "Project boundary required",
                "Documentary evidence required",
                "Community evidence required"
            ],

            "Status": [
                "Reviewed",
                "Reviewed",
                "Open",
                "Open",
                "Open",
                "Open"
            ]
        }
    )

    st.dataframe(
        findings,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# FOOTER
# ============================================================

st.markdown("---")

st.caption(
    f"""
    Uujuzi ESG & Governance Assurance Checker |
    Prototype generated {datetime.now().strftime('%Y-%m-%d')} |
    Organization: {organization}
    """
)

st.caption(
    """
    Demonstration data is synthetic unless explicitly identified as
    externally sourced. GIS/satellite evidence must be interpreted
    according to its spatial resolution, temporal coverage and methodology.
    """
)
