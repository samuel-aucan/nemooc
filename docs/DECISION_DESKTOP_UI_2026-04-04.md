# Decision de Interfaz Desktop

Fecha: 2026-04-04  
Baseline Git: `2e22689`  
Proyecto: [`INGRESO OC`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC)

## Decision tomada
Se adopta **PySide6 + Qt Widgets** como nueva base de interfaz para la version desktop.

La version web queda **solo como referencia funcional y de UX**, sin modificaciones durante esta migracion.

La version desktop actual en `CustomTkinter` se mantiene como respaldo operativo mientras la nueva interfaz Qt no alcance paridad suficiente.

## Por que se tomo esta decision
La app desktop actual ya funciona, pero su techo visual y de productividad esta limitado por:
- tablas densas basadas en `ttk.Treeview`
- layouts complejos resueltos a mano
- dificultad para lograr una apariencia mas profesional y consistente
- menor flexibilidad para splitters, docking, barras de herramientas, estados y navegacion experta

Qt resuelve mejor:
- tablas complejas con `QTableView`
- filtros y ordenamiento con `QSortFilterProxyModel`
- divisiones ajustables con `QSplitter`
- barras de herramientas y acciones rapidas
- theming mas serio
- accesos de teclado y flujos de trabajo intensivos

## Alternativas evaluadas
### 1. Evolucionar la UI actual sobre `CustomTkinter`
Ventajas:
- menor riesgo
- reutilizacion alta
- mas rapido al inicio

Desventajas:
- techo visual y tecnico menor
- tablas y estados complejos mas fragiles

### 2. `CustomTkinter` + componentes mas potentes para tablas
Ventajas:
- conserva la base actual
- mejora parcialmente productividad

Desventajas:
- mezcla de paradigmas
- complejidad incremental sin resolver la base visual

### 3. `PySide6 + Qt Widgets`
Ventajas:
- mejor base para producto desktop serio
- mejor look y mejor ergonomia operativa
- mejor escalabilidad a futuro

Desventajas:
- mayor inversion inicial
- requiere migracion ordenada

## Regla clave
La migracion a Qt se hara **en paralelo**, no sobreescribiendo la UI actual.

Esto significa:
- no se toca la version web
- no se reemplaza `app/ui` de inmediato
- no se mezcla logica de negocio con widgets Qt
- no se elimina `CustomTkinter` hasta validar que la nueva version cubre el flujo principal

## Como se hara
### Estructura objetivo
Se creara una nueva capa de UI en paralelo dentro de `nemo_oc`, por ejemplo:

```text
nemo_oc/
  app/                <- dominio y logica ya existente, compartida
  app_qt/             <- nueva UI Qt
    main.py
    bootstrap.py
    shell/
    pages/
    widgets/
    models/
    viewmodels/
    theme/
```

### Reglas de arquitectura
La logica existente se reutiliza desde:
- `app/config.py`
- `app/db.py`
- `app/models/`
- `app/repositories/`
- `app/services/`

La nueva capa Qt consumira esa logica mediante adaptadores o viewmodels propios, evitando:
- copiar reglas de negocio dentro de widgets
- depender de codigo UI web
- acoplar la UI nueva a `CustomTkinter`

### Regla de referencia funcional
La web se usa para:
- entender modulos
- replicar prioridades de UX
- mapear interacciones y estados

La web **no** se toca y **no** se transpila a desktop.

## Alcance funcional esperado de la nueva desktop
La nueva interfaz Qt debe cubrir, en este orden:
1. Login y control de usuarios local
2. Bandeja principal de OCs con detalle inferior
3. Importaciones
4. Configuracion
5. Holdings
6. Estadisticas y revision experta

## Puntos de control para decidir si seguir o volver atras
### Checkpoint A
Despues de construir:
- shell principal
- sidebar
- tema
- bandeja principal con detalle

Si en ese punto Qt no entrega una mejora clara en:
- densidad visual
- velocidad operativa
- mantenibilidad

se puede volver a la estrategia 1 o 2 sin perder el trabajo de analisis, porque:
- la logica de negocio seguira intacta
- la web seguira como referencia UX
- el plan de migracion seguira vigente

### Checkpoint B
Despues de implementar:
- importaciones
- configuracion
- holdings

Si el costo de terminar `stats` o `users` en Qt se vuelve desproporcionado, se puede:
- dejar la shell Qt como version principal
- mantener algunos modulos viejos temporalmente
- o revaluar una evolucion mas incremental

## Como volver a este punto en el futuro
Para retomar esta decision mas adelante:
1. Leer este documento:
   [`DECISION_DESKTOP_UI_2026-04-04.md`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/DECISION_DESKTOP_UI_2026-04-04.md)
2. Leer el plan operativo:
   [`PLAN_MIGRACION_DESKTOP_QT_2026-04-04.md`](c:/Users/SamuelBelmar/OneDrive%20-%20Nemo%20Chile%20S.A/Escritorio/PROYECTOS%20/INGRESO%20OC/PLAN_MIGRACION_DESKTOP_QT_2026-04-04.md)
3. Partir desde el baseline Git:
   `2e22689`
4. Confirmar que la web sigue tratandose como referencia y no como objetivo de cambios
5. Crear o retomar una rama dedicada a la migracion Qt

## Decision ejecutiva
Se aprueba avanzar con **PySide6 + Qt Widgets**, con migracion paralela y reversible, tomando la web como modelo funcional y de UX, pero manteniendo intacta la desktop actual hasta alcanzar paridad real.
