#!/bin/bash
set -e

# Main package
mkdir -p arcnical/{cli,ui,orchestrator,qualification,ingest,parse,graph,metrics,heuristics}
mkdir -p arcnical/layers/config
mkdir -p arcnical/review/{prompts,tools}
mkdir -p arcnical/{security,practice,report,eval,cache}

# Tests
mkdir -p tests/{unit,integration,fixtures}

# Docs & CI
mkdir -p .github/workflows
mkdir -p docs/ADR

# Runtime directories (created on first run)
mkdir -p .arcnical/{reports,cache}

echo "✓ Directory structure created"
