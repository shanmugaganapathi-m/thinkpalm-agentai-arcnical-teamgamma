"""
Heuristics Evaluator - Orchestrates all L2, L3, and Security detectors

Runs all checks and aggregates findings in a single pass.
"""

from typing import List, Dict, Optional
import logging

from arcnical.schema import Recommendation, Severity
from arcnical.graph.builder import CodeKnowledgeGraph
from arcnical.heuristics.l2_detector import L2Detector, L2Finding
from arcnical.heuristics.l3_detector import L3Detector, L3Finding
from arcnical.heuristics.security_scanner import SecurityScanner, SecurityFinding


logger = logging.getLogger(__name__)


class HeuristicsEvaluator:
    """
    Evaluates all heuristics layers and aggregates findings.
    
    Runs L2 (structural), L3 (quality), and security checks,
    returning a unified findings report.
    """
    
    def __init__(self):
        """Initialize heuristics evaluator"""
        self.l2_detector = L2Detector()
        self.l3_detector = L3Detector()
        self.security_scanner = SecurityScanner()
    
    def run_all_heuristics(
        self,
        graph: CodeKnowledgeGraph,
        repo_path: str,
        layer_config: Optional[Dict] = None,
        enable_security: bool = True
    ) -> Dict[str, List]:
        """
        Run all heuristics checks on repository.
        
        Args:
            graph: Knowledge graph from parsing
            repo_path: Repository root path
            layer_config: Layer configuration (optional)
            enable_security: Whether to run security scans (default True)
            
        Returns:
            Dictionary with findings organized by layer:
            {
                "l2_findings": [L2Finding, ...],
                "l3_findings": [L3Finding, ...],
                "security_findings": [SecurityFinding, ...],
                "summary": {...}
            }
        """
        logger.info("Starting heuristics evaluation...")
        
        findings_dict = {
            "l2_findings": [],
            "l3_findings": [],
            "security_findings": [],
            "summary": {}
        }
        
        try:
            # L2: Structural Issues
            logger.info("Running L2 (structural) heuristics...")
            l2_findings = self.l2_detector.run_all_l2_checks(
                graph,
                repo_path,
                layer_config
            )
            findings_dict["l2_findings"] = l2_findings
            logger.info(f"  Found {len(l2_findings)} L2 issues")
        
        except Exception as e:
            logger.error(f"Error running L2 heuristics: {e}")
        
        try:
            # L3: Code Quality Issues
            logger.info("Running L3 (quality) heuristics...")
            l3_findings = self.l3_detector.run_all_l3_checks(
                graph,
                repo_path
            )
            findings_dict["l3_findings"] = l3_findings
            logger.info(f"  Found {len(l3_findings)} L3 issues")
        
        except Exception as e:
            logger.error(f"Error running L3 heuristics: {e}")
        
        if enable_security:
            try:
                # Security: Secrets and Vulnerabilities
                logger.info("Running security scans...")
                security_findings = self.security_scanner.scan_for_secrets(repo_path)
                findings_dict["security_findings"] = security_findings
                logger.info(f"  Found {len(security_findings)} security issues")
            
            except Exception as e:
                logger.error(f"Error running security scans: {e}")
        
        # Generate summary
        findings_dict["summary"] = self._generate_summary(findings_dict)
        
        logger.info("Heuristics evaluation complete")
        
        return findings_dict
    
    def convert_to_recommendations(
        self,
        findings_dict: Dict[str, List]
    ) -> List[Recommendation]:
        """
        Convert all findings to Recommendation objects for reporting.
        
        Args:
            findings_dict: Dictionary from run_all_heuristics()
            
        Returns:
            List of Recommendation objects
        """
        recommendations = []
        
        # L2 findings
        for finding in findings_dict.get("l2_findings", []):
            if isinstance(finding, L2Finding):
                recommendations.append(finding.to_recommendation())
        
        # L3 findings
        for finding in findings_dict.get("l3_findings", []):
            if isinstance(finding, L3Finding):
                recommendations.append(finding.to_recommendation())
        
        # Security findings (converted to Recommendation format)
        for finding in findings_dict.get("security_findings", []):
            if isinstance(finding, SecurityFinding):
                from arcnical.schema import RecommendationCategory
                rec = Recommendation(
                    id=finding.id,
                    title=finding.title,
                    severity=finding.severity,
                    category=RecommendationCategory.SECURITY,
                    layer="SECURITY",
                    evidence=f"{finding.finding_type}: {finding.description}",
                    rationale="Security vulnerability detected",
                    suggested_action="Review and remediate secret exposure. Rotate affected credentials."
                )
                recommendations.append(rec)
        
        return recommendations
    
    @staticmethod
    def _generate_summary(findings_dict: Dict[str, List]) -> Dict:
        """
        Generate summary statistics for all findings.
        
        Args:
            findings_dict: Dictionary with findings
            
        Returns:
            Summary dictionary
        """
        l2_findings = findings_dict.get("l2_findings", [])
        l3_findings = findings_dict.get("l3_findings", [])
        security_findings = findings_dict.get("security_findings", [])
        
        summary = {
            "total_findings": len(l2_findings) + len(l3_findings) + len(security_findings),
            "l2_count": len(l2_findings),
            "l3_count": len(l3_findings),
            "security_count": len(security_findings),
            "by_severity": {
                "CRITICAL": 0,
                "HIGH": 0,
                "MEDIUM": 0,
                "LOW": 0,
            },
            "blocking_findings": []
        }
        
        # Count by severity
        for finding in l2_findings + l3_findings + security_findings:
            severity = finding.severity.value.upper()
            if severity in summary["by_severity"]:
                summary["by_severity"][severity] += 1
            
            # Track blocking findings (L2 structural issues)
            if isinstance(finding, L2Finding) and finding.severity == Severity.HIGH:
                summary["blocking_findings"].append(finding.title)
        
        summary["has_blocking"] = len(summary["blocking_findings"]) > 0
        
        return summary


