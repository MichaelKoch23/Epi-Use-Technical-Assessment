#!/usr/bin/env bash
set -euo pipefail

echo "→ api: lint"   && (cd api && uv run ruff check . && uv run ruff format --check .)
echo "→ api: types"  && (cd api && uv run mypy app)
echo "→ api: tests"  && (cd api && uv run pytest -q)
echo "→ web: types"  && (cd web && npx tsc --noEmit)
echo "→ web: lint"   && (cd web && npx oxlint src)
echo "→ web: build"  && (cd web && npm run build)
echo "→ image builds" && docker build -q -t ehm:check . > /dev/null
echo "✓ all checks passed"
