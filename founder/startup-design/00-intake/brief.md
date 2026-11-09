# Brief inicial

> **Lectura conjunta:** el brainstorm posterior propone $70.000 y CABA como primer foco. Consultar [el índice vigente](../../README.md) y [las correcciones](../01-discovery/corrections-2026-11-09.md); este intake conserva el contexto de la entrevista.

**Phase:** 1 — Intake
**Project:** materialia
**Date:** 2026-11-09
**Confidence:** Medium (producto: alta; mercado y clientes: baja, sin contacto con clientes)

---

## La idea
- **Problema:** los comercios de sanitarios, grifería, mamparas y ferretería atienden consultas por WhatsApp a mano: se pierden ventas fuera de horario, se responde lento y se cotiza con precios viejos. [Assumption — no validado con clientes]
- **Solución:** un agente de ventas por chat (web y WhatsApp oficial de Meta) que lee stock y precio reales de la planilla del local, arma el pedido, manda el link de pago y solo lo marca cobrado con el pago verificado. Lo que no sabe, lo deriva al dueño. [Código presente; 622 tests reportados por Claude, no reproducidos en el cierre documental]
- **Origen:** idea propia de los socios, sin observación previa de clientes.
- **Estado:** producto funcionando en local. WhatsApp etapa 1 hecha (PR #74), sin probar con Meta real porque la cuenta de prueba está restringida desde el 09/11/2026. Sin deploy, sin landing, sin nombre de empresa definitivo.

## Los fundadores
- **Matías (Mati) y Tomás (Tommy).** Los dos estudian en la facultad; Mati además tiene otro trabajo.
- **Dedicación:** variable. A veces uno le dedica uno o dos días enteros y el otro nada; otras veces, una hora cada uno. [Data, dicho por el founder]
- **Fortalezas que ven en sí mismos:** saben programar el producto y creen que saben vender cara a cara. [Founder-reported]
- **Sin contactos en el rubro** ni experiencia trabajando en él.
- **Presupuesto:** unos USD 50 por mes cada uno (USD 100 en total), siempre que el precio de los servicios sea razonable. Esperan que en uno o dos meses el negocio cubra los costos. [Data, dicho por el founder]
- **Legal:** Mati tiene un monotributo (categoría a confirmar). Tomás no. Evalúan una SAS más adelante.

## El mercado
- **Cliente ideal:** dueño de un comercio físico de sanitarios, grifería, mamparas o ferretería, sin tienda online, que hoy contesta WhatsApp a mano.
- **Geografía:** Capital Federal para los primeros locales, recorriendo a pie. Después, venta remota a cualquier lugar, usando a los primeros como respaldo. El plan anterior de Tommy (`founder/launch.md`) decía zona sur del GBA; los socios viven en Capital.
- **Cómo lo resuelven hoy:** WhatsApp Business a mano, un empleado, o plataformas genéricas en dólares (ver `preflight.md`).
- **Competidores conocidos:** ver `founder/competitors.md`.

## El negocio
- **Modelo:** suscripción mensual. Precio previo propuesto por Tommy: $35.000 + IVA por mes, con 2 meses gratis de piloto. [Assumption — panel simulado, no validado]
- **Meta a 6 meses:** al menos 10 clientes fijos y contentos, que vendan más gracias al producto. [Data, dicho por el founder]
- **Meta personal:** retorno de al menos el doble de lo que ponen, unos USD 100 por mes para cada uno. [Data, dicho por el founder]

## Restricciones
- WhatsApp solo con la API oficial de Meta. La cuenta de prueba y el portfolio están restringidos desde el 09/11/2026 (apelación pendiente, la hace Mati a mano).
- Ley 25.326 de datos personales.
- Plata limitada: unos USD 100 por mes entre los dos.

## Contacto con clientes
- **Cero conversaciones.** [Data] Los socios reconocen que pudo ser un error construir antes de validar.

## Preguntas duras
- **¿Por qué ustedes y no Meta?** Respuesta del founder: simplicidad, más permisos y ser un respaldo si Meta bloquea. **Corrección [Opinion]:** el producto usa la API de Meta y está sujeto a sus mismas reglas, así que no puede ser un respaldo contra Meta. La diferencia real hoy es que lee stock y precio reales, arma el pedido y lo cobra verificado, no inventa y se instala en persona cobrando en pesos.
- **¿Qué los haría dejar?** "No frenaríamos": preguntarían por qué los rechazan (precio, funciones, complejidad o calidad) y cambiarían el rumbo según eso. No hay un límite de tiempo ni de plata definido.

---

## Flags

**Red Flags:**
- **Cero conversaciones con clientes después de construir un producto completo.** Todo lo que se sabe del mercado es supuesto.

**Yellow Flags:**
- **No hay criterio para frenar** (ni de tiempo ni de plata). Sin eso, la plata y el tiempo pueden irse sin una decisión.
- **Las metas no cierran con el precio actual** [Estimate, con los datos de `founder/cfo.md`, tipo de cambio ARS 1.450]. 10 locales a $35.000 dejan unos USD 30 por mes de ganancia después de costos, no USD 200. Se revisa en la fase financiera.
- **Dedicación de tiempo variable**, sin un mínimo acordado entre los socios.
- **Ninguno tiene experiencia ni contactos en el rubro.**
- **La venta remota a escala es un supuesto:** no se probó que un local se dé de alta sin visita.

## Sources
- Entrevista con el founder (Mati), 09/11/2026
- Repo: `founder/cfo.md`, `founder/launch.md`, `founder/competitors.md`, PR #74
