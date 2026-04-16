"""
Plotly Graph Components for Streamlit Dashboard

Integrates interactive dependency graphs into Streamlit tabs using plotly + networkx.
"""

import streamlit as st
import json
from pathlib import Path
from typing import Dict, Any, Optional
import networkx as nx
import plotly.graph_objects as go


class StreamlitGraphComponent:
    """Streamlit components for graph visualization."""

    # Cap nodes shown to keep layout fast and readable
    MAX_NODES = 150

    @staticmethod
    def load_analysis_data() -> Optional[Dict[str, Any]]:
        """Load latest analysis JSON."""
        json_path = Path(".arcnical/results/latest_analysis.json")
        if not json_path.exists():
            return None
        try:
            with open(json_path, 'r') as f:
                return json.load(f)
        except Exception:
            return None

    @staticmethod
    def build_dependency_graph(analysis_data: Dict[str, Any]) -> nx.DiGraph:
        """
        Build NetworkX graph from analysis data.

        Nodes = files (sized/coloured by LOC).
        Edges = dependency references found in findings (L4 / Standard depth only).
        """
        graph = nx.DiGraph()

        findings = analysis_data.get("findings", [])
        file_structure = analysis_data.get("file_structure", {})
        files = file_structure.get("files", {})

        for filename, loc in files.items():
            if isinstance(loc, (int, float)):
                graph.add_node(
                    filename,
                    label=filename,
                    size=StreamlitGraphComponent._get_node_size(loc),
                    color=StreamlitGraphComponent._get_node_color(loc),
                    loc=loc,
                )

        # Edges from static import analysis (available in Quick + Standard)
        file_imports = file_structure.get("imports", {})
        for src, targets in file_imports.items():
            if src not in graph:
                continue
            for tgt in targets:
                if tgt in graph and src != tgt:
                    graph.add_edge(src, tgt, color="#4fc3f7", title="import", severity="Low")

        # Additional edges from LLM findings (Standard depth only)
        for finding in findings:
            evidence = finding.get("evidence", {})
            references = evidence.get("references", [])
            if len(references) >= 2:
                for i in range(len(references) - 1):
                    source = references[i].get("file", "")
                    target = references[i + 1].get("file", "")
                    if source and target and source != target:
                        graph.add_edge(
                            source, target,
                            color=StreamlitGraphComponent._get_edge_color(
                                finding.get("severity", "Low")
                            ),
                            title=finding.get("title", "Dependency"),
                            severity=finding.get("severity", "Low"),
                        )

        return graph

    @staticmethod
    def _get_node_color(loc: float) -> str:
        if loc <= 100:
            return "#388e3c"
        elif loc <= 300:
            return "#fbc02d"
        elif loc <= 600:
            return "#ff9800"
        return "#d32f2f"

    @staticmethod
    def _get_node_size(loc: float) -> int:
        if loc <= 0:
            return 8
        if loc <= 100:
            return 10
        if loc <= 300:
            return 16
        if loc <= 600:
            return 22
        return 30

    @staticmethod
    def _get_edge_color(severity: str) -> str:
        s = severity.lower()
        if s == "critical":
            return "#ff5252"   # bright red
        elif s == "high":
            return "#ffab40"   # bright orange
        elif s == "medium":
            return "#fff176"   # light yellow
        return "#4fc3f7"       # light blue (default / normal import)

    @staticmethod
    def display_graph_in_streamlit(graph: nx.DiGraph) -> None:
        """Render dependency graph as an interactive plotly figure."""
        if not graph.nodes():
            st.info("No graph data available. Run analysis first.")
            return

        # Limit nodes for performance — keep the largest files
        nodes = list(graph.nodes(data=True))
        if len(nodes) > StreamlitGraphComponent.MAX_NODES:
            nodes_sorted = sorted(nodes, key=lambda n: n[1].get("loc", 0), reverse=True)
            keep = {n[0] for n in nodes_sorted[:StreamlitGraphComponent.MAX_NODES]}
            subgraph = graph.subgraph(keep)
            st.caption(
                f"Showing top {StreamlitGraphComponent.MAX_NODES} files by LOC "
                f"({len(graph.nodes())} total)."
            )
        else:
            subgraph = graph

        # Layout — spring is good for small graphs; fall back to random for large
        n = len(subgraph.nodes())
        if n <= 80:
            pos = nx.spring_layout(subgraph, seed=42, k=1.8)
        else:
            pos = nx.random_layout(subgraph, seed=42)

        # ── Edge traces (one trace per severity colour for legend) ──
        edge_groups: Dict[str, list] = {}
        for u, v, attr in subgraph.edges(data=True):
            color = attr.get("color", "#4fc3f7")
            edge_groups.setdefault(color, [])
            x0, y0 = pos[u]
            x1, y1 = pos[v]
            edge_groups[color] += [x0, x1, None]
            edge_groups[color] += [y0, y1, None]  # will be split below

        edge_traces = []
        severity_label = {
            "#d32f2f": "Critical dep",
            "#ff9800": "High dep",
            "#fbc02d": "Medium dep",
            "#1976d2": "Dependency",
        }
        seen_colors: Dict[str, list] = {}
        for u, v, attr in subgraph.edges(data=True):
            color = attr.get("color", "#4fc3f7")
            if color not in seen_colors:
                seen_colors[color] = {"x": [], "y": []}
            x0, y0 = pos[u]
            x1, y1 = pos[v]
            seen_colors[color]["x"] += [x0, x1, None]
            seen_colors[color]["y"] += [y0, y1, None]

        for color, coords in seen_colors.items():
            edge_traces.append(go.Scatter(
                x=coords["x"], y=coords["y"],
                mode="lines",
                line=dict(width=1.5, color=color),
                hoverinfo="none",
                showlegend=False,
            ))

        # ── Node trace ──
        node_ids = list(subgraph.nodes())
        node_x = [pos[n][0] for n in node_ids]
        node_y = [pos[n][1] for n in node_ids]
        node_colors = [subgraph.nodes[n].get("color", "#1976d2") for n in node_ids]
        node_sizes = [subgraph.nodes[n].get("size", 10) for n in node_ids]
        node_hover = [
            f"<b>{n}</b><br>LOC: {int(subgraph.nodes[n].get('loc', 0))}"
            for n in node_ids
        ]

        node_trace = go.Scatter(
            x=node_x, y=node_y,
            mode="markers",
            hoverinfo="text",
            hovertext=node_hover,
            marker=dict(
                color=node_colors,
                size=node_sizes,
                line=dict(width=0.8, color="#111"),
                opacity=0.9,
            ),
            showlegend=False,
        )

        fig = go.Figure(
            data=edge_traces + [node_trace],
            layout=go.Layout(
                height=560,
                margin=dict(b=4, l=4, r=4, t=4),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(13,17,27,0.6)",
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                hovermode="closest",
                dragmode="pan",
            ),
        )

        st.plotly_chart(fig, use_container_width=True)

    @staticmethod
    def display_graph_statistics(graph: nx.DiGraph) -> None:
        """Display graph statistics."""
        if not graph.nodes():
            st.info("No graph data available.")
            return

        num_nodes = len(graph.nodes())
        num_edges = len(graph.edges())
        density = nx.density(graph) if num_nodes > 0 else 0
        degrees = dict(graph.degree())
        avg_degree = sum(degrees.values()) / max(num_nodes, 1)

        circular_deps = []
        try:
            circular_deps = list(nx.simple_cycles(graph))
        except Exception:
            pass

        hub_modules = sorted(degrees.items(), key=lambda x: x[1], reverse=True)[:5]

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Files/Modules", num_nodes)
        with col2:
            st.metric("Dependencies", num_edges)
        with col3:
            st.metric("Graph Density", f"{density:.2f}")
        with col4:
            st.metric("Avg Connections", f"{avg_degree:.1f}")

        st.subheader("Hub Modules (Most Connected)")
        if hub_modules:
            st.dataframe(
                [{"Module": name, "Connections": count} for name, count in hub_modules],
                use_container_width=True,
            )
        else:
            st.info("No hub modules detected.")

        st.subheader("Circular Dependencies")
        if circular_deps:
            st.warning(f"Found {len(circular_deps)} circular dependency chains")
            for cycle in circular_deps[:5]:
                st.code(" → ".join(cycle[:3]) + " → ...", language="text")
        else:
            st.success("No circular dependencies detected.")

    @staticmethod
    def display_legend() -> None:
        """Display graph legend."""
        st.subheader("Graph Legend")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Node color — file complexity (LOC):**")
            st.markdown("🟢 Green: < 100 LOC")
            st.markdown("🟡 Yellow: 100–300 LOC")
            st.markdown("🟠 Orange: 300–600 LOC")
            st.markdown("🔴 Red: > 600 LOC")
        with col2:
            st.markdown("**Edge color — finding severity:**")
            st.markdown("🔴 Bright red: Critical")
            st.markdown("🟠 Bright orange: High")
            st.markdown("🟡 Light yellow: Medium")
            st.markdown("🔵 Light blue: Normal import")
