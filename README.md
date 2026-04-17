# NemoOC

Punto de entrada rapido del proyecto `INGRESO OC`.

## Versiones del proyecto

- Desktop: [`nemo_oc/README.md`](./nemo_oc/README.md)
- Web: [`nemo_oc_web/INSTALAR.md`](./nemo_oc_web/INSTALAR.md)
- Documentacion tecnica: [`docs/PROYECTO_COMPLETO.md`](./docs/PROYECTO_COMPLETO.md)
- Decision UI desktop Qt: [`docs/DECISION_DESKTOP_UI_2026-04-04.md`](./docs/DECISION_DESKTOP_UI_2026-04-04.md)
- Plan migracion desktop Qt: [`docs/PLAN_MIGRACION_DESKTOP_QT_2026-04-04.md`](./docs/PLAN_MIGRACION_DESKTOP_QT_2026-04-04.md)
- Estado sistema (snapshot abr-2026): [`docs/ESTADO_SISTEMA_2026-04-03.md`](./docs/ESTADO_SISTEMA_2026-04-03.md)
- Manual reenvio OCs privadas: [`docs/MANUAL_REENVIO_AUTOMATICO_OCS_PRIVADAS.md`](./docs/MANUAL_REENVIO_AUTOMATICO_OCS_PRIVADAS.md)

## Control de versiones local

- Version actual: [`VERSION.json`](./VERSION.json)
- Historial funcional: [`CHANGELOG.md`](./CHANGELOG.md)
- Indice de respaldos: [`RESPALDOS/INDICE_RESPALDOS.md`](./RESPALDOS/INDICE_RESPALDOS.md)
- Crear checkpoint: `python crear_checkpoint.py vX.Y.Z descripcion-corta`
- Vista previa sin escribir: `python crear_checkpoint.py vX.Y.Z descripcion-corta --dry-run`

Flujo recomendado:
1. Actualizar `CHANGELOG.md` con el resumen funcional.
2. Crear el checkpoint con `crear_checkpoint.py`.
3. Verificar que `VERSION.json` y `RESPALDOS/INDICE_RESPALDOS.md` quedaron actualizados.

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

Preview Qt en paralelo:

```bash
cd nemo_oc
python app_qt/main.py
```

## Nota

La version web y la desktop comparten datos y catalogos. No conviene ejecutarlas al mismo tiempo.
