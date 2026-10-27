# Flujo de trabajo compartido

Acuerdo autorizado el **25/10/2026**. Para el estado técnico y las propuestas todavía pendientes, empezar por [current-state.md](current-state.md).

## Modalidades y ownership

| Rol | Responsabilidad |
|---|---|
| Los dos socios | Acordar producto, prioridades, alcance y aceptación final. |
| Codex orquestador | Ayudar a pensar, revisar contexto, preparar especificaciones y briefs, coordinar y mantener continuidad. No implementa código de producto. |
| Implementador | Ejecutar una entrega acotada con un owner por archivo y evidencia de validación. |
| Revisor | Evaluar el diff y la evidencia en un contexto separado, según la modalidad. |

**Modalidad coordinada:** el Codex orquestador mantiene el rol de documentación y coordinación. Claude Code y Codex personal pueden implementar: el código de Claude lo revisa Codex personal y el de Codex personal lo revisa Claude.

**Modalidad del socio con Claude Code:** Claude puede planificar e implementar tareas delimitadas. Otra sesión o un subagente en modo lectura revisa el diff en un contexto fresco. La separación de contexto no acredita diversidad de modelo ni de cuenta. Esta modalidad permite trabajar con su propia cuenta y herramientas; no requiere instalar Codex.

En ambas modalidades, la revisión cubre el alcance, las invariantes y la evidencia de validación. Si no hay un contexto revisor independiente disponible, preparar diff, revisión base y evidencia y derivarlos al otro socio antes de dar el trabajo por revisado. Mientras tanto pueden avanzar tareas independientes.

Asignar un único owner por archivo antes de editar. Dividir tareas paralelas por archivos y dependencias; serializar cualquier cambio que comparta ownership. Los subagentes reciben un alcance delimitado, entregables y validación; su trabajo vuelve al owner y pasa por la revisión correspondiente. Evitar varias revisiones equivalentes del mismo diff.

## De una idea a una entrega

1. **Contexto:** leer el estado, inspeccionar el código relevante y contrastar planes aportados por los socios. Terminar con hechos, dudas y alcance separados.
2. **Especificación:** acordar comportamiento, casos de aceptación, límites y decisiones abiertas con los socios. Un plan técnico desarrolla una especificación; no sustituye esas decisiones.
3. **Brief:** el responsable de coordinación de la modalidad asigna una entrega acotada a un implementador y un revisor. El brief queda listo cuando contiene los campos de la sección siguiente.
4. **Implementación:** el owner aplica las skills seleccionadas y valida el comportamiento cambiado. Para interfaces, incluir comprobación en navegador; para datos o permisos, comprobar aislamiento y casos de acceso denegado.
5. **Revisión:** entregar al revisor de la modalidad el diff exacto o revisión base, criterio de aceptación y evidencia. Agrupar las correcciones y volver a revisar lo modificado; resolver los hallazgos pendientes antes de declarar la entrega lista.
6. **Cierre:** seguir el protocolo de la sección final y presentar el resultado a los socios para aceptación. Publicar o integrar con la instrucción correspondiente.

## Contenido del brief

- Objetivo, comportamiento esperado y criterio de aceptación comprobable.
- Modalidad, revisión base, dependencias, archivos permitidos, owner y revisor por archivos y exclusiones de alcance.
- Ejecutor, contexto de revisión y sus límites; subagentes y límites si aportan trabajo independiente.
- Skills concretas por fase, disponibles en el entorno del ejecutor.
- Modelo y esfuerzo solicitados y efectivos, verificados al iniciar; herramientas y acceso necesarios. Si la configuración requerida no está disponible, informar la diferencia y acordar el ajuste antes de continuar con esa parte, sin sustituciones silenciosas.
- Pruebas o comprobaciones proporcionadas al riesgo del cambio, evidencia esperada y documentación a actualizar.

Los briefs usan roles y referencias del proyecto, sin rutas privadas, credenciales, identidades personales ni modelos fijos heredados de otra tarea. Mantener instrucciones breves y agrupar correcciones para cuidar contexto y cuota.

## Economía de contexto

Preferencia expresa del usuario, 26/10/2026: cuidar tokens del orquestador y de los ejecutores para prolongar la sesión, conservando alcance, validación y revisión.

- El orquestador entrega un brief corto con objetivo, revisión base, archivos, aceptación y referencias al contexto existente.
- Leer las invariantes al iniciar; después consultar sólo fuentes y skills pertinentes. Usar búsquedas y fragmentos concretos; releer cuando cambie la fuente o falte información.
- Implementador y revisor comparten la revisión base, el diff y la evidencia. El revisor trabaja en contexto separado sobre ese alcance; ampliar sólo ante dependencias o hallazgos.
- Ejecutar comprobaciones proporcionadas al cambio. Repetirlas cuando haya modificaciones, fallos o dudas pendientes. Guardar logs extensos y devolver resultado, evidencia y pendientes en pocas líneas.
- Usar subagentes para trabajo independiente que justifique su contexto. Agrupar hallazgos y correcciones en una devolución.
- Cerrar con decisiones y pendientes breves en el estado; enlazar el detalle. Mantener la configuración acordada de modelo y esfuerzo y registrar la efectiva.

## Estado y Codebase Memory

Git y los Markdown versionados son la fuente de verdad. [current-state.md](current-state.md) conserva la revisión inspeccionada, cambios locales relevantes, decisiones, evidencia con fecha, pendientes y próximo paso. Una observación de una base remota debe distinguirse del esquema versionado y revalidarse antes de actuar sobre ella. Las credenciales quedan en el mecanismo de secretos del entorno.

Codebase Memory es opcional. Si está disponible, su manifiesto `artifact.json` registra la revisión indexada, fecha, resultado y límites; exportar y persistir el grafo sólo si la herramienta lo permite. Referir el manifiesto desde el estado, sin copiar hashes del grafo a un Markdown que forme parte del mismo índice. Si la indexación no se ejecutó o falló, dejar ese estado explícito y mantener la continuidad en los Markdown.

El MCP es un índice derivado: no instala skills, concede acceso a servicios ni genera automáticamente el resumen de negocio y decisiones. Puede facilitar búsquedas; no garantiza ahorro de contexto. Estas reglas exigen la primera lectura en los entornos que cargan `AGENTS.md` o `CLAUDE.md`; Codebase Memory no hace que un agente externo lea un archivo automáticamente. Al incorporar el entorno del socio, comprobar esa carga y enviar la primera lectura en el brief inicial.

## Protocolo de cierre

1. Actualizar `current-state.md` y las decisiones con resultado, evidencia, pendientes y próximo paso.
2. Revisar el diff de código y documentación según la modalidad; distinguir lo revisado de los cambios posteriores.
3. Crear el commit y publicar únicamente dentro de la autorización vigente, registrando la revisión entregada.
4. Si se usa Codebase Memory, indexar la revisión cerrada, persistir/exportar el artefacto mediante las capacidades disponibles y registrar esa revisión en `artifact.json`.
5. Versionar el manifiesto y artefacto cuando esté autorizado. El commit que los incorpora puede ser posterior al commit indexado: conservar esa diferencia explícita, sin afirmar que el índice contiene su propia actualización.
