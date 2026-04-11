"""
Unit tests for L2 Heuristics Detector
"""

import pytest
from arcnical.heuristics.l2_detector import L2Detector, L2Finding
from arcnical.graph.builder import CodeKnowledgeGraph
from arcnical.parse.parser import Symbol, SymbolType, Import, ParseResult


class TestL2Detector:
    """Tests for L2 heuristics detection"""
    
    @pytest.fixture
    def detector(self):
        """Create L2 detector instance"""
        return L2Detector()
    
    @pytest.fixture
    def graph_no_cycles(self):
        """Create graph with no cycles"""
        graph = CodeKnowledgeGraph()
        graph.add_import_edge(Import(
            source_file="a.py", source_module="a", target_module="b"
        ))
        graph.add_import_edge(Import(
            source_file="b.py", source_module="b", target_module="c"
        ))
        return graph
    
    @pytest.fixture
    def graph_with_cycles(self):
        """Create graph with circular imports"""
        graph = CodeKnowledgeGraph()
        graph.add_import_edge(Import(
            source_file="a.py", source_module="a", target_module="b"
        ))
        graph.add_import_edge(Import(
            source_file="b.py", source_module="b", target_module="c"
        ))
        graph.add_import_edge(Import(
            source_file="c.py", source_module="c", target_module="a"
        ))
        return graph
    
    def test_detect_circular_imports_no_cycles(self, detector, graph_no_cycles):
        """Test that no cycles are detected when there are none"""
        findings = detector.detect_circular_imports(graph_no_cycles)
        assert len(findings) == 0
    
    def test_detect_circular_imports_with_cycles(self, detector, graph_with_cycles):
        """Test detection of circular imports"""
        findings = detector.detect_circular_imports(graph_with_cycles)
        assert len(findings) > 0
        assert all(isinstance(f, L2Finding) for f in findings)
        assert all("Circular" in f.title for f in findings)
        assert all(hasattr(f, 'evidence_data') for f in findings)
    
    def test_detect_god_classes_normal_class(self, detector):
        """Test that normal classes are not flagged"""
        graph = CodeKnowledgeGraph()
        
        # Add a normal class
        class_sym = Symbol(
            file="test.py",
            type=SymbolType.CLASS,
            name="NormalClass",
            qualified_name="test.NormalClass",
            lineno=1,
            end_lineno=20
        )
        graph.add_symbol(class_sym)
        
        findings = detector.detect_god_classes(graph, ".")
        # Should not flag this class (too small)
        assert len(findings) == 0
    
    def test_detect_god_classes_many_methods(self, detector):
        """Test detection of classes with too many methods"""
        graph = CodeKnowledgeGraph()
        
        # Add class
        class_sym = Symbol(
            file="test.py",
            type=SymbolType.CLASS,
            name="LargeClass",
            qualified_name="test.LargeClass",
            lineno=1,
            end_lineno=30
        )
        graph.add_symbol(class_sym)
        
        # Add 25 methods
        for i in range(25):
            method_sym = Symbol(
                file="test.py",
                type=SymbolType.METHOD,
                name=f"method{i}",
                qualified_name=f"test.LargeClass.method{i}",
                lineno=i+2,
                parent_qualified_name="test.LargeClass"
            )
            graph.add_symbol(method_sym)
        
        findings = detector.detect_god_classes(graph, ".")
        # Should detect god class (25 methods > 20 threshold)
        assert len(findings) > 0
        assert any("method" in f.title.lower() for f in findings)
        assert all(hasattr(f, 'evidence_data') for f in findings)
    
    def test_detect_layer_violations(self, detector):
        """Test layer violation detection"""
        graph = CodeKnowledgeGraph()
        
        findings = detector.detect_layer_violations(graph)
        # Placeholder - should return empty list for now
        assert isinstance(findings, list)
    
    def test_run_all_l2_checks(self, detector, graph_with_cycles):
        """Test running all L2 checks"""
        findings = detector.run_all_l2_checks(graph_with_cycles, ".")
        
        assert isinstance(findings, list)
        # Should have findings (cycles detected)
        assert len(findings) > 0
    
    def test_finding_has_evidence(self, detector, graph_with_cycles):
        """Test that findings include evidence data"""
        findings = detector.detect_circular_imports(graph_with_cycles)
        
        for finding in findings:
            assert finding.evidence_data is not None
            assert "cycle" in finding.evidence_data
    
    def test_finding_conversion_to_recommendation(self, detector, graph_with_cycles):
        """Test converting L2 findings to recommendations"""
        findings = detector.detect_circular_imports(graph_with_cycles)
        
        if findings:
            finding = findings[0]
            rec = finding.to_recommendation()
            
            assert rec.id is not None
            assert rec.title is not None
            assert rec.severity is not None
            # Evidence is now an Evidence object, not dict
            assert rec.evidence is not None
            assert hasattr(rec.evidence, 'metric')
            assert hasattr(rec.evidence, 'value')
            assert hasattr(rec.evidence, 'references')
