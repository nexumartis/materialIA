# Conversación natural Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** conversación natural que respete pedido, catálogo y capacidades reales.
**Architecture:** conservar planner/herramientas y estado servidor; corregir contexto/redacción/validación en la capa conversacional, con respaldo pertinente y sin repetir acciones.
**Tech Stack:** Python/FastAPI/Postgres, Ollama existente, pytest.
**Spec:** ../specs/2026-10-26-conversacion-natural-design.md.

## Global Constraints

- Base 6290f60, branch feat/natural-sales-conversation. Claude implementa, Codex personal revisa; orquestador documenta.
- Ponytail full. Leer sólo skills pertinentes: Superpowers TDD/debugging/verificación y Agent Skills seguridad/API según cambio.
- DB descartable loopback existente, mock/simulado para tests; smoke sólo Ollama local qwen3:8b, máximo 20 llamadas, sin cambiar defaults.
- Sin commits por ejecutor, nuevas migraciones, servicios externos, WhatsApp ni cobros reales.

## Review Focus

- Negación válida («no tenés que pagar») debe pasar y afirmación contradictoria no; probar con PAID y PENDING_PAYMENT.
- Varios pedidos/attention_reason: no resumir el equivocado ni esconder revisión humana; probar orden ambiguo.
- Una corrección parcial conserva restricciones pertinentes y un cambio de categoría las limpia; probar ambas.
- Reintentar redacción no duplica carrito/pedido/pago; comprobar efectos en DB y número de llamadas.
- Caída del modelo/filtro conserva respuesta contextual y modo declarado; no inventa acciones. Probar agradecimiento y consulta comercial.

### Task 1: coherencia y capacidades
**Files:** modificar llm_sales.py y sales_agent.py; helper mínimo sólo si hace falta; tests/test_llm_sales.py y nuevo test conversacional si aporta.
**Interfaces:** consumir `_Turn`, `_context`, `orders.conversation_orders`, `agent_profile`; conservar handle_sales_message/SalesReply y contratos HTTP. Cualquier nueva función y responsabilidad debe quedar identificada en el reporte de implementación, evitando capas especulativas.
- [x] Reproducir el caso del video con estado de pago real en DB + planner guionado que contradice ese estado; regresiones de canales/descuento/negaciones/revisión humana. Confirmar fallo previo relevante.
- [x] Aplicar el mínimo control/contexto que evita contradicciones y acciones no realizadas, respetando el bucle y las mutaciones existentes.
- [x] Ejecutar pruebas focalizadas, incluyendo que el cliente no paga dos veces y el modelo no crea pedidos sin consentimiento.

### Task 2: naturalidad, preferencias y recomendaciones
**Files:** mismos archivos de agente; tests conversacionales y fixtures aislados por test. No cambiar datos compartidos de seed para forzar resultados.
**Interfaces:** reutilizar perfil/estado por conversación y datos de herramientas. Mantener texto final + UI estructurada existentes.
- [x] Agregar casos de cambio de preferencia/cantidad/categoría, comparación sustentada, cierre social y falta de datos; fallo previo o criterio de mejora explícito.
- [x] Ajustar instrucciones/ejemplos y la libertad de redacción de herramientas, conservando el resumen inequívoco y confirmación de compra. Hacer preguntas sólo cuando aporten información necesaria.
- [x] Verificar semántica y efectos, no una única frase memorizada. Cubrir las cinco clases de Review Focus.

### Task 3: comprobación y entrega
**Files:** evaluación reproducible en backend/tests o backend/evals; reporte de ejecución fuera del repo, que sintetizará el orquestador.
- [x] Ejecutar smoke local acotado con qwen3:8b y capturar transcripciones/latencia/live-fallback. Fijar criterios antes de observar resultados, registrar fallos y límites; no repetir para elegir sólo éxitos.
- [x] Ejecutar una suite final con PV_REQUIRE_DB=1. Si cambió UX/contrato, ejecutar build/E2E pertinentes; si no, conservar evidencia previa y justificar.
- [x] Devolver archivos, decisiones, resultados, límites, modelo/esfuerzo efectivos, skills leídas y comandos sin secretos. Pausar para revisión cruzada; el orquestador conserva publicación y cierre.


Cierre 27/10: 174/0/0 sin exclusiones, revisión cruzada aprobada. Resultado y límites vigentes en docs/reviews/2026-10-26-conversacion-natural.md. La autorización posterior del usuario cubre commit, publicación e integración a main por el orquestador.
