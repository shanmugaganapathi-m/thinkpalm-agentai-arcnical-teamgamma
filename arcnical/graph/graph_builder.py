"""
PyVis Dependency Graph Builder for Arcnical Dashboard

Visualizes code dependencies as an interactive network graph using PyVis.
Shows nodes as files/modules and edges as dependencies.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
import networkx as nx
from pyvis.network import Network


class DependencyGraphBuilder:
    """Build and visualize dependency graphs using PyVis."""

    def __init__(self, analysis_data: Optional[Dict[str, Any]] = None):
        """
        Initialize the graph builder.
        
        Args:
            analysis_data: Analysis JSON data from Phase 1
        """
        self.analysis_data = analysis_data or self._load_latest_analysis()
        self.graph = nx.DiGraph()
        self.node_sizes = {}
        self.node_colors = {}

    @staticmethod
    def _load_latest_analysis() -> Dict[str, Any]:
        """Load latest analysis JSON file."""
        json_path = Path(".arcnical/results/latest_analysis.json")
        
        if not json_path.exists():
            return {}
        
        try:
            with open(json_path, 'r') as f:
                return json.load(f)
        except Exception:
            return {}

    def build_graph(self) -> nx.DiGraph:
        """
        Build NetworkX graph from analysis data.
        
        Returns:
            NetworkX DiGraph
        """
        if not self.analysis_data:
            return self.graph
        
        # Extract findings to build dependency relationships
        findings = self.analysis_data.get("findings", [])
        file_structure = self.analysis_data.get("file_structure", {})
        
        # Create nodes from file structure
        self._create_nodes(file_structure)
        
        # Create edges from findings
        self._create_edges(findings)
        
        return self.graph

    def _create_nodes(self, file_structure: Dict[str, Any]) -> None:
        """
        Create graph nodes from file structure.
        
        Args:
            file_structure: File structure from analysis
        """
        files = file_structure.get("files", {})
        
        for filename, loc in files.items():
            if isinstance(loc, (int, float)):
                # Simple file with LOC count
                self.graph.add_node(
                    filename,
                    title=filename,
                    label=filename,
                    size=self._calculate_node_size(loc),
                    color=self._calculate_node_color(loc),
                )
                self.node_sizes[filename] = loc
            elif isinstance(loc, dict):
                # Nested structure
                self._add_nested_nodes(filename, loc, "")

    def _add_nested_nodes(self, parent: str, structure: Dict, prefix: str) -> None:
        """
        Recursively add nested file structure nodes.
        
        Args:
            parent: Parent node name
            structure: Nested structure dict
            prefix: Path prefix
        """
        for key, value in structure.items():
            full_path = f"{prefix}{key}" if prefix else key
            
            if isinstance(value, (int, float)):
                # Leaf node with LOC
                self.graph.add_node(
                    full_path,
                    title=full_path,
                    label=key,
                    size=self._calculate_node_size(value),
                    color=self._calculate_node_color(value),
                )
                self.node_sizes[full_path] = value
                
                # Add edge from parent
                if parent:
                    self.graph.add_edge(parent, full_path)
            elif isinstance(value, dict):
                # Nested directory
                new_prefix = f"{prefix}{key}/"
                self._add_nested_nodes(full_path, value, new_prefix)

    def _create_edges(self, findings: List[Dict[str, Any]]) -> None:
        """
        Create graph edges from findings.
        
        Args:
            findings: List of findings from analysis
        """
        for finding in findings:
            evidence = finding.get("evidence", {})
            references = evidence.get("references", [])
            
            if len(references) >= 2:
                # Create edges between referenced files
                for i in range(len(references) - 1):
                    source = references[i].get("file", "")
                    target = references[i + 1].get("file", "")
                    
                    if source and target and source != target:
                        # Color edge based on finding severity
                        edge_color = self._get_edge_color(finding.get("severity", "Low"))
                        
                        self.graph.add_edge(
                            source,
                            target,
                            color=edge_color,
                            weight=1,
                            title=finding.get("title", "Dependency"),
                        )

    def _calculate_node_size(self, loc: float) -> int:
        """
        Calculate node size based on lines of code.
        
        Args:
            loc: Lines of code
            
        Returns:
            Node size (10-50)
        """
        if loc <= 0:
            return 10
        if loc <= 100:
            return 15
        if loc <= 300:
            return 25
        if loc <= 600:
            return 35
        return 50

    def _calculate_node_color(self, loc: float) -> str:
        """
        Calculate node color based on complexity/LOC.
        
        Green = Low LOC (simple)
        Yellow = Medium LOC
        Orange = High LOC
        Red = Very High LOC (complex)
        
        Args:
            loc: Lines of code
            
        Returns:
            Color hex code
        """
        if loc <= 100:
            return "#388e3c"  # Green
        elif loc <= 300:
            return "#fbc02d"  # Yellow
        elif loc <= 600:
            return "#ff9800"  # Orange
        else:
            return "#d32f2f"  # Red

    def _get_edge_color(self, severity: str) -> str:
        """
        Get edge color based on finding severity.
        
        Args:
            severity: Finding severity (Critical, High, Medium, Low)
            
        Returns:
            Color hex code
        """
        severity_lower = severity.lower()
        
        if severity_lower == "critical":
            return "#d32f2f"  # Red
        elif severity_lower == "high":
            return "#ff9800"  # Orange
        elif severity_lower == "medium":
            return "#fbc02d"  # Yellow
        else:
            return "#1976d2"  # Blue (normal dependency)

    def create_pyvis_graph(self, output_path: str = "arcnical_graph.html") -> str:
        """
        Create interactive PyVis visualization.
        
        Args:
            output_path: Path to save HTML file
            
        Returns:
            Path to generated HTML file
        """
        # Build the graph first
        if not self.graph.nodes():
            self.build_graph()
        
        # Create PyVis network
        net = Network(
            height="750px",
            width="100%",
            directed=True,
            physics=True,
        )
        
        # Add nodes
        for node in self.graph.nodes(data=True):
            node_id = node[0]
            node_attr = node[1]
            
            net.add_node(
                node_id,
                label=node_attr.get("label", node_id),
                title=node_attr.get("title", node_id),
                size=node_attr.get("size", 20),
                color=node_attr.get("color", "#1976d2"),
            )
        
        # Add edges
        for edge in self.graph.edges(data=True):
            source, target, attr = edge
            net.add_edge(
                source,
                target,
                color=attr.get("color", "#1976d2"),
                title=attr.get("title", "Dependency"),
                weight=attr.get("weight", 1),
            )
        
        # Configure physics
        net.show_buttons(filter_=["physics"])
        net.toggle_physics(True)
        
        # Save HTML
        net.write_html(output_path)
        
        return output_path

    def get_graph_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the graph.
        
        Returns:
            Dictionary with graph statistics
        """
        if not self.graph.nodes():
            self.build_graph()
        
        return {
            "nodes": len(self.graph.nodes()),
            "edges": len(self.graph.edges()),
            "density": nx.density(self.graph),
            "avg_degree": sum(dict(self.graph.degree()).values()) / max(len(self.graph.nodes()), 1),
        }

    def get_circular_imports(self) -> List[Tuple[str, str]]:
        """
        Detect circular imports/dependencies.
        
        Returns:
            List of circular dependency pairs
        """
        if not self.graph.nodes():
            self.build_graph()
        
        cycles = []
        try:
            for cycle in nx.simple_cycles(self.graph):
                if len(cycle) >= 2:
                    cycles.append((cycle[0], cycle[-1]))
        except nx.NetworkXError:
            pass
        
        return cycles

    def get_hub_modules(self, top_n: int = 5) -> List[Tuple[str, int]]:
        """
        Get most connected modules (hubs).
        
        Args:
            top_n: Number of top hubs to return
            
        Returns:
            List of (module, connection_count) tuples
        """
        if not self.graph.nodes():
            self.build_graph()
        
        degrees = dict(self.graph.degree())
        sorted_degrees = sorted(degrees.items(), key=lambda x: x[1], reverse=True)
        
        return sorted_degrees[:top_n]
