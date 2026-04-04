# NemoOC Web - Instrucciones de instalacion

## Requisitos

- Python 3.9 o superior
- Node.js 18 o superior

Descarga Node.js desde https://nodejs.org y elige la version "LTS".

## Primera vez

Abre una terminal en la carpeta `nemo_oc_web\` y ejecuta:

```bash
# 1. Instalar dependencias de Python
pip install -r requirements.txt

# 2. Instalar dependencias del frontend
cd frontend
npm install
cd ..
```

## Levantar la app

Desde la carpeta `nemo_oc_web\` ejecuta:

```bash
python run.py
```

Luego abre en el navegador:

- Frontend: http://localhost:5173
- Backend API: http://127.0.0.1:8001

El script `run.py` levanta ambos servidores en paralelo.

Para detenerlos, presiona `Ctrl+C` en la terminal.

## Si quieres levantar cada parte por separado

Backend:

```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8001 --reload
```

Frontend:

```bash
cd frontend
npm run dev
```

## Notas importantes

- La app web usa la misma base de datos y catalogos que la app desktop.
- No ejecutes la version desktop y la version web al mismo tiempo.
- Los catalogos se pueden subir desde Configuracion > Catalogos.
