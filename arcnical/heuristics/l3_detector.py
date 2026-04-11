"""
L3 Heuristics Detector - Code Quality Issues

Detects:
- High cyclomatic complexity (>15)
- Large files (>600 LOC)
- Unstable modules (instability >0.8)
- High fan-out (>10 dependencies)
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
import os

from arcnical.schema import Recommendation, Severity, RecommendationCategory
from arcnical.graph.builder import CodeKnowledgeGraph
from arcnical.metrics.calculator import ComplexityCalculator, CouplingCalculator, LOCCalculator
from arcnical.parse.parser import SymbolType


@dataclass
class L3Finding:
    """L3 Finding representation"""
    id: str
    title: str
    severity: Severity
    evidence: Dict
    category: RecommendationCategory
    layer: str = "L3"
    
    def to_recommendation(self) -> Recommendation:
        """Convert to schema Recommendation"""
        return Recommendation(
            id=self.id,
            title=self.title,
            severity=self.severity,
            category=self.category,
            layer=self.layer,
            evidence=str(self.evidence),
            rationale=f"Code quality issue detected at layer {self.layer}",
            suggested_action=self._get_suggested_action(),
        )
    
    def _get_suggested_action(self) -> str:
        """Get suggested action based on finding type"""
        if "complexity" in self.title.lower():
            return "Refactor to reduce cyclomatic complexity. Break into smaller functions."
        elif "large file" in self.title.lower():
            return "Split file into multiple smaller modules with focused responsibilities."
        elif "unstable" in self.title.lower():
            return "Reduce outgoing dependencies. Extract interfaces to decouple."
        elif "high fan-out" in self.title.lower():
            return "Reduce number of dependencies. Apply dependency injection or facade pattern."
        return "Review and refactor code quality."


class L3Detector:
    """Detects Layer 3 (Code Quality) issues"""
    
    # Thresholds
    COMPLEXITY_THRESHOLD = 15
    LOC_THRESHOLD = 600
    INSTABILITY_THRESHOLD = 0.8
    FAN_OUT_THRESHOLD = 10
    
    def __init__(self):
        """Initialize L3 detector"""
        self.complexity_calc = ComplexityCalculator()
        self.coupling_calc = CouplingCalculator()
        self.loc_calc = LOCCalculator()
    
    def detect_high_complexity(
        self,
        repo_path: str
    ) -> List[L3Finding]:
        """
        Detect functions with high cyclomatic complexity.
        
        Threshold: Complexity > 15
        
        Args:
            repo_path: Repository root path
            
        Returns:
            List of high complexity findings
        """
        findings = []
        finding_count = 0
        
        # Walk through Python files
        for root, dirs, files in os.walk(repo_path):
            # Skip non-source directories
            dirs[:] = [d for d in dirs if d not in (
                '__pycache__', '.git', '.venv', 'venv', 'node_modules', 'dist', 'build', '.pytest_cache'
            )]
            
            for file in files:
                if file.endswith('.py'):
                    filepath = os.path.join(root, file)
                    
                    try:
                        avg_complexity, max_complexity, total = self.complexity_calc.calculate_file_complexity(filepath)
                        
                        # Report max complexity per file if exceeds threshold
                        if max_complexity > self.COMPLEXITY_THRESHOLD:
                            finding_count += 1
                            finding = L3Finding(
                                id=f"L3-COMPLEXITY-{finding_count:03d}",
                                title=f"High complexity in {os.path.basename(filepath)}: {max_complexity}",
                                severity=Severity.MEDIUM if max_complexity < 20 else Severity.HIGH,
                                evidence={
                                    "file": filepath,
                                    "max_complexity": max_complexity,
                                    "avg_complexity": round(avg_complexity, 2),
                                    "threshold": self.COMPLEXITY_THRESHOLD
                                },
                                category=RecommendationCategory.REFACTORING
                            )
                            findings.append(finding)
                    except Exception:
                        # Gracefully handle parsing errors
                        pass
        
        return findings
    
    def detect_large_files(
        self,
        repo_path: str
    ) -> List[L3Finding]:
        """
        Detect files with too many lines of code.
        
        Threshold: LOC > 600
        
        Args:
            repo_path: Repository root path
            
        Returns:
            List of large file findings
        """
        findings = []
        finding_count = 0
        
        # Walk through Python files
        for root, dirs, files in os.walk(repo_path):
            # Skip non-source directories
            dirs[:] = [d for d in dirs if d not in (
                '__pycache__', '.git', '.venv', 'venv', 'node_modules', 'dist', 'build', '.pytest_cache'
            )]
            
            for file in files:
                if file.endswith('.py'):
                    filepath = os.path.join(root, file)
                    
                    try:
                        loc = self.loc_calc.count_file_loc(filepath)
                        
                        if loc > self.LOC_THRESHOLD:
                            finding_count += 1
                            finding = L3Finding(
                                id=f"L3-LARGEFILE-{finding_count:03d}",
                                title=f"Large file: {os.path.basename(filepath)} ({loc} LOC)",
                                severity=Severity.LOW,
                                evidence={
                                    "file": filepath,
                                    "loc": loc,
                                    "threshold": self.LOC_THRESHOLD
                                },
                                category=RecommendationCategory.STRUCTURE
                            )
                            findings.append(finding)
                    except Exception:
                        pass
        
        return findings
    
    def detect_unstable_modules(
        self,
        graph: CodeKnowledgeGraph
    ) -> List[L3Finding]:
        """
        Detect modules with high instability.
        
        Instability = Ce / (Ca + Ce)
        - Ce = efferent coupling (outgoing dependencies)
        - Ca = afferent coupling (incoming dependencies)
        
        Threshold: I > 0.8 (unstable - mostly outgoing, few incoming)
        
        Args:
            graph: Knowledge graph
            
        Returns:
            List of unstable module findings
        """
        findings = []
        finding_count = 0
        
        # Calculate instability for all nodes
        instability_values = self.coupling_calc.calculate_instability(graph)
        
        for module, instability in instability_values.items():
            if instability > self.INSTABILITY_THRESHOLD:
                finding_count += 1
                fan_in = graph.fan_in(module)
                fan_out = graph.fan_out(module)
                
                finding = L3Finding(
                    id=f"L3-UNSTABLE-{finding_count:03d}",
                    title=f"Unstable module: {module} (I={instability:.2f})",
                    severity=Severity.LOW,
                    evidence={
                        "module": module,
                        "instability": round(instability, 2),
                        "fan_in": fan_in,
                        "fan_out": fan_out,
                        "threshold": self.INSTABILITY_THRESHOLD
                    },
                    category=RecommendationCategory.COUPLING
                )
                findings.append(finding)
        
        return findings
    
    def detect_high_fan_out(
        self,
        graph: CodeKnowledgeGraph
    ) -> List[L3Finding]:
        """
        Detect modules with too many outgoing dependencies.
        
        Threshold: Fan-out > 10
        
        Args:
            graph: Knowledge graph
            
        Returns:
            List of high fan-out findings
        """
        findings = []
        finding_count = 0
        
        for node in graph.graph.nodes():
            fan_out = graph.fan_out(node)
            
            if fan_out > self.FAN_OUT_THRESHOLD:
                finding_count += 1
                dependencies = graph.get_dependencies(node)
                
                finding = L3Finding(
                    id=f"L3-FANOUT-{finding_count:03d}",
                    title=f"High fan-out: {node} ({fan_out} dependencies)",
                    severity=Severity.LOW,
                    evidence={
                        "module": node,
                        "fan_out": fan_out,
                        "dependencies": dependencies[:5],  # Show first 5
                        "threshold": self.FAN_OUT_THRESHOLD
                    },
                    category=RecommendationCategory.COUPLING
                )
                findings.append(finding)
        
        return findings
    
    def run_all_l3_checks(
        self,
        graph: CodeKnowledgeGraph,
        repo_path: str
    ) -> List[L3Finding]:
        """
        Run all L3 heuristics checks.
        
        Args:
            graph: Knowledge graph
            repo_path: Repository root path
            
        Returns:
            Combined list of all L3 findings
        """
        findings = []
        
        # Check complexity
        findings.extend(self.detect_high_complexity(repo_path))
        
        # Check file size
        findings.extend(self.detect_large_files(repo_path))
        
        # Check instability
        findings.extend(self.detect_unstable_modules(graph))
        
        # Check fan-out
        findings.extend(self.detect_high_fan_out(graph))
        
        return findings
