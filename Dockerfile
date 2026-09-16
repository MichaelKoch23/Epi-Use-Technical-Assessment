# ---- stage 1: build the SPA
FROM node:22-alpine AS web
WORKDIR /web
COPY web/package*.json web/.npmrc ./
RUN npm ci
COPY web/ ./
RUN npm run build

# ---- stage 2: runtime
FROM python:3.12-slim
WORKDIR /srv
COPY api/pyproject.toml api/uv.lock ./
RUN pip install --no-cache-dir uv && uv sync --frozen --no-dev
ENV PATH="/srv/.venv/bin:${PATH}"
COPY api/app ./app
COPY --from=web /web/dist ./static

# Run as an unprivileged user. Nothing here writes to the filesystem at
# runtime, so the whole tree can stay owned by root and simply be readable
# - a container process that is compromised then cannot modify the code it
# is running.
RUN useradd --system --no-create-home --uid 10001 appuser
USER appuser

ENV PORT=8080

# --proxy-headers makes uvicorn rebuild `request.client` from the
# left-most X-Forwarded-For entry. Cloud Run always terminates the
# connection itself, so without this every request appears to originate
# from the same ingress address - which would collapse the per-IP login
# rate limiter (app/core/rate_limit.py) into a single global bucket:
# useless against one attacker, and a denial of service against everyone
# else once that bucket fills.
#
# --forwarded-allow-ips="*" is safe *only* because this container is never
# reached directly - Cloud Run is the sole ingress and overwrites the
# header. Exposing this port without a trusted proxy in front would let a
# client spoof its own address and evade the limiter, so that pairing is
# part of the deployment contract, not an implementation detail.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
