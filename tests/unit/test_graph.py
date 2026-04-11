"""
Unit tests for knowledge graph builder.
"""

import pytest
import json
import tempfile
from pathlib import Path

from arcnical.graph.builder import CodeKnowledgeGraph, GraphPersistence
from arcnical.parse.parser import Symbol, SymbolType, Import, Call, ParseResult


class TestCodeKnowledgeGraph:
    """Tests for CodeKnowledgeGraph."""
    
    @pytest.fixture
    def graph(self):
        """Create empty graph."""
        return CodeKnowledgeGraph()
    
    def test_add_symbol(self, graph):
        """Test adding a symbol to graph."""
        symbol = Symbol(
            file="test.py",
            type=SymbolType.FUNCTION,
            name="test_func",
            qualified_name="module.test_func",
            lineno=10,
        )
        
        graph.add_symbol(symbol)
        
        assert "module.test_func" in graph.graph.nodes()
        assert graph.symbols["module.test_func"] == symbol
    
    def test_add_import_edge(self, graph):
        """Test adding import edge."""
        from arcnical.parse.parser import Import
        
        import_obj = Import(
            source_file="file1.py",
            source_module="module1",
            target_module="module2",
            import_type="import",
        )
        
        graph.add_import_edge(import_obj)
        
        assert graph.graph.has_edge("module1", "module2")
        edge_data = graph.graph.get_edge_data("module1", "module2")
        assert edge_data['type'] == 'import'
    
    def test_add_call_edge(self, graph):
        """Test adding function call edge."""
        call = Call(
            caller_file="test.py",
            caller_qualified_name="func1",
            called_qualified_name="func2",
            lineno=5,
        )
        
        graph.add_call_edge(call)
        
        assert graph.graph.has_edge("func1", "func2")
        edge_data = graph.graph.get_edge_data("func1", "func2")
        assert edge_data['type'] == 'call'
    
    def test_add_parse_result(self, graph):
        """Test adding complete parse result."""
        result = ParseResult()
        result.symbols = [
            Symbol(
                file="test.py",
                type=SymbolType.FUNCTION,
                name="func1",
                qualified_name="test.func1",
                lineno=1,
            ),
            Symbol(
                file="test.py",
                type=SymbolType.FUNCTION,
                name="func2",
                qualified_name="test.func2",
                lineno=5,
            ),
        ]
        result.imports = [
            Import(
                source_file="test.py",
                source_module="test",
                target_module="other",
                import_type="import",
            )
        ]
        
        graph.add_parse_result(result)
        
        assert len(graph.symbols) == 2
        assert graph.graph.number_of_edges() >= 1
    
    def test_detect_cycles_no_cycles(self, graph):
        """Test cycle detection with no cycles."""
        graph.add_import_edge(Import(
            source_file="a.py", source_module="a", target_module="b"
        ))
        graph.add_import_edge(Import(
            source_file="b.py", source_module="b", target_module="c"
        ))
        
        cycles = graph.detect_cycles()
        
        assert len(cycles) == 0
    
    def test_detect_cycles_with_cycles(self, graph):
        """Test cycle detection with circular dependency."""
        graph.add_import_edge(Import(
            source_file="a.py", source_module="a", target_module="b"
        ))
        graph.add_import_edge(Import(
            source_file="b.py", source_module="b", target_module="c"
        ))
        graph.add_import_edge(Import(
            source_file="c.py", source_module="c", target_module="a"
        ))
        
        cycles = graph.detect_cycles()
        
        assert len(cycles) > 0
        assert graph.get_cycle_count() > 0
    
    def test_fan_in_fan_out(self, graph):
        """Test fan-in and fan-out calculation."""
        graph.add_import_edge(Import(
            source_file="a.py", source_module="a", target_module="b"
        ))
        graph.add_import_edge(Import(
            source_file="c.py", source_module="c", target_module="b"
        ))
        
        # b has 2 incoming (from a and c) and 0 outgoing
        assert graph.fan_in("b") == 2
        assert graph.fan_out("b") == 0
        
        # a has 0 incoming and 1 outgoing (to b)
        assert graph.fan_in("a") == 0
        assert graph.fan_out("a") == 1
    
    def test_instability_calculation(self, graph):
        """Test instability metric (I = Ce / (Ca + Ce))."""
        # Add edges to create known instability
        graph.add_import_edge(Import(
            source_file="a.py", source_module="a", target_module="b"
        ))
        
        # a: fan_in=0, fan_out=1 -> I = 1/(0+1) = 1.0 (unstable)
        assert graph.instability("a") == 1.0
        
        # b: fan_in=1, fan_out=0 -> I = 0/(1+0) = 0.0 (stable)
        assert graph.instability("b") == 0.0
    
    def test_get_symbol_info(self, graph):
        """Test retrieving symbol information."""
        symbol = Symbol(
            file="test.py",
            type=SymbolType.CLASS,
            name="MyClass",
            qualified_name="module.MyClass",
            lineno=10,
            end_lineno=20,
        )
        graph.add_symbol(symbol)
        
        info = graph.get_symbol_info("module.MyClass")
        
        assert info is not None
        assert info['name'] == "MyClass"
        assert info['type'] == "class"
        assert info['lineno'] == 10
    
    def test_get_dependencies(self, graph):
        """Test getting dependencies (outgoing edges)."""
        graph.add_import_edge(Import(
            source_file="a.py", source_module="a", target_module="b"
        ))
        graph.add_import_edge(Import(
            source_file="a.py", source_module="a", target_module="c"
        ))
        
        deps = graph.get_dependencies("a")
        
        assert "b" in deps
        assert "c" in deps
    
    def test_get_dependents(self, graph):
        """Test getting dependents (incoming edges)."""
        graph.add_import_edge(Import(
            source_file="a.py", source_module="a", target_module="c"
        ))
        graph.add_import_edge(Import(
            source_file="b.py", source_module="b", target_module="c"
        ))
        
        dependents = graph.get_dependents("c")
        
        assert "a" in dependents
        assert "b" in dependents
    
    def test_summary(self, graph):
        """Test graph summary statistics."""
        graph.add_symbol(Symbol(
            file="test.py", type=SymbolType.FUNCTION,
            name="f", qualified_name="f", lineno=1
        ))
        graph.add_import_edge(Import(
            source_file="a.py", source_module="a", target_module="b"
        ))
        
        summary = graph.summary()
        
        assert 'total_nodes' in summary
        assert 'total_edges' in summary
        assert 'circular_dependencies' in summary
        assert summary['total_nodes'] > 0


