# Estado actual — materialIA / Presupuesto Vivo

**Primera lectura en cada tarea.** Actualizar al cerrar una entrega, distinguiendo observaciones, acuerdos y propuestas. Flujo acordado: [AI-WORKFLOW.md](AI-WORKFLOW.md). Invariantes de negocio: [CLAUDE.md](../CLAUDE.md).

## Observaciones del 25/10/2026

Revisión de referencia: `origin/main` en `72d6ed3d4b75090fc737d8a9d3204f6530eaca6b`. Este registro resume la revisión previa del repositorio y del entorno compartido; no demuestra el estado de una revisión posterior.

- MVP para convertir consultas de mamparas/cerramientos en oportunidades trazables, con precios deterministas y revisión humana. Backend Python/FastAPI, interfaz React en `web/` y Supabase Postgres. El seed contiene datos sintéticos.
- Las últimas seis PR estaban integradas; no había PR abierta. La aplicación tiene chat, gestión de oportunidades y seguimiento.
- La interfaz usa `/sandbox/chat`. El agente nuevo está expuesto por `/sandbox/agent/chat` y `/sandbox/agent/confirm`; su circuito todavía está separado del chat visible.
- El código tiene [0001_init.sql](../supabase/migrations/0001_init.sql) y [0002_activity.sql](../supabase/migrations/0002_activity.sql). En la observación previa de Supabase cloud figuraba sólo la migración inicial y faltaba `opportunity_activity`. Revalidar ese remoto antes de planificar o aplicar cambios; esta documentación no sincroniza la base.
- No hay login, registro ni panel de administración de usuarios. La selección A/B pertenece al sandbox; no es autorización mediante usuarios y membresías reales.
- No se ejecutaron la aplicación ni las pruebas durante esta revisión. Los conteos de tests y resultados de [TAREA01_REPORTE.md](TAREA01_REPORTE.md), fechado el 22/10/2026, son evidencia histórica, no validación actual. Consultar ese reporte cuando haga falta ese contexto.
- Se verificaron los accesos de Claude Code y de Codex personal para los actores designados, sin iniciar tareas de implementación. Cada brief deberá verificar su configuración efectiva de modelo y esfuerzo.
- El nicho y los precios del servicio siguen siendo hipótesis de negocio por validar. El README conserva una puesta en marcha histórica y ahora enlaza esta guía de estado y el onboarding; sus instrucciones requieren revalidación al ejecutar la aplicación.

## Acuerdo operativo autorizado

Los dos socios acuerdan producto, prioridades y aceptación. En la modalidad coordinada, el Codex orquestador ayuda a pensar y documenta; Claude Code y Codex personal implementan con revisión cruzada. El socio con sólo Claude Code puede planificar e implementar entregas acotadas y revisar en un contexto fresco, sin que eso acredite diversidad de modelo o cuenta. Si no dispone de ese contexto, deriva diff y evidencia al otro socio antes de dar el trabajo por revisado. Cada archivo tiene un único owner. Los detalles están en [AI-WORKFLOW.md](AI-WORKFLOW.md); la preparación del entorno, en [ONBOARDING.md](ONBOARDING.md).

El usuario autorizó publicar en GitHub esta entrega documental y compartir lo necesario para el entorno del socio. La entrega está aprobada para publicación en la rama `docs/shared-ai-workflow` y su PR de documentación; las referencias de GitHub acreditan el resultado de la publicación. El merge requiere su autorización correspondiente. El código de producto, las pruebas, el esquema y las dependencias permanecen intactos.

## Decisión de producto aprobada

Empezar con registro del propietario, login/logout y acceso a su negocio; preparar la relación para varias personas por empresa. Invitaciones, detalle de roles y gestión del equipo quedan para una entrega posterior. Usuario es persona y negocio es empresa; el acceso a varios negocios por persona queda por definir. Ver [decisión de alcance](decisions/2026-10-25-cuentas-alcance.md).

## Revisión de la documentación operativa

