"""
Test suite for Arcnical output schema (v2.0)

Validates that the Pydantic schema correctly enforces the contract
between backend and consumers.
"""

import pytest
import json
from datetime import datetime
from arcnical.schema import (
    Report,
    Metadata,
    Qualification,
    Summary,
    LayerResult,
    Recommendation,
    TargetClassification,
    LayerStatus,
    Severity,
    RecommendationCategory,
    AnalysisDepth,
    TokenUsage,
    Evidence,
    FileReference,
    LanguageBreakdown,
    Metrics,
    PracticeDetection,
    ArchitectureHealthScore,
    SecurityFinding,
    SchemaValidator,
)


class TestMetadata:
    """Test metadata block"""

    def test_metadata_minimal(self):
        """Metadata with required fields only"""
        meta = Metadata(
            tool_version="0.2.0",
            model="claude-sonnet-4-6",
            graph_hash="sha256:abc123",
        )
        assert meta.tool_version == "0.2.0"
        assert meta.model == "claude-sonnet-4-6"
        assert meta.prompt_version == "v1"
        assert meta.force_used is False
        assert meta.token_usage.input == 0

    def test_metadata_full(self):
        """Metadata with all optional fields"""
        usage = TokenUsage(input=1000, output=500, estimated_usd=0.045)
        meta = Metadata(
            tool_version="0.2.0",
            model="claude-sonnet-4-6",
            prompt_version="v1",
            layer_config_version="v1",
            graph_hash="sha256:abc123",
            commit_sha="deadbeef",
            depth=AnalysisDepth.STANDARD,
            force_used=True,
            token_usage=usage,
        )
        assert meta.force_used is True
        assert meta.commit_sha == "deadbeef"
        assert meta.token_usage.estimated_usd == 0.045


class TestQualification:
    """Test target qualification"""

    def test_qualification_application(self):
        """Qualification for application target"""
        qual = Qualification(
            classification=TargetClassification.APPLICATION,
            confidence=0.94,
            signals=["pyproject.toml present", "src/ ratio 0.71"],
        )
        assert qual.classification == TargetClassification.APPLICATION
        assert qual.confidence == 0.94
        assert len(qual.signals) == 2

    def test_qualification_non_application(self):
        """Qualification for non-application target"""
        qual = Qualification(
            classification=TargetClassification.DOCS_OR_DATA,
            confidence=0.92,
            signals=["Low code ratio (0.08)", "Mostly markdown files"],
        )
        assert qual.classification == TargetClassification.DOCS_OR_DATA

    def test_confidence_bounds(self):
        """Confidence must be 0-1"""
        with pytest.raises(ValueError):
            Qualification(
                classification=TargetClassification.APPLICATION,
                confidence=1.5,  # Invalid
                signals=[],
            )


class TestLayerResult:
    """Test layer results"""

    def test_layer_passed(self):
        """L1 layer passes"""
        layer = LayerResult(
            id="L1",
            name="Structural Integrity",
            status=LayerStatus.PASSED,
            findings_count=0,
        )
        assert layer.id == "L1"
        assert layer.status == LayerStatus.PASSED

    def test_layer_blocked(self):
        """L2 layer is blocked"""
        layer = LayerResult(
            id="L2",
            name="Architectural Rules",
            status=LayerStatus.BLOCKED,
            findings_count=1,
            blocking_findings=["critical_circular_import"],
        )
        assert layer.status == LayerStatus.BLOCKED
        assert len(layer.blocking_findings) == 1


class TestRecommendation:
    """Test recommendations"""

    def test_recommendation_full(self):
        """Complete recommendation with evidence"""
        ref = FileReference(file="src/auth/manager.py", line=42, symbol="AuthManager.handle_session")
        evidence = Evidence(
            metric="instability",
            value=0.61,
            references=[ref],
        )
        rec = Recommendation(
            id="REC-001",
            title="Extract session logic from auth module",
            severity=Severity.HIGH,
            category=RecommendationCategory.ARCHITECTURE,
            layer="L4",
            evidence=evidence,
            rationale="The AuthManager class is too tightly coupled to session handling.",
            suggested_action="Move session logic to dedicated SessionManager class.",
            verified=True,
        )
        assert rec.id == "REC-001"
        assert rec.severity == Severity.HIGH
        assert rec.verified is True

    def test_recommendation_minimal(self):
        """Recommendation with minimal fields"""
        ref = FileReference(file="src/module.py")
        evidence = Evidence(metric="complexity", value=18.0, references=[ref])
        rec = Recommendation(
            id="REC-002",
            title="Reduce function complexity",
            severity=Severity.MEDIUM,
            category=RecommendationCategory.CODE_HEALTH,
            layer="L3",
            evidence=evidence,
            rationale="High complexity reduces maintainability.",
            suggested_action="Break function into smaller units.",
        )
        assert rec.line is None  # Optional field


