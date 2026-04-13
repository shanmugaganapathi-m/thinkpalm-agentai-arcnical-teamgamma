"""
Arcnical Streamlit Dashboard - Phase 4+ with Repository Input

Complete application with:
- Repository path input field in sidebar
- PyVis graph visualization (Phase 3)
- CLI bridge with sidebar controls (Phase 4)
- Live status updates
- Dynamic re-run capability
"""

import json
import os
import streamlit as st
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import networkx as nx
import tempfile
import time
import subprocess
from dotenv import load_dotenv
from arcnical.cli_bridge import CLIBridge

# Load environment variables from .env
load_dotenv()

# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Arcnical - Architecture Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown("""
<style>
/* Header styling */
.header-container {
    background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
    padding: 20px;
    border-radius: 8px;
    margin-bottom: 20px;
}

.header-title {
    color: white;
    font-size: 24px;
    font-weight: 600;
    margin: 0;
}

/* Severity badge styles */
.severity-critical { color: #d32f2f; font-weight: 600; }
.severity-high { color: #ff9800; font-weight: 600; }
.severity-medium { color: #fbc02d; font-weight: 600; }
.severity-low { color: #388e3c; font-weight: 600; }

/* CLI Display */
.cli-display {
    background: #1e1e1e;
    border: 1px solid #d32f2f;
    border-radius: 4px;
    padding: 12px;
    font-family: 'Courier New', monospace;
    font-size: 11px;
    color: #00ff00;
    line-height: 1.4;
    max-height: 300px;
    overflow-y: auto;
}

.cli-header {
    color: #d32f2f;
    font-weight: 600;
    text-transform: uppercase;
    margin: 0 0 8px 0;
    font-size: 10px;
}

.config-header {
    color: #fbc02d;
    font-weight: 600;
    text-transform: uppercase;
    margin: 0 0 8px 0;
    font-size: 10px;
}

</style>
""", unsafe_allow_html=True)

# ============================================================
# SESSION STATE INITIALIZATION
# ============================================================

def initialize_session_state():
    """Initialize session state variables."""
    if "provider" not in st.session_state:
        st.session_state.provider = "claude"
    
    if "depth" not in st.session_state:
        st.session_state.depth = "standard"
    
    if "repo_path" not in st.session_state:
        st.session_state.repo_path = "./test_repo"
    
    if "status" not in st.session_state:
        st.session_state.status = "Ready"
    
    if "execution_time" not in st.session_state:
        st.session_state.execution_time = None
    
    if "last_run_time" not in st.session_state:
        st.session_state.last_run_time = None
    
    if "findings_count" not in st.session_state:
        st.session_state.findings_count = 0
    
    if "analysis_data" not in st.session_state:
        st.session_state.analysis_data = None

    if "analyze_triggered" not in st.session_state:
        st.session_state.analyze_triggered = False

    if "cli_output" not in st.session_state:
        st.session_state.cli_output = ""

    if "analyze_error" not in st.session_state:
        st.session_state.analyze_error = None

# ============================================================
# DATA LOADING
# ============================================================

@st.cache_data
def load_analysis_data() -> Optional[Dict[str, Any]]:
    """Load latest analysis JSON."""
    json_path = Path(".arcnical/results/latest_analysis.json")
    
    if not json_path.exists():
        return None
    
    try:
        with open(json_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Failed to load analysis: {e}")
        return None


def count_findings(data: Optional[Dict[str, Any]]) -> Dict[str, int]:
    """Count findings by severity."""
    if not data or not data.get("findings"):
        return {"critical": 0, "high": 0, "medium": 0, "low": 0}
    
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    
    for finding in data["findings"]:
        severity = finding.get("severity", "").lower()
        if severity == "critical":
            counts["critical"] += 1
        elif severity == "high":
            counts["high"] += 1
        elif severity == "medium":
            counts["medium"] += 1
        elif severity == "low":
            counts["low"] += 1
    
    return counts


def calculate_health_score(data: Optional[Dict[str, Any]]) -> int:
    """Calculate health score from data."""
    if not data or not data.get("scores"):
        return 50
    
    scores = data["scores"]
    return int(
        (scores.get("overall", 0) * 0.4 +
         scores.get("maintainability", 0) * 0.3 +
         scores.get("structure", 0) * 0.2 +
         scores.get("security", 0) * 0.1)
    )


def build_dependency_graph(analysis_data: Dict[str, Any]) -> nx.DiGraph:
    """Build NetworkX graph from analysis data."""
    graph = nx.DiGraph()
    
    findings = analysis_data.get("findings", [])
    file_structure = analysis_data.get("file_structure", {})
    
    # Create nodes — files may be a dict {filename: loc} or a language-ratio string
    files = file_structure.get("files", {})

    if isinstance(files, dict):
        for filename, loc in files.items():
            if isinstance(loc, (int, float)):
                color = get_node_color(loc)
                size = get_node_size(loc)

                graph.add_node(
                    filename,
                    title=filename,
                    label=filename,
                    size=size,
                    color=color,
                    loc=loc,
                )
    
    # Create edges
    for finding in findings:
        evidence = finding.get("evidence", {})
        references = evidence.get("references", [])
        
        if len(references) >= 2:
            for i in range(len(references) - 1):
                source = references[i].get("file", "")
                target = references[i + 1].get("file", "")
                
                if source and target and source != target:
                    edge_color = get_edge_color(finding.get("severity", "Low"))
                    
                    graph.add_edge(
                        source,
                        target,
                        color=edge_color,
                        weight=1,
                        title=finding.get("title", "Dependency"),
                        severity=finding.get("severity", "Low"),
                    )
    
    return graph


def get_node_color(loc: float) -> str:
    """Get node color based on LOC."""
    if loc <= 100:
        return "#388e3c"  # Green
    elif loc <= 300:
        return "#fbc02d"  # Yellow
    elif loc <= 600:
        return "#ff9800"  # Orange
    else:
        return "#d32f2f"  # Red


def get_node_size(loc: float) -> int:
    """Get node size based on LOC."""
    if loc <= 0:
        return 10
    if loc <= 100:
        return 15
    if loc <= 300:
        return 25
    if loc <= 600:
        return 35
    return 50


def get_edge_color(severity: str) -> str:
    """Get edge color based on severity."""
    severity_lower = severity.lower()
    
    if severity_lower == "critical":
        return "#d32f2f"  # Red
    elif severity_lower == "high":
        return "#ff9800"  # Orange
    elif severity_lower == "medium":
        return "#fbc02d"  # Yellow
    else:
        return "#1976d2"  # Blue


def render_pyvis_graph(graph: nx.DiGraph) -> str:
    """Render PyVis graph and return HTML path."""
    from pyvis.network import Network
    
    net = Network(
        height="750px",
        width="100%",
        directed=True,
        physics=True,
        notebook=False,
    )
    
    net.physics.enabled = True
    net.physics.dynamic_friction = 0.5
    net.physics.stabilization.iterations = 200
    
    # Add nodes
    for node in graph.nodes(data=True):
        node_id = node[0]
        node_attr = node[1]
        
        net.add_node(
            node_id,
            label=node_attr.get("label", node_id),
            title=f"{node_attr.get('label', node_id)} ({int(node_attr.get('loc', 0))} LOC)",
            size=node_attr.get("size", 20),
            color=node_attr.get("color", "#1976d2"),
        )
    
    # Add edges
    for edge in graph.edges(data=True):
        source, target, attr = edge
        net.add_edge(
            source,
            target,
            color=attr.get("color", "#1976d2"),
            title=attr.get("title", "Dependency"),
            weight=attr.get("weight", 1),
        )
    
    net.show_buttons(filter_=["physics"])
    net.toggle_physics(True)
    
    temp_file = Path(tempfile.gettempdir()) / "arcnical_graph.html"
    net.write_html(str(temp_file))

    return str(temp_file)

# ============================================================
# SIDEBAR - PHASE 4+ with Repository Input
# ============================================================

def render_sidebar() -> tuple:
    """Render enhanced sidebar with Phase 4+ controls."""
    with st.sidebar:
        st.markdown("## ⚙️ Analysis Controls")
        st.divider()
        
        # Repository Path Input
        st.markdown("### 📁 Repository")
        repo_path_input = st.text_input(
            "Enter repository path or GitHub URL",
            value=st.session_state.repo_path,
            placeholder="./test_repo or https://github.com/owner/repo",
            help="Local path (./test_repo) or GitHub URL (https://github.com/owner/repo)",
            key="repo_path_input",
        )

        if repo_path_input:
            st.session_state.repo_path = repo_path_input

        # Validate path display
        if st.session_state.repo_path.startswith("https://"):
            st.caption(f"🌐 GitHub URL: {st.session_state.repo_path}")
        elif st.session_state.repo_path.startswith("./") or st.session_state.repo_path.startswith("/"):
            st.caption(f"✅ Local path: {st.session_state.repo_path}")
        else:
            st.caption(f"📍 Path: {st.session_state.repo_path}")

        # Analyze submit button
        analyze_clicked = st.button(
            "🔍 Analyze Repository",
            use_container_width=True,
            type="primary",
            key="analyze_button",
            help="Run architecture analysis on the repository above",
        )

        if analyze_clicked:
            st.session_state.analyze_triggered = True
            st.session_state.analyze_error = None

        st.divider()
        
        # Provider Selector
        st.markdown("### 🤖 LLM Provider")
        provider_options = ["Claude", "OpenAI", "Gemini"]
        provider_index = 0 if st.session_state.provider == "claude" else (1 if st.session_state.provider == "openai" else 2)
        
        provider_display = st.radio(
            "Select LLM Provider",
            options=provider_options,
            index=provider_index,
            label_visibility="collapsed",
            horizontal=False,
        )
        
        provider_map = {"Claude": "claude", "OpenAI": "openai", "Gemini": "gemini"}
        st.session_state.provider = provider_map[provider_display]
        
        provider_info = {
            "Claude": "🔵 Anthropic Claude - Recommended",
            "OpenAI": "🟢 OpenAI GPT - Coming soon",
            "Gemini": "🟡 Google Gemini - Coming soon"
        }
        st.caption(provider_info.get(provider_display, ""))
        
        st.divider()
        
        # Depth Selector
        st.markdown("### 📊 Analysis Depth")
        depth_options = ["Quick", "Standard"]
        depth_index = 0 if st.session_state.depth == "quick" else 1
        
        depth_display = st.radio(
            "Select Analysis Depth",
            options=depth_options,
            index=depth_index,
            label_visibility="collapsed",
            horizontal=False,
        )
        
        depth_map = {"Quick": "quick", "Standard": "standard"}
        st.session_state.depth = depth_map[depth_display]
        
        depth_info = {
            "Quick": "⚡ L1-L3 only (no LLM)",
            "Standard": "🔬 Full L1-L4 (with LLM)"
        }
        st.caption(depth_info.get(depth_display, ""))
        
        st.divider()
        
        # Re-run last analysis
        st.markdown("### 🔄 Quick Re-run")

        re_run_clicked = st.button(
            "🔄 Re-run Last Analysis",
            use_container_width=True,
            type="secondary",
            key="re_run_button",
            help="Re-run analysis with the same settings"
        )

        if re_run_clicked:
            st.session_state.analyze_triggered = True
            st.session_state.analyze_error = None
        
        st.divider()
        
        # Status Display
        st.markdown("### 📡 Status")
        
        status_colors = {
            "Ready": "🟢",
            "Running": "🟡",
            "Complete": "🟢",
            "Error": "🔴"
        }
        
        status_emoji = status_colors.get(st.session_state.status, "⚪")
        st.markdown(f"**{status_emoji} {st.session_state.status}**")
        
        st.markdown("---")
        
        if st.session_state.last_run_time:
            st.markdown(f"**Last Run:** {st.session_state.last_run_time}")
        else:
            st.markdown("**Last Run:** Never")
        
        if st.session_state.execution_time:
            st.markdown(f"**Time:** {st.session_state.execution_time:.2f}s")
        else:
            st.markdown("**Time:** —")
        
        st.markdown(f"**Findings:** {st.session_state.findings_count}")
        
        st.divider()
        
        # Settings Summary
        st.markdown("### ⚙️ Current Settings")
        settings_text = f"""
- **Repository:** {st.session_state.repo_path}
- **Provider:** {st.session_state.provider.capitalize()}
- **Depth:** {st.session_state.depth.capitalize()}
- **Status:** {st.session_state.status}
        """
        st.markdown(settings_text)
        
        return st.session_state.provider, st.session_state.depth, st.session_state.repo_path, st.session_state.analyze_triggered

# ============================================================
# MAIN APPLICATION
# ============================================================

def main():
    """Main application."""
    
    initialize_session_state()
    
    # Render sidebar and get controls
    provider, depth, repo_path, analyze_triggered = render_sidebar()

    # ============================================================
    # ANALYSIS EXECUTION
    # ============================================================

    if analyze_triggered:
        st.session_state.analyze_triggered = False  # Reset trigger

        # Resolve API key based on selected provider
        api_key_map = {
            "claude": os.getenv("ANTHROPIC_API_KEY"),
            "openai": os.getenv("OPENAI_API_KEY"),
            "gemini": os.getenv("GEMINI_API_KEY"),
        }
        api_key = api_key_map.get(provider)

        if depth == "standard" and (not api_key or api_key == "env_file_api_placeholder"):
            st.warning(
                f"⚠️ No API key found for **{provider.capitalize()}**. "
                "Open `.env` and replace `env_file_api_placeholder` with your key, "
                "or switch to **Quick** depth (no LLM required)."
            )
        else:
            st.session_state.status = "Running"
            with st.spinner(f"Running analysis on `{repo_path}` ..."):
                success, message, exec_time, data = CLIBridge.execute_analysis(
                    repo_path=repo_path,
                    depth=depth,
                    provider=provider,
                    api_key=api_key if depth == "standard" else None,
                )

            if success:
                st.session_state.status = "Complete"
                st.session_state.execution_time = exec_time
                st.session_state.last_run_time = datetime.now().strftime("%H:%M:%S")
                st.session_state.analysis_data = data
                st.session_state.findings_count = len(data.get("findings", []))
                st.session_state.cli_output = CLIBridge.get_cli_output_display(
                    repo_path, depth, provider, exec_time, st.session_state.findings_count
                )
                st.success(message)
                load_analysis_data.clear()  # Bust cache so fresh data loads
                st.rerun()
            else:
                st.session_state.status = "Error"
                st.session_state.analyze_error = message
                st.error(message)

    # Load analysis data
    analysis_data = load_analysis_data()
    
    if not analysis_data:
        st.error("❌ No analysis data found. Run analysis first.")
        st.info(
            f"To generate analysis data, use the Re-run button in the sidebar or run:\n"
            f"```bash\n"
            f"python -m arcnical analyze {repo_path} --depth {depth}\n"
            f"```"
        )
        return
    
    # Update session state with current data
    st.session_state.analysis_data = analysis_data
    finding_counts = count_findings(analysis_data)
    st.session_state.findings_count = sum(finding_counts.values())
    health_score = calculate_health_score(analysis_data)
    
    # ============================================================
    # HEADER SECTION
    # ============================================================
    
    col1, col2 = st.columns([0.85, 0.15])
    
    with col1:
        st.markdown(
            f"""
            <div style="display: flex; gap: 24px; align-items: center;">
                <div>
                    <span class="severity-critical">🔴 {finding_counts['critical']} CRITICAL</span>
                    <span style="margin-left: 12px;" class="severity-high">🟠 {finding_counts['high']} HIGH</span>
                    <span style="margin-left: 12px;" class="severity-medium">🟡 {finding_counts['medium']} MEDIUM</span>
                    <span style="margin-left: 12px;" class="severity-low">🟢 {finding_counts['low']} LOW</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    with col2:
        st.markdown(
            f"""
            <div style="
                width: 80px; 
                height: 80px; 
                border: 4px solid #ff9800; 
                border-radius: 50%; 
                display: flex; 
                align-items: center; 
                justify-content: center;
            ">
                <div style="text-align: center;">
                    <div style="font-size: 28px; font-weight: 600; color: #ff9800;">{health_score}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    st.divider()
    
    # ============================================================
    # TABS
    # ============================================================
    
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Overview",
        "🔗 Graph",
        "📈 Metrics",
        "📁 Files",
        "🔍 Findings",
        "💾 Export"
    ])
    
    with tab1:
        st.subheader("Analysis Overview")
        
        if analysis_data.get("metadata"):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Tool Version", analysis_data["metadata"].get("tool_version", "N/A"))
            with col2:
                st.metric("Model", analysis_data["metadata"].get("model", "N/A"))
            with col3:
                st.metric("Depth", analysis_data["metadata"].get("depth", "N/A"))
        
        if analysis_data.get("scores"):
            scores = analysis_data["scores"]
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Overall", scores.get("overall", 0))
            with col2:
                st.metric("Maintainability", scores.get("maintainability", 0))
            with col3:
                st.metric("Structure", scores.get("structure", 0))
            with col4:
                st.metric("Security", scores.get("security", 0))
    
    with tab2:
        st.subheader("📊 Dependency Graph")
        
        try:
            graph = build_dependency_graph(analysis_data)
            
            if not graph.nodes():
                st.info("No file-level dependency data available. Graph requires per-file LOC data in `file_structure.files`.")
            elif graph.nodes():
                st.subheader("Graph Statistics")
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Files/Modules", len(graph.nodes()))
                with col2:
                    st.metric("Dependencies", len(graph.edges()))
                with col3:
                    density = nx.density(graph) if graph.nodes() else 0
                    st.metric("Density", f"{density:.2f}")
                with col4:
                    degrees = dict(graph.degree())
                    avg_degree = sum(degrees.values()) / max(len(graph.nodes()), 1) if graph.nodes() else 0
                    st.metric("Avg Connections", f"{avg_degree:.1f}")
                
                st.divider()
                st.subheader("Interactive Dependency Network")
                
                html_file = render_pyvis_graph(graph)
                with open(html_file, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                
                st.components.v1.html(html_content, height=800)
                
                st.divider()
                st.subheader("🔌 Hub Modules (Most Connected)")
                hub_modules = sorted(degrees.items(), key=lambda x: x[1], reverse=True)[:5]
                
                if hub_modules:
                    hub_data = [{"Module": name, "Connections": count} for name, count in hub_modules]
                    st.dataframe(hub_data, use_container_width=True)
        
        except Exception as e:
            st.error(f"Failed to render graph: {e}")
    
    with tab3:
        st.subheader("Metrics")
        
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Findings Summary**")
            findings_data = {
                "Critical": finding_counts["critical"],
                "High": finding_counts["high"],
                "Medium": finding_counts["medium"],
                "Low": finding_counts["low"],
            }
            st.bar_chart(findings_data)
        
        with col2:
            st.write("**Health Scores**")
            if analysis_data.get("scores"):
                scores = analysis_data["scores"]
                scores_data = {
                    "Overall": scores.get("overall", 0),
                    "Maintainability": scores.get("maintainability", 0),
                    "Structure": scores.get("structure", 0),
                    "Security": scores.get("security", 0),
                }
                st.bar_chart(scores_data)
    
    with tab4:
        st.subheader("Files")
        
        if analysis_data.get("file_structure"):
            file_struct = analysis_data["file_structure"]
            st.write(f"**Total Files:** {file_struct.get('total_files', 0)}")
            files_val = file_struct.get("files", {})
            if isinstance(files_val, dict):
                st.json(files_val, expanded=False)
            else:
                st.write(f"**Language Breakdown:** {files_val}")
    
    with tab5:
        st.subheader("Findings")
        
        if analysis_data.get("findings"):
            findings = analysis_data["findings"]
            st.write(f"**Total Findings:** {len(findings)}")
            
            for i, finding in enumerate(findings[:10], 1):
                with st.expander(f"{i}. {finding.get('title', 'N/A')} ({finding.get('severity', 'N/A')})"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**ID:** {finding.get('id', 'N/A')}")
                        st.write(f"**Severity:** {finding.get('severity', 'N/A')}")
                    with col2:
                        st.write(f"**Layer:** {finding.get('layer', 'N/A')}")
                        st.write(f"**Verified:** {finding.get('verified', False)}")
                    
                    st.write(f"**Rationale:** {finding.get('rationale', 'N/A')}")
    
    with tab6:
        st.subheader("Export")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📥 Export JSON", use_container_width=True):
                st.json(analysis_data)
        
        with col2:
            if st.button("📄 Export PDF", use_container_width=True):
                st.info("PDF export coming in Phase 5")
    
    # ============================================================
    # BOTTOM SECTION - PHASE 4+
    # ============================================================
    
    st.divider()
    
    col1, col2 = st.columns([0.5, 0.5])
    
    with col1:
        st.markdown("### CLI Command Display")
        st.markdown(f"**Status:** ✅ {st.session_state.status}")

        cli_command = st.session_state.cli_output or CLIBridge.get_cli_output_display(
            repo_path,
            st.session_state.depth,
            st.session_state.provider,
            st.session_state.execution_time,
            st.session_state.findings_count,
        )

        st.code(cli_command, language="bash")
    
    with col2:
        st.markdown("### Configuration")
        st.markdown(f"**Status:** ✅ {st.session_state.status}")
        
        config_info = f"""
**Model:** claude-sonnet-4-6
**Provider:** {st.session_state.provider.capitalize()}
**Depth:** {st.session_state.depth.capitalize()}
**Repository:** {repo_path}
**Last Run:** {st.session_state.last_run_time or 'Never'}"""
        
        if st.session_state.execution_time:
            config_info += f"\n**Time:** {st.session_state.execution_time:.2f}s"
        
        config_info += f"\n**Findings:** {st.session_state.findings_count}"
        
        st.markdown(config_info)


if __name__ == "__main__":
    main()
