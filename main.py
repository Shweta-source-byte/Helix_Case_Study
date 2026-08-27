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
        ["Custom Input", "Incomplete Feature Spec (High Risk)", "Structured Feature Spec (Low Risk)"]
    )

GITHUB_URLS = {
    "Incomplete Feature Spec (High Risk)": "https://raw.githubusercontent.com/ugur10/prd-template/main/PRD_TEMPLATE.md",
    "Structured Feature Spec (Low Risk)": "https://raw.githubusercontent.com/ugur10/prd-template/main/EXAMPLE_PRD.md"
}

spec_text = ""
if repo_option != "Custom Input":
    url = GITHUB_URLS[repo_option]
    try:
        response = requests.get(url)
        if response.status_code == 200:
            spec_text = response.text
            st.info(f"Loaded sample spec from repository.")
        else:
            st.error("Failed to fetch document from GitHub.")
    except Exception as e:
        st.error(f"Error loading source: {e}")

# Text Area Input
user_spec = st.text_area("Product Specification / Epic Description", value=spec_text, height=280)

# Audit Engine Call
def analyze_spec_risk(text, key):
    client = OpenAI(api_key=key)
    
    prompt = f"""
    You are a Forward Deployed AI Strategist at Helix analyzing a Product Specification.
    Evaluate the spec for technical completeness, cross-team dependencies, and missing edge cases.

    Return your analysis STRICTLY as JSON with the following structure:
    {{
        "risk_level": "<HIGH | MEDIUM | LOW>",
        "readiness_summary": "<2-sentence summary of technical readiness and main risks>",
        "cross_team_dependencies": [
            {{
                "team": "<Team name, e.g., Medellín Integrations Team, Core Infra, Security, Pipeline>",
                "reason": "<Why this spec impacts them and what contract/API coordination is required>"
            }}
        ],
        "missing_technical_edge_cases": ["<list 3 specific unaddressed technical edge cases or SLA gaps>"],
        "gherkin_acceptance_criteria": [
            {{
                "feature": "<Brief feature or scenario name>",
                "given": "<Given condition>",
                "when": "<When action>",
                "then": "<Then outcome>"
            }}
        ]
    }}

    Spec Content:
    {text}
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content)

# Action Trigger
if st.button("🚀 Analyze Spec & Generate Criteria", type="primary"):
    if not api_key:
        st.warning("Please enter your OpenAI API Key in the sidebar.")
    elif not user_spec.strip():
        st.warning("Please provide a product spec to analyze.")
    else:
        with st.spinner("Analyzing technical edge cases, routing cross-team dependencies, and structuring Gherkin criteria..."):
            try:
                result = analyze_spec_risk(user_spec, api_key)
                
                st.markdown("---")
                
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

                # Main Section Layout
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

            except Exception as e:
                st.error(f"An error occurred during evaluation: {e}")