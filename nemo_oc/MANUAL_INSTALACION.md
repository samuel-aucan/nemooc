# NemoOC Web
Manual de uso y configuracion

Actualizado: 2026-04-03
Version: 2.0 Web
Desarrollado por Samuel Belmar

## 1. Que hace el sistema

NemoOC Web centraliza dos flujos:

- OCs publicas de Mercado Publico.
- OCs privadas recibidas por correo y procesadas por holding.

La idea es simple:

- la bandeja principal muestra las OCs y su detalle para trabajar rapido
- Mercado Publico trae OCs publicas desde la API
- OCs Privadas lee correos reenviados a automatizacionnemo@gmail.com
- Holdings concentra la configuracion de cada grupo privado
- Estadisticas concentra la cobertura, las sugerencias y la cola de correccion experta
- Usuarios permite que solo un administrador cree y controle accesos

## 2. Antes de comenzar

### 2.1 Levantar la web

1. Abre la carpeta nemo_oc_web.
2. Ejecuta python run.py.
3. Abre http://localhost:5173 en el navegador.
4. El frontend queda en el puerto 5173 y la API interna en 8001.

### 2.2 Configuracion minima inicial

### 2.2 Acceso seguro inicial

Desde abril de 2026 la web ya no abre de forma publica. Primero pide usuario y contraseña.

Primer ingreso:

1. Abre la web.
2. Si todavia no existe ningun usuario, aparecera la pantalla Crear administrador.
3. Define nombre, usuario y contraseña.
4. Guarda ese acceso porque sera la cuenta inicial del sistema.
5. Desde ese momento todas las rutas quedan protegidas por sesion.

Ingresos siguientes:

1. Entra a la web.
2. Usa tu usuario y contraseña.
3. La sesion queda activa en el navegador hasta cerrar sesion o expirar.

### 2.3 Como crear mas usuarios

Una vez creado el primer administrador, ya no existe registro abierto.

Solo un administrador puede:

- crear usuarios nuevos
- definir si seran `admin` u `operador`
- activar o desactivar accesos
- resetear contraseñas
- reiniciar acceso con token temporal para que el usuario defina una clave nueva

Eso se hace desde el modulo Usuarios.

Flujo recomendado para reiniciar acceso:

1. Entra a Usuarios.
2. Busca al usuario.
3. Haz clic en `Reiniciar acceso`.
4. El sistema genera un token temporal.
5. Entrega ese token de forma segura al usuario.
6. El usuario entra a Login > `Activar acceso`.
7. Pega el token y define su nueva contraseña.

### 2.4 Configuracion minima inicial

1. Entra a Configuracion.
2. En la seccion Mercado Publico pega el Ticket API.
3. Completa el Codigo empresa.
4. Guarda los cambios.
5. Usa Prueba rapida API para validar que la conexion responda.

### 2.5 Catalogos generales

En Configuracion > Catalogos se cargan los archivos generales del sistema:

- Homologacion CM
- Maestra SAP
- Cartera de clientes
- Correos de vendedores
- Licitaciones

Los catalogos por holding ya no se cargan aqui. Esos se administran dentro del modulo Holdings.

## 3. Uso diario

### 3.1 Descargar OCs publicas

1. Entra a Importar.
2. Define Fecha desde y Fecha hasta.
3. Marca Convenio Marco y Otras si corresponde.
4. Haz clic en Descargar OCs.
5. Espera el resultado y revisa la bitacora de la misma pantalla.

### 3.2 Sincronizar OCs privadas

1. En la misma pantalla Importar usa Sincronizar Gmail.
2. El sistema lee la casilla configurada para privados.
3. Toma correos no leidos que cumplan el filtro.
4. Descarga los PDF adjuntos.
5. Intenta identificar el holding y crear la OC.

### 3.3 Trabajar en la bandeja

1. La parte superior muestra la lista de OCs.
2. La parte inferior muestra el detalle de la OC seleccionada.
3. El panel de filtros esta archivado al costado y se puede abrir o cerrar.
4. La idea es no salir de la misma pantalla para revisar varias OCs rapido.

### 3.4 Trabajar en Estadisticas

Este modulo no es solo un tablero. Es una mesa de trabajo para cerrar lineas pendientes.

Que muestra arriba:

- cuantas OCs y lineas se estan analizando
- cuanto ya esta cubierto
- cuanto sigue pendiente
- cuantas lineas ya tienen sugerencia
- cuantas lineas siguen sin sugerencia

