#!/usr/bin/env python
"""Check Evidence structure"""

from arcnical.heuristics.l2_detector import L2Detector
from arcnical.graph.builder import CodeKnowledgeGraph
from arcnical.parse.parser import Import

try:
    detector = L2Detector()
    graph = CodeKnowledgeGraph()
    graph.add_import_edge(Import(source_file='a.py', source_module='a', target_module='b'))
    graph.add_import_edge(Import(source_file='b.py', source_module='b', target_module='a'))
    findings = detector.detect_circular_imports(graph)
    
    if findings:
        rec = findings[0].to_recommendation()
        evidence = rec.evidence
        
        print(f'[OK] Recommendation ID: {rec.id}')
        print(f'[OK] Evidence type: {type(evidence).__name__}')
        
        has_metric = hasattr(evidence, 'metric')
        has_value = hasattr(evidence, 'value')
        has_references = hasattr(evidence, 'references')
        
        print(f'[OK] Has metric: {has_metric}')
        print(f'[OK] Has value: {has_value}')
        print(f'[OK] Has references: {has_references}')
        
        if has_metric and has_value and has_references:
            print('[OK] Evidence structure PASSED')
        else:
            print('[FAIL] Evidence structure FAILED - missing fields')
    else:
        print('[FAIL] No findings found')
        
except Exception as e:
    print(f'[FAIL] Evidence check failed: {e}')
