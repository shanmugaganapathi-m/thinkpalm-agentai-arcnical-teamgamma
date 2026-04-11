"""
Unit tests for metrics calculator.
"""

import pytest
import tempfile
from pathlib import Path

from arcnical.metrics.calculator import (
    ComplexityCalculator,
    CouplingCalculator,
    LOCCalculator,
    GodClassDetector,
    MetricsAggregator,
)
from arcnical.graph.builder import CodeKnowledgeGraph
from arcnical.parse.parser import Symbol, SymbolType, Import, ParseResult


class TestComplexityCalculator:
    """Tests for complexity calculator."""
    
    @pytest.fixture
    def calculator(self):
        """Create calculator instance."""
        try:
            return ComplexityCalculator()
        except ImportError:
            pytest.skip("radon not installed")
    
    def test_calculate_file_complexity(self, calculator):
        """Test calculating complexity for a file."""
        # Create temp file with Python code
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
def simple():
    return 1

def complex_func(x):
    if x > 0:
        if x > 10:
            if x > 100:
                return "big"
            return "medium"
        return "small"
    return "negative"
""")
            temp_path = f.name
        
        try:
            avg, max_c, total = calculator.calculate_file_complexity(temp_path)
            
            # complex_func should have high complexity
            assert max_c > 0
            assert avg > 0
        finally:
            Path(temp_path).unlink()


class TestCouplingCalculator:
    """Tests for coupling calculator."""
    
    def test_calculate_fan_in_fan_out(self):
        """Test fan-in/fan-out calculation from graph."""
        graph = CodeKnowledgeGraph()
        graph.add_import_edge(Import(
            source_file="a.py",
            source_module="a",
            target_module="b",
        ))
        graph.add_import_edge(Import(
            source_file="c.py",
            source_module="c",
            target_module="b",
        ))
        
        results = CouplingCalculator.calculate_fan_in_fan_out(graph)
        
        assert results["a"] == (0, 1)  # No incoming, 1 outgoing
        assert results["b"] == (2, 0)  # 2 incoming, no outgoing
        assert results["c"] == (0, 1)  # No incoming, 1 outgoing
    
    def test_calculate_instability(self):
        """Test instability calculation."""
        graph = CodeKnowledgeGraph()
        graph.add_import_edge(Import(
            source_file="a.py", source_module="a", target_module="b"
        ))
        
        results = CouplingCalculator.calculate_instability(graph)
        
        # a: unstable (only outgoing)
        assert results["a"] == 1.0
        
        # b: stable (only incoming)
        assert results["b"] == 0.0


class TestLOCCalculator:
    """Tests for lines of code calculator."""
    
    def test_count_file_loc(self):
        """Test counting LOC in a file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
# Comment line
def hello():
    print("hello")  # inline comment
    
    # Another comment
    return 42
""")
            temp_path = f.name
        
        try:
            loc = LOCCalculator.count_file_loc(temp_path)
            
            # Should count non-comment, non-blank lines
            assert loc > 0
        finally:
            Path(temp_path).unlink()
    
    def test_count_function_loc(self):
        """Test counting LOC in a function."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""def myfunction():
    line1 = 1
    line2 = 2
    # comment
    
    line3 = 3
    return line1 + line2 + line3
""")
            temp_path = f.name
        
        try:
            # Count lines 1-7
            loc = LOCCalculator.count_function_loc(temp_path, 1, 7)
            
            assert loc > 0
        finally:
            Path(temp_path).unlink()


class TestGodClassDetector:
    """Tests for God Class detection."""
    
    def test_is_god_class_by_loc(self):
        """Test detecting God Class by LOC."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            # Create a class with >300 lines
            f.write("class BigClass:\n")
            for i in range(350):
                f.write(f"    line{i} = {i}\n")
            temp_path = f.name
        
        try:
            is_god, reason = GodClassDetector.is_god_class(temp_path, 1, 351, 1)
            
            assert is_god
            assert "LOC" in reason
        finally:
            Path(temp_path).unlink()
    
    def test_is_god_class_by_method_count(self):
        """Test detecting God Class by method count."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("class ClassWithManyMethods:\n")
            for i in range(25):
                f.write(f"    def method{i}(self): pass\n")
            temp_path = f.name
        
        try:
            is_god, reason = GodClassDetector.is_god_class(temp_path, 1, 26, 25)
            
            assert is_god
            assert "Methods" in reason
        finally:
            Path(temp_path).unlink()
    
    def test_not_god_class(self):
        """Test that normal classes aren't flagged."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("class NormalClass:\n")
            for i in range(5):
                f.write(f"    def method{i}(self): pass\n")
            temp_path = f.name
        
        try:
            is_god, reason = GodClassDetector.is_god_class(temp_path, 1, 6, 5)
            
            assert not is_god
        finally:
            Path(temp_path).unlink()


class TestMetricsAggregator:
    """Tests for metrics aggregator."""
    
    @pytest.fixture
    def aggregator(self):
        """Create aggregator instance."""
        try:
            return MetricsAggregator()
        except ImportError:
            pytest.skip("radon not installed")
    
    def test_compute_coupling_metrics(self, aggregator):
        """Test computing coupling metrics."""
        graph = CodeKnowledgeGraph()
        graph.add_import_edge(Import(
            source_file="a.py", source_module="a", target_module="b"
        ))
        graph.add_import_edge(Import(
            source_file="b.py", source_module="b", target_module="c"
        ))
        
        metrics = aggregator._compute_coupling_metrics(graph)
        
        assert 'avg_fan_in' in metrics
        assert 'avg_fan_out' in metrics
        assert 'avg_instability' in metrics
        assert metrics['modules_analyzed'] == 3
