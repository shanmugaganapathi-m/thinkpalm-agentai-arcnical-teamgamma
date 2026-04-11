"""
Arcnical Output Schema v2.0 - FROZEN

This is the contract between the backend analysis pipeline and all consumers
(CLI, Streamlit UI, evaluation harness).

DO NOT change this without explicit approval.

Version: 2.0
Tool: arcnical 0.2.0
Schema locked: [Timestamp]
"""

from typing import Any, Dict, List, Literal, Optional
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime


# ============================================================================
# ENUMS
# ============================================================================


class TargetClassification(str, Enum):
    """Target type classification (FR-QUAL)"""
    APPLICATION = "application"
    LIBRARY = "library"
    DOCS_OR_DATA = "docs-or-data"
    UNKNOWN = "unknown"


class LayerStatus(str, Enum):
    """Per-layer status (FR-LAY)"""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    WARNED = "warned"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


class Severity(str, Enum):
    """Recommendation severity"""
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class RecommendationCategory(str, Enum):
    """Recommendation category"""
    ARCHITECTURE = "Architecture"
    MAINTAINABILITY = "Maintainability"
    PERFORMANCE = "Performance"
    SECURITY = "Security"
    CODE_HEALTH = "Code Health"
    STRUCTURE = "Structure"
    OTHER = "Other"


class AnalysisDepth(str, Enum):
    """Analysis depth mode (FR-CLI-03)"""
    QUICK = "quick"      # L1-L3 only, no LLM
    STANDARD = "standard"  # All 4 layers with LLM


# ============================================================================
# METADATA
# ============================================================================


class TokenUsage(BaseModel):
    """LLM token usage tracking (FR-REV-06)"""
    input: int = Field(0, description="Input tokens used")
    output: int = Field(0, description="Output tokens used")
    estimated_usd: float = Field(0.0, description="Estimated cost in USD")


class Metadata(BaseModel):
    """Report metadata block (FR-LAY-04, FR-REV-06, FR-REV-07)"""
    tool_version: str = Field(..., description="Arcnical version, e.g. '0.2.0'")
    model: str = Field(
        ...,
        description="LLM model ID, e.g. 'claude-sonnet-4-6'"
    )
    prompt_version: str = Field(
        "v1",
        description="Prompt template version, e.g. 'v1'"
    )
    layer_config_version: str = Field(
        "v1",
        description="Layer configuration version"
    )
    graph_hash: str = Field(
        ...,
        description="SHA256 hash of knowledge graph for reproducibility"
    )
    commit_sha: Optional[str] = Field(
        None,
        description="Git HEAD commit SHA if repo is a Git repo"
    )
    generated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Report generation timestamp (ISO 8601)"
    )
    depth: AnalysisDepth = Field(
        AnalysisDepth.STANDARD,
        description="Analysis depth mode (quick or standard)"
    )
    force_used: bool = Field(
        False,
        description="Whether --force flag was used to bypass qualification/halts"
    )
    token_usage: TokenUsage = Field(
        default_factory=TokenUsage,
        description="LLM token usage tracking"
    )


# ============================================================================
# TARGET QUALIFICATION (FR-QUAL)
# ============================================================================


class QualificationSignal(BaseModel):
    """Individual signal used in qualification"""
    signal: str = Field(..., description="Signal description")
    weight: float = Field(1.0, description="Weight in classification (0-1)")


class Qualification(BaseModel):
    """Target qualification block (FR-QUAL-03)"""
    classification: TargetClassification = Field(
        ...,
        description="Classified target type"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score (0-1)"
    )
    signals: List[str] = Field(
        default_factory=list,
        description="Signals observed (e.g. 'pyproject.toml present', 'src/ ratio 0.71')"
    )


# ============================================================================
# SUMMARY
# ============================================================================


class LanguageBreakdown(BaseModel):
    """Language distribution in codebase"""
    python: float = Field(0.0, ge=0.0, le=1.0)
    typescript: float = Field(0.0, ge=0.0, le=1.0)
    javascript: float = Field(0.0, ge=0.0, le=1.0)
    go: float = Field(0.0, ge=0.0, le=1.0)
    java: float = Field(0.0, ge=0.0, le=1.0)
    rust: float = Field(0.0, ge=0.0, le=1.0)
    other: float = Field(0.0, ge=0.0, le=1.0)


