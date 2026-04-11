#!/bin/bash
# Create __init__.py stub files in all modules

modules=(
  "arcnical/cli"
  "arcnical/ui"
  "arcnical/orchestrator"
  "arcnical/qualification"
  "arcnical/ingest"
  "arcnical/parse"
  "arcnical/graph"
  "arcnical/metrics"
  "arcnical/heuristics"
  "arcnical/review"
  "arcnical/review/prompts"
  "arcnical/review/tools"
  "arcnical/security"
  "arcnical/practice"
  "arcnical/report"
  "arcnical/eval"
  "arcnical/cache"
  "tests"
  "tests/unit"
  "tests/integration"
)

for module in "${modules[@]}"; do
  touch "$module/__init__.py"
  echo "# Module: $module" > "$module/__init__.py"
done

echo "✓ Created __init__.py files"
