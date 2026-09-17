FROM node:22-alpine AS web
WORKDIR /web
COPY web/package*.json web/.npmrc ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /srv
COPY api/pyproject.toml api/uv.lock ./
ENV UV_COMPILE_BYTECODE=1
RUN pip install --no-cache-dir uv && uv sync --frozen --no-dev
ENV PATH="/srv/.venv/bin:${PATH}"
COPY api/app ./app
RUN python -m compileall -q app
COPY --from=web /web/dist ./static

RUN useradd --system --no-create-home --uid 10001 appuser
USER appuser

ENV PORT=8080

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
