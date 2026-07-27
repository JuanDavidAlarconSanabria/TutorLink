# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# TutorLink API — imagen del backend (FastAPI + SQLAlchemy)
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS base

# Evita .pyc y fuerza logs sin buffer (útiles en `docker logs`)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencias del sistema necesarias para psycopg2 y argon2-cffi
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Se instalan primero las dependencias de Python para aprovechar la caché
# de capas de Docker cuando sólo cambia el código fuente.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Dependencias adicionales para poder correr la suite de tests dentro del contenedor
COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt

COPY . .

# Usuario sin privilegios (buena práctica de seguridad para contenedores)
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
