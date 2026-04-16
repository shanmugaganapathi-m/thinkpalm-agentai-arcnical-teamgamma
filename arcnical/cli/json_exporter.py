# arcnical/cli/json_exporter.py
"""
JSON Export Module for Arcnical Analysis Results

This module handles exporting complete analysis reports to JSON format,
serving as the data bridge between CLI and Streamlit UI.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from arcnical.schema import Report, Recommendation, Evidence, FileReference, ArchitectureHealthScore


class AnalysisExporter:
    """Export analysis results to JSON format."""

    def __init__(self, output_dir: Optional[str] = None):
        """
        Initialize the exporter.
        
        Args:
            output_dir: Directory to save JSON files. Default: .arcnical/results/
        """
        if output_dir is None:
            output_dir = ".arcnical/results"
        
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export(
        self,
        report: Report,
        filename: str = "latest_analysis.json",
        per_file_loc: Optional[Dict[str, int]] = None,
        file_imports: Optional[Dict[str, list]] = None,
        repo_path: Optional[str] = None,
    ) -> Path:
        """
        Export a complete analysis report to JSON.

        Args:
            report: The Report object to export
            filename: Output filename (default: latest_analysis.json)
            per_file_loc: Optional {relative_path: loc} dict for graph nodes

        Returns:
            Path to the exported JSON file

        Raises:
            ValueError: If report is invalid
        """
        if not isinstance(report, Report):
            raise ValueError("report must be a Report instance")

        report_dict = self._report_to_dict(
            report,
            per_file_loc=per_file_loc or {},
            file_imports=file_imports or {},
            repo_path=repo_path or "",
        )

        output_path = self.output_dir / filename
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report_dict, f, indent=2, default=str)

        return output_path

    def _report_to_dict(
        self,
        report: Report,
        per_file_loc: Optional[Dict[str, int]] = None,
        file_imports: Optional[Dict[str, list]] = None,
        repo_path: str = "",
    ) -> Dict[str, Any]:
        """
        Convert Report object to dictionary.

        Args:
            report: Report object to convert
            per_file_loc: Optional {relative_path: loc} for graph node data

        Returns:
            Dictionary representation of the report
        """
        findings_list = [self._finding_to_dict(f) for f in report.recommendations]
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for f in report.recommendations:
            sev = (f.severity.value if hasattr(f.severity, "value") else str(f.severity)).lower()
            if sev in severity_counts:
                severity_counts[sev] += 1
        findings_summary = {**severity_counts, "total": sum(severity_counts.values())}

        model = report.metadata.model or ""
        if "claude" in model.lower():
            provider = "claude"
        elif "gpt" in model.lower() or "openai" in model.lower():
            provider = "openai"
        elif "gemini" in model.lower():
            provider = "gemini"
        else:
            provider = "—"

        depth = report.metadata.depth.value if hasattr(report.metadata.depth, "value") else str(report.metadata.depth)
        ts = report.metadata.generated_at.isoformat() if report.metadata.generated_at else ""

        return {
            "metadata": self._metadata_to_dict(report.metadata),
            "scores": self._scores_to_dict(report.scores),
            "file_structure": self._file_structure_to_dict(report.summary, per_file_loc or {}, file_imports or {}),
            "findings": findings_list,
            "findings_summary": findings_summary,
            "practice_detection": self._practice_detection_to_dict(report.practice_detection),
            "blocking_findings": [
                r.id for r in report.recommendations
                if r.severity.value in ("Critical", "High")
            ],
            "generated_at": ts,
            # Flat keys consumed directly by the Streamlit UI
            "repo_path": repo_path,
            "llm_model": model,
            "llm_provider": provider,
            "analysis_depth": depth,
            "analysis_timestamp": ts,
        }

    def _metadata_to_dict(self, metadata: Any) -> Dict[str, Any]:
        """Convert metadata to dictionary."""
        return {
            "tool_version": metadata.tool_version,
            "model": metadata.model,
            "prompt_version": metadata.prompt_version,
            "layer_config_version": metadata.layer_config_version,
            "graph_hash": metadata.graph_hash,
            "commit_sha": metadata.commit_sha,
            "generated_at": metadata.generated_at.isoformat() if metadata.generated_at else None,
            "depth": metadata.depth.value if hasattr(metadata.depth, 'value') else str(metadata.depth),
            "force_used": metadata.force_used,
            "token_usage": {
                "input_tokens": metadata.token_usage.input if metadata.token_usage else 0,
                "output_tokens": metadata.token_usage.output if metadata.token_usage else 0,
            }
        }

    def _scores_to_dict(self, scores: ArchitectureHealthScore) -> Dict[str, int]:
        """Convert health scores to dictionary."""
        return {
            "overall": scores.overall,
            "maintainability": scores.maintainability,
            "structure": scores.structure,
            "security": scores.security,
        }

    def _file_structure_to_dict(
        self,
        summary: Any,
        per_file_loc: Optional[Dict[str, int]] = None,
        file_imports: Optional[Dict[str, list]] = None,
    ) -> Dict[str, Any]:
        """
        Build file structure summary from report summary.

        ``files``   — {path: loc} dict for graph nodes.
        ``imports`` — {source_path: [target_path, ...]} for graph edges.
        """
        if summary is None:
            return {"total_files": 0, "files": {}, "imports": {}}

        return {
            "total_files": getattr(summary, "file_count", 0) or 0,
            "files": per_file_loc if per_file_loc else {},
            "imports": file_imports if file_imports else {},
        }

    def _finding_to_dict(self, finding: Recommendation) -> Dict[str, Any]:
        """
        Convert a finding/recommendation to dictionary.
        
        Args:
            finding: Recommendation object
            
        Returns:
            Dictionary representation of the finding
        """
        evidence_dict = {}
        if finding.evidence:
            evidence_dict = {
                "metric": finding.evidence.metric,
                "value": finding.evidence.value,
                "references": [
                    {
                        "file": ref.file,
                        "line": ref.line,
                        "symbol": ref.symbol,
                    }
                    for ref in finding.evidence.references
                ]
            }
        
        return {
            "id": finding.id,
            "title": finding.title,
            "severity": finding.severity.value if hasattr(finding.severity, 'value') else str(finding.severity),
            "category": finding.category.value if hasattr(finding.category, 'value') else str(finding.category),
            "layer": finding.layer,
            "evidence": evidence_dict,
            "rationale": finding.rationale,
            "suggested_action": finding.suggested_action,
            "verified": finding.verified,
            "line": finding.line,
        }

    def _practice_detection_to_dict(self, practice_detection: Any) -> Dict[str, Any]:
        """
        Convert practice detection results to dictionary.
        
        Args:
            practice_detection: PracticeDetection object
            
        Returns:
            Dictionary with practice detection info
        """
        if not practice_detection:
            return {}
        
        tests = getattr(practice_detection, "tests", None)
        docs = getattr(practice_detection, "docs", None)
        ci_cd = getattr(practice_detection, "ci_cd", []) or []

        return {
            "has_tests": {
                "detected": bool(
                    getattr(tests, "framework", None) or
                    getattr(tests, "ratio", 0) > 0
                ),
                "framework": getattr(tests, "framework", None),
                "ratio": getattr(tests, "ratio", 0),
            },
            "has_documentation": {
                "detected": bool(
                    getattr(docs, "readme", False) or
                    getattr(docs, "adr_dir", False)
                ),
                "readme": getattr(docs, "readme", False),
                "adr_dir": getattr(docs, "adr_dir", False),
            },
            "has_ci_cd": {
                "detected": len(ci_cd) > 0,
                "platforms": ci_cd,
            },
            "code_coverage": {
                "detected": False,
                "percentage": None,
            },
        }

    @staticmethod
    def load_json(filepath: str) -> Dict[str, Any]:
        """
        Load a JSON analysis file.
        
        Args:
            filepath: Path to JSON file
            
        Returns:
            Dictionary with analysis data
            
        Raises:
            FileNotFoundError: If file doesn't exist
            json.JSONDecodeError: If JSON is invalid
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)

    @staticmethod
    def get_latest_analysis() -> Optional[Dict[str, Any]]:
        """
        Get the latest analysis JSON file.
        
        Returns:
            Dictionary with analysis data, or None if no file exists
        """
        latest_path = Path(".arcnical/results/latest_analysis.json")
        
        if not latest_path.exists():
            return None
        
        try:
            return AnalysisExporter.load_json(str(latest_path))
        except (json.JSONDecodeError, IOError):
            return None
