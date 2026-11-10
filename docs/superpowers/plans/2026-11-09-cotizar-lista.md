# Plan — cotizar_lista

Spec: `docs/superpowers/specs/2026-11-09-cotizar-lista-design.md`. TDD con planner guionado
(`backend/tests/test_llm_sales.py`), Postgres real con `PV_REQUIRE_DB=1`.

1. **Tests en rojo** (`test_llm_sales.py`):
   - lista del plomero: una llamada a `cotizar_lista`, renglones con subtotal/total del servidor,
     «llave de paso 1/2» no cae en «canilla dos llaves», inodoro a pedido ⇒ `requires_human`,
     la respuesta del modelo con esos importes pasa el control, la guía está en el prompt;
   - stock parcial, sin stock y producto de otro negocio (no aparece);
   - respuesta con un total inventado ⇒ respaldo = texto de la cotización;
   - agotar `MAX_STEPS` ⇒ una llamada más sin herramientas.
2. **Herramienta:** `_Turn.quote_list` (sales_agent.py), esquema y `_execute` (llm_sales.py).
3. **Control:** renglones cotizados en `_catalog`; respaldo con la cotización en `_fallback`.
4. **Prompt:** guía `cotizar_lista` en `sales_skills.py`.
5. **`for … else`** de `MAX_STEPS`.
6. **Verificar:** suite completa en base limpia; medición con la conversación de prueba
   (tenant C, `gpt-oss:120b-cloud`): la lista se cotiza con total y baja el consumo del turno.