class TestReport:
    """Test complete report validation"""

    @pytest.fixture
    def minimal_report_dict(self) -> dict:
        """Minimal valid report dict"""
        return {
            "schema_version": "2.0",
            "metadata": {
                "tool_version": "0.2.0",
                "model": "claude-sonnet-4-6",
                "graph_hash": "sha256:test",
            },
            "target_type": "application",
            "qualification": {
                "classification": "application",
                "confidence": 0.95,
                "signals": ["pyproject.toml present"],
            },
            "summary": {
                "repo": "test/repo",
                "language_breakdown": {},
                "loc_total": 5000,
                "file_count": 50,
            },
            "layers": [
                {
                    "id": "L1",
                    "name": "Structural Integrity",
                    "status": "passed",
                    "findings_count": 0,
                },
                {
                    "id": "L2",
                    "name": "Architectural Rules",
                    "status": "passed",
                    "findings_count": 0,
                },
                {
                    "id": "L3",
                    "name": "Code Health",
                    "status": "passed",
                    "findings_count": 2,
                },
                {
                    "id": "L4",
                    "name": "Semantic Review",
                    "status": "passed",
                    "findings_count": 1,
                },
            ],
            "scores": {
                "overall": 82.5,
                "maintainability": 85.0,
                "structure": 80.0,
                "security": 82.0,
            },
            "metrics": {
                "complexity_avg": 8.5,
                "complexity_p95": 22.0,
                "instability_avg": 0.45,
                "circular_dependency_count": 0,
                "god_class_count": 1,
                "hotspot_files": [],
            },
            "practice_detection": {
                "architecture_style": "modular_monolith",
                "api_surfaces": ["rest:fastapi"],
                "ci_cd": ["github_actions"],
                "containerization": ["dockerfile"],
                "iac": [],
                "observability": ["opentelemetry"],
                "docs": {
                    "readme": True,
                    "adr_dir": False,
                    "docstring_coverage": 0.42,
                },
                "tests": {
                    "framework": "pytest",
                    "ratio": 0.38,
                },
            },
        }

    def test_report_validation_minimal(self, minimal_report_dict):
        """Validate minimal report"""
        report = Report(**minimal_report_dict)
        assert report.schema_version == "2.0"
        assert report.target_type == TargetClassification.APPLICATION
        assert len(report.layers) == 4

    def test_report_with_recommendations(self, minimal_report_dict):
        """Report with recommendations"""
        minimal_report_dict["recommendations"] = [
            {
                "id": "REC-001",
                "title": "Fix circular imports",
                "severity": "Critical",
                "category": "Architecture",
                "layer": "L2",
                "evidence": {
                    "metric": "circular_dependency",
                    "value": 1.0,
                    "references": [{"file": "src/a.py", "line": 10}],
                },
                "rationale": "Circular dependency blocks module isolation.",
                "suggested_action": "Refactor to remove cycle.",
                "verified": True,
            }
        ]
        report = Report(**minimal_report_dict)
        assert len(report.recommendations) == 1
        assert report.recommendations[0].severity == Severity.CRITICAL

    def test_schema_validator_dict(self, minimal_report_dict):
        """Test SchemaValidator with dict"""
        report = SchemaValidator.validate_report(minimal_report_dict)
        assert isinstance(report, Report)
        assert report.metadata.tool_version == "0.2.0"

    def test_schema_validator_json(self, minimal_report_dict):
        """Test SchemaValidator with JSON string"""
        json_str = json.dumps(minimal_report_dict)
        report = SchemaValidator.validate_json(json_str)
        assert isinstance(report, Report)


class TestSecurityFinding:
    """Test security findings"""

    def test_gitleaks_finding(self):
        """Gitleaks secret detection"""
        finding = SecurityFinding(
            scanner="gitleaks",
            finding_type="secret",
            severity=Severity.CRITICAL,
            description="AWS API key found in code",
            file_references=[
                FileReference(file=".env", line=5),
            ],
        )
        assert finding.scanner == "gitleaks"
        assert finding.severity == Severity.CRITICAL

    def test_pip_audit_finding(self):
        """pip-audit vulnerability"""
        finding = SecurityFinding(
            scanner="pip-audit",
            finding_type="vulnerability",
            severity=Severity.HIGH,
            description="Django SQL injection (CVE-2024-1234)",
            file_references=[
                FileReference(file="requirements.txt", line=42),
            ],
        )
        assert finding.scanner == "pip-audit"


class TestHealthScore:
    """Test Architecture Health Score"""

    def test_score_valid(self):
        """Valid health scores"""
        scores = ArchitectureHealthScore(
            overall=85.0,
            maintainability=88.0,
            structure=82.0,
            security=85.0,
        )
        assert scores.overall == 85.0
        assert scores.maintainability == 88.0

    def test_score_bounds(self):
        """Scores must be 0-100"""
        with pytest.raises(ValueError):
            ArchitectureHealthScore(
                overall=110.0,  # Invalid
                maintainability=80.0,
                structure=80.0,
                security=80.0,
            )


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


class TestSchemaIntegration:
    """Integration tests for schema"""

    def test_schema_json_roundtrip(self):
        """Schema survives JSON serialization/deserialization"""
        original_dict = {
            "schema_version": "2.0",
            "metadata": {
                "tool_version": "0.2.0",
                "model": "claude-sonnet-4-6",
                "graph_hash": "sha256:test",
            },
            "target_type": "application",
            "qualification": {
                "classification": "application",
                "confidence": 0.95,
                "signals": [],
            },
            "summary": {
                "repo": "test/repo",
                "language_breakdown": {},
                "loc_total": 0,
                "file_count": 0,
            },
            "layers": [
                {
                    "id": "L1",
                    "name": "L1",
                    "status": "passed",
                    "findings_count": 0,
                },
            ],
            "scores": {
                "overall": 80.0,
                "maintainability": 80.0,
                "structure": 80.0,
                "security": 80.0,
            },
            "metrics": {
                "complexity_avg": 0.0,
                "complexity_p95": 0.0,
                "instability_avg": 0.0,
                "circular_dependency_count": 0,
                "god_class_count": 0,
                "hotspot_files": [],
            },
            "practice_detection": {
                "docs": {},
                "tests": {},
            },
        }

        # Serialize to JSON
        report1 = Report(**original_dict)
        json_str = report1.model_dump_json()

        # Deserialize from JSON
        report2 = SchemaValidator.validate_json(json_str)

        assert report1.metadata.tool_version == report2.metadata.tool_version
        assert report1.summary.repo == report2.summary.repo


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
