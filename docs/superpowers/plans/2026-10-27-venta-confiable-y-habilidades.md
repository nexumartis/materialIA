# Venta confiable y habilidades Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Root orquesta; Claude Code implementa; Codex personal revisa en contexto fresco. Sin subagentes extra por defecto, para cuidar tokens.

**Goal:** corregir acciones/cantidades/referentes del vendedor y cargar tres guías comerciales en el planner, conservando los controles existentes.
**Architecture:** reutilizar `_Turn`, el dominio de pedidos y el planner LLM; correcciones compartidas cuando afectan acciones; fallback acotado. Guías internas estáticas/versionadas, sin framework ni migración.
**Tech Stack:** Python/FastAPI/Postgres, pytest, Ollama Cloud existente, Playwright.
**Spec:** ../specs/2026-10-27-venta-confiable-y-habilidades-design.md.

## Constraints / ownership

- Base de7abbe, rama fix/sales-intent-and-playbooks. Claude: `backend/app/agent/sales_agent.py`, `llm_sales.py`, nuevo `sales_skills.py`, `backend/app/domain/orders.py`, tests y harness de aceptación. Sólo ampliar a opportunities si el registro humano lo exige y dejarlo justificado.
- Root: spec, plan y estado/reporte. Codex: revisión de fuentes/evidencia, sin edición. Ningún ejecutor hace commit/push/merge ni cambia nube, perfiles demo o .env del usuario.
- DB de tests local 55436, contenedor materialia-test-20261026, 0001–0007. Credencial en el mecanismo local de coordinación, no imprimir. Demo del usuario 4173/8077 y DB 54322 no se usan para pytest/reset.
- Modelos: Claude opus/high solicitados (registrar efectivo); Codex gpt-6.1-sol/high. Ponytail full, Superpowers TDD/debugging/verificación, pruebas Playwright por UI. Usar sólo skills pertinentes.

## Review Focus

- Consulta/negativa y «dale» tras humano no mutan ni con planner guionado que propone una acción errónea.
- Cantidad absoluta vs suma/resta; números de precio, medida y opción no son cantidades. Ambigüedad no decide por azar.
- Numeración corresponde a última lista real; marca/nombre mantienen referente y filtros; dos pedidos en un mensaje no se pisan.
- Mutaciones y confirmaciones son atómicas/idempotentes donde ya lo eran; no romper stock, políticas, dry-run, tokens ni pagos.
- Guías se cargan al planner sin otorgar herramientas desactivadas; su presencia no sustituye validación ni prueba live.

### Task 1: acciones y cantidades

**Files:** sales_agent.py, orders.py, llm_sales.py; tests nuevos de conversación y de dominio reutilizando shop/Scripted.
**Interfaces:** conservar handle_sales_message/SalesReply y endpoints actuales. El dominio necesita una operación de fijar cantidad de línea de carrito abierto con chequeo de tenant, stock y total, reutilizando transacciones actuales; nombre/firma finales a criterio del owner y documentados en su informe. Actualizar todos sus llamadores. El planner y fallback comparten la validación de acciones cuando corresponde, sin duplicar un segundo servidor de reglas.

- [x] Escribir regresiones de la spec: dale tras humano, consulta con negación, 500 g/40 cm/precio, fijar/restar/eliminar y cotización sin mutación. Confirmar fallos previos relevantes.
- [x] Implementar consentimiento contextual y operaciones mínimas; exponer a herramientas existentes o una herramienta de cantidad si hace falta. Declarar límites heurísticos.
- [x] Probar una acción mal propuesta por Scripted y una válida; cantidades/totales reales y otras líneas inalteradas. Conservar confirmación explícita y pruebas de pedidos/pagos.

### Task 2: selección y recorrido del usuario

**Files:** sales_agent.py y tests; ampliar fixture local del test para marcas reales, sin editar seed compartido.
**Interfaces:** resolver producto contra opciones/foco vigentes antes de búsqueda; conservar ID de producto independientemente de texto de marca. Acción breve sólo con propuesta de agregar vigente. La guía no debe inventar una opción fuera de rango.

- [x] Reproducir consulta amplia, «la nro3», selección por marca ambigua/unívoca y el recorrido literal del usuario con pedido compuesto.
- [x] Corregir el mínimo: listado de catálogo real, resolución de opciones/referentes, acción flexible más exploración canilla, humano y cierre pertinentes. Mantener estructura y caps actuales de resultados.
- [x] Verificar carrito flexible+mate $96.700 y no duplicación al recibir una posición que ya no existe en la nueva lista. Probar cambio de tipo/filtros y múltiples líneas.

### Task 3: guías comerciales y cierre

**Files:** nuevo sales_skills.py, llm_sales.py, tests pertinentes; harness Playwright local de aceptación si aporta reproducción.
**Interfaces:** tres guías asesorar_catalogo/gestionar_carrito/cerrar_o_derivar, renderizadas en el prompt actual. Reducir repeticiones al incorporarlas; máximo orientativo 600 palabras entre las tres. Sin plugins arbitrarios, UI nueva ni dependencias. Nombres/tipos internos restantes a criterio del owner.

- [x] Integrar guías con instrucciones, herramientas y límites; comprobar su uso por el planner y los controles de herramientas desactivadas. Evitar pruebas que sólo espejen texto literal.
- [x] Ejecutar suite completa con PV_REQUIRE_DB=1, sin exclusiones. Registrar conteos, fallos y warnings; contrastar con baseline actual, no con los 208 informados por otro entorno.
- [x] Levantar servicios aislados de aceptación (8078/4174), recorrer por Playwright el caso del usuario y cantidades/humano; contrastar carrito con UI/servidor. Para live usar gpt-oss:120b-cloud ya autorizado, máximo operativo de 30 llamadas nuevas, sin repetir para elegir éxitos. Si no alcanza o falla, informar límite antes de ampliar.
- [x] Entregar diff, hashes de archivos, evidencia roja/verde, suite, transcripciones, latencia, modo/fallback y limitaciones. Detener servicios de aceptación y pausar edición para Codex personal. No cambiar la demo del usuario antes de revisión.

Root consolida revisión/correcciones y actualiza continuidad. La publicación y la integración de este corte se acuerdan al cerrar; no heredarlas de la instrucción de cerrar PR13 de la etapa anterior.

Cierre28/10: Matías autorizó publicación a Git y pase a Tomi. Claude implementó el corte inicial; Codex personal corrigió R1; revisión final de Claude aprobada. Backend269 passed; aceptación funcional de6 mensajes cumplida, T1–T5 live y T6 mock; 42 llamadas cloud acumuladas. La aceptación íntegramente live queda pendiente, ver reporte de cierre. No hubo ampliación de scope ni migraciones.
