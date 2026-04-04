# NemoOC

Punto de entrada rapido del proyecto `INGRESO OC`.

## Versiones

- Desktop: [`nemo_oc/README.md`](./nemo_oc/README.md)
- Web: [`nemo_oc_web/INSTALAR.md`](./nemo_oc_web/INSTALAR.md)
- Documentacion tecnica general: [`PROYECTO_COMPLETO.md`](./PROYECTO_COMPLETO.md)

## Probar la version web

Desde la carpeta `nemo_oc_web`:

```bash
pip install -r requirements.txt
cd frontend
npm install
cd ..
python run.py
```

Luego abre:

- Frontend: `http://localhost:5173`
- Backend API: `http://127.0.0.1:8001`

## Probar la version desktop

Desde la carpeta `nemo_oc`:

```bash
pip install -r requirements.txt
python app/main.py
```

## Nota

La version web y la desktop comparten datos y catalogos. No conviene ejecutarlas al mismo tiempo.