class Summary(BaseModel):
    """Report summary (high-level stats)"""
    repo: str = Field(..., description="Repository name or path")
    language_breakdown: LanguageBreakdown = Field(
        default_factory=LanguageBreakdown,
        description="Language distribution"
    )
    loc_total: int = Field(0, description="Total lines of code")
    file_count: int = Field(0, description="Total files analyzed")


# ============================================================================
# LAYERS
# ============================================================================


class LayerResult(BaseModel):
    """Single layer result (FR-LAY-04)"""
    id: Literal["L1", "L2", "L3", "L4"] = Field(..., description="Layer ID")
    name: str = Field(..., description="Layer name")
    status: LayerStatus = Field(..., description="Layer execution status")
    findings_count: int = Field(0, ge=0, description="Count of findings in this layer")
    blocking_findings: List[str] = Field(
        default_factory=list,
        description="IDs of blocking findings (if any)"
    )


# ============================================================================
# METRICS
# ============================================================================


class Metrics(BaseModel):
    """Code metrics (FR-STR-03)"""
    complexity_avg: float = Field(0.0, description="Average cyclomatic complexity")
    complexity_p95: float = Field(0.0, description="95th percentile cyclomatic complexity")
    instability_avg: float = Field(0.0, description="Average instability (I = Ce / (Ca + Ce))")
    circular_dependency_count: int = Field(0, ge=0, description="Count of circular import cycles")
    god_class_count: int = Field(0, ge=0, description="Count of god-class candidates")
    hotspot_files: List[str] = Field(
        default_factory=list,
        description="Top hotspot files by complexity × churn"
    )


# ============================================================================
# ARCHITECTURE & PRACTICE DETECTION (FR-ARCH)
# ============================================================================


class DocsInfo(BaseModel):
    """Documentation posture (FR-ARCH-06)"""
    readme: bool = Field(False, description="README present")
    adr_dir: bool = Field(False, description="ADR directory present")
    docstring_coverage: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="Sample-based docstring coverage"
    )


class TestsInfo(BaseModel):
    """Test posture (FR-ARCH-07)"""
    framework: Optional[str] = Field(None, description="Detected test framework")
    ratio: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="Test-to-source file ratio"
    )


class PracticeDetection(BaseModel):
    """Architecture & practice detection block (FR-ARCH)"""
    architecture_style: Optional[str] = Field(
        None,
        description="Inferred architecture style (e.g. 'modular_monolith', 'microservices')"
    )
    api_surfaces: List[str] = Field(
        default_factory=list,
        description="API surface types (e.g. 'rest:fastapi', 'graphql', 'grpc')"
    )
    ci_cd: List[str] = Field(
        default_factory=list,
        description="CI/CD platforms detected"
    )
    containerization: List[str] = Field(
        default_factory=list,
        description="Containerization tools (e.g. 'dockerfile', 'docker_compose')"
    )
    iac: List[str] = Field(
        default_factory=list,
        description="Infrastructure-as-Code tools (terraform, pulumi, etc)"
    )
    observability: List[str] = Field(
        default_factory=list,
        description="Observability tools (logging, metrics, tracing)"
    )
    docs: DocsInfo = Field(
        default_factory=DocsInfo,
        description="Documentation posture"
    )
    tests: TestsInfo = Field(
        default_factory=TestsInfo,
        description="Test posture"
    )


# ============================================================================
# RECOMMENDATIONS (FR-REV-04, FR-REP-03)
# ============================================================================


class FileReference(BaseModel):
    """Reference to a file, function, or symbol (FR-REV-05)"""
    file: str = Field(..., description="File path")
    line: Optional[int] = Field(None, ge=1, description="Line number (optional)")
    symbol: Optional[str] = Field(None, description="Function/class name (optional)")


class Evidence(BaseModel):
    """Explainability block for recommendations (FR-REP-03)"""
    metric: str = Field(..., description="Metric name (e.g. 'instability', 'complexity')")
    value: float = Field(..., description="Metric value")
    references: List[FileReference] = Field(
        ...,
        description="File/line/symbol references (verified against graph)"
    )


class Recommendation(BaseModel):
    """Single recommendation (FR-REV-04)"""
    id: str = Field(..., description="Unique recommendation ID (e.g. 'REC-001')")
    title: str = Field(..., description="Short title of recommendation")
    severity: Severity = Field(..., description="Severity level")
    category: RecommendationCategory = Field(..., description="Recommendation category")
    layer: Literal["L1", "L2", "L3", "L4"] = Field(
        ...,
        description="Layer that produced this recommendation"
    )
    evidence: Evidence = Field(..., description="Evidence for recommendation")
    rationale: str = Field(..., description="Explanation of why this matters")
    suggested_action: str = Field(..., description="Concrete action to take")
    line: Optional[int] = Field(None, description="Source line number, if applicable")
    verified: bool = Field(
        True,
        description="Whether all citations were verified against knowledge graph"
    )


