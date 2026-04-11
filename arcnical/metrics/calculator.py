"""
Metrics Calculator for code quality analysis.

Computes:
- Cyclomatic complexity
- Fan-in / fan-out (coupling metrics)
- Instability
- Lines of code
- God classes detection
"""

import os
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path
from collections import defaultdict

try:
    from radon.complexity import cc_visit
    from radon.metrics import mi_visit, RADON_AVAILABLE
    RADON_AVAILABLE = True
except ImportError:
    RADON_AVAILABLE = False

from arcnical.graph.builder import CodeKnowledgeGraph
from arcnical.parse.parser import SymbolType


class ComplexityCalculator:
    """Calculate cyclomatic complexity for functions and files."""
    
    def __init__(self):
        """Initialize complexity calculator."""
        if not RADON_AVAILABLE:
            raise ImportError(
                "radon not installed. Run: pip install radon"
            )
    
    def calculate_function_complexity(self, filepath: str, function_name: str) -> float:
        """
        Calculate cyclomatic complexity for a specific function.
        
        Args:
            filepath: Path to Python file
            function_name: Name of the function
            
        Returns:
            Cyclomatic complexity score
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Get all function complexities
            results = cc_visit(content, min='A')  # Get all functions
            
            # Find matching function
            for result in results:
                if result.name == function_name:
                    return result.complexity
            
            return 0.0
        except Exception:
            return 0.0
    
    def calculate_file_complexity(self, filepath: str) -> Tuple[float, float, float]:
        """
        Calculate average and max complexity for a file.
        
        Returns:
            Tuple of (avg_complexity, max_complexity, total_complexity)
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            results = cc_visit(content, min='A')
            
            if not results:
                return 0.0, 0.0, 0.0
            
            complexities = [r.complexity for r in results]
            avg_complexity = sum(complexities) / len(complexities)
            max_complexity = max(complexities)
            total_complexity = sum(complexities)
            
            return avg_complexity, max_complexity, total_complexity
        except Exception:
            return 0.0, 0.0, 0.0


class CouplingCalculator:
    """Calculate coupling metrics from knowledge graph."""
    
    @staticmethod
    def calculate_fan_in_fan_out(
        graph: CodeKnowledgeGraph
    ) -> Dict[str, Tuple[int, int]]:
        """
        Calculate fan-in and fan-out for all nodes.
        
        Returns:
            Dict mapping node ID to (fan_in, fan_out) tuple
        """
        results = {}
        for node in graph.graph.nodes():
            results[node] = (graph.fan_in(node), graph.fan_out(node))
        return results
    
    @staticmethod
    def calculate_instability(
        graph: CodeKnowledgeGraph
    ) -> Dict[str, float]:
        """
        Calculate instability metric for all nodes.
        
        Returns:
            Dict mapping node ID to instability score (0.0 to 1.0)
        """
        results = {}
        for node in graph.graph.nodes():
            results[node] = graph.instability(node)
        return results


class LOCCalculator:
    """Calculate lines of code metrics."""
    
    @staticmethod
    def count_file_loc(filepath: str) -> int:
        """Count lines of code in a file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Remove blank lines and comments for actual LOC count
            loc = 0
            for line in lines:
                stripped = line.strip()
                if stripped and not stripped.startswith('#'):
                    loc += 1
            return loc
        except Exception:
            return 0
    
    @staticmethod
    def count_function_loc(filepath: str, start_line: int, end_line: int) -> int:
        """Count lines of code in a function."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Lines are 1-indexed in metadata, 0-indexed in array
            loc = 0
            for i in range(start_line - 1, min(end_line, len(lines))):
                stripped = lines[i].strip()
                if stripped and not stripped.startswith('#'):
                    loc += 1
            return loc
        except Exception:
            return 0


class GodClassDetector:
    """Detect God Classes (classes that do too much)."""
    
    # Thresholds
    MAX_LOC_PER_CLASS = 300
    MAX_METHODS_PER_CLASS = 20
    
    @staticmethod
    def is_god_class(
        filepath: str,
        class_start: int,
        class_end: int,
        method_count: int
    ) -> Tuple[bool, str]:
        """
        Determine if a class is a God Class.
        
        Returns:
            Tuple of (is_god_class, reason)
        """
        loc = LOCCalculator.count_function_loc(filepath, class_start, class_end)
        
        reasons = []
        if loc > GodClassDetector.MAX_LOC_PER_CLASS:
            reasons.append(f"LOC: {loc} > {GodClassDetector.MAX_LOC_PER_CLASS}")
        if method_count > GodClassDetector.MAX_METHODS_PER_CLASS:
            reasons.append(f"Methods: {method_count} > {GodClassDetector.MAX_METHODS_PER_CLASS}")
        
        return len(reasons) > 0, "; ".join(reasons)


