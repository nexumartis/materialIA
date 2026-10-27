# Agentes personalizados por negocio: estructura, configuración y memoria

Investigación del 27/10/2026 para decidir cómo evoluciona el agente de ventas. Compara patrones
publicados (fuentes al final) con lo que ya existe en el repo. Las fuentes de proveedores (blogs)
se toman como patrones, no como estándares.

## 1. Qué recomienda la práctica actual

**Empezar simple y agregar complejidad sólo cuando hace falta.** Anthropic distingue *workflows*
(caminos de código predefinidos) de *agentes* (el modelo decide qué herramienta usar) y recomienda
la solución más simple posible; desaconseja usar frameworks por defecto porque esconden los prompts
y las respuestas. [1]

**Ingeniería de contexto** [2]:
- Prompt de sistema a la "altura correcta": ni lógica rígida ni consignas vagas; el mínimo que
  define el comportamiento, en secciones; crecer a partir de fallas observadas.
- Herramientas pocas, claras, sin superposición, que devuelven información compacta.
- Recuperación *just-in-time*: el agente guarda identificadores y trae los datos con herramientas
  cuando los necesita, en vez de cargar todo en el prompt.
- Conversaciones largas: *compactación* (resumir y seguir), *notas estructuradas* que el agente
  escribe fuera del contexto y relee, y subagentes para tareas acotadas.

**Configuración por cliente (multi-tenant)** [3][4]:
- Una configuración por tenant guardada en base (prompt, modelo, herramientas habilitadas,
  límites), con **versión activa**, historial y caché corta.
- Prompt en **capas**: base de la plataforma → plantilla del rubro → ajustes del cliente →
  contexto de la tarea.
- Aislamiento: prompts, base de conocimiento (vectores) y memoria de conversaciones separados por
  tenant; nunca compartidos.

**Memoria** [5][6][7]:

| Tipo | Qué guarda | Alcance | Ejemplo para nosotros |
|---|---|---|---|
| Corto plazo | la conversación en curso | un hilo | `messages` + `agent_state` |
| Largo plazo **semántica** | hechos/preferencias destiladas | entre conversaciones | "prefiere grifería negra, compra para obra en Rosario" |
| Largo plazo **episódica** | eventos pasados | entre conversaciones | pedidos anteriores, reclamos |
| **Procedimental** | reglas y forma de trabajar | el agente | perfil del negocio, reglas, prompts |

- LangGraph separa memoria del hilo (checkpoints) de un *store* de largo plazo en JSON por
  *namespace* (p. ej. `[tenant, cliente]`); la memoria semántica puede ser **un perfil que se
  actualiza** o **una colección de recuerdos**. Escribir memoria "en caliente" (durante la
  respuesta) agrega latencia; "en segundo plano" (un proceso aparte) la evita. [6]
- Letta usa *memory blocks*: bloques con etiqueta y límite que van siempre en el prompt; pueden
  ser de **sólo lectura** (políticas de la empresa) y compartirse entre agentes. [7]
- Mem0/LangMem extraen memorias de las conversaciones como servicio externo. [5]

