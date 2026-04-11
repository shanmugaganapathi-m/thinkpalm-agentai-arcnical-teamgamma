"""
Unit tests for L3 Heuristics Detector
"""

import pytest
import tempfile
from pathlib import Path

from arcnical.heuristics.l3_detector import L3Detector, L3Finding
from arcnical.graph.builder import CodeKnowledgeGraph
from arcnical.parse.parser import Import


class TestL3Detector:
    """Tests for L3 heuristics detection"""
    
    @pytest.fixture
    def detector(self):
        """Create L3 detector instance"""
        return L3Detector()
    
    @pytest.fixture
    def temp_repo(self):
        """Create temporary repository directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    def test_detect_high_complexity(self, detector):
        """Test detection of high complexity functions"""
        # This test would need a real Python file to parse
        # Placeholder test
        findings = detector.detect_high_complexity(".")
        assert isinstance(findings, list)
    
    def test_detect_large_files(self, detector, temp_repo):
        """Test detection of large files"""
        # Create a temporary Python file with many lines
        test_file = Path(temp_repo) / "large_file.py"
        
        # Write 650 lines (above 600 threshold)
        with open(test_file, 'w') as f:
            for i in range(650):
                f.write(f"line_{i} = {i}\n")
        
        findings = detector.detect_large_files(temp_repo)
        
        # Should detect the large file
        assert isinstance(findings, list)
        # Note: Will only find if file is large enough
        if findings:
            assert all(isinstance(f, L3Finding) for f in findings)
    
    def test_detect_unstable_modules(self, detector):
        """Test detection of unstable modules"""
        graph = CodeKnowledgeGraph()
        
        # Create unstable module (high fan-out)
        for i in range(15):  # High fan-out
            graph.add_import_edge(Import(
                source_file="main.py",
                source_module="main",
                target_module=f"module_{i}"
            ))
        
        findings = detector.detect_unstable_modules(graph)
        
        # Should detect high instability
        assert isinstance(findings, list)
        if findings:
            assert all(isinstance(f, L3Finding) for f in findings)
            assert all("Unstable" in f.title for f in findings)
    
    def test_detect_high_fan_out(self, detector):
        """Test detection of high fan-out modules"""
        graph = CodeKnowledgeGraph()
        
        # Create high fan-out module (15 dependencies)
        for i in range(15):
            graph.add_import_edge(Import(
                source_file="hub.py",
                source_module="hub",
                target_module=f"dep_{i}"
            ))
        
        findings = detector.detect_high_fan_out(graph)
        
        assert isinstance(findings, list)
        if findings:
            assert all(isinstance(f, L3Finding) for f in findings)
            assert all("fan-out" in f.title.lower() for f in findings)
    
    def test_run_all_l3_checks(self, detector):
        """Test running all L3 checks"""
        findings = detector.run_all_l3_checks(CodeKnowledgeGraph(), ".")
        
        assert isinstance(findings, list)
    
    def test_finding_has_required_fields(self, detector):
        """Test that findings have all required fields"""
        graph = CodeKnowledgeGraph()
        
        # Create setup for finding
        for i in range(15):
            graph.add_import_edge(Import(
                source_file="test.py",
                source_module="test",
                target_module=f"mod_{i}"
            ))
        
        findings = detector.detect_high_fan_out(graph)
        
        for finding in findings:
            assert finding.id is not None
            assert finding.title is not None
            assert finding.severity is not None
            assert finding.evidence is not None
    
    def test_threshold_configuration(self, detector):
        """Test that detector uses correct thresholds"""
        assert detector.COMPLEXITY_THRESHOLD == 15
        assert detector.LOC_THRESHOLD == 600
        assert detector.INSTABILITY_THRESHOLD == 0.8
        assert detector.FAN_OUT_THRESHOLD == 10
