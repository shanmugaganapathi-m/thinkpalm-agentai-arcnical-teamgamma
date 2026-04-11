#!/usr/bin/env python
"""Check L2Detector functionality"""

from arcnical.heuristics.l2_detector import L2Detector
from arcnical.graph.builder import CodeKnowledgeGraph
from arcnical.parse.parser import Import

try:
    detector = L2Detector()
    graph = CodeKnowledgeGraph()
    graph.add_import_edge(Import(source_file='a.py', source_module='a', target_module='b'))
    graph.add_import_edge(Import(source_file='b.py', source_module='b', target_module='a'))
    findings = detector.detect_circular_imports(graph)
    
    count = len(findings)
    has_evidence = hasattr(findings[0], 'evidence_data') if findings else False
    
    print(f'[OK] Found {count} circular imports')
    print(f'[OK] Evidence data exists: {has_evidence}')
    
    if count > 0 and has_evidence:
        print('[OK] L2Detector functionality PASSED')
    else:
        print('[FAIL] L2Detector functionality FAILED')
        
except Exception as e:
    print(f'[FAIL] L2Detector check failed: {e}')
