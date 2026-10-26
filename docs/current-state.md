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

**Pendientes / riesgos aceptados:**
- Remoto **no tocado ni verificado**: si tiene 0002, algoritmo de firma del JWKS, `enable_confirmations`, y si `grant app_user to postgres` funciona en hosted (probar con `supabase db push --dry-run`). Requiere login nexumartis y autorización expresa.
- `set local role` no es barrera ante inyección SQL en el backend (`reset role` vuelve a postgres). Hoy todo el SQL es parametrizado; a futuro, rol de login propio para el panel.
- El trigger crea negocio también para altas sin confirmar: con la anon key cualquiera puede crear negocios vacíos. Sin rate limit ni limpieza.
- Cambio menor en sandbox: `PATCH` con `stage` inválido sobre id inexistente devuelve 400 (antes 404); get/update/actividad ahora en una sola transacción.
- Configurar `SUPABASE_URL` en `backend/.env` y `VITE_SUPABASE_URL`/`VITE_SUPABASE_ANON_KEY` en `web/.env` para usar el panel.

## Codebase Memory

La revisión indexada y sus metadatos de **materialIA** se consultan en [.codebase-memory/artifact.json](../.codebase-memory/artifact.json), cuyo campo `commit` identifica la revisión fuente efectiva. El cierre incluye persistencia del grafo mediante Codebase Memory después del commit documental. El commit que empaqueta el manifiesto y el grafo puede ser posterior al commit fuente indexado: esa diferencia no acredita cambios de producto ni que el índice contenga su propia actualización. Verificar el manifiesto al retomar y refrescar el índice si cambiaron las fuentes.

Git y estos Markdown siguen siendo la fuente de verdad. Un nuevo agente debe recibir la indicación de leer este archivo; el MCP no impone esa lectura automáticamente.