Claude Code con **Sonnet 5.5** completó una revisión independiente en lectura de `AGENTS.md`, `CLAUDE.md`, `docs/AI-WORKFLOW.md`, `docs/SKILLS.md` y `docs/current-state.md`. Se aceptó y corrigió H1: `AGENTS.md` exige ahora leer las invariantes de negocio y seguridad en toda tarea, porque también regulan secretos y envíos. El mapa de `CLAUDE.md` apunta al directorio completo de migraciones.

El **26/10/2026**, Claude Code con **Sonnet 5.5** aprobó la revisión final de la entrega documental, incluidas ambas modalidades, el onboarding, la decisión de alcance y las notas iniciales del plan. Ver [informe de revisión final](reviews/2026-10-26-documentacion.md). Esta aprobación corresponde a la documentación compartida; el plan de cuentas conserva pendiente su aprobación técnica. El orquestador verificó además el hash del plan original y la integridad de los 193 archivos del kit local, sin diferencias.

## Plan recibido del socio, pendiente de revisión

El **25/10/2026** el usuario entregó el archivo del socio, recibido como `2026-10-25-cuentas-multitenant.md`. Se conserva una copia íntegra en [docs/superpowers/plans/2026-10-25-cuentas-multitenant.md](superpowers/plans/2026-10-25-cuentas-multitenant.md), sin cambios de contenido.

- Tamaño: **15.577 bytes**. SHA-256 del original y de la copia: `967f83078943c047d115a7ca787e89d0857c308c5dae0a696f2687004ec4cec8`.
- El orquestador leyó el plan. Sigue sin aprobación técnica y su recepción no autoriza ejecutar sus instrucciones. Falta contrastar su seguridad y contratos con el código, el esquema y el alcance aprobado de cuentas y aislamiento.
- Referencia una especificación `docs/superpowers/specs/2026-10-25-cuentas-multitenant-design.md`, todavía no localizada. Falta recibirla o aclarar esa referencia antes de considerar completo el contexto de diseño.

Las [notas iniciales del orquestador, registradas el 26/10/2026](reviews/2026-10-25-cuentas-multitenant-notas.md), reúnen cinco puntos a corregir o verificar; no sustituyen la revisión técnica independiente pendiente ni acreditan pruebas ejecutadas.

## Próximo paso propuesto, pendiente de revisión

1. Obtener o aclarar la especificación de diseño referenciada y completar la revisión técnica del plan.
2. Reducir y corregir el plan al alcance aprobado de cuentas y aislamiento, separando catálogo; contrastar identidad, acceso por empresa, seguridad y contratos con el código y el esquema vigentes. Revalidar el desfase observado de migraciones.
3. Resolver las decisiones técnicas pendientes y producir la especificación, criterios de aceptación y briefs para los implementadores y revisores de cada modalidad.

## Entrega: cuentas del propietario + aislamiento (26/10/2026, rama `feat/accounts-multitenant`)

Modalidad del socio con Claude Code. Implementa el [plan v2](superpowers/plans/2026-10-26-cuentas-multitenant-v2.md), que corrige el v1 con las cinco notas del orquestador y se ciñe al alcance aprobado (sin catálogo, invitaciones ni roles). La especificación referenciada está en [specs/2026-10-25-cuentas-multitenant-design.md](superpowers/specs/2026-10-25-cuentas-multitenant-design.md); el plan v2 reemplaza sus secciones de catálogo.

**Hecho (local):**
- Migración [0003_accounts.sql](../supabase/migrations/0003_accounts.sql): `memberships`, rol `app_user` sin BYPASSRLS, grants mínimos (sin escritura en `memberships`/`tenants`), políticas permisivas + restrictivas `to app_user` (la GUC del sandbox no amplía acceso), RLS en `tenants`/`audit_events` (antes expuestas a anon/authenticated), FK compuesta de actividad, trigger de provisioning en el signup.
- Backend: JWT verificado por JWKS (local firma ES256; HS256/`none` rechazados), `user_tx` (una transacción por request como `app_user`), `/app/me` y `/app/opportunities*`. 401 sin sesión válida, 403 sin negocio, 503 si el JWKS no responde. Sandbox y agente sin cambios de contrato.
- Front: registro, login/logout, panel por sesión; el chat demo A/B sigue sin cuenta.

