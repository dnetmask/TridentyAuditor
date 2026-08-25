# Build context: la raíz del repo (no backend/), porque esta imagen necesita
# tanto backend/ como frontend/ — ver deploy/docker-compose.yml
# (`context: .., dockerfile: backend/Dockerfile`). Todas las rutas COPY de
# aquí en adelante son relativas a la raíz del repo, no a este directorio.

FROM node:22-slim AS frontend-builder
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
# npm ci respeta el lockfile tal cual — un build reproducible es también un
# control de cadena de suministro (Fase S1/Q).
RUN npm ci
COPY frontend/ ./
# Mismo origen en runtime (esta imagen sirve la SPA y la API en el mismo
# puerto, ver app/main.py::SPAStaticFiles), así que el cliente no necesita
# una URL absoluta de API — las peticiones relativas ya apuntan al lugar
# correcto sea cual sea el host/puerto publicado.
ENV VITE_API_BASE_URL=""
RUN npm run build

FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
    && rm -rf /var/lib/apt/lists/*

FROM base AS builder
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*
COPY backend/pyproject.toml ./
COPY backend/app ./app
RUN pip install --no-cache-dir --prefix=/install .

FROM base AS runtime
COPY --from=builder /install /usr/local
COPY backend/app ./app
COPY backend/alembic ./alembic
COPY backend/alembic.ini ./
COPY backend/scripts ./scripts
COPY --from=frontend-builder /frontend/dist ./app/static/frontend

RUN useradd --create-home --uid 1000 tridenty
# El volumen de MOD·DOC (ver deploy/docker-compose.yml) monta aquí encima —
# crearlo y darle dueño ahora es lo que Docker copia al volumen la primera
# vez que se usa, así el proceso sin privilegios de abajo puede escribir.
RUN mkdir -p /app/data/documents && chown -R tridenty:tridenty /app/data
USER tridenty

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
