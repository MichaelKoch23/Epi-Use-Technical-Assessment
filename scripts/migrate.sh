#!/usr/bin/env bash
# Run Alembic migrations against a named Neon branch.
#
# Usage: ./scripts/migrate.sh <dev|prod>
#
# The target branch is resolved by name through the Neon CLI rather than
# from a locally-cached connection string, and "prod" requires a typed
# confirmation, so a stale env file or a fat-fingered argument can't send a
# migration to the wrong database.
set -euo pipefail

PROJECT_ID="wild-surf-18764091"

usage() {
    echo "Usage: $(basename "$0") <dev|prod>" >&2
    echo "  dev   migrate the Neon 'dev' branch" >&2
    echo "  prod  migrate the Neon 'main' (production) branch" >&2
    exit 1
}

[ $# -eq 1 ] || usage

TARGET="$1"
case "$TARGET" in
    dev)
        BRANCH="dev"
        ;;
    prod)
        BRANCH="main"
        ;;
    *)
        usage
        ;;
esac

command -v neon >/dev/null 2>&1 || {
    echo "error: the Neon CLI ('neon') is required but was not found on PATH" >&2
    exit 1
}

echo "Target: $TARGET (Neon branch '$BRANCH', project $PROJECT_ID)"

if [ "$TARGET" = "prod" ]; then
    read -r -p "About to run migrations against PRODUCTION. Type 'prod' to continue: " CONFIRM
    if [ "$CONFIRM" != "prod" ]; then
        echo "Aborted." >&2
        exit 1
    fi
fi

# Direct (non-pooled) connection: Alembic needs session-level behaviour that
# PgBouncer transaction-mode pooling doesn't support. `neon connection-string`
# returns the direct URL by default; the pooled one carries a "-pooler" host.
DIRECT_URL="$(neon connection-string "$BRANCH" --project-id "$PROJECT_ID")"

case "$DIRECT_URL" in
    *-pooler*)
        echo "error: resolved a pooled connection string; migrations require a direct connection" >&2
        exit 1
        ;;
esac

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
API_DIR="$SCRIPT_DIR/../api"

echo "Running alembic upgrade head against '$BRANCH'..."
cd "$API_DIR"
DATABASE_URL="$DIRECT_URL" uv run alembic upgrade head
