@echo off
REM PRE-SESSION #5 VERIFICATION CHECKLIST - WINDOWS BATCH

echo =====================================================
echo PRE-SESSION #5 VERIFICATION CHECKLIST
echo =====================================================
echo.

REM CHECK 1: Files
echo 1. CHECKING FILES...
if exist "arcnical\heuristics\l2_detector.py" (
    echo   [OK] l2_detector.py
) else (
    echo   [FAIL] l2_detector.py MISSING
)

if exist "arcnical\heuristics\l3_detector.py" (
    echo   [OK] l3_detector.py
) else (
    echo   [FAIL] l3_detector.py MISSING
)

if exist "arcnical\heuristics\security_scanner.py" (
    echo   [OK] security_scanner.py
) else (
    echo   [FAIL] security_scanner.py MISSING
)

if exist "arcnical\heuristics\evaluator.py" (
    echo   [OK] evaluator.py
) else (
    echo   [FAIL] evaluator.py MISSING
)

if exist "tests\unit\test_heuristics_l2.py" (
    echo   [OK] test_heuristics_l2.py
) else (
    echo   [FAIL] test_heuristics_l2.py MISSING
)

if exist "tests\unit\test_heuristics_l3.py" (
    echo   [OK] test_heuristics_l3.py
) else (
    echo   [FAIL] test_heuristics_l3.py MISSING
)

if exist "tests\unit\test_security.py" (
    echo   [OK] test_security.py
) else (
    echo   [FAIL] test_security.py MISSING
)

echo.
echo 2. RUNNING TESTS...
python -m pytest tests/unit/ -q
echo.

echo 3. TESTING IMPORTS...
python -c "from arcnical.heuristics.l2_detector import L2Detector; print('[OK] L2Detector imports')"
python -c "from arcnical.heuristics.l3_detector import L3Detector; print('[OK] L3Detector imports')"
python -c "from arcnical.heuristics.security_scanner import SecurityScanner; print('[OK] SecurityScanner imports')"
python -c "from arcnical.heuristics.evaluator import HeuristicsEvaluator; print('[OK] HeuristicsEvaluator imports')"
echo.

echo 4. TESTING L2DETECTOR FUNCTIONALITY...
python tests_check_l2.py
echo.

echo 5. TESTING EVIDENCE STRUCTURE...
python tests_check_evidence.py
echo.

echo 6. CHECKING COVERAGE...
python -m pytest tests/unit/ --cov=arcnical --cov-report=term-only -q
echo.

echo =====================================================
echo VERIFICATION COMPLETE
echo =====================================================
pause
