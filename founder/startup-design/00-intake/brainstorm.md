# Brainstorm

**Phase:** 2 — Brainstorm
**Project:** materialia
**Date:** 2026-11-09
**Confidence:** Low (todo es [Opinion] o [Assumption]; nada validado con clientes)

---

## Variantes exploradas
1. Base: agente en WhatsApp y web que lee stock, arma pedido y cobra, por abono mensual.
2. Instalación hecha por los socios (alta + abono).
3. Cobro por venta cerrada y pagada por el agente.
4. Cliente distinto: mayoristas y distribuidores.
5. Versión mínima: solo precio y stock; el dueño cierra.
6. Plataforma multi-rubro (peluquerías, talleres, canchas, imprentas).
7. Venta por canal (sistema de gestión, marcas, contadores).
8. Presupuesto de obra: cotiza listas de materiales (texto, foto, audio).

## Decisiones del founder (09/11/2026)
| Decisión | Elección | Nota |
|---|---|---|
| Qué venden | El programa + lo dejan andando ellos: guía para crear o conectar la cuenta de Meta, reunión virtual, presencial si hace falta. | [Data, founder] |
| Cómo cobran | Fijo de **$70.000/mes** + un extra de ~1% si el local duplica su venta. | [Assumption — precio no validado] |
| A quién | Locales que venden al público **y** mayoristas/distribuidores, en sanitarios y ferretería. Otros rubros (peluquerías, talleres) más adelante. | [Data, founder] |
| Qué hace | Todo: asesora ("quiero hacer el baño" → opciones y combos), arma el pedido, manda el link de pago, verifica el cobro, y cotiza listas de obra. | [Data, founder] |
| Idea extra | Actualización de precios asistida: sugerir el % del mes (IPC del INDEC u otro índice) y que el dueño lo acepte, cambie o descarte. Backlog de producto. | [Data, founder] |

## Observaciones al refinar [Opinion]
- **El extra de 1% sobre "duplicar la venta" no se puede medir bien.** Habría que conocer la facturación total del local antes y después, y que el dueño la comparta. Además, la suba puede tener otras causas (temporada, inflación). Eso genera discusiones. Lo que el sistema sí mide sin discusión es **la venta que pasó por el agente con pago verificado**. Propuesta: fijo + un % chico solo sobre esas ventas. A validar con locales.
- **Minoristas y mayoristas a la vez es abarcar mucho.** Compran distinto: el mayorista maneja listas por cliente, cuenta corriente y precios por volumen. Propuesta: empezar con los 10 minoristas de Capital, y que las charlas digan si el mayorista es el segundo paso.
- **"Asesorar" (decoración, combos) choca con la regla de honestidad del producto:** no inventar medidas ni compatibilidades. Se puede hacer con combos armados por el dueño, no con recomendaciones libres.
- **$70.000 está por debajo de la competencia en dólares.** Con un tipo de cambio de ARS 1.450 son unos USD 48; Cliengo cobra USD 119 y Botmaker USD 149. Hay margen para cobrar más, pero hay que validarlo con locales.

## Idea refinada
Un vendedor por WhatsApp y web para comercios de sanitarios, grifería y ferretería de Capital que **se los dejan funcionando ustedes**. Conoce el stock y el precio real de su planilla de Google Sheets, asesora con los combos del local, cotiza listas de obra, arma el pedido, cobra y verifica el pago. Abono fijo en pesos, con un posible % sobre las ventas que cierra. Mayoristas y otros rubros vienen después de los primeros 10 locales.

---

## Flags

**Red Flags:**
- Ninguno nuevo (sigue el de cero clientes consultados, en `brief.md`).

**Yellow Flags:**
- Cobrar sobre "duplicar la facturación" no se puede medir y puede romper la relación con el cliente.
- Intención de abarcar minoristas, mayoristas y otros rubros: riesgo de dispersarse.
- El asesoramiento libre puede generar respuestas inventadas.

## Sources
- Conversación con el founder, 09/11/2026
- `founder/competitors.md` (precios de la competencia, 05/11/2026)
