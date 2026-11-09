# Incorporar el entorno de un socio

Actualizado el **09/11/2026**. El repo comparte producto, decisiones, investigación y las 17 skills de negocio usadas por Mati con Claude. Cada socio conserva sus cuentas y secretos locales.

## Retomar el proyecto

1. Con el árbol de trabajo limpio, actualizar `main` con `git pull --ff-only origin main`. Si la entrega sigue en una PR, obtener la rama indicada allí; conservar los cambios propios al cambiar de rama.
2. Abrir Claude Code en la raíz del repo, donde están `CLAUDE.md`, `AGENTS.md`, `backend/` y `founder/`. Leer [current-state.md](current-state.md), las invariantes de [CLAUDE.md](../CLAUDE.md) y [AI-WORKFLOW.md](AI-WORKFLOW.md).
3. Para negocio, empezar por [founder/README.md](../founder/README.md), [PROGRESS.md](../founder/startup-design/PROGRESS.md) y las correcciones. La base de cuentas ya está implementada; el plan original de cuentas no es la próxima tarea.
4. Definir una tarea, owner, revisor y comprobación. Tomi puede usar otro contexto de Claude para revisar; registrar esa modalidad sin afirmar diversidad de modelo o cuenta.

## Skills compartidas

Las **17 skills de negocio** están completas en [`.claude/skills/`](../.claude/skills/README.md). Al obtener esta entrega no hace falta copiar archivos desde la PC de Mati ni ejecutar un instalador. Se incluyen referencias, scripts auxiliares y licencias; la importación no ejecuta esos scripts.

Según la [documentación oficial de Claude Code](https://code.claude.com/docs/en/skills), las skills del proyecto viven en `.claude/skills/<nombre>/SKILL.md`. Abrir `/` y comprobar `startup-design` y `customer-research`; si no aparecen, pedir a Claude que identifique las rutas cargadas. Una skill personal homónima puede prevalecer: comparar versiones y usar explícitamente la ruta del proyecto. Archivos presentes no acreditan carga efectiva.

El [manifiesto](../.claude/skills/manifest.json) registra procedencia e integridad. Codex u otra herramienta puede leer cada `SKILL.md` por ruta; este paquete no configura automáticamente otros clientes.

El core de ingeniería (Superpowers, Agent Skills, Matt Pocock, Ponytail, Impeccable y Taste Skill) conserva sus fuentes en [SKILLS.md](SKILLS.md). No se incluye ni instala entero aquí. Confirmar disponibilidad para cada brief. El kit local opcional del 25/10 (12 skills) sigue siendo un extra externo; no es necesario para continuar el trabajo de negocio de hoy.

## Qué queda local

Sesiones y perfiles de navegador, accesos de Claude/Codex, `.env` y tokens de Meta, ElevenLabs, Supabase y Mercado Pago. Configurarlos con los ejemplos del repo y el mecanismo de secretos propio. No copiar credenciales de otro socio ni publicarlas.

La restricción de Meta está documentada, pero no se comprobó de nuevo en esta entrega. La prueba real está en [whatsapp-pruebas.md](whatsapp-pruebas.md). Consultar ese estado antes de conectar un número, consumir créditos o desplegar.

## Prompt inicial para Claude Code

```text
Retomá materialIA. Leé docs/current-state.md, CLAUDE.md y AGENTS.md.
Seguí docs/AI-WORKFLOW.md, modalidad del socio con Claude Code.
Para negocio, leé founder/README.md y founder/startup-design/PROGRESS.md,
incluidas las correcciones de fuentes. Conservá lo ya investigado.
Las skills compartidas están en .claude/skills/; consultá docs/SKILLS.md
y cargá sólo la necesaria. Confirmá la ruta efectiva.
Distinguí hipótesis, entrevistas reales y simulaciones. Los precios anteriores
y calendarios de ejemplo no son acuerdos con clientes.
Primero resumí el estado y la próxima tarea; después prepará un brief acotado.
Revisá en un contexto separado y actualizá el estado al cerrar.
Publicá o modificá servicios externos sólo dentro de la autorización recibida.
```

## Memoria y cierre

Git, [current-state.md](current-state.md) y [founder/README.md](../founder/README.md) permiten continuar sin otra cuenta de IA. Codebase Memory es un índice de código opcional; no contiene toda la conversación ni reemplaza documentos de negocio. Comprobar su [manifiesto](../.codebase-memory/artifact.json) antes de usarlo. Si está viejo o falló su actualización, consultar las fuentes del repo y registrar el límite.

Seguir el cierre de [AI-WORKFLOW](AI-WORKFLOW.md#protocolo-de-cierre): estado → revisión → publicación autorizada → índice opcional con su revisión exacta. Publicar en una rama o PR no implica que ya esté en `main`.
