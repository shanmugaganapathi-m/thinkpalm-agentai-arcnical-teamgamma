"""
Security Scanner - Secrets and Vulnerabilities Detection

Integrates gitleaks for finding hardcoded secrets, API keys, credentials, etc.
Gracefully handles cases where gitleaks is not installed.
"""

import subprocess
import json
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass

from arcnical.schema import Severity


logger = logging.getLogger(__name__)


@dataclass
class SecurityFinding:
    """Security finding representation"""
    id: str
    title: str
    severity: Severity
    finding_type: str
    description: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    evidence: Dict = None
    
    def __post_init__(self):
        """Initialize evidence dict if None"""
        if self.evidence is None:
            self.evidence = {}


class SecurityScanner:
    """Scans for security issues and secrets"""
    
    def __init__(self, enable_gitleaks: bool = True):
        """
        Initialize security scanner.
        
        Args:
            enable_gitleaks: Whether to enable gitleaks scanning (default True)
        """
        self.enable_gitleaks = enable_gitleaks
        self.gitleaks_available = self._check_gitleaks_available()
    
    @staticmethod
    def _check_gitleaks_available() -> bool:
        """
        Check if gitleaks is installed and available.
        
        Returns:
            True if gitleaks is available, False otherwise
        """
        try:
            result = subprocess.run(
                ["gitleaks", "--version"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def scan_for_secrets(
        self,
        repo_path: str,
        verbose: bool = False
    ) -> List[SecurityFinding]:
        """
        Scan repository for hardcoded secrets using gitleaks.
        
        Detects:
        - API keys and tokens
        - AWS credentials
        - Private keys
        - Passwords
        - Database credentials
        - etc.
        
        Args:
            repo_path: Path to repository to scan
            verbose: Enable verbose output (default False)
            
        Returns:
            List of security findings (empty if gitleaks not available)
        """
        findings = []
        
        if not self.enable_gitleaks:
            logger.debug("gitleaks scanning disabled")
            return findings
        
        if not self.gitleaks_available:
            logger.warning(
                "gitleaks not installed or not available. "
                "Secrets scanning skipped. "
                "Install with: pip install gitleaks or https://github.com/gitleaks/gitleaks"
            )
            return findings
        
        try:
            # Run gitleaks in JSON mode
            cmd = [
                "gitleaks",
                "detect",
                "--source", repo_path,
                "--json",
                "--no-color"
            ]
            
            if verbose:
                cmd.append("--verbose")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=60,
                text=True
            )
            
            # gitleaks returns exit code 1 if secrets found, 0 if none
            if result.returncode in (0, 1):
                if result.stdout:
                    try:
                        gitleaks_findings = json.loads(result.stdout)
                        
                        # Process each finding
                        for i, finding_data in enumerate(gitleaks_findings):
                            finding = self._parse_gitleaks_finding(finding_data, i + 1)
                            if finding:
                                findings.append(finding)
                    except json.JSONDecodeError:
                        logger.warning("Failed to parse gitleaks JSON output")
            else:
                logger.warning(f"gitleaks scan failed with code {result.returncode}")
        
        except subprocess.TimeoutExpired:
            logger.warning("gitleaks scan timed out after 60 seconds")
        except Exception as e:
            logger.warning(f"Error running gitleaks: {e}")
        
        return findings
    
    @staticmethod
    def _parse_gitleaks_finding(finding_data: Dict, index: int) -> Optional[SecurityFinding]:
        """
        Parse gitleaks JSON finding into SecurityFinding.
        
        Args:
            finding_data: Raw gitleaks finding dictionary
            index: Finding index (for ID generation)
            
        Returns:
            SecurityFinding object or None if parsing fails
        """
        try:
            # Extract key information from gitleaks output
            rule_id = finding_data.get("RuleID", "UNKNOWN")
            rule_description = finding_data.get("Description", "Secret detected")
            file_path = finding_data.get("File", "")
            line_number = finding_data.get("StartLine", 0)
            secret_match = finding_data.get("Match", "")
            
            # Determine severity based on secret type
            severity = SecurityScanner._determine_severity(rule_id)
            
            finding = SecurityFinding(
                id=f"SEC-{index:03d}",
                title=f"Secret detected: {rule_description}",
                severity=severity,
                finding_type=rule_id,
                description=f"Potential {rule_description.lower()} found in source code",
                file_path=file_path,
                line_number=line_number,
                evidence={
                    "rule_id": rule_id,
                    "file": file_path,
                    "line": line_number,
                    "secret_type": rule_description,
                    "match_length": len(secret_match) if secret_match else 0
                }
            )
            
            return finding
        
        except Exception as e:
            logger.warning(f"Failed to parse gitleaks finding: {e}")
            return None
    
    @staticmethod
    def _determine_severity(rule_id: str) -> Severity:
        """
        Determine severity based on secret type.
        
        Args:
            rule_id: gitleaks rule ID (e.g., "AWS Manager ID")
            
        Returns:
            Severity level
        """
        rule_upper = rule_id.upper()
        
        # Critical severity for high-impact secrets
        if any(kw in rule_upper for kw in ["AWS", "PRIVATE KEY", "CRYPTO", "GITHUB", "GITLAB"]):
            return Severity.CRITICAL
        
        # High severity for credentials
        if any(kw in rule_upper for kw in ["PASSWORD", "API KEY", "TOKEN", "DATABASE"]):
            return Severity.HIGH
        
        # Medium for generic secrets
        return Severity.MEDIUM
    
    def scan_repository(
        self,
        repo_path: str
    ) -> Dict[str, List[SecurityFinding]]:
        """
        Run comprehensive security scan on repository.
        
        Args:
            repo_path: Path to repository
            
        Returns:
            Dictionary with security findings organized by type
        """
        findings_dict = {
            "secrets": [],
            "summary": {}
        }
        
        # Scan for secrets
        secret_findings = self.scan_for_secrets(repo_path)
        findings_dict["secrets"] = secret_findings
        
        # Generate summary
        findings_dict["summary"] = {
            "total_findings": len(secret_findings),
            "critical": len([f for f in secret_findings if f.severity == Severity.CRITICAL]),
            "high": len([f for f in secret_findings if f.severity == Severity.HIGH]),
            "medium": len([f for f in secret_findings if f.severity == Severity.MEDIUM]),
            "low": len([f for f in secret_findings if f.severity == Severity.LOW]),
        }
        
        return findings_dict


class SecurityEvaluator:
    """Evaluates and formats security findings"""
    
    @staticmethod
    def format_findings(findings: List[SecurityFinding]) -> List[Dict]:
        """
        Format security findings for reporting.
        
        Args:
            findings: List of security findings
            
        Returns:
            Formatted findings list
        """
        formatted = []
        
        for finding in findings:
            formatted.append({
                "id": finding.id,
                "title": finding.title,
                "severity": finding.severity.value,
                "type": finding.finding_type,
                "file": finding.file_path,
                "line": finding.line_number,
                "description": finding.description,
                "evidence": finding.evidence
            })
        
        return formatted
    
    @staticmethod
    def summarize_findings(findings: List[SecurityFinding]) -> Dict:
        """
        Create summary of security findings.
        
        Args:
            findings: List of findings
            
        Returns:
            Summary dictionary
        """
        return {
            "total": len(findings),
            "critical": len([f for f in findings if f.severity == Severity.CRITICAL]),
            "high": len([f for f in findings if f.severity == Severity.HIGH]),
            "medium": len([f for f in findings if f.severity == Severity.MEDIUM]),
            "low": len([f for f in findings if f.severity == Severity.LOW]),
            "has_critical": any(f.severity == Severity.CRITICAL for f in findings),
            "has_high": any(f.severity == Severity.HIGH for f in findings),
        }