class FindingsFormatter:
    """Formats findings for display and reporting"""
    
    @staticmethod
    def format_findings_summary(summary: Dict) -> str:
        """
        Format findings summary for console output.
        
        Args:
            summary: Summary dictionary from HeuristicsEvaluator
            
        Returns:
            Formatted summary string
        """
        lines = []
        lines.append("=" * 70)
        lines.append("HEURISTICS FINDINGS SUMMARY")
        lines.append("=" * 70)
        lines.append("")
        lines.append(f"Total Findings: {summary['total_findings']}")
        lines.append(f"  L2 (Structural):  {summary['l2_count']}")
        lines.append(f"  L3 (Quality):     {summary['l3_count']}")
        lines.append(f"  Security:         {summary['security_count']}")
        lines.append("")
        lines.append("By Severity:")
        lines.append(f"  Critical: {summary['by_severity']['CRITICAL']}")
        lines.append(f"  High:     {summary['by_severity']['HIGH']}")
        lines.append(f"  Medium:   {summary['by_severity']['MEDIUM']}")
        lines.append(f"  Low:      {summary['by_severity']['LOW']}")
        lines.append("")
        
        if summary['has_blocking']:
            lines.append("⚠️  BLOCKING FINDINGS (must fix):")
            for finding in summary['blocking_findings'][:5]:  # Show first 5
                lines.append(f"  - {finding}")
            if len(summary['blocking_findings']) > 5:
                lines.append(f"  ... and {len(summary['blocking_findings']) - 5} more")
        
        lines.append("=" * 70)
        
        return "\n".join(lines)
    
    @staticmethod
    def format_finding_detail(finding) -> str:
        """
        Format a single finding for display.
        
        Args:
            finding: L2Finding, L3Finding, or SecurityFinding
            
        Returns:
            Formatted finding string
        """
        lines = []
        lines.append(f"ID: {finding.id}")
        lines.append(f"Title: {finding.title}")
        lines.append(f"Severity: {finding.severity.value}")
        
        if hasattr(finding, 'layer'):
            lines.append(f"Layer: {finding.layer}")
        
        if hasattr(finding, 'category'):
            lines.append(f"Category: {finding.category.value}")
        
        if hasattr(finding, 'finding_type'):
            lines.append(f"Type: {finding.finding_type}")
        
        if finding.evidence:
            lines.append("Evidence:")
            for key, value in finding.evidence.items():
                if isinstance(value, (list, dict)):
                    lines.append(f"  {key}: {str(value)[:50]}...")
                else:
                    lines.append(f"  {key}: {value}")
        
        return "\n".join(lines)
