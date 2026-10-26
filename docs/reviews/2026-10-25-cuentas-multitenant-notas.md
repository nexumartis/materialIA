# Cuentas multitenant — notas de revisión inicial

**Notas del orquestador, 26/10/2026 ART**, sobre el plan fechado el 25/10/2026 y el código de referencia `72d6ed3d4b75090fc737d8a9d3204f6530eaca6b`.

Se leyeron el plan y el código; no se ejecutaron producto ni pruebas. Estas notas no constituyen una auditoría independiente ni acreditan una vulnerabilidad implementada.
Los riesgos condicionales describen interpretaciones del diseño propuesto que deben resolverse antes de implementarlo.

Documento revisado: [plan original](../superpowers/plans/2026-10-25-cuentas-multitenant.md), conservado intacto.
El diseño que referencia en su línea 11, `docs/superpowers/specs/2026-10-25-cuentas-multitenant-design.md`, sigue sin localizarse.

## 1. Grants y autorización de memberships

**Referencia:** Task 1, líneas 37–40 y 68: la lista de tablas y el `grant select,insert,update,delete on <tablas de negocio>` son ambiguos.
Si ese grant incluye `memberships` y la política sólo verifica el `user_id` propio, un usuario podría modificar su propio `tenant_id` o rol manteniendo el mismo `user_id`.
**Corrección conceptual:** enumerar grants por tabla/operación y reservar el aprovisionamiento de membresías a un camino autorizado; impedir la autoadjudicación de empresa o permisos.
Diseñar también el acceso con RLS/rol a `tenants` para `/app/me` y a `audit_events` para auditoría: ambas faltan en la lista de Task 1 y existen en [0001_init.sql](../../supabase/migrations/0001_init.sql), líneas 11 y 121.
Revisar la composición con políticas previas: las permisivas se combinan mediante OR y `WITH CHECK` controla la fila resultante de INSERT/UPDATE. Fuente: [PostgreSQL, CREATE POLICY](https://www.postgresql.org/docs/current/sql-createpolicy.html).

## 2. Verificación JWT según el proyecto real

**Referencia:** Task 2, líneas 112 y 118, fija HS256 y un secreto compartido para `jwt.decode`.
No se consultó la configuración real de firma del proyecto; esa suposición sigue sin verificar.
**Corrección conceptual:** elegir el verificador según la configuración real; usar JWKS cuando la firma sea asimétrica y validar firma, emisor, audiencia, `sub` con UUID válido y expiración.
La documentación distingue claves asimétricas y secretas; el endpoint JWKS no devuelve claves si no se usan las primeras. Fuente: [Supabase, JWT](https://supabase.com/docs/guides/auth/jwts).

## 3. Reutilizar dominio bajo una transacción autenticada completa

**Referencia:** Task 3, líneas 137–138, permite reutilizar dominio con `user_tx` o cursor inyectado.
Hoy [opportunities.py](../../backend/app/domain/opportunities.py) abre `tenant_tx` en `get_opportunity` (156–157), `update_opportunity` (171–212), `log_activity` (217–219) y `audit` (253–255); el update llama a `get_opportunity` y `log_activity`.
[db.py](../../backend/app/db.py), líneas 51–65, obtiene una conexión del pool y fija contexto local de tenant; cambiar sólo la ruta HTTP no acredita que las operaciones anidadas usen el rol autenticado.
**Corrección conceptual:** definir un contrato de cursor/transacción por request que abarque lecturas, escrituras, actividad y auditoría, conservando el sandbox por su camino previsto.
Probar reutilización del pool entre usuarios, rollback y limpieza de rol/contexto; comprobar que ningún helper escape a una conexión con permisos mayores.

## 4. Pruebas que demuestren aislamiento

**Referencia:** Task 3, línea 147: `all(o for o in r.json())` sólo comprueba la veracidad de los elementos y también devuelve verdadero para una lista vacía.
Ese assert no identifica oportunidades de A ni excluye las de B, aunque el comentario diga lo contrario.
**Corrección conceptual:** exigir resultado no vacío e identidades exactas esperadas de A, ausencia de las de B y denegaciones de lectura/escritura cruzadas, además de casos sin autenticación o membresía.
[conftest.py](../../backend/tests/conftest.py), líneas 33–37, omite pruebas si Postgres no está accesible: una suite SKIPPED por falta de base no demuestra aislamiento ni se reporta como PASSED.

## 5. Contratos de API y casos funcionales de sesión

**Referencia:** Task 5, líneas 203, 214–215, propone cambiar `api.ts` a `/app/*` y verificar build/capturas, pero el plan no define `/app/chat`.
[api.ts](../../web/src/lib/api.ts), líneas 90–110, comparte cliente para `/health`, oportunidades, actividad y `/sandbox/chat`; [main.py](../../backend/app/main.py), líneas 55–80, conserva health y chat sandbox.
**Corrección conceptual:** delimitar qué llamadas migran al panel autenticado y preservar los contratos de health, sandbox y chat previstos; evitar un cambio genérico de prefijo que apunte a endpoints inexistentes.
Agregar casos funcionales de confirmación de correo, sesión vencida y errores de acceso/red, además de build y revisión visual.

## Estado y siguiente revisión

La **revisión técnica independiente del plan sigue pendiente**. Estas notas son insumos para reducir/corregir el plan al alcance de cuentas y aislamiento aprobado, con catálogo separado.
Los comandos de reset y commits incluidos en el plan no otorgan autorización automática: rige el [acuerdo del repositorio](../../AGENTS.md).
Resolver estas decisiones y la referencia de diseño ausente antes de preparar la especificación técnica y los briefs de implementación.
