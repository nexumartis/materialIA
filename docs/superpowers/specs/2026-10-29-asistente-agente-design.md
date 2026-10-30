# Crear el agente paso a paso — diseño (roadmap etapa 6)

**Origen:** [roadmap](../../roadmap.md), etapa 6. Tomi pidió seguir sin ronda de preguntas («seguí con lo otro del road map», 29/10/2026), así que lo marcado **(decisión de Claude)** no fue acordado: revisarlo.

## Por qué

Hoy un negocio nuevo cae en un panel con muchas secciones y en «Mi agente», un formulario largo. No hay un camino que diga qué falta para tener el agente andando ni una forma de probarlo como lo vería un cliente antes de publicarlo.

## Objetivo

Un asistente guiado en `#/asistente`, con progreso visible:

1. Negocio
2. Rubro
3. Catálogo
4. Cómo habla
5. Políticas
6. Cobro
7. Probar
8. Publicar

«Mi agente» queda como pantalla de ajustes y ofrece abrir el asistente. Un registro nuevo entra directo al asistente.

## No-objetivos

- **WhatsApp en «Publicar».** Está fuera del alcance de `CLAUDE.md`; el paso lo dice sin prometer fecha.
- **Conectar el catálogo con otras plataformas** (Tiendanube, Mercado Libre: roadmap etapa 4). Sólo CSV.
- **Configurar Mercado Pago por negocio.** El paso de cobro informa el medio que está activo y cómo se confirman las transferencias (Pedidos).
- **Editar el nombre del negocio.** No hay endpoint para eso; se muestra el que se cargó al registrarse.

## Diseño

- **Sin migraciones** (decisión de Claude):
  - el progreso se calcula de los datos que ya existen (link, rubro, catálogo con productos, nombre y saludo, envíos u horarios, medios de pago, pruebas corridas, versión publicada);
  - el borrador y el paso actual se guardan en el navegador, como comodidad: perderlos no rompe nada.
- **Lo que guarda en el servidor:** el perfil, una sola vez, en **Publicar**; así no se crea una versión por cada paso (decisión de Claude).
  - El rubro trae su plantilla con `GET /app/agent-templates/{key}` **sin aplicarla**: la vuelca en el borrador (nombre, tono, saludo, preguntas y reglas; no toca envíos, horarios ni medios de pago).
  - La carga del catálogo sí se guarda en el momento, porque es la misma acción de la página Catálogo.
- **Borrador del navegador:** se descarta si el perfil guardado cambió desde otro lado, para no pisar esos cambios al publicar.
- **Progreso:** lo que el sistema completa solo (link, rubro, nombre) cuenta recién cuando el dueño pasó por ese paso.
- **Publicar:** usa `PUT /app/agent-profile` con `require_evals`. Si fallan las pruebas, ofrece «Publicar igual», como «Mi agente», según el código estructurado del 409 (`X-Error-Code: evals_failed`).
- **Vista previa:** `POST /app/agent-preview` con `{message, conversation_id, profile}`.
  - Un mensaje por vez, con el perfil **borrador** (sin el link), en una conversación de prueba del canal `eval`: sin pedidos, stock apartado ni cobros. El carrito de prueba es transitorio.
  - `DELETE /app/agent-preview/{id}` la borra al reiniciar o al salir del paso, y el worker limpia las abandonadas después de 1 hora.
  - Hasta 12 mensajes por vista previa (decisión de Claude).
  - Muestra «Respuesta por reglas (sin IA)» cuando no hay modelo configurado.
  - El negocio sale de la membresía; el perfil pasa por la misma validación que al guardar.
  - (Cambió tras la revisión: reproducir toda la charla en cada mensaje costaba de forma cuadrática y cambiaba respuestas ya vistas.)

## Aceptación

- La vista previa responde con el borrador (por ejemplo, el nombre de vendedor nuevo) sin cambiar el perfil vigente. Al reiniciar no quedan conversaciones, pedidos ni oportunidades.
- Sin sesión ⇒ 401; conversación de otro negocio o fuera del canal `eval` ⇒ 404; pasado el tope ⇒ 409.
- Recorrido completo en el navegador: registro ⇒ asistente ⇒ catálogo CSV ⇒ prueba ⇒ publicar ⇒ link de la tienda, que responde con lo configurado. Sin desborde a 390 px.
