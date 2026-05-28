FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema para pdfplumber y otros
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copiar nemo_oc (core: modelos, servicios, repositorio)
COPY nemo_oc/ /app/nemo_oc/

# Copiar backend web
COPY nemo_oc_web/ /app/nemo_oc_web/

# Instalar dependencias Python
RUN pip install --no-cache-dir -r /app/nemo_oc_web/requirements.txt

# Directorio de datos persistente
RUN mkdir -p /app/data

WORKDIR /app/nemo_oc_web

ENV PYTHONPATH=/app/nemo_oc:/app/nemo_oc_web
ENV DATA_SOURCE=supabase

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