class TestGraphPersistence:
    """Tests for graph persistence (save/load)."""
    
    def test_save_and_load(self):
        """Test saving and loading graph to/from JSON."""
        graph = CodeKnowledgeGraph()
        
        # Add some data
        graph.add_symbol(Symbol(
            file="test.py",
            type=SymbolType.FUNCTION,
            name="test_func",
            qualified_name="test.test_func",
            lineno=10,
        ))
        graph.add_import_edge(Import(
            source_file="a.py",
            source_module="module_a",
            target_module="module_b",
        ))
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            GraphPersistence.save(graph, temp_path)
            
            # Load back
            loaded_graph = GraphPersistence.load(temp_path)
            
            # Verify
            assert "test.test_func" in loaded_graph.graph.nodes()
            assert loaded_graph.graph.has_edge("module_a", "module_b")
        finally:
            Path(temp_path).unlink()
    
    def test_json_format(self):
        """Test JSON format of saved graph."""
        graph = CodeKnowledgeGraph()
        graph.add_import_edge(Import(
            source_file="a.py",
            source_module="a",
            target_module="b",
        ))
        
        json_data = graph.to_json()
        
        assert 'nodes' in json_data
        assert 'edges' in json_data
        assert 'summary' in json_data
        assert len(json_data['nodes']) > 0
        assert len(json_data['edges']) > 0
