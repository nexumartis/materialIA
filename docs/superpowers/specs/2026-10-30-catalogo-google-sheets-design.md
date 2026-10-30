# Google Sheets como catálogo vivo — diseño

**Origen:** backlog priorizado del [roadmap](../../roadmap.md#backlog-priorizado-competencia-30102026), ítem 1 (relevamiento de la competencia del 30/10/2026). Tomi pidió empezar sin ronda de preguntas («empezá a trabajar»), así que lo marcado **(decisión de Claude)** no fue acordado: revisarlo.

## Por qué

El cliente objetivo ya maneja su catálogo en Excel o Google Sheets. Hoy tiene que exportar un CSV y subirlo cada vez que cambia un precio. Con la planilla conectada, el agente vende con lo que el dueño ya mantiene, sin un paso extra.

## Objetivo

- El dueño pega el link de su Google Sheet (compartida como «cualquier persona con el enlace puede ver»).
- El sistema lee la pestaña indicada con el **mismo formato que el CSV** actual y la sincroniza:
  - al conectar;
  - cuando el dueño toca «Sincronizar ahora»;
  - cada 15 minutos, desde el worker.
- El panel muestra la última sincronización, cuántos productos se crearon o actualizaron, y los errores por fila.

## No-objetivos

- **OAuth de Google ni planillas privadas.** Se usa la exportación CSV pública de la pestaña (decisión de Claude: sin credenciales ni secretos nuevos).
- **Escribir en la planilla.** La sincronización va en un solo sentido: planilla → catálogo.
- **Despublicar productos que desaparecen de la planilla.** Se informan, pero no se pausan solos (decisión de Claude: borrar una fila por error no debe sacar productos de la venta).
- **Excel en OneDrive y otras planillas.**

## Regla de stock (decisión de Claude)

La planilla **no pisa** el stock en cada sincronización, porque eso borraría lo que se vendió y podría vender de más. Por producto se guarda `sheet_stock`, el último valor leído de la planilla:

- Si el valor de la planilla **cambió** desde la última lectura, el dueño actualizó su conteo: se aplica como stock físico, con el mismo control de hoy (nunca por debajo de lo apartado; si queda por debajo, es un error de esa fila).
- Si **no cambió**, se respeta el stock actual, que ya incluye las ventas del agente.

Precios, nombres, categorías, fotos y estado activo salen siempre de la planilla, como en el CSV.

Esto responde, para la planilla, la pregunta abierta del pase del 28/10 sobre la fuente principal del inventario: los dueños deberían acordarlo al validar con clientes reales.

## Seguridad

- Sólo se aceptan links de `docs.google.com/spreadsheets/d/<ID>`. El servidor **arma la URL de exportación** con ese ID y la pestaña (`gid`); nunca descarga una URL arbitraria.
- Las redirecciones sólo pueden ir a `docs.google.com` o `*.googleusercontent.com`.
- La descarga tiene tiempo máximo de 15 s y un tope de 2 MB, igual que el CSV.
- Una planilla privada devuelve HTML de login: se detecta y se responde «compartila como cualquier persona con el enlace».
- El negocio sale de la membresía; la tabla `catalog_sources` tiene RLS como el resto del panel.

## Aceptación

- Conectar un link válido importa los productos. Un link de otro dominio, malformado o privado se rechaza con un mensaje claro y no guarda nada.
- Precio cambiado en la planilla ⇒ el precio se actualiza al sincronizar.
- Stock sin cambios en la planilla después de una venta ⇒ se mantiene lo vendido. Stock cambiado ⇒ se aplica. Stock por debajo de lo apartado ⇒ error en esa fila.
- El worker sincroniza las fuentes vencidas y una falla de red no frena a las demás.
- Otro negocio no ve ni toca la fuente; sin membresía ⇒ 403.
- En el navegador: conectar, ver el estado y sincronizar desde Catálogo y desde el paso Catálogo del asistente.