**Evidencia:** `PV_REQUIRE_DB=1 pytest -q` → **84 passed, 0 skipped** contra Postgres local con 0001–0003. Migración reaplicada dos veces sin error. Signup real contra Supabase Auth local → `/app/me` 200 con el negocio; token adulterado → 401. `npm run build` sin errores. Recorrido en Chrome (registro → panel vacío → logout → login con clave errónea muestra error → login → panel; chat demo sin sesión) completo.

**Revisión:** subagente en contexto fresco y sólo lectura (mismo modelo y cuenta: no acredita diversidad). Sin bloqueantes; se corrigieron 6 hallazgos (503 en caída del JWKS, test de que `user_tx` corre como `app_user`, FK compuesta, EXECUTE de anon/authenticated, recarga del panel en cada refresh de token, test vacuo). Pendiente revisión cruzada del otro socio.

**Verificación del remoto (26/10/2026, sólo lectura, PR #8 ya mergeado en `main` @ `e69358b`):**
- `supabase migration list --linked`: remoto tiene sólo **0001**; faltan **0002** y **0003**. `db push --dry-run` aplicaría ambas (el dry-run no ejecuta SQL: no valida `grant app_user to postgres` en hosted; en local `postgres` tampoco es superusuario y funciona).
- JWKS remoto: **ES256 (EC)** → compatible con la verificación del backend sin cambios.
- Auth remoto: `mailer_autoconfirm=false` (exige confirmar el correo) y signup habilitado. El signup del front manda `emailRedirectTo` al panel; agregar esa URL a las Redirect URLs del proyecto.
- Aplicar 0002+0003 al remoto requiere autorización expresa (`supabase db push`).

**Pendientes / riesgos aceptados:**
- `set local role` no es barrera ante inyección SQL en el backend (`reset role` vuelve a postgres). Hoy todo el SQL es parametrizado; a futuro, rol de login propio para el panel.
- El trigger crea negocio también para altas sin confirmar: con la anon key cualquiera puede crear negocios vacíos. Sin rate limit ni limpieza.
- Cambio menor en sandbox: `PATCH` con `stage` inválido sobre id inexistente devuelve 400 (antes 404); get/update/actividad ahora en una sola transacción.
- Configurar `SUPABASE_URL` en `backend/.env` y `VITE_SUPABASE_URL`/`VITE_SUPABASE_ANON_KEY` en `web/.env` para usar el panel.

## Codebase Memory

La revisión indexada y sus metadatos de **materialIA** se consultan en [.codebase-memory/artifact.json](../.codebase-memory/artifact.json), cuyo campo `commit` identifica la revisión fuente efectiva. El cierre incluye persistencia del grafo mediante Codebase Memory después del commit documental. El commit que empaqueta el manifiesto y el grafo puede ser posterior al commit fuente indexado: esa diferencia no acredita cambios de producto ni que el índice contenga su propia actualización. Verificar el manifiesto al retomar y refrescar el índice si cambiaron las fuentes.

Git y estos Markdown siguen siendo la fuente de verdad. Un nuevo agente debe recibir la indicación de leer este archivo; el MCP no impone esa lectura automáticamente.

## Entrega: agente de ventas end-to-end — base de comercio (26/10/2026, rama `feat/sales-agent-commerce`)

Modalidad del socio con Claude Code. Objetivo pedido por el usuario: un vendedor por chat que consulta stock y precio reales, arma carrito y pedido, manda el link de Mercado Pago, confirma el pago verificado y responde el estado; canal final WhatsApp/Instagram. Diseño, desvíos respecto de la especificación del socio y etapas: [specs/2026-10-26-agente-ventas-design.md](superpowers/specs/2026-10-26-agente-ventas-design.md).

**Hecho (local, sin tocar el remoto):**
- Migración [0004_commerce.sql](../supabase/migrations/0004_commerce.sql): stock por producto con `reserved <= on_hand` en la base, historial de movimientos, pedidos (el carrito es un pedido `CART_OPEN`, uno por conversación), líneas, pagos, avisos de pago y "servidor" del proveedor simulado; FK compuestas por tenant; RLS y sin acceso para anon/authenticated. Seed: empresa demo **C (grifería)** con marcas, precios y stock ficticios.
- Stock concurrente: apartado con un `UPDATE` condicional, todo o nada y en orden de `item_id`; se aparta al confirmar la compra y vence a los `RESERVATION_MINUTES`; el pago verificado lo convierte en venta una sola vez; pago tardío se re-aparta o queda para devolución humana.
- Pagos: interfaz con proveedor `simulated` (default, mismo camino de webhook firmado → consulta del pago → aplicación idempotente) y adaptador `mercadopago` (Checkout Pro por REST, firma `x-signature`). Un pedido pasa a `PAID` sólo con el pago aprobado consultado al proveedor por el monto y moneda exactos; "ya pagué" no cambia nada; pago duplicado o monto distinto ⇒ revisión humana.
- Agente de ventas (`/sandbox/sales/chat`, empresa C) con planner determinista (sin LLM): búsqueda con presupuesto, color y ambiente, referencias ("la segunda"), carrito, resumen + "sí" antes de cobrar, link de pago, estado del pedido, agotado ⇒ alternativas reales, productos a pedido ⇒ persona. CRM: el pedido crea/avanza la oportunidad de la conversación.
- Worker `python -m app.worker` (libera reservas vencidas, una transacción por pedido). Front: sección **Agente de ventas** (`#/venta`) con chat, carrito, pedidos y link al checkout simulado.

**Evidencia:** `PV_REQUIRE_DB=1 pytest -q` → **125 passed** contra Postgres local con 0001–0004 (84 previos + 41 nuevos); las pruebas de concurrencia (20 compras simultáneas de la última unidad ⇒ 1 gana; checkouts cruzados sin deadlock; vencimientos en paralelo con compras) pasaron en 10–15 corridas repetidas. Migración 0004 reaplicada dos veces sin error. `npm run build` sin errores. Recorrido en Chrome del escenario A hasta el link de pago; pago aprobado en el checkout simulado ⇒ pedido `PAID`, stock 6 → 5 y aviso de pago confirmado en la conversación.

**Revisión:** subagente en contexto fresco (lectura). Sin caminos de sobreventa. Corregidos: vencimientos en lote con riesgo de deadlock, pago duplicado aceptado en silencio, nuevo link tras un rechazo, agente que describía mal pedidos con revisión pendiente, recomendación "con stock" sin stock, confirmación de un total distinto al resumido, simulado habilitado con Mercado Pago configurado, auditoría de avisos falsos. Re-revisión de las correcciones: aprobada; sus dos observaciones menores (revisión pendiente que no se limpiaba al pagar, pago correcto bloqueado tras uno con monto distinto) también se corrigieron y tienen prueba.

**Límites conocidos / pendientes:**
- Mercado Pago real **no probado**: requiere `MP_ACCESS_TOKEN`/`MP_WEBHOOK_SECRET` de prueba y una URL pública (túnel). El adaptador sólo se probó contra un transporte HTTP falso; la firma sigue la documentación pública sin vector oficial.
- Comprensión por reglas (modo `mock`): cubre los escenarios, no toda la variedad del lenguaje. Siguiente etapa: planner con LLM sobre las mismas herramientas.
- Endpoints `/sandbox/*` sin autenticación (incluye `orders/{id}/status` y `maintenance/expire-reservations`): sólo para la demo; el avance operativo y la vista de pedidos pasan al panel autenticado en la siguiente etapa.
- Sin envíos/tracking reales (el agente lo dice), sin reposición de stock al reintegrar, un depósito por empresa, variantes como SKU propios.
- WhatsApp/Instagram y mensajes a clientes reales siguen fuera de alcance por CLAUDE.md hasta que los dos socios lo cambien.
- Migraciones 0002–0004 sin aplicar en el Supabase remoto.

**Cómo probarlo:** `supabase db reset` (o aplicar 0004 + seed), backend en 8077 (`PAYMENT_PROVIDER=simulated` por defecto), `npm run dev` en `web/`, abrir `#/venta` y seguir "¿tenés canillas negras para cocina?" → "¿cuál por menos de 100 mil?" → "quiero la segunda" → "la compro" → "sí" → abrir el checkout de prueba y pagar → volver al chat y preguntar "¿ya salió mi pedido?".

### Misma rama, 26/10/2026 (tarde): se retira el producto anterior y el agente pasa a usar LLM

- **Retirado por pedido del usuario:** chat de cotización de mamparas (`/sandbox/chat`, `/sandbox/agent/*`, `orchestrator`, `llm_adapter`, `tool_agent`, `pricing`, skills YAML), empresas demo A/B, UI `legacy/` y su diagrama, y sus pruebas. Quedan cuentas, panel de oportunidades (CRM), catálogo/importación y el agente de ventas. Seed: C (grifería) y D (ferretería, segunda empresa para aislamiento).
- **Planner con LLM** ([llm_sales.py](../backend/app/agent/llm_sales.py)): con `LLM_PROVIDER=ollama` el modelo lee la conversación y el contexto (última lista, carrito, último pedido) y elige herramientas; el servidor ejecuta. Controles: el modelo no puede crear pedidos ni links (el "sí" se procesa de forma determinista), lo que cambia el carrito o pide confirmación llega al cliente tal cual, y una respuesta con precios/cantidades/pedidos/links que no salieron de una herramienta se descarta. Si el modelo falla, responde el planner por reglas.
- **Evidencia:** `PV_REQUIRE_DB=1 pytest -q` → **117 passed** (incluye pruebas del planner LLM con un modelo guionado). Conversación real contra `gpt-oss:120b` (Ollama Cloud): ~1,6–3 s por mensaje; entendió "1", "pico extarible", "no quiero sumar nada más" y "sacame la de dos llaves" recordando el turno anterior.
- **Pendiente:** revisión en contexto fresco de este último tramo (retiro + planner LLM) antes del PR.
- **Mensajes interactivos** (misma rama): tarjetas de producto con foto (ilustraciones propias en `backend/app/static/products`), detalle al tocar, botones de respuesta y botón de pago; el contenido se guarda en `messages.payload` y se traduce a imagen/lista/botones de WhatsApp (ver §10 del diseño). Cuenta de demo **local** `demo@canillas.local` vinculada a la empresa C (creada en el Supabase local, no versionada). `pytest` → **119 passed**.

## Entrega: cada negocio arma su agente (26/10/2026, rama `feat/business-setup`)

Decisiones del usuario: CRM propio del panel, catálogo por CSV + edición, "cómo habla" con plantilla por rubro + formulario. Diseño: §11 de [specs/2026-10-26-agente-ventas-design.md](superpowers/specs/2026-10-26-agente-ventas-design.md).

- **Supabase remoto:** con autorización del usuario se aplicaron **0002, 0003 y 0004** (`supabase db push`; verificado con `supabase migration list`). El seed **no** se cargó en el remoto: la CLI sólo actualizó el hash del archivo; el remoto conserva datos sintéticos viejos de A/B. Falta cargar C/D (SQL editor del dashboard o `DATABASE_URL` remoto válido) y aplicar **0005**.
- **Migración 0005:** `agent_profiles` (rubro, link público único, vendedor, tono, saludo, FAQ, reglas, envíos, horarios, medios de pago) y acceso del panel (`app_user`, permisiva + restrictiva) a catálogo, precios, stock, pedidos y perfil.
- **Panel:** **Mi agente** (plantilla por rubro, formulario, link de la tienda), **Catálogo** (CSV con validación por fila, plantilla descargable, edición de precio/stock/estado; el stock nunca baja de lo apartado), **Pedidos** (avance preparación/despacho/entrega, alertas de revisión).
- **Tienda pública** `#/tienda/<slug>`: el servidor resuelve el negocio por el slug; el agente usa el perfil (nombre, tono, FAQ, reglas) con IA y por reglas; lo que no está cargado lo deriva a una persona.
- **Evidencia:** `PV_REQUIRE_DB=1 pytest -q` → **127 passed** (aislamiento del panel por RLS en catálogo/stock/pedidos/perfil, importación CSV, link único, tienda pública). Migración 0005 reaplicada dos veces. `npm run build` sin errores. Chrome: login con la cuenta demo → Mi agente, Catálogo y Pedidos; tienda pública en 390 px con tarjetas verticales.
- **Pendiente:** revisión en contexto fresco de esta rama; Mercado Pago por negocio; CRM externos; WhatsApp.