Que muestra abajo:

- una cola de sugerencias y correcciones
- una fila por cada linea pendiente o manual
- detalle de la linea directamente en la misma tabla
- editor inline para corregir sin cambiar de pantalla
- aceptacion directa en la fila cuando ya existe una sugerencia clara
- guardado manual solo desde una seleccion valida de la maestra

Forma recomendada de uso:

1. Entra a Estadisticas.
2. Define el rango de fechas.
3. Parte por la vista Pendientes.
4. Si una fila ya trae una sugerencia buena, puedes aceptarla directo sin expandir.
5. Si necesitas mas contexto, haz clic en la fila.
6. Se abrira un panel dentro de la misma tabla.
7. Si no hay sugerencia suficiente, busca en la maestra.
8. Selecciona un resultado real de la maestra para guardar manualmente.
9. Usa Revisadas para revisar lineas que ya fueron tocadas manualmente.
10. Usa Sin sugerencia para atacar primero lo mas dificil.

## 4. Holdings explicados en simple

### 4.1 Que es un holding

Un holding es un grupo privado que comparte una misma logica comercial dentro del sistema.

En la practica, un holding suele compartir:

- reglas parecidas
- mismo catalogo de homologacion
- mismos precios de referencia
- PDFs parecidos entre si
- varios RUTs compradores asociados

Ejemplo:

- Banmedica puede incluir Clinica Santa Maria, Clinica Ciudad del Mar, Clinica Biobio y Clinicas Davila.
- ACHS puede incluir ACHS y sus empresas externas relacionadas.

### 4.2 Cuando NO conviene meter todo en el mismo holding

Si un grupo nuevo cambia de forma importante en alguna de estas cosas, conviene crear otro holding:

- usa otro catalogo
- tiene otras condiciones
- el PDF es de otra familia
- requiere otro parser

Regla practica:

- mismo comportamiento -> mismo holding
- comportamiento distinto -> otro holding

### 4.3 Lo mas importante para entender holdings

Un holding no es un solo correo.
Un holding no es un solo RUT.
Un holding no es una sola clinica.

Un holding es un grupo de compradores que el sistema debe tratar con la misma logica.

## 5. Como configurar un holding paso a paso

### 5.1 Paso 1: crear el holding

En Holdings crea el registro base con estos campos:

- ID interno: nombre tecnico corto. Ejemplo: banmedica.
- Nombre visible: nombre que vera el usuario. Ejemplo: Banmedica.
- Prefijo OC: prefijo que usara el sistema. Ejemplo: BM.
- Activo: dejalo apagado si aun no terminas de configurarlo.

Consejo:

- crea primero el holding
- completa lo demas
- activalo al final

### 5.2 Paso 2: agregar los RUTs compradores

Esta es la senal principal para que el sistema reconozca el holding.

Orden recomendado:

1. Abre el holding.
2. Ve al bloque RUTs compradores.
3. Usa Buscar en cartera maestra.
4. Escribe razon social, RUT o codigo cliente CN.
5. Selecciona la sugerencia correcta.
6. Revisa RUT, Nombre visible y Sucursal.
7. Haz clic en Agregar.

Importante:

- un holding puede tener muchos RUTs compradores
- no importa si el RUT llega con puntos, guion o sin formato
- el sistema normaliza el RUT para poder reconocerlo igual
- si tienes dudas, usa la razon social de cartera como referencia

### 5.3 Paso 3: agregar los correos esperados

Los correos esperados ayudan cuando el mail llega reenviado y el sistema necesita una pista adicional.

Aqui puedes pegar:

- un correo completo
- o solo el dominio

Ejemplos:

- achs.cl
- clinicasantamaria.cl
- fastudillo@clinicasantamaria.cl

El sistema guarda la parte util del dominio para la deteccion.

No necesitas cargar todos los correos del holding.
Basta con cargar los remitentes o dominios mas tipicos.

### 5.4 Paso 4: subir el catalogo del holding

Cada holding debe tener su propio Excel de homologacion y precios.

Ese archivo sirve para:

- homologar codigos internos del holding con SAP
- tener precios de referencia
- comparar el precio del PDF contra el precio registrado

Importante:

- el precio del PDF es el precio operativo real de la OC
- el precio del catalogo es un precio de control
- si hay diferencia, hoy se genera advertencia, no bloqueo

### 5.5 Paso 5: usar ayudas avanzadas solo si hace falta