**Productos comerciales** (Intercom Fin, plataformas de WhatsApp) [8][9]: el negocio configura
tono y largo de respuestas, *guidance* condicional ("si preguntan por medios de pago, usá el
artículo X"), fuentes de conocimiento (artículos, PDF, fragmentos), acciones contra sistemas
(pedidos, CRM, links de pago) y reglas de derivación a humanos por tema o complejidad.

## 2. Dónde estamos

| Pieza | Hoy en el repo | Coincide con la práctica |
|---|---|---|
| Capas de prompt | reglas fijas en código → plantilla por rubro → `agent_profiles` → contexto del turno | sí |
| Configuración por negocio | fila en `agent_profiles` (Postgres, RLS) | sí, **sin versiones** |
| Herramientas | 7 fijas, iguales para todos | parcial: no se habilitan por negocio |
| Conocimiento del negocio | FAQ y textos dentro del prompt | sirve para poco texto; **sin RAG** |
| Memoria corta | últimos 16 mensajes + `agent_state` (IDs, confirmación pendiente) | sí, **sin compactación** |
| Memoria larga del cliente | no existe: cada conversación arranca de cero | falta |
| Memoria episódica | pedidos/oportunidades en la base, pero el agente sólo ve los de la conversación | parcial |
| Procedimental | perfil y reglas los edita el negocio; el agente no se reescribe | sí (a propósito) |
| Guardrails | el servidor controla tenant, precios, stock, pagos, confirmación | sí, más estricto que la media |
| Framework | código propio, sin LangGraph/Mem0 | coincide con [1] |

## 3. Recomendación (por orden) — implementada el 27/10/2026 en `feat/agent-architecture`

Estado: las seis piezas están implementadas (migración `0007_agent_architecture.sql`, ver
`docs/current-state.md`). Notas de implementación entre corchetes.

1. **Versionar el perfil del agente.** Tabla `agent_profile_versions` (versión, autor, fecha,
   contenido); "Guardar" crea versión nueva; poder volver atrás; registrar qué versión respondió
   cada mensaje (auditoría y comparación). [`agent_profile_versions`, `messages.profile_version`;
   restaurar crea una versión nueva y no cambia el link.]
2. **Reglas del negocio que el código hace cumplir.** Separar lo que es *estilo* (prompt) de lo que
   es *política* (código): compra mínima, zonas de envío, productos sólo con persona, horario de
   atención. Herramientas habilitables por negocio. [compra mínima, zonas de envío y categorías
   sólo-persona en el dominio de pedidos; 6 herramientas apagables, que ni se le ofrecen al modelo.]
3. **Memoria del cliente** (requiere identificarlo: teléfono en WhatsApp o sesión del comprador de
   PR #12):
   - tabla `customer_memory` por `(tenant, cliente)` con un **perfil semántico** corto
     (preferencias, zona, para qué compra) — el patrón "perfil que se actualiza";
   - se escribe **en segundo plano** (worker) al cerrar la conversación, no en caliente;
   - entra al prompt como bloque de sólo lectura con límite de tamaño;
   - herramienta `historial_cliente` para pedidos anteriores (episódica) *just-in-time*;
   - el cliente puede pedir que se borre; retención definida.
   [web: clave aleatoria del navegador, hash SHA-256(negocio+clave); "Olvidarme" en la tienda;
   destilado por el worker con IA o reglas, saneado de montos/teléfonos/emails. Retención: pendiente.]
4. **Compactación** de conversaciones largas: al pasar N mensajes, resumir lo anterior en
   `agent_state.summary` (sin precios ni stock: sólo intención e IDs). [columnas propias
   `conversations.summary/summary_until` para que el worker no pise el estado del turno.]
5. **Base de conocimiento por negocio (RAG)** cuando haya documentos largos (fichas técnicas,
   manuales): `pgvector` en Supabase con RLS por tenant y herramienta `buscar_info_negocio`.
6. **Evaluaciones por negocio**: casos de prueba por rubro/perfil corridos antes de activar una
   versión nueva del perfil (el repo ya tiene `backend/evals/`). [casos por negocio, corren sobre
   el borrador en conversaciones descartables; "Guardar" no activa una versión que los falle.]

Mantener: código propio y simple (sin framework), un solo agente con herramientas, y el servidor
como dueño de dinero, stock y confirmaciones.

## Fuentes

1. Anthropic — Building effective agents: https://www.anthropic.com/research/building-effective-agents
2. Anthropic — Effective context engineering for AI agents: https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
3. CallSphere — Building multi-tenant AI agent platforms (blog de proveedor): https://callsphere.ai/blog/building-multi-tenant-ai-agent-platforms-architecture
4. Designing multi-tenant agent isolation (blog): https://besthub.dev/articles/designing-multi-tenant-agent-isolation-for-verifiable-tenant-boundaries-9f83f2e27e84
5. Long-term memory con LangGraph + Mem0 (tutorial): https://www.centron.de/en/tutorial/build-ai-agents-with-long-term-memory-using-langgraph-mem0/
6. LangGraph — Memory: https://docs.langchain.com/oss/python/langgraph/memory
7. Letta — Memory blocks: https://docs.letta.com/guides/agents/memory-blocks
8. Intercom Fin — guidance (artículo de ayuda): https://intercom.help/fin4all/en/articles/10644329-provide-fin-ai-agent-with-specific-guidance
9. Patrón WhatsApp + RAG (plantilla de proveedor): https://hub.ability.ai/use-cases/ai-driven-automated-whatsapp-customer-service-and-support-with-rag-knowledge-base-integration
