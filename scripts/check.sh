#!/usr/bin/env bash
set -euo pipefail

echo "-> api: lint"   && (cd api && uv run ruff check . && uv run ruff format --check .)
echo "-> api: types"  && (cd api && uv run mypy app)
echo "-> api: tests"  && (cd api && uv run pytest -q)
# tsc -b, not tsc --noEmit: the root tsconfig is a solution file with
# "files": [], so non-build mode type-checks nothing at all and passes.
echo "-> web: types"  && (cd web && npx tsc -b)
echo "-> web: lint"   && (cd web && npx oxlint src)
echo "-> web: tests"  && (cd web && npm run test)
echo "-> web: build"  && (cd web && npm run build)
echo "-> image builds" && docker build -q -t ehm:check . > /dev/null
echo "OK all checks passed"