# ============================================================================
# SECURITY FINDINGS
# ============================================================================


class SecurityFinding(BaseModel):
    """Security finding from gitleaks, pip-audit, npm-audit (FR-SEC)"""
    scanner: str = Field(..., description="Scanner name (e.g. 'gitleaks', 'pip-audit')")
    finding_type: str = Field(..., description="Type of finding")
    severity: Severity = Field(..., description="Severity level")
    description: str = Field(..., description="Finding description")
    file_references: List[FileReference] = Field(
        default_factory=list,
        description="Affected files/lines"
    )


# ============================================================================
# ROOT REPORT
# ============================================================================


class ArchitectureHealthScore(BaseModel):
    """Architecture Health Score (FR-REP-05)"""
    overall: float = Field(0.0, ge=0.0, le=100.0, description="Overall score")
    maintainability: float = Field(
        0.0,
        ge=0.0,
        le=100.0,
        description="Maintainability sub-score"
    )
    structure: float = Field(
        0.0,
        ge=0.0,
        le=100.0,
        description="Structure sub-score"
    )
    security: float = Field(
        0.0,
        ge=0.0,
        le=100.0,
        description="Security sub-score"
    )


class Report(BaseModel):
    """Arcnical analysis report root (FR-REP-01)"""
    schema_version: str = Field("2.0", description="Schema version")
    metadata: Metadata = Field(..., description="Report metadata")
    target_type: TargetClassification = Field(
        ...,
        description="Classified target type (from qualification)"
    )
    qualification: Qualification = Field(..., description="Target qualification result")
    summary: Summary = Field(..., description="Repository summary")
    layers: List[LayerResult] = Field(..., description="Per-layer results")
    scores: ArchitectureHealthScore = Field(
        ...,
        description="Architecture Health Score (FR-REP-05)"
    )
    metrics: Metrics = Field(..., description="Code metrics")
    practice_detection: PracticeDetection = Field(
        ...,
        description="Architecture & practice detection (FR-ARCH)"
    )
    recommendations: List[Recommendation] = Field(
        default_factory=list,
        description="Recommendations grouped by severity (descending)"
    )
    security_findings: List[SecurityFinding] = Field(
        default_factory=list,
        description="Security findings from cross-cutting security stage"
    )
    skipped_scanners: List[str] = Field(
        default_factory=list,
        description="Scanners skipped (e.g. 'gitleaks: not installed')"
    )
    unparsed_files: List[str] = Field(
        default_factory=list,
        description="Files that failed to parse"
    )
    feedback: Dict[str, Any] = Field(
        default_factory=dict,
        description="User feedback (thumbs up/down per recommendation)"
    )


# ============================================================================
# CONFIGURATION MODELS
# ============================================================================


class LayerConfig(BaseModel):
    """Layer configuration (from YAML files - FR-LAY-02)"""
    id: Literal["L1", "L2", "L3", "L4"]
    name: str
    description: str
    checks: List[str]
    blocking_conditions: List[str] = Field(
        default_factory=list,
        description="Conditions that cause pipeline halt (unless --force)"
    )
    enabled: bool = Field(True)


# ============================================================================
# VALIDATION
# ============================================================================


class SchemaValidator:
    """Helper to validate reports against schema"""

    @staticmethod
    def validate_report(data: Dict[str, Any]) -> Report:
        """Validate a report dict and return typed Report object"""
        return Report(**data)

    @staticmethod
    def validate_json(json_str: str) -> Report:
        """Validate a JSON string and return typed Report object"""
        import json
        data = json.loads(json_str)
        return Report(**data)


__all__ = [
    # Root
    "Report",
    # Enums
    "TargetClassification",
    "LayerStatus",
    "Severity",
    "RecommendationCategory",
    "AnalysisDepth",
    # Blocks
    "Metadata",
    "Qualification",
    "Summary",
    "LayerResult",
    "Metrics",
    "PracticeDetection",
    "Recommendation",
    "SecurityFinding",
    "ArchitectureHealthScore",
    # Config
    "LayerConfig",
    # Validator
    "SchemaValidator",
]
