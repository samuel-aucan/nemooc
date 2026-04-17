# Manual: Reenvio Automatico de OCs Privadas a `automatizacionnemo@gmail.com`

Este instructivo deja configurado el correo de Nemo para que las Ordenes de Compra privadas se deriven automaticamente a la casilla que lee el sistema.

## Objetivo

Cuando llegue un correo de OC al buzón operativo de Nemo en Microsoft 365 / Outlook:

- se reenviara o redirigira automaticamente a `automatizacionnemo@gmail.com`
- conservara el PDF adjunto
- evitara reglas duplicadas
- ayudara a que la misma OC no se procese dos veces

## Recomendacion

La forma mas estable es configurar la regla en `Outlook Web`:

- funciona aunque el PC este apagado
- la regla queda en el servidor
- es mas facil de revisar y mantener

## Antes de empezar

Ten a mano:

- la cuenta de correo de Nemo donde llegan las OCs
- acceso a `Outlook Web`
- el correo destino: `automatizacionnemo@gmail.com`

## Importante: usar `Redirigir` antes que `Reenviar`

Si Outlook te da ambas opciones, usa `Redirigir a`.

Ventaja:

- el mensaje mantiene al remitente original
- eso ayuda al sistema a identificar mejor el holding

Si no aparece `Redirigir a`, usa `Reenviar a`.

## Paso a paso en Outlook Web

1. Entra a `https://outlook.office.com/` con la cuenta donde llegan las OCs.

2. Haz clic en el engranaje `Configuracion`.

3. Entra a:
   `Correo` > `Reglas`

4. Haz clic en `Agregar nueva regla`.

5. Pon un nombre claro, por ejemplo:
   `OCs privadas a automatizacionnemo`

6. En `Agregar una condicion`, elige la opcion de asunto.
   Dependiendo de la version puede verse como:
   - `El asunto incluye`
   - `Subject includes`

7. Como primer filtro, usa una frase segura:
   `Orden de Compra`

8. En `Agregar una accion`, elige:
   - `Redirigir a`
   - o, si no existe, `Reenviar a`

9. Escribe el destino:
   `automatizacionnemo@gmail.com`

10. Activa la opcion:
    `Detener el procesamiento de mas reglas`
    o
    `Stop processing more rules`

11. Guarda la regla.

## Regla adicional para asuntos cortos tipo `OC 648856 NEMO`

No conviene partir con `OC` sola, porque es demasiado amplia y puede capturar correos que no son OCs.

Haz esto:

1. Parte solo con la regla `Orden de Compra`.

2. Revisa durante 2 o 3 dias si quedaron OCs afuera.

3. Si ves que llegan asuntos como:
   - `OC 648856 NEMO`
   - `OC_493366`
   - `OC-xxxxx`

4. Crea una segunda regla, separada, por ejemplo:
   - condicion: `El asunto incluye`
   - valor: `OC `
   - accion: `Redirigir a automatizacionnemo@gmail.com`
   - activar: `Detener el procesamiento de mas reglas`

## Orden recomendado de reglas

Si usas mas de una regla, dejalas asi:

1. `Orden de Compra`
2. `OC `

Y en ambas:

- activa `Detener el procesamiento de mas reglas`

Eso ayuda a que el mismo correo no sea tratado por varias reglas al mismo tiempo.

## Prueba rapida

Despues de guardar la regla:

1. Enviate un correo de prueba a la casilla de Nemo.
2. Usa un asunto que cumpla la regla, por ejemplo:
   `Orden de Compra prueba`
3. Adjunta un PDF cualquiera.
4. Verifica que llegue a `automatizacionnemo@gmail.com`.
5. Verifica que el adjunto llegue correctamente.

## Que hacer si no reenvia

Si la regla parece correcta, pero el correo no sale hacia Gmail, lo mas probable es que Microsoft 365 tenga bloqueado el reenvio automatico externo.

En ese caso hay que pedir a TI o al administrador de Microsoft 365:

`Permitir auto-forward externo solo para la casilla de OCs de Nemo hacia automatizacionnemo@gmail.com`

## Recomendacion operativa para no duplicar OCs

1. Usa la menor cantidad posible de reglas.

2. No crees varias reglas con condiciones muy parecidas, por ejemplo:
   - una con `OC`
   - otra con `Orden`
   - otra con `Compra`

3. En todas las reglas, activa:
   `Detener el procesamiento de mas reglas`

4. No hagas reenvio manual ademas del automatico para el mismo correo.

## Como evita duplicados hoy el sistema

Hoy el sistema ya omite una OC si su `codigo_oc` ya existe en la base.

Eso se apoya en:

- la clave primaria de `oc_cabecera.codigo_oc`
- la revision previa de codigos existentes antes de guardar

Para privadas, el codigo queda asi:

- `RS-<numero>` para RedSalud
- `IN-<numero>` para Indisa
- `BM-<numero>` para Banmedica
- `AC-<numero>` para ACHS

Por ejemplo, si la misma OC `4500263258` de ACHS llega dos veces, el sistema deberia guardar solo una:

- `AC-4500263258`

## Límite actual importante

La deduplicacion actual es fuerte cuando la OC se reconoce bien y se obtiene su numero.

Si un PDF entra como `Pendiente` porque no se reconocio correctamente, existe mas riesgo de duplicacion, porque en ese caso el sistema usa un codigo de respaldo.

La mejora recomendada para blindarlo al 100% mas adelante es agregar deduplicacion tambien por:

- `Message-ID` del correo
- hash del PDF adjunto

## Configuracion recomendada para partir

Primera etapa:

- 1 regla con `Orden de Compra`

Segunda etapa, solo si hace falta:

- 1 regla extra con `OC `

Siempre:

- destino `automatizacionnemo@gmail.com`
- accion `Redirigir a`
- `Detener el procesamiento de mas reglas`

## Referencias oficiales

- Microsoft Support: reglas en Outlook  
  https://support.microsoft.com/en-us/office/manage-email-messages-by-using-rules-in-outlook-c24f5dea-9465-4df4-ad17-a50704d66c59

- Microsoft Support: reenvio / redireccion automatica  
  https://support.microsoft.com/en-us/office/use-rules-to-automatically-forward-messages-45aa9664-4911-4f96-9663-ece42816d746

- Microsoft Learn: reenvio de correo y advertencia sobre auto-forward externo  
  https://learn.microsoft.com/en-us/exchange/recipients-in-exchange-online/manage-user-mailboxes/configure-email-forwarding
