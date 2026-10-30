# Google Sheets como catálogo vivo — revisión y correcciones

**Rama:** `feat/catalogo-google-sheets`. **Implementó:** Claude Code (sesión de Tomi). **Diseño:** [spec](../superpowers/specs/2026-10-30-catalogo-google-sheets-design.md). **Estado:** sin revisión de Mati. Migración **0011**: aplicada en la base local y en la de pruebas, no en la nube.

## Revisión en contexto fresco (Claude, 30/10/2026)

La hizo `/code-review high` sobre el diff sin commitear. Encontró 10 hallazgos y los 10 están corregidos con test en `backend/tests/test_catalog_sheet.py`:

| # | Hallazgo | Corrección |
|---|---|---|
| 1 | Una celda rara (`1e999`, un número gigante) tiraba toda la sincronización y el estado quedaba sin registrar | `_number` rechaza valores no finitos o fuera de rango; un `DataError` de la base es error de esa fila; `sync` registra cualquier falla inesperada como «No se pudo leer» |
| 2 | Una planilla privada redirige a `accounts.google.com`, y el control de dominios mostraba «sitio no permitido» | La redirección al login de Google se informa como planilla privada; el test simula esa redirección real |
| 3 | Stock por debajo de lo apartado descartaba también el precio y los datos de la fila | El stock va en su propio savepoint: el resto de la fila se aplica y el stock queda como aviso «stock no aplicado», que se reintenta en la próxima lectura |
| 4 | La sincronización manual y la del worker podían correr a la vez y duplicar precios | La importación bloquea la fuente (`for update`); la segunda espera y reaplica sin duplicar |
| 5 | Las sincronizaciones no dejaban auditoría | `catalog_sheet_synced` cuando hay altas o cambios reales de precio o stock |
| 6 | Reconectar o cambiar de planilla no la volvía la fuente del stock | `connect`/`disconnect` limpian `sheet_stock` |
| 7 | Se rechazaban links reales: publicados en la web (`/d/e/2PACX…`), multi-cuenta (`/u/0/`) o sin `https://` | Se aceptan, y los publicados usan su exportación `pub?output=csv` (`catalog_sources.published`) |
| 8 | Una planilla lenta podía frenar el worker | Descarga con tope total de 30 s; el worker reclama de a una, con presupuesto por vuelta de 45 s |
| 9 | Si fallaba la primera consulta, el panel mostraba «Conectar» aunque hubiera una planilla conectada | Muestra el error con «Reintentar» |
| 10 | Con error de lectura, el panel mostraba la lista de faltantes de la última lectura buena | La lista de faltantes se muestra sólo con estado OK |

## Evidencia (30/10/2026)

- **Backend:** suite completa en DB descartable (0001–0011 + seed); `test_catalog_sheet.py` con 33 casos, todos sin red (transporte HTTP falso).
- **Navegador**, en un entorno aislado:
  - `npm run e2e:planilla` **5/5**: incluye una consulta real a Google con un ID inexistente y el mensaje que ve el dueño;
  - `e2e:comprobantes` **17/17**, `e2e:bandeja` **11/11**, `e2e:asistente` **15/15**, `e2e` **36 PASS, 0 FAIL**.

## Límites

- No se probó con una planilla pública real con productos; lo cubre el transporte falso. Probarlo con una planilla de un negocio antes de un piloto.
- Sólo planillas públicas (por link o publicadas); sin OAuth.
- Los productos que salen de la planilla no se pausan solos.
