# Conversación natural y coherente — alcance autorizado

El usuario aprobó empezar por conversación natural/coherencia, manteniendo al orquestador fuera del código de producto y revisión cruzada Claude Code/Codex personal. Base `6290f60`, posterior a la PR #12; corte separado. Ponytail full: mínimo cambio completo, reutilizar contratos y tests existentes.

## Resultado

El agente atiende con tono del negocio, entiende referencias/correcciones y recomienda con datos reales. Las frases se adaptan al contexto; pedidos y acciones permanecen controlados por el servidor. Se presenta honestamente como asistente virtual. No se promete indistinguibilidad humana.

Caso del video: después de PAID + «gracias», reconoce el cierre sin pedir pagar otra vez ni ofrecer envíos por email/WhatsApp que no ejecuta. El video no identifica commit; reproducir la causa en la base actual con un planner guionado contradictorio y evaluar con modelo local real.

## Comportamiento

1. Estado actual de pedido/carrito prevalece sobre frases viejas del historial. Un pago sólo lo confirma el proveedor verificado. PAID/PREPARING/DISPATCHED no vuelven a pendiente por texto del modelo; PENDING_PAYMENT + «ya pagué» tampoco pasa a pagado. Elegir aclaración ante pedidos ambiguos.
2. Recomendaciones justificadas por ficha, características y presupuesto disponibles. Conservar preferencias pertinentes dentro de la conversación, respetar correcciones (negra → cromo, cantidad, presupuesto) y limpiar filtros cuando cambia el tipo de búsqueda. Una categoría/compatibilidad que no consta se pregunta o deriva, sin inventar.
3. Redacción breve y cercana según perfil, sin recitar instrucciones ni hacer preguntas comerciales al cerrar un agradecimiento. Ejemplos variados orientan el estilo, no fijan respuestas literales para cada intención. Carrito puede expresarse naturalmente; resumen de compra conserva productos/cantidades/total inequívocos y consentimiento explícito antes de crear pedido/pago.
4. Las capacidades habilitadas limitan lo que afirma haber hecho: sin herramienta de envío no dice «ya te envié» o promete mandar mensajes; sin regla aprobada no concede descuentos. Distinguir política del negocio («hacemos envíos») de una acción del agente («te envié un email»).
5. Preservar importes, disponibilidad, números de pedido/links, aislamiento, idempotencia y privacidad ya probados. Un control rechazado devuelve un respaldo pertinente, sin convertir un «gracias» en búsqueda de productos. Si se reintenta redacción, como máximo una vez y sin repetir herramientas/mutaciones. No basar toda la garantía en una lista creciente de frases prohibidas.

## Aceptación y evidencia

- Regresiones con DB local requerida y planners guionados: PAID+gracias+respuesta contradictoria; pago pendiente declarado pagado; promesa de canal inexistente; descuento no autorizado; datos de precio/stock falsos; cambiar preferencia/cantidad; pregunta de comparación; entrega desconocida; modelo caído; compra/confirmación existentes. Cubrir afirmaciones, negaciones legítimas y estados con atención humana.
- Mini conjunto de conversaciones variadas con criterios: coherencia con estado, fidelidad al catálogo, pertinencia de preguntas, recomendaciones y naturalidad. Evitar asserts de una redacción exacta salvo los campos imprescindibles de confirmación.
- Smoke cualitativo real con Ollama **qwen3:8b local disponible**, sin cambiar defaults/versionar credenciales. Registrar respuestas, modo live/fallback, modelo y latencias; máximo 20 llamadas al modelo en total. No representa validación de gpt-oss:120b del video. Si el runtime no permite una comprobación útil, declarar ese límite; no equiparar tests guionados a calidad del modelo real.
- Una suite backend final, y navegador/build existentes si cambian contratos/UX. No repetir checks sin cambios o fallo concreto.

## Límites y responsables

Sin entrenamiento de pesos, memoria entre clientes, KB automática, nuevas tablas o proveedor nuevo. El circuito de aprendizaje aprobado por el dueño es posterior. OCR/constancia de compra se registran como otro corte, sin mezclarlos con esta entrega.

Claude Code posee `backend/app/agent/llm_sales.py`, `sales_agent.py`, helper acotado si lo necesita y tests/evaluación correspondientes. Codex personal revisa en contexto separado. Orquestador posee spec/plan/estado/reportes. Cambios de pagos, API pública, SQL o frontend requieren demostrar una dependencia concreta antes de ampliar ownership. No reset remoto, WhatsApp, cobros reales ni contactos. La publicación se coordina después de revisión bajo la autorización vigente; el ejecutor no hace commits.

Decisiones técnicas menores quedan al ejecutor. Priorizar contexto de estado/capacidades, una política de respuesta acotada y reutilización del planner/tool loop, sin agregar un equipo de agentes al runtime.
