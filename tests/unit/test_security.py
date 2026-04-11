"""
Unit tests for Security Scanner
"""

import pytest
from arcnical.heuristics.security_scanner import (
    SecurityScanner, SecurityFinding, SecurityEvaluator
)
from arcnical.schema import Severity


class TestSecurityScanner:
    """Tests for security scanning"""
    
    @pytest.fixture
    def scanner(self):
        """Create security scanner instance"""
        return SecurityScanner()
    
    def test_scanner_initialization(self, scanner):
        """Test scanner initializes correctly"""
        assert scanner is not None
        assert hasattr(scanner, 'enable_gitleaks')
        assert hasattr(scanner, 'gitleaks_available')
    
    def test_check_gitleaks_available(self, scanner):
        """Test gitleaks availability check"""
        available = scanner._check_gitleaks_available()
        # Test that method returns boolean (gitleaks may or may not be installed)
        assert isinstance(available, bool)
    
    def test_scan_for_secrets_disabled(self, scanner):
        """Test that scan respects disabled flag"""
        scanner.enable_gitleaks = False
        findings = scanner.scan_for_secrets(".")
        # Should return empty when disabled
        assert findings == []
    
    def test_scan_for_secrets_not_available(self, scanner):
        """Test graceful handling when gitleaks not available"""
        scanner.gitleaks_available = False
        findings = scanner.scan_for_secrets(".")
        # Should return empty when gitleaks not available
        assert findings == []
    
    def test_parse_gitleaks_finding(self):
        """Test parsing gitleaks finding data"""
        test_data = {
            "RuleID": "AWS Manager ID",
            "Description": "AWS Manager ID",
            "File": "config.py",
            "StartLine": 42,
            "Match": "AKIAIOSFODNN7EXAMPLE"
        }
        
        finding = SecurityScanner._parse_gitleaks_finding(test_data, 1)
        
        assert finding is not None
        assert finding.id == "SEC-001"
        assert finding.finding_type == "AWS Manager ID"
        assert finding.file_path == "config.py"
        assert finding.line_number == 42
    
    def test_determine_severity_critical(self):
        """Test severity determination for critical secrets"""
        severity = SecurityScanner._determine_severity("AWS Manager ID")
        assert severity == Severity.CRITICAL
        
        severity = SecurityScanner._determine_severity("PRIVATE KEY")
        assert severity == Severity.CRITICAL
    
    def test_determine_severity_high(self):
        """Test severity determination for high-risk secrets"""
        severity = SecurityScanner._determine_severity("Database Password")
        assert severity == Severity.HIGH
    
    def test_determine_severity_medium(self):
        """Test severity determination for medium-risk secrets"""
        severity = SecurityScanner._determine_severity("Generic Secret")
        assert severity == Severity.MEDIUM
    
    def test_scan_repository(self, scanner):
        """Test full repository scan"""
        result = scanner.scan_repository(".")
        
        assert "secrets" in result
        assert "summary" in result
        assert isinstance(result["secrets"], list)
        assert isinstance(result["summary"], dict)
    
    def test_security_finding_creation(self):
        """Test creating security finding"""
        finding = SecurityFinding(
            id="SEC-001",
            title="API Key detected",
            severity=Severity.CRITICAL,
            finding_type="API_KEY",
            description="Hardcoded API key found",
            file_path="config.py",
            line_number=10
        )
        
        assert finding.id == "SEC-001"
        assert finding.title == "API Key detected"
        assert finding.severity == Severity.CRITICAL


class TestSecurityEvaluator:
    """Tests for security findings evaluation"""
    
    def test_format_findings(self):
        """Test formatting findings"""
        finding = SecurityFinding(
            id="SEC-001",
            title="Secret detected",
            severity=Severity.HIGH,
            finding_type="API_KEY",
            description="API key in source",
            file_path="app.py",
            line_number=15
        )
        
        formatted = SecurityEvaluator.format_findings([finding])
        
        assert len(formatted) == 1
        assert formatted[0]["id"] == "SEC-001"
        assert formatted[0]["severity"] == "High"
        assert formatted[0]["type"] == "API_KEY"
    
    def test_summarize_findings(self):
        """Test findings summary generation"""
        findings = [
            SecurityFinding(
                id="SEC-001",
                title="Critical secret",
                severity=Severity.CRITICAL,
                finding_type="API_KEY",
                description="test"
            ),
            SecurityFinding(
                id="SEC-002",
                title="High secret",
                severity=Severity.HIGH,
                finding_type="PASSWORD",
                description="test"
            ),
            SecurityFinding(
                id="SEC-003",
                title="Medium secret",
                severity=Severity.MEDIUM,
                finding_type="TOKEN",
                description="test"
            )
        ]
        
        summary = SecurityEvaluator.summarize_findings(findings)
        
        assert summary["total"] == 3
        assert summary["critical"] == 1
        assert summary["high"] == 1
        assert summary["medium"] == 1
        assert summary["has_critical"] is True
    
    def test_summarize_no_findings(self):
        """Test summary with no findings"""
        summary = SecurityEvaluator.summarize_findings([])
        
        assert summary["total"] == 0
        assert summary["critical"] == 0
        assert summary["has_critical"] is False
