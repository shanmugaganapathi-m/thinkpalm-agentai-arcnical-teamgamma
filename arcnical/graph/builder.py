"""
Code Knowledge Graph Builder

Creates and manages a networkx graph representing the structure and relationships
of code in a repository.
"""

import json
from typing import List, Dict, Set, Any, Tuple, Optional
from dataclasses import asdict

try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False

from arcnical.parse.parser import ParseResult, Symbol, Import, Call, SymbolType


class CodeKnowledgeGraph:
    """
    Represents the structure of a codebase as a directed graph.
    
    Nodes represent code elements (files, modules, classes, functions).
    Edges represent relationships (imports, calls, containment).
    """
    
    def __init__(self):
        """Initialize empty knowledge graph."""
        if not NETWORKX_AVAILABLE:
            raise ImportError(
                "networkx not installed. Run: pip install networkx"
            )
        
        self.graph = nx.DiGraph()
        self.symbols: Dict[str, Symbol] = {}
        self.cycles: Optional[List[List[str]]] = None
    
    def add_parse_result(self, result: ParseResult):
        """Add all symbols and relationships from a ParseResult."""
        # Add symbols as nodes
        for symbol in result.symbols:
            self.add_symbol(symbol)
        
        # Add import relationships as edges
        for import_obj in result.imports:
            self.add_import_edge(import_obj)
        
        # Add call relationships as edges
        for call in result.calls:
            self.add_call_edge(call)
    
    def add_symbol(self, symbol: Symbol):
        """Add a code symbol as a node to the graph."""
        self.symbols[symbol.qualified_name] = symbol
        
        node_data = {
            'type': symbol.type.value,
            'file': symbol.file,
            'name': symbol.name,
            'language': symbol.language,
            'lineno': symbol.lineno,
            'end_lineno': symbol.end_lineno,
        }
        
        if symbol.is_async:
            node_data['async'] = True
        if symbol.is_decorated:
            node_data['decorated'] = True
        
        self.graph.add_node(symbol.qualified_name, **node_data)
    
    def add_import_edge(self, import_obj: Import):
        """Add an import relationship as an edge."""
        source = import_obj.source_module
        target = import_obj.target_module
        
        # Only add edge if both nodes exist or create them
        if source not in self.graph:
            self.graph.add_node(source, type='module')
        if target not in self.graph:
            self.graph.add_node(target, type='module')
        
        edge_data = {
            'type': 'import',
            'import_type': import_obj.import_type,
            'lineno': import_obj.lineno,
        }
        
        if import_obj.target_name:
            edge_data['target_name'] = import_obj.target_name
        
        self.graph.add_edge(source, target, **edge_data)
    
    def add_call_edge(self, call: Call):
        """Add a function call relationship as an edge."""
        caller = call.caller_qualified_name
        called = call.called_qualified_name
        
        # Ensure nodes exist
        if caller not in self.graph:
            self.graph.add_node(caller, type='function')
        if called not in self.graph:
            self.graph.add_node(called, type='function')
        
        edge_data = {
            'type': 'call',
            'lineno': call.lineno,
        }
        
        self.graph.add_edge(caller, called, **edge_data)
    
    def detect_cycles(self) -> List[List[str]]:
        """Detect all circular dependencies in the graph."""
        try:
            cycles = list(nx.simple_cycles(self.graph))
            self.cycles = cycles
            return cycles
        except nx.NetworkXNoCycle:
            self.cycles = []
            return []
    
    def get_cycle_count(self) -> int:
        """Get count of circular dependencies."""
        if self.cycles is None:
            self.detect_cycles()
        return len(self.cycles) if self.cycles else 0
    
    def fan_in(self, node: str) -> int:
        """Count incoming edges (how many import this node)."""
        return self.graph.in_degree(node)
    
    def fan_out(self, node: str) -> int:
        """Count outgoing edges (how many does this node import)."""
        return self.graph.out_degree(node)
    
    def instability(self, node: str) -> float:
        """
        Calculate instability metric I = Ce / (Ca + Ce).
        
        Where:
        - Ce (efferent coupling) = fan_out = outgoing dependencies
        - Ca (afferent coupling) = fan_in = incoming dependencies
        
        I = 0: Maximally stable (no dependencies)
        I = 1: Maximally unstable (only outgoing dependencies)
        """
        ce = self.fan_out(node)
        ca = self.fan_in(node)
        
        if ca + ce == 0:
            return 0.0
        
        return ce / (ca + ce)
    
    def get_symbol_info(self, qualified_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a symbol."""
        if qualified_name not in self.symbols:
            return None
        
        symbol = self.symbols[qualified_name]
        info = {
            'qualified_name': symbol.qualified_name,
            'name': symbol.name,
            'type': symbol.type.value,
            'file': symbol.file,
            'lineno': symbol.lineno,
            'end_lineno': symbol.end_lineno,
            'language': symbol.language,
            'fan_in': self.fan_in(qualified_name),
            'fan_out': self.fan_out(qualified_name),
            'instability': self.instability(qualified_name),
        }
        
        return info
    
    def get_all_symbols_of_type(self, symbol_type: SymbolType) -> List[Symbol]:
        """Get all symbols of a specific type."""
        return [
            s for s in self.symbols.values()
            if s.type == symbol_type
        ]
    
    def get_dependencies(self, node: str) -> List[str]:
        """Get all direct dependencies of a node (outgoing edges)."""
        return list(self.graph.successors(node))
    
    def get_dependents(self, node: str) -> List[str]:
        """Get all nodes that depend on this node (incoming edges)."""
        return list(self.graph.predecessors(node))
    
    def summary(self) -> Dict[str, Any]:
        """Get summary statistics about the graph."""
        all_cycles = self.detect_cycles() if self.cycles is None else self.cycles
        
        return {
            'total_nodes': self.graph.number_of_nodes(),
            'total_edges': self.graph.number_of_edges(),
            'total_symbols': len(self.symbols),
            'circular_dependencies': len(all_cycles),
            'node_types': self._count_node_types(),
            'edge_types': self._count_edge_types(),
        }
    
    def _count_node_types(self) -> Dict[str, int]:
        """Count nodes by type."""
        counts = {}
        for node, data in self.graph.nodes(data=True):
            node_type = data.get('type', 'unknown')
            counts[node_type] = counts.get(node_type, 0) + 1
        return counts
    
    def _count_edge_types(self) -> Dict[str, int]:
        """Count edges by type."""
        counts = {}
        for source, target, data in self.graph.edges(data=True):
            edge_type = data.get('type', 'unknown')
            counts[edge_type] = counts.get(edge_type, 0) + 1
        return counts
    
    def to_json(self) -> Dict[str, Any]:
        """Serialize graph to JSON-compatible format."""
        return {
            'nodes': self._nodes_to_json(),
            'edges': self._edges_to_json(),
            'summary': self.summary(),
        }
    
    def _nodes_to_json(self) -> List[Dict[str, Any]]:
        """Convert nodes to JSON format."""
        nodes = []
        for node, data in self.graph.nodes(data=True):
            node_data = {'id': node}
            node_data.update(data)
            nodes.append(node_data)
        return nodes
    
    def _edges_to_json(self) -> List[Dict[str, Any]]:
        """Convert edges to JSON format."""
        edges = []
        for source, target, data in self.graph.edges(data=True):
            edge_data = {
                'source': source,
                'target': target,
            }
            edge_data.update(data)
            edges.append(edge_data)
        return edges
    
    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "CodeKnowledgeGraph":
        """Reconstruct graph from JSON format."""
        graph = cls()
        
        # Add nodes
        for node_data in data.get('nodes', []):
            node_id = node_data.pop('id')
            graph.graph.add_node(node_id, **node_data)
        
        # Add edges
        for edge_data in data.get('edges', []):
            source = edge_data.pop('source')
            target = edge_data.pop('target')
            graph.graph.add_edge(source, target, **edge_data)
        
        return graph


class GraphPersistence:
    """Handle saving and loading knowledge graphs."""
    
    @staticmethod
    def save(graph: CodeKnowledgeGraph, filepath: str):
        """Save graph to JSON file."""
        data = graph.to_json()
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    
    @staticmethod
    def load(filepath: str) -> CodeKnowledgeGraph:
        """Load graph from JSON file."""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return CodeKnowledgeGraph.from_json(data)
