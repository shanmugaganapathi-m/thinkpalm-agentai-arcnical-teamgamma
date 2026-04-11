"""
L2 Heuristics Detector - Structural Issues

Detects:
- Circular imports (cycles in dependency graph)
- God classes (>300 LOC or >20 methods)
- Layer violations (cross-layer dependencies)
"""

from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass

from arcnical.schema import (
    Recommendation, Severity, RecommendationCategory,
    Evidence, FileReference
)
from arcnical.graph.builder import CodeKnowledgeGraph
from arcnical.parse.parser import SymbolType
from arcnical.metrics.calculator import LOCCalculator


@dataclass
class L2Finding:
    """L2 Finding representation"""
    id: str
    title: str
    severity: Severity
    evidence_data: Dict  # Raw data for evidence
    category: RecommendationCategory
    layer: str = "L2"
    
    def to_recommendation(self) -> Recommendation:
        """Convert to schema Recommendation"""
        # Build Evidence object from raw data
        evidence = self._build_evidence()
        
        return Recommendation(
            id=self.id,
            title=self.title,
            severity=self.severity,
            category=self.category,
            layer=self.layer,
            evidence=evidence,
            rationale=f"Architectural issue detected at layer {self.layer}",
            suggested_action=self._get_suggested_action(),
        )
    
    def _build_evidence(self) -> Evidence:
        """Build Evidence object from evidence_data"""
        # Determine metric name based on finding type
        if "cycle" in self.evidence_data:
            metric = "circular_imports"
            value = float(self.evidence_data.get("cycle_length", 0))
        elif "loc" in self.evidence_data:
            metric = "god_class_loc"
            value = float(self.evidence_data.get("loc", 0))
        else:
            metric = "structural_issue"
            value = 1.0
        
        # Build file references from evidence
        references = []
        
        if "file" in self.evidence_data:
            references.append(FileReference(
                file=self.evidence_data["file"],
                line=self.evidence_data.get("lineno", 1),
                symbol=self.evidence_data.get("qualified_name", "")
            ))
        
        return Evidence(
            metric=metric,
            value=value,
            references=references
        )
    
    def _get_suggested_action(self) -> str:
        """Get suggested action based on finding type"""
        if "Circular" in self.title:
            return "Refactor to break circular dependency. Consider extracting common code to new module."
        elif "God class" in self.title:
            return "Split class into smaller, focused classes. Consider Single Responsibility Principle."
        elif "Layer violation" in self.title:
            return "Move code to correct layer or create intermediate layer for shared concerns."
        return "Review and refactor affected code."


class L2Detector:
    """Detects Layer 2 (Structural) issues"""
    
    def __init__(self):
        """Initialize L2 detector"""
        self.loc_calculator = LOCCalculator()
    
    def detect_circular_imports(
        self, 
        graph: CodeKnowledgeGraph
    ) -> List[L2Finding]:
        """
        Detect circular import dependencies.
        
        Args:
            graph: Knowledge graph with import edges
            
        Returns:
            List of circular import findings
        """
        findings = []
        cycles = graph.detect_cycles()
        
        for i, cycle in enumerate(cycles):
            # Format cycle as A → B → C → A
            cycle_str = " → ".join(cycle + [cycle[0]])
            
            finding = L2Finding(
                id=f"L2-CIRCULAR-{i+1:03d}",
                title=f"Circular import dependency: {cycle_str}",
                severity=Severity.HIGH,
                evidence_data={
                    "cycle": cycle,
                    "cycle_length": len(cycle),
                    "modules": cycle,
                    "metric": "circular_imports"
                },
                category=RecommendationCategory.ARCHITECTURE
            )
            findings.append(finding)
        
        return findings
    
    def detect_god_classes(
        self,
        graph: CodeKnowledgeGraph,
        repo_path: str,
        loc_threshold: int = 300,
        method_threshold: int = 20
    ) -> List[L2Finding]:
        """
        Detect God Classes (classes doing too much).
        
        Criteria:
        - >300 lines of code, OR
        - >20 methods
        
        Args:
            graph: Knowledge graph with class symbols
            repo_path: Root repository path
            loc_threshold: Lines of code threshold (default 300)
            method_threshold: Method count threshold (default 20)
            
        Returns:
            List of god class findings
        """
        findings = []
        classes = graph.get_all_symbols_of_type(SymbolType.CLASS)
        
        for class_symbol in classes:
            # Count LOC
            loc = self.loc_calculator.count_function_loc(
                class_symbol.file,
                class_symbol.lineno,
                class_symbol.end_lineno or class_symbol.lineno
            )
            
            # Count methods (children in graph)
            methods = [
                s for s in graph.symbols.values()
                if s.type == SymbolType.METHOD 
                and s.parent_qualified_name == class_symbol.qualified_name
            ]
            method_count = len(methods)
            
            # Check thresholds
            reasons = []
            if loc > loc_threshold:
                reasons.append(f"{loc} LOC (>{loc_threshold})")
            if method_count > method_threshold:
                reasons.append(f"{method_count} methods (>{method_threshold})")
            
            if reasons:
                finding = L2Finding(
                    id=f"L2-GODCLASS-{len(findings)+1:03d}",
                    title=f"God class: {class_symbol.name} ({', '.join(reasons)})",
                    severity=Severity.MEDIUM,
                    evidence_data={
                        "class_name": class_symbol.name,
                        "qualified_name": class_symbol.qualified_name,
                        "file": class_symbol.file,
                        "lineno": class_symbol.lineno,
                        "loc": loc,
                        "method_count": method_count,
                        "reasons": reasons,
                        "metric": "god_class"
                    },
                    category=RecommendationCategory.CODE_HEALTH
                )
                findings.append(finding)
        
        return findings
    
    def detect_layer_violations(
        self,
        graph: CodeKnowledgeGraph,
        layer_config: Optional[Dict] = None
    ) -> List[L2Finding]:
        """
        Detect layer boundary violations.
        
        Checks that dependencies respect layer structure:
        - L1 (Interface) can depend on L2 (Structure)
        - L2 can depend on L3 (Implementation)
        - No backwards dependencies allowed
        
        Args:
            graph: Knowledge graph
            layer_config: Layer configuration (optional for future use)
            
        Returns:
            List of layer violation findings
        """
        findings = []
        
        # For now, placeholder implementation
        # Will be enhanced when layer configuration is fully defined
        # This would check module paths/names against layer rules
        
        # Example logic (commented):
        # for node in graph.graph.nodes():
        #     for dependency in graph.get_dependencies(node):
        #         if is_layer_violation(node, dependency, layer_config):
        #             findings.append(...)
        
        return findings
    
    def run_all_l2_checks(
        self,
        graph: CodeKnowledgeGraph,
        repo_path: str,
        layer_config: Optional[Dict] = None
    ) -> List[L2Finding]:
        """
        Run all L2 heuristics checks.
        
        Args:
            graph: Knowledge graph
            repo_path: Repository root path
            layer_config: Layer configuration
            
        Returns:
            Combined list of all L2 findings
        """
        findings = []
        
        # Check circular imports
        findings.extend(self.detect_circular_imports(graph))
        
        # Check god classes
        findings.extend(self.detect_god_classes(graph, repo_path))
        
        # Check layer violations
        findings.extend(self.detect_layer_violations(graph, layer_config))
        
        return findings
