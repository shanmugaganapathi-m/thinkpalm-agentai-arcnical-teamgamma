"""
Orchestrator - coordinates L1-L4 analysis pipeline.
"""

import hashlib
import json
import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

from arcnical.schema import (
    AnalysisDepth,
    ArchitectureHealthScore,
    DocsInfo,
    LanguageBreakdown,
    LayerResult,
    LayerStatus,
    Metadata,
    Metrics,
    PracticeDetection,
    Qualification,
    Report,
    SecurityFinding,
    FileReference,
    Severity,
    Summary,
    TargetClassification,
    TestsInfo,
    TokenUsage,
)
from arcnical.parse.parser import ParseResult
from arcnical.graph.builder import CodeKnowledgeGraph
from arcnical.report.builder import HealthScoreCalculator

logger = logging.getLogger(__name__)

_SKIP_DIRS = frozenset({
    '__pycache__', '.git', '.venv', 'venv', 'node_modules',
    'dist', 'build', '.tox', '.mypy_cache', '.pytest_cache',
    '.ruff_cache', 'htmlcov', 'coverage',
})


class Orchestrator:
    """Coordinates the full analysis pipeline (L1-L4)."""

    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self._parse_result: Optional[ParseResult] = None
        self._graph: Optional[CodeKnowledgeGraph] = None
        self._findings: dict = {}
        self._raw_metrics: dict = {}
        self.file_loc: dict = {}  # {relative_filepath: loc} — populated by _compute_loc_metrics

    # ------------------------------------------------------------------
    # Public pipeline methods
    # ------------------------------------------------------------------

    def run_l1_qualification(self) -> Report:
        """Parse repo, classify target type, return initial Report."""
        logger.info("L1: Parsing repository...")
        self._parse_result = self._parse_repo()

        logger.info("L1: Building knowledge graph...")
        self._graph = CodeKnowledgeGraph()
        self._graph.add_parse_result(self._parse_result)
        self._graph.detect_cycles()

        graph_hash = self._compute_graph_hash()
        commit_sha = self._get_commit_sha()

        logger.info("L1: Classifying repository...")
        qualification = self._classify_repo()
        practice = self._detect_practices()
        self._raw_metrics = self._compute_loc_metrics()

        repo_name = Path(self.repo_path).name

        metadata = Metadata(
            tool_version="0.2.0",
            model="claude-sonnet-4-6",
            prompt_version="v1",
            layer_config_version="v1",
            graph_hash=graph_hash,
            commit_sha=commit_sha,
            generated_at=datetime.utcnow(),
            depth=AnalysisDepth.STANDARD,
            force_used=False,
            token_usage=TokenUsage(),
        )

        summary = self._build_summary(repo_name)

        layers = [
            LayerResult(id="L1", name="Qualification", status=LayerStatus.PASSED, findings_count=0),
            LayerResult(id="L2", name="Structural Issues", status=LayerStatus.PENDING, findings_count=0),
            LayerResult(id="L3", name="Code Quality", status=LayerStatus.PENDING, findings_count=0),
            LayerResult(id="L4", name="LLM Review", status=LayerStatus.PENDING, findings_count=0),
        ]

        return Report(
            metadata=metadata,
            target_type=qualification.classification,
            qualification=qualification,
            summary=summary,
            layers=layers,
            scores=ArchitectureHealthScore(),
            metrics=Metrics(),
            practice_detection=practice,
            recommendations=[],
            security_findings=[],
            skipped_scanners=[],
            unparsed_files=self._parse_result.unparsed_files,
        )

    def run_l2_structure(self, report: Report) -> Report:
        """Run L2 structural heuristics and update the report."""
        if self._graph is None:
            raise RuntimeError("run_l1_qualification() must be called first")

        logger.info("L2: Running structural heuristics...")
        from arcnical.heuristics.l2_detector import L2Detector

        l2_detector = L2Detector()
        l2_findings = l2_detector.run_all_l2_checks(self._graph, self.repo_path)
        self._findings["l2_findings"] = l2_findings

        l2_recs = [f.to_recommendation() for f in l2_findings if hasattr(f, "to_recommendation")]
        report.recommendations.extend(l2_recs)

        blocking = [f.title for f in l2_findings if f.severity in (Severity.CRITICAL, Severity.HIGH)]
        report.layers[1] = LayerResult(
            id="L2",
            name="Structural Issues",
            status=LayerStatus.WARNED if l2_findings else LayerStatus.PASSED,
            findings_count=len(l2_findings),
            blocking_findings=blocking,
        )

        report.metrics.circular_dependency_count = self._graph.get_cycle_count()
        return report

    def run_l3_heuristics(self, report: Report) -> Report:
        """Run L3 quality heuristics + security scan and update the report."""
        if self._graph is None:
            raise RuntimeError("run_l1_qualification() must be called first")

        logger.info("L3: Running quality heuristics...")
        from arcnical.heuristics.l3_detector import L3Detector
        from arcnical.heuristics.security_scanner import SecurityScanner

        l3_findings = L3Detector().run_all_l3_checks(self._graph, self.repo_path)
        self._findings["l3_findings"] = l3_findings

        logger.info("L3: Running security scan...")
        raw_sec = SecurityScanner().scan_for_secrets(self.repo_path)
        self._findings["security_findings"] = raw_sec

        l3_recs = [f.to_recommendation() for f in l3_findings if hasattr(f, "to_recommendation")]
        report.recommendations.extend(l3_recs)

        schema_sec = []
        for sf in raw_sec:
            refs = []
            if getattr(sf, "file_path", None):
                refs = [FileReference(file=sf.file_path, line=getattr(sf, "line_number", None))]
            schema_sec.append(SecurityFinding(
                scanner="gitleaks",
                finding_type=getattr(sf, "finding_type", "secret"),
                severity=sf.severity,
                description=sf.description,
                file_references=refs,
            ))
        report.security_findings = schema_sec

        report.layers[2] = LayerResult(
            id="L3",
            name="Code Quality",
            status=LayerStatus.WARNED if l3_findings else LayerStatus.PASSED,
            findings_count=len(l3_findings),
            blocking_findings=[],
        )

        # Recalculate health scores now that we have all findings
        report.scores = HealthScoreCalculator().calculate_health_score(
            self._findings, self._raw_metrics
        )

        # Update full metrics
        self._update_report_metrics(report)

        # Sort recommendations: Critical → High → Medium → Low
        _order = {Severity.CRITICAL: 0, Severity.HIGH: 1, Severity.MEDIUM: 2, Severity.LOW: 3}
        report.recommendations.sort(key=lambda r: _order.get(r.severity, 9))

        return report

    def run_full_analysis(self) -> Report:
        """Run L1-L3 deterministic analysis (no L4 LLM call)."""
        report = self.run_l1_qualification()
        report = self.run_l2_structure(report)
        report = self.run_l3_heuristics(report)
        return report

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def _parse_repo(self) -> ParseResult:
        """Walk repo and parse all Python / TypeScript files."""
        result = ParseResult()

        try:
            from arcnical.parse.python_parser import PythonParser
            py_parser: Optional[object] = PythonParser()
        except Exception as e:
            logger.warning("Python parser unavailable: %s", e)
            py_parser = None

        try:
            from arcnical.parse.typescript_parser import TypeScriptParser
            ts_parser: Optional[object] = TypeScriptParser()
        except Exception as e:
            logger.warning("TypeScript parser unavailable: %s", e)
            ts_parser = None

        for root, dirs, files in os.walk(self.repo_path):
            dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
            for filename in files:
                filepath = os.path.join(root, filename)
                if filename.endswith(".py") and py_parser is not None:
                    result.merge(py_parser.parse_file(filepath))
                elif filename.endswith((".ts", ".tsx", ".js", ".jsx")) and ts_parser is not None:
                    result.merge(ts_parser.parse_file(filepath))

        return result

    # ------------------------------------------------------------------
    # L1 classification
    # ------------------------------------------------------------------

    def _classify_repo(self) -> Qualification:
        """Heuristically classify the repository target type."""
        repo = Path(self.repo_path)
        signals: list[str] = []
        app_score = 0
        lib_score = 0
        docs_score = 0

        # Entry points → application
        _entry_points = {
            "main.py", "app.py", "__main__.py", "manage.py",
            "wsgi.py", "asgi.py", "server.py", "run.py",
            "index.ts", "index.js", "server.ts", "server.js",
            "app.ts", "app.js", "main.ts", "main.js",
        }
        for ep in _entry_points:
            if (repo / ep).exists():
                signals.append(f"entry point present: {ep}")
                app_score += 2
                break

        # Python package metadata → library
        if any((repo / f).exists() for f in ("pyproject.toml", "setup.py", "setup.cfg")):
            signals.append("python package metadata present")
            lib_score += 2

        # package.json
        pkg_json = repo / "package.json"
        if pkg_json.exists():
            signals.append("package.json present")
            try:
                pkg = json.loads(pkg_json.read_text(encoding="utf-8", errors="ignore"))
                if pkg.get("main") or pkg.get("exports") or pkg.get("module"):
                    lib_score += 2
                    signals.append("package.json exports library surface")
                if pkg.get("scripts", {}).get("start") or pkg.get("scripts", {}).get("dev"):
                    app_score += 2
                    signals.append("package.json has start/dev script")
            except Exception:
                pass

        # Containerization → application
        if (repo / "Dockerfile").exists():
            signals.append("Dockerfile present")
            app_score += 2
        if (repo / "docker-compose.yml").exists() or (repo / "docker-compose.yaml").exists():
            signals.append("docker-compose present")
            app_score += 1

        # Test directories → application indicator
        for td in ("tests", "test", "__tests__", "spec"):
            if (repo / td).is_dir():
                signals.append(f"test directory present: {td}")
                app_score += 1
                break

        # Markdown ratio → docs/data
        try:
            all_files = [f for f in repo.rglob("*") if f.is_file()
                         and not any(p in f.parts for p in _SKIP_DIRS)]
            md_files = [f for f in all_files if f.suffix in (".md", ".rst", ".txt")]
            if all_files:
                md_ratio = len(md_files) / len(all_files)
                signals.append(f"markdown ratio: {md_ratio:.2f}")
                if md_ratio > 0.6:
                    docs_score += 3
        except Exception:
            pass

        max_score = max(app_score, lib_score, docs_score)
        if max_score == 0:
            classification = TargetClassification.UNKNOWN
            confidence = 0.3
        elif docs_score == max_score and docs_score > 2:
            classification = TargetClassification.DOCS_OR_DATA
            confidence = min(0.95, 0.5 + docs_score * 0.1)
        elif app_score >= lib_score:
            classification = TargetClassification.APPLICATION
            confidence = min(0.95, 0.5 + app_score * 0.05)
        else:
            classification = TargetClassification.LIBRARY
            confidence = min(0.95, 0.5 + lib_score * 0.05)

        return Qualification(
            classification=classification,
            confidence=round(confidence, 2),
            signals=signals,
        )

    # ------------------------------------------------------------------
    # Practice detection
    # ------------------------------------------------------------------

    def _detect_practices(self) -> PracticeDetection:
        """Detect CI/CD, containerisation, IaC, tests, and docs posture."""
        repo = Path(self.repo_path)

        ci_cd, containerization, iac, observability = [], [], [], []

        if (repo / ".github" / "workflows").is_dir():
            ci_cd.append("github_actions")
        if (repo / ".gitlab-ci.yml").exists():
            ci_cd.append("gitlab_ci")
        if (repo / ".circleci" / "config.yml").exists():
            ci_cd.append("circleci")
        if (repo / "Jenkinsfile").exists():
            ci_cd.append("jenkins")

        if (repo / "Dockerfile").exists():
            containerization.append("dockerfile")
        if (repo / "docker-compose.yml").exists() or (repo / "docker-compose.yaml").exists():
            containerization.append("docker_compose")

        if list(repo.rglob("*.tf"))[:1]:
            iac.append("terraform")
        if (repo / "Pulumi.yaml").exists() or (repo / "Pulumi.yml").exists():
            iac.append("pulumi")

        # Architecture style
        top_dirs = {d.name for d in repo.iterdir() if d.is_dir() and d.name not in _SKIP_DIRS}
        if "services" in top_dirs or "microservices" in top_dirs:
            arch = "microservices"
        elif "src" in top_dirs or "lib" in top_dirs:
            arch = "modular_monolith"
        elif "app" in top_dirs or "apps" in top_dirs:
            arch = "modular_monolith"
        else:
            arch = None

        # Docs
        readme = (repo / "README.md").exists() or (repo / "README.rst").exists()
        adr_dir = (repo / "docs" / "adr").is_dir() or (repo / "adr").is_dir()

        # Tests
        test_fw = None
        test_ratio = 0.0
        try:
            py_files = [
                f for f in repo.rglob("*.py")
                if not any(p in f.parts for p in _SKIP_DIRS)
            ]
            test_files = [
                f for f in py_files
                if f.stem.startswith("test_") or f.stem.endswith("_test")
            ]
            if py_files:
                test_ratio = round(len(test_files) / len(py_files), 2)

            if list(repo.rglob("conftest.py"))[:1] or list(repo.rglob("pytest.ini"))[:1]:
                test_fw = "pytest"
            elif list(repo.rglob("*.test.ts"))[:1] or list(repo.rglob("*.spec.ts"))[:1]:
                test_fw = "jest"
        except Exception:
            pass

        return PracticeDetection(
            architecture_style=arch,
            api_surfaces=[],
            ci_cd=ci_cd,
            containerization=containerization,
            iac=iac,
            observability=observability,
            docs=DocsInfo(readme=readme, adr_dir=adr_dir, docstring_coverage=0.0),
            tests=TestsInfo(framework=test_fw, ratio=test_ratio),
        )

    # ------------------------------------------------------------------
    # Metrics helpers
    # ------------------------------------------------------------------

    def _compute_loc_metrics(self) -> dict:
        """Count total LOC across all source files and populate self.file_loc."""
        from arcnical.metrics.calculator import LOCCalculator
        loc_calc = LOCCalculator()
        total = 0
        _src_exts = {".py", ".ts", ".tsx", ".js", ".jsx"}
        repo_root = Path(self.repo_path).resolve()
        for root, dirs, files in os.walk(self.repo_path):
            dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
            for fn in files:
                if Path(fn).suffix in _src_exts:
                    full_path = os.path.join(root, fn)
                    loc = loc_calc.count_file_loc(full_path)
                    total += loc
                    # Store relative path so the graph works regardless of clone location
                    try:
                        rel = str(Path(full_path).resolve().relative_to(repo_root))
                    except ValueError:
                        rel = full_path
                    self.file_loc[rel] = loc
        return {"loc_total": total}

    def _update_report_metrics(self, report: Report) -> None:
        """Replace report.metrics with fully computed values."""
        try:
            from arcnical.metrics.calculator import MetricsAggregator
            all_m = MetricsAggregator().compute_all_metrics(self.repo_path, self._graph)
            cx = all_m.get("complexity_metrics", {})
            cp = all_m.get("coupling_metrics", {})
            qc = all_m.get("code_quality", {})
            report.metrics = Metrics(
                complexity_avg=round(cx.get("complexity_avg", 0.0), 2),
                complexity_p95=round(cx.get("complexity_p95", 0.0), 2),
                instability_avg=round(cp.get("avg_instability", 0.0), 2),
                circular_dependency_count=self._graph.get_cycle_count(),
                god_class_count=qc.get("god_classes", 0),
                hotspot_files=[],
            )
        except Exception as e:
            logger.warning("Full metrics computation failed: %s", e)

    def _build_summary(self, repo_name: str) -> Summary:
        lang = self._parse_result.language_breakdown if self._parse_result else {}
        total = sum(lang.values()) or 1
        return Summary(
            repo=repo_name,
            language_breakdown=LanguageBreakdown(
                python=round(lang.get("python", 0) / total, 2),
                typescript=round(lang.get("typescript", 0) / total, 2),
                javascript=round(lang.get("javascript", 0) / total, 2),
            ),
            loc_total=self._raw_metrics.get("loc_total", 0),
            file_count=self._parse_result.total_files if self._parse_result else 0,
        )

    def build_file_imports(self) -> dict:
        """
        Build {source_rel_path: [target_rel_path, ...]} from parsed imports.

        Only includes edges where both endpoints are known files in file_loc.
        Relative TS/JS imports are resolved to actual file paths.
        Python module-dot-notation is converted to path form.
        Paths are normalised to forward slashes.
        """
        if not self._parse_result or not self.file_loc:
            return {}

        repo_root = Path(self.repo_path).resolve()
        # Normalise known-file keys to forward slashes for consistent lookup
        known = {k.replace("\\", "/"): k for k in self.file_loc}

        result: dict = {}

        for imp in self._parse_result.imports:
            # ── source file → relative fwd-slash path ──
            try:
                src_rel = (
                    Path(imp.source_file).resolve()
                    .relative_to(repo_root)
                    .as_posix()
                )
            except (ValueError, OSError):
                continue
            if src_rel not in known:
                continue

            target_rel = None
            mod = imp.target_module

            if imp.language == "python":
                # e.g. arcnical.graph.builder -> arcnical/graph/builder.py
                candidate = mod.replace(".", "/") + ".py"
                if candidate in known:
                    target_rel = candidate
                else:
                    candidate_init = mod.replace(".", "/") + "/__init__.py"
                    if candidate_init in known:
                        target_rel = candidate_init

            else:
                # TypeScript / JavaScript
                if mod.startswith("."):
                    # Relative import – resolve against source directory
                    try:
                        src_dir = Path(imp.source_file).resolve().parent
                        resolved = (src_dir / mod).resolve()
                        for ext in (".ts", ".tsx", ".js", ".jsx"):
                            fwd = resolved.with_suffix(ext).as_posix()
                            try:
                                rel = Path(fwd).relative_to(repo_root).as_posix()
                            except ValueError:
                                continue
                            if rel in known:
                                target_rel = rel
                                break
                        if not target_rel:
                            # Try index file
                            for ext in (".ts", ".tsx", ".js"):
                                idx = (resolved / ("index" + ext)).as_posix()
                                try:
                                    rel = Path(idx).relative_to(repo_root).as_posix()
                                except ValueError:
                                    continue
                                if rel in known:
                                    target_rel = rel
                                    break
                    except Exception:
                        pass
                # Non-relative (npm packages) – skip

            if target_rel and target_rel != src_rel:
                result.setdefault(src_rel, [])
                if target_rel not in result[src_rel]:
                    result[src_rel].append(target_rel)

        return result

    def _compute_graph_hash(self) -> str:
        if self._graph is None:
            return hashlib.sha256(b"empty").hexdigest()
        try:
            s = self._graph.summary()
            return hashlib.sha256(json.dumps(s, sort_keys=True).encode()).hexdigest()
        except Exception:
            return hashlib.sha256(b"error").hexdigest()

    def _get_commit_sha(self) -> Optional[str]:
        try:
            r = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if r.returncode == 0:
                return r.stdout.strip()
        except Exception:
            pass
        return None
