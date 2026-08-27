import streamlit as st
import requests
import json
from openai import OpenAI

# Page Setup
st.set_page_config(page_title="Helix AI Spec & Risk Engine", layout="wide")

st.title("⚡ Helix AI Spec & Risk Engine")
st.caption("Catch upstream spec gaps, cross-team dependencies, and generate Gherkin criteria before sprint planning.")

# Sidebar Configuration
with st.sidebar:
    st.header("Configuration")
    api_key = st.text_input("OpenAI API Key", type="password")
    
    st.markdown("---")
    st.subheader("Sample Spec Loader")
    repo_option = st.selectbox(
        "Select Spec Source",
        ["Custom Input", "High Risk Spec (Vague)", "Low Risk Spec (Detailed)"]
    )

# Sample Inputs for testing
HIGH_RISK_SAMPLE = """# Feature: Real-time Notification System
We want to add real-time push notifications so users know when someone comments on their pipeline item. 

## Requirements
- It should be fast and load quickly.
- Send a push notification immediately when a comment is added.
- Make sure it handles a lot of traffic without crashing.
- UI should look modern and clean."""

LOW_RISK_SAMPLE = """# Feature: Bulk Lead Import API Endpoint
Expose a REST API endpoint `/api/v1/leads/bulk-import` allowing external integrations to batch-upload leads.

## Technical Specifications
- Endpoint: POST `/api/v1/leads/bulk-import`
- Authentication: Bearer Token via OAuth 2.0.
- Payload Limit: Maximum 1,000 lead objects per request; 10MB payload size limit.
- Rate Limiting: 50 requests per minute per tenant ID.
- Behavior:
  - Validates schema per lead object.
  - Inserts valid leads; returns an array of `failed_records` with error codes.
  - Emits a `lead.bulk_imported` event to Kafka for downstream ingestion by the Medellín Integrations Team."""

spec_text = ""
if repo_option == "High Risk Spec (Vague)":
    spec_text = HIGH_RISK_SAMPLE
elif repo_option == "Low Risk Spec (Detailed)":
    spec_text = LOW_RISK_SAMPLE

# Layout: Two Side-by-Side Columns for Input and Raw JSON
col_input, col_raw_json = st.columns(2)

with col_input:
    st.subheader("📝 Input Product Specification")
    user_spec = st.text_area("Product Specification / Epic Description", value=spec_text, height=350)

with col_raw_json:
    st.subheader("🔍 Raw OpenAI API JSON Response")
    # Placeholder box before analysis is run
    raw_json_display = st.text_area(
        "Raw JSON Output", 
        value=st.session_state.get("raw_json_str", "// Raw JSON returned by OpenAI will appear here after clicking analyze..."), 
        height=350
    )

# Audit Engine Call
def analyze_spec_risk(text, key):
    client = OpenAI(api_key=key)
    
    prompt = f"""
    You are a Forward Deployed AI Strategist evaluating a product spec at Helix.
    Your goal is to catch upstream spec gaps, identify cross-team dependencies, and reduce mid-sprint rework.

    Specific Helix Context to Analyze:
    1. Cross-Team Dependencies: Check if this spec impacts:
       - Medellín Integrations Team (API contract changes, sync endpoints, event schemas)
       - Austin Infrastructure/Pipeline Pods (database schema changes, queue systems, auth)
    2. Missing Technical Edge Cases: Identify missing SLAs, rate limits, error handling, or scale limits.
    3. Gherkin Acceptance Criteria: Generate structured Gherkin test scenarios (GIVEN/WHEN/THEN) for Jira.

    CRITICAL INSTRUCTION: Your output MUST be valid JSON containing the keyword "JSON". Do not wrap in markdown quotes. Return strictly this structure:
    {{
        "risk_level": "<HIGH | MEDIUM | LOW>",
        "readiness_summary": "<Executive summary focusing on spec readiness and handoff risks>",
        "cross_team_dependencies": [
            {{
                "team": "<e.g., Medellín Integrations Team or Pipeline Core Pod>",
                "reason": "<Specific reason for impact and necessary API/schema coordination>"
            }}
        ],
        "missing_technical_edge_cases": ["<Specific missing SLA, failure mode, or edge case>"],
        "gherkin_acceptance_criteria": [
            {{
                "feature": "<Scenario title>",
                "given": "<Precondition>",
                "when": "<User action>",
                "then": "<Expected result>"
            }}
        ]
    }}

    Spec Content to Evaluate:
    {text}
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    
    raw_content = response.choices[0].message.content
    return raw_content, json.loads(raw_content)

# Action Trigger
if st.button("🚀 Analyze Spec & Generate Criteria", type="primary"):
    if not api_key:
        st.warning("Please enter your OpenAI API Key in the sidebar.")
    elif not user_spec.strip():
        st.warning("Please provide a product spec to analyze.")
    else:
        with st.spinner("Analyzing spec and fetching raw response..."):
            try:
                raw_json_str, result = analyze_spec_risk(user_spec, api_key)
                
                # Format JSON nicely for display
                formatted_json = json.dumps(json.loads(raw_json_str), indent=2)
                st.session_state["raw_json_str"] = formatted_json
                
                # Rerun to refresh the raw JSON text area value immediately
                st.rerun()

            except Exception as e:
                st.error(f"An error occurred during evaluation: {e}")

# Render Analyzed Dashboard below the inputs if session data exists
if "raw_json_str" in st.session_state and st.session_state["raw_json_str"].startswith("{"):
    result = json.loads(st.session_state["raw_json_str"])
    
    st.markdown("---")
    st.header("📊 Structured Analysis Dashboard")
    
    # Header Summary Bar
    col1, col2 = st.columns([1, 3])
    
    with col1:
        risk = result.get("risk_level", "MEDIUM")
        if risk == "HIGH":
            st.error(f"Risk Level: {risk}")
        elif risk == "MEDIUM":
            st.warning(f"Risk Level: {risk}")
        else:
            st.success(f"Risk Level: {risk}")

    with col2:
        st.subheader("Readiness Assessment")
        st.write(result.get("readiness_summary", ""))

    # Detailed Section Layout
    c_left, c_right = st.columns(2)
    
    with c_left:
        st.subheader("🔗 Identified Cross-Team Dependencies")
        deps = result.get("cross_team_dependencies", [])
        if deps:
            for dep in deps:
                st.markdown(f"**{dep.get('team', 'Unknown Team')}:** {dep.get('reason', '')}")
        else:
            st.write("No cross-team dependencies flagged.")
            
        st.subheader("⚠️ Missing Technical Edge Cases")
        for gap in result.get("missing_technical_edge_cases", []):
            st.write(f"- {gap}")

    with c_right:
        st.subheader("⚙️ Generated Gherkin Acceptance Criteria")
        gherkin_list = result.get("gherkin_acceptance_criteria", [])
        for i, g in enumerate(gherkin_list, 1):
            st.markdown(f"**Scenario {i}: {g.get('feature', 'Feature')}**")
            st.code(
                f"GIVEN {g.get('given', '')}\nWHEN {g.get('when', '')}\nTHEN {g.get('then', '')}",
                language="gherkin"
            )
