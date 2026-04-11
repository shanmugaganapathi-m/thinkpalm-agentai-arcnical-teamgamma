# Arcnical

**Clinical architecture reviews for your codebase**

Arcnical is an AI-powered tool that analyzes GitHub repositories, evaluates code structure and architecture patterns, and generates comprehensive architecture reports with actionable recommendations.

## Vision

Prove that a tool combining **deterministic static analysis** with a **retrieval-driven LLM review pass** can generate architecture feedback that a senior engineer would meaningfully agree with.

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/arcnical/arcnical.git
cd arcnical

# Install with uv (recommended)
uv sync

# Or with pip
pip install -e .
```

### First Run

Set your Anthropic API key:
```bash
export ANTHROPIC_API_KEY="sk-..."
```

Analyze a local repository:
```bash
arcnical analyze .
```

Analyze a public GitHub repository:
```bash
arcnical analyze https://github.com/owner/repo
```

View the report in Streamlit:
```bash
streamlit run arcnical/ui/app.py
```

## Features

### Layered Analysis

Arcnical organizes analysis into 4 ordered layers:

1. **L1: Structural Integrity** - Parse success, manifests, import resolution
2. **L2: Architectural Rules** - Circular dependencies, god classes, layer violations
3. **L3: Code Health** - Complexity, coupling, instability, hotspots
4. **L4: Semantic Review** - LLM-powered architecture, maintainability, performance review

Plus a **cross-cutting Security stage** running in parallel with L2/L3.

### What Arcnical Detects

- ✅ Circular import cycles
- ✅ God classes (>300 LOC or >20 methods)
- ✅ Layer violations
- ✅ High complexity functions (cyclomatic >15)
- ✅ Instable modules
- ✅ Hotspot files
- ✅ Hardcoded secrets (gitleaks)
- ✅ Vulnerable dependencies (pip-audit, npm audit)
- ✅ Architecture patterns (monolith, microservices, etc)
- ✅ API surface types (REST, GraphQL, gRPC)
- ✅ CI/CD & IaC presence
- ✅ Test & documentation posture
- ✅ Architecture Health Score

## Usage

### CLI Commands

```bash
# Analyze a repository (full pipeline)
arcnical analyze <path-or-url>

# JSON output only
arcnical analyze . --json

# Quick mode (L1-L3 only, no LLM calls)
arcnical analyze . --depth quick

# Standard mode (all 4 layers with LLM)
arcnical analyze . --depth standard

# Override qualification or layer halts
arcnical analyze . --force

# Run evaluation against golden set
arcnical eval

# Re-render an existing report
arcnical report <run-id>
```

### Environment Variables

```bash
ANTHROPIC_API_KEY        # Claude API key (required)
GITHUB_TOKEN            # GitHub token for private repos (optional)
```

## Output

Arcnical generates three report formats:

- **JSON** - Structured data (schema v2.0) for programmatic consumption
- **Markdown** - Human-readable with metrics, layer results, and recommendations
- **HTML** - Browser-friendly (optional, P2)

Reports are written to `.arcnical/reports/` and auto-added to `.gitignore`.

## Architecture

```
arcnical/
├── cli/                 # Typer CLI commands
├── ui/                  # Streamlit viewer
├── orchestrator/        # asyncio DAG stage runner
├── qualification/       # Target classifier (application vs non-app)
├── ingest/             # Path/URL loaders
├── parse/              # tree-sitter wrappers
├── graph/              # Knowledge graph builder
├── metrics/            # Complexity/coupling/churn
├── heuristics/         # L2/L3 deterministic findings
├── layers/             # Layer definitions + config
├── review/             # L4 LLM agent
├── security/           # gitleaks/pip-audit/npm-audit
├── practice/           # Architecture pattern detection
├── report/             # JSON/Markdown/HTML generators
├── eval/               # Golden repo evaluation
├── cache/              # File-based caching
└── schema.py           # Pydantic output schema (frozen)
```

## Technology Stack

| Layer | Technology |
|-------|-----------|
| **CLI** | Typer |
| **TUI Output** | Rich |
| **Parsing** | tree-sitter (Python, TypeScript/JavaScript) |
| **Graph** | networkx |
| **Metrics** | radon, custom TS/JS |
| **Git** | GitPython |
| **LLM** | Anthropic Claude API |
| **Web UI** | Streamlit |
| **Schema** | Pydantic v2 |
| **Templating** | Jinja2 |
| **Package Mgmt** | uv |

## Development

### Setup

```bash
uv sync --all-extras
```

### Run Tests

```bash
pytest tests/ -v
pytest tests/unit/test_schema.py -v  # Schema tests only
```

### Lint & Type Check

```bash
ruff check arcnical/
mypy arcnical/
```

### Running Locally

```bash
# Analyze current directory
arcnical analyze .

# View reports
streamlit run arcnical/ui/app.py
```

## Acceptance Criteria

Arcnical ships when:

- ✅ `arcnical analyze <path>` works end-to-end on ≥3/5 golden repos
- ✅ `arcnical analyze <github-url>` works on public repos
- ✅ Target qualification correctly classifies application/non-application
- ✅ All 4 layers (L1-L4) produce output on ≥3 golden repos
- ✅ Every recommendation has verified evidence + file references
- ✅ `arcnical eval` reports recall ≥0.6 on Critical/High findings
- ✅ Zero hallucinated file paths in final reports
- ✅ `--depth quick` produces useful report with zero LLM calls
- ✅ `--force` flag demonstrated working
- ✅ Streamlit viewer loads and renders reports with layer badges
- ✅ README explains install, first run, env vars, CLI, --force
- ✅ Tagged v0.2.0, reproducible from fresh clone

## Out of Scope (v0.2.0)

- Business/domain alignment checks
- Runtime profiling & dynamic analysis
- Disaster recovery / RTO-RPO assessment
- Regulatory compliance (GDPR, HIPAA, SOC2)
- Infrastructure cost estimation
- Threat modelling beyond gitleaks + pip-audit
- Monorepo multi-package deep analysis
- Languages beyond Python + TypeScript/JavaScript

## Future

- Runtime profiling (v0.3+)
- Interactive layer gating
- Deeper practice detection (not just presence)
- IDE integration (VS Code, Cursor)
- Additional language depth (Go, Java, Rust)

## Contributing

Coming soon.

## License

MIT

## Authors

Arcnical Team

---

**Version:** 0.2.0  
**Schema:** 2.0  
**Status:** Prototype (target delivery: 15 April 2026)
