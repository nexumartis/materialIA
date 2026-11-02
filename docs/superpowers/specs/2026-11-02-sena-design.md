# Seña para productos a pedido — diseño

**Origen:** backlog priorizado del [roadmap](../../roadmap.md), ítem 8, y el relevamiento de la competencia: «inodoros, vanitorys y otros productos a pedido se trabajan con seña; el pago parcial también tiene que estar verificado». Tomi pidió seguir sin preguntas, así que lo marcado **(decisión de Claude)** no fue acordado: revisarlo.

## Flujo
1. Un cliente pide un producto «a pedido». El agente no lo vende: lo deriva, como antes.
2. El dueño abre la conversación en la bandeja, toca **Cotizar productos a pedido** y completa:
   - productos a pedido del catálogo, con cantidad y precio que él define;
   - una seña opcional (hay un atajo para el 30%).
3. Se crea un pedido `PENDING_PAYMENT` marcado como `quote`, que vence en 7 días. En el chat del cliente queda el resumen con el link de pago de la seña, o del total si no hay seña.
4. **Seña verificada** (proveedor o transferencia cotejada por el dueño) ⇒ el pedido pasa a `DEPOSIT_PAID` («señado, falta pagar el saldo») y deja de vencer. En el chat queda el aviso y el link del saldo.
5. **Saldo verificado** ⇒ el pedido pasa a `PAID`, con la constancia de siempre, y sigue el circuito normal (preparación, despacho).

## Reglas de plata (no se relajan)
- Un pago acredita sólo si coincide con lo que el pedido debe en ese momento:
  - con seña pendiente: la seña o el total completo;
  - señado: sólo el saldo.

  Cualquier otro monto queda «requiere revisión».
- El mismo aviso de pago de la seña reenviado no cuenta como saldo, aunque la seña sea igual al saldo (seña del 50%).
- Devolución de la seña ⇒ `REFUNDED` y revisión humana.
- Un comprobante o su OCR no acreditan nada, como siempre.
- El link del saldo es un cobro aparte, con su propia clave de idempotencia en Mercado Pago.

## Decisiones de Claude
- **Sólo productos a pedido.** Lo que tiene stock y precio lo vende el agente con su reserva.
- **Sin stock.** El pedido a medida no aparta ni descuenta stock: se fabrica o se encarga.
- **Sólo el dueño cotiza**, porque fija precios. El staff ve el pedido pero no lo crea.
- **Vigencia de 7 días** para pagar la seña. El saldo no vence.
- **Constancia única** al pagarse todo. La seña tiene aviso en el chat, no constancia propia.
- **Sin envío ni cancelación de señados** en la cotización. Cancelar un pedido señado implica devolver plata: lo hace una persona por fuera.

## Esquema (0017)
- `orders.quote`, `orders.deposit` (`0 < seña < total`) y `orders.deposit_paid_at`.
- Estado `DEPOSIT_PAID`: se reemplaza el check de estados por uno más amplio.
