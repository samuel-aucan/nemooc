FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema para pdfplumber y otros
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Cache bust — incrementar para forzar rebuild completo
ARG CACHEBUST=20260528004
RUN echo "Cache bust: $CACHEBUST"

# Copiar nemo_oc (core: modelos, servicios, repositorio)
COPY nemo_oc/ /app/nemo_oc/

# Copiar backend web
COPY nemo_oc_web/ /app/nemo_oc_web/

# Copias explícitas de módulos críticos (garantiza que estén aunque haya cache)
COPY nemo_oc_web/backend/api/gd_routes.py /app/nemo_oc_web/backend/api/gd_routes.py
COPY nemo_oc_web/backend/api/poc_sse.py /app/nemo_oc_web/backend/api/poc_sse.py
COPY nemo_oc_web/backend/core/repo_selector.py /app/nemo_oc_web/backend/core/repo_selector.py
COPY nemo_oc_web/backend/supabase_oc_repository.py /app/nemo_oc_web/backend/supabase_oc_repository.py

# Instalar dependencias Python
RUN pip install --no-cache-dir -r /app/nemo_oc_web/requirements.txt

# Directorio de datos persistente
RUN mkdir -p /app/data

WORKDIR /app/nemo_oc_web

ENV PYTHONPATH=/app/nemo_oc:/app/nemo_oc_web
ENV DATA_SOURCE=supabase

EXPOSE 8000

# Entrypoint Python: lee PORT del entorno sin depender de shell expansion
COPY start.py /app/start.py

CMD ["python", "/app/start.py"]
