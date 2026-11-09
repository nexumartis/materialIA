# Skills de negocio compartidas

17 skills usadas por Mati con Claude, incorporadas el 09/11/2026 para continuar con Tomi.
Los `SKILL.md`, referencias, ejemplos y scripts coinciden con los repositorios contrastados
en las revisiones del [manifiesto](manifest.json); sólo se agregó a cada skill la licencia MIT
de su origen. Los hashes normalizan CRLF a LF para funcionar entre Windows, macOS y Linux.

| Origen | Skills | Licencia |
|---|---|---|
| [Jake Schincariol / founder-skill](https://github.com/Jakeschincariol/founder-skill) | Las 11 `founder-*` | MIT, copyright 2026 Jake Schincariol |
| [Ferdinando Bons / startup-skill](https://github.com/ferdinandobons/startup-skill) | Las 4 `startup-*` | MIT, copyright 2026 Ferdinando Bons |
| [Corey Haines / marketingskills](https://github.com/coreyhaines31/marketingskills) | `customer-research`, `sales-enablement` | MIT, copyright 2025 Corey Haines |

Cada carpeta incluye `LICENSE`. Conservar esa atribución al copiarla. Los scripts auxiliares
se distribuyen como parte de las skills; su copia no ejecuta nada ni instala dependencias.

Seguir [ONBOARDING](../../docs/ONBOARDING.md) y [SKILLS](../../docs/SKILLS.md). En Claude Code,
comprobar las skills del proyecto y resolver duplicados personales por su ruta efectiva.
Otros agentes pueden leer cada `SKILL.md` por ruta; no se acredita descubrimiento automático
en Codex. No se incluyen configuraciones, hooks, cuentas ni permisos de los equipos de origen.

Para negocio, comenzar por [founder/README.md](../../founder/README.md), no por una ejecución
completa de todos los packs. Respetar el workflow del proyecto: alcance acotado, revisión y
economía de contexto. Los paneles de agentes producen simulaciones, no compradores reales.