class MetricsAggregator:
    """Aggregate all metrics for a repository."""
    
    def __init__(self):
        """Initialize metrics aggregator."""
        self.complexity_calc = ComplexityCalculator()
        self.coupling_calc = CouplingCalculator()
        self.loc_calc = LOCCalculator()
    
    def compute_all_metrics(
        self,
        repo_path: str,
        graph: CodeKnowledgeGraph
    ) -> Dict[str, Any]:
        """
        Compute all metrics for the repository.
        
        Args:
            repo_path: Root path of repository
            graph: Knowledge graph with symbols and relationships
            
        Returns:
            Dictionary with all computed metrics
        """
        metrics = {
            'complexity_metrics': self._compute_complexity_metrics(repo_path),
            'coupling_metrics': self._compute_coupling_metrics(graph),
            'code_quality': self._compute_code_quality(repo_path, graph),
            'graph_summary': graph.summary(),
        }
        
        return metrics
    
    def _compute_complexity_metrics(self, repo_path: str) -> Dict[str, Any]:
        """Compute complexity metrics for all Python files."""
        complexities = []
        
        for root, dirs, files in os.walk(repo_path):
            # Skip common non-source directories
            dirs[:] = [d for d in dirs if d not in (
                '__pycache__', '.git', '.venv', 'venv', 'node_modules', 'dist', 'build'
            )]
            
            for file in files:
                if file.endswith('.py'):
                    filepath = os.path.join(root, file)
                    try:
                        avg, max_c, total = self.complexity_calc.calculate_file_complexity(filepath)
                        if avg > 0:
                            complexities.append({
                                'file': filepath,
                                'avg': avg,
                                'max': max_c,
                                'total': total,
                            })
                    except Exception:
                        pass
        
        if not complexities:
            return {
                'complexity_avg': 0.0,
                'complexity_p95': 0.0,
                'complexity_max': 0.0,
                'files_analyzed': 0,
            }
        
        # Calculate percentiles
        sorted_avg = sorted([c['avg'] for c in complexities])
        sorted_max = sorted([c['max'] for c in complexities])
        
        p95_idx = int(len(sorted_avg) * 0.95)
        
        return {
            'complexity_avg': sum(c['avg'] for c in complexities) / len(complexities),
            'complexity_max': max(c['max'] for c in complexities),
            'complexity_p95': sorted_avg[p95_idx] if sorted_avg else 0.0,
            'files_analyzed': len(complexities),
            'files_with_high_complexity': len([
                c for c in complexities
                if c['avg'] > 10  # Arbitrary threshold
            ]),
        }
    
    def _compute_coupling_metrics(self, graph: CodeKnowledgeGraph) -> Dict[str, Any]:
        """Compute coupling metrics from graph."""
        fan_in_out = self.coupling_calc.calculate_fan_in_fan_out(graph)
        instability = self.coupling_calc.calculate_instability(graph)
        
        if not fan_in_out:
            return {
                'avg_fan_in': 0.0,
                'avg_fan_out': 0.0,
                'avg_instability': 0.0,
                'modules_analyzed': 0,
            }
        
        fan_ins = [v[0] for v in fan_in_out.values()]
        fan_outs = [v[1] for v in fan_in_out.values()]
        instabilities = list(instability.values())
        
        return {
            'avg_fan_in': sum(fan_ins) / len(fan_ins),
            'avg_fan_out': sum(fan_outs) / len(fan_outs),
            'max_fan_in': max(fan_ins),
            'max_fan_out': max(fan_outs),
            'avg_instability': sum(instabilities) / len(instabilities),
            'unstable_modules': len([i for i in instabilities if i > 0.8]),
            'modules_analyzed': len(fan_in_out),
        }
    
    def _compute_code_quality(self, repo_path: str, graph: CodeKnowledgeGraph) -> Dict[str, Any]:
        """Compute overall code quality metrics."""
        # Count classes and detect god classes
        classes = graph.get_all_symbols_of_type(SymbolType.CLASS)
        god_classes = 0
        
        for cls in classes:
            filepath = cls.file
            start = cls.lineno
            end = cls.end_lineno or start
            
            # Count methods in class (approximation: look at children in graph)
            method_count = len([
                s for s in classes
                if s.parent_qualified_name == cls.qualified_name
            ])
            
            is_god, _ = GodClassDetector.is_god_class(filepath, start, end, method_count)
            if is_god:
                god_classes += 1
        
        # Count circular dependencies
        circular_deps = graph.get_cycle_count()
        
        return {
            'total_classes': len(classes),
            'god_class_count': god_classes,
            'circular_dependency_count': circular_deps,
            'functions': len(graph.get_all_symbols_of_type(SymbolType.FUNCTION)),
            'methods': len(graph.get_all_symbols_of_type(SymbolType.METHOD)),
        }
