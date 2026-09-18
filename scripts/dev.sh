#!/usr/bin/env bash
set -euo pipefail

echo "-> building and starting the production image against the Neon dev branch"
echo "-> http://localhost:8080 once the container is up"
echo "-> for frontend hot reload, run 'npm run dev' in web/ separately - but always"
echo "  re-check this container before calling a change done"

docker compose up --build