Las ayudas avanzadas son opcionales.

Solo usalas si el holding no se reconoce bien con:

- RUTs compradores
- correos esperados
- catalogo ya cargado

Ejemplos de ayuda avanzada:

- un texto caracteristico del PDF
- un texto del asunto
- un texto del remitente

Si no estas seguro, dejalas vacias.

### 5.6 Paso 6: activar el holding

Activa el holding cuando ya tenga al menos:

- nombre y prefijo correctos
- RUTs compradores cargados
- correos esperados minimos
- catalogo subido o plan claro para subirlo enseguida

Si todavia falta informacion, es mejor dejarlo inactivo.

## 6. Como decide el sistema a que holding pertenece una OC privada

El sistema no depende de una sola pista.
Combina varias senales.

Orden practico de decision:

1. RUT detectado dentro del PDF.
2. Nombre de empresa o sucursal dentro del PDF.
3. Correo original o dominio del correo reenviado.
4. Textos del asunto o del cuerpo.
5. Ayudas avanzadas si existen.

Si aun asi no esta claro, la OC no se fuerza.
Queda en estado Pendiente para revision.

## 7. Que significa Pendiente

Una OC privada puede quedar Pendiente cuando ocurre algo como esto:

- el holding no se reconoce con suficiente confianza
- no hay match claro con el catalogo
- falta informacion importante
- el PDF viene muy distinto a lo esperado

Pendiente no significa error irreversible.
Significa que el sistema prefirio no cargar algo dudoso de forma automatica.

## 8. Precios y duplicados

### 8.1 Comparacion de precios

Para privados se comparan dos cosas:

- precio del PDF
- precio referencia del catalogo del holding

Si no coinciden, el sistema deja advertencia.
Eso sirve para control comercial.

### 8.2 Duplicados

La meta es que una misma OC no aparezca dos veces en el software.

Hoy la deduplicacion funciona especialmente bien cuando la OC se reconoce bien y se obtiene su numero.

Por eso conviene:

- cargar bien los RUTs compradores
- cargar los correos esperados
- mantener el holding bien configurado

Mientras mejor configurado este el holding, menor riesgo de duplicados o pendientes innecesarios.

## 9. Orden recomendado para configurar un holding nuevo

1. Crea el holding.
2. Agrega sus RUTs compradores desde cartera maestra.
3. Agrega los correos o dominios esperados.
4. Sube el catalogo Excel del holding.
5. Prueba con 1 o 2 PDFs reales.
6. Si detecta bien, activalo.
7. Si no detecta bien, recien ahi agrega ayudas avanzadas.

Este orden evita enredos y hace mas facil diagnosticar problemas.

## 10. Casos concretos

### 10.1 Banmedica

Banmedica es un holding.
Dentro de el pueden vivir varios RUTs compradores, por ejemplo clinicas del grupo.

No hace falta crear un holding distinto por cada clinica si comparten:

- mismas condiciones
- mismo catalogo
- mismo comportamiento general

### 10.2 ACHS

ACHS puede tener varios RUTs relacionados bajo una misma logica.
Mientras el comportamiento y el catalogo sean comunes, siguen bajo el mismo holding.

### 10.3 Clinicas regionales

Si un grupo como Clinicas Regionales necesita otra logica, otro parser o otro catalogo, debe vivir como holding aparte.

## 11. Problemas comunes

### 11.1 La API de Mercado Publico responde lento

Usa Prueba rapida API.
Si la API externa esta lenta o sin respuesta, el sistema ahora debe mostrarlo como error y no como cero resultados.

### 11.2 Una OC privada no se reconoce

Revisa en este orden:

1. si el holding existe
2. si tiene RUTs compradores correctos
3. si tiene correos esperados utiles
4. si el PDF pertenece realmente a ese holding
5. si hace falta una ayuda avanzada

### 11.3 No encuentro un cliente al agregar RUTs

Prueba buscar por:

- razon social
- RUT
- codigo cliente CN

Si no aparece en cartera, puedes cargarlo manualmente de forma temporal y luego completarlo cuando la cartera este actualizada.

## 12. Manual complementario

La configuracion del reenvio automatico desde Outlook a automatizacionnemo@gmail.com se documenta aparte en:

- MANUAL_REENVIO_AUTOMATICO_OCS_PRIVADAS.md

Ese manual explica el correo.
Este manual explica el sistema y, especialmente, la logica de holdings.
