# Equipo: empleados con roles y notas internas — diseño

**Origen:** backlog priorizado del [roadmap](../../roadmap.md), ítem 6. Tomi pidió seguir sin ronda de preguntas («seguí con todo eso»), así que lo marcado **(decisión de Claude)** no fue acordado: revisarlo.

## Objetivo
- El dueño invita empleados por email desde **Equipo**, ve las invitaciones pendientes, las cancela y quita accesos.
- Hay dos roles:
  - `owner`: puede todo;
  - `staff`: atiende la bandeja (toma conversaciones, responde y deja notas), pedidos, oportunidades y comprobantes, y ve el catálogo.
- El equipo deja **notas internas** en cada conversación. No las ven el cliente ni el agente.
- La «asignación» es la toma de control que ya existe (`taken_by`, filtro «mías»).

## Reglas
- **Sólo el dueño** (devuelven 403 al staff):
  - plata: acreditar transferencias, cancelar pedidos y el registro mensual CSV;
  - catálogo: edición, importación y planilla;
  - configuración del agente: perfil, versiones, propuestas desde la web, conocimiento y evaluaciones;
  - costo de IA;
  - Equipo.

  (decisión de Claude)
- **Sin emails** (alcance: no se envía nada). El dueño le avisa al empleado, que se registra con ese email. **(decisión de Claude)**
- **Entrar exige el email confirmado:**
  - si el email ya está confirmado al registrarse, entra al negocio que lo invitó;
  - si no, no se crea nada hasta confirmarlo. Así nadie puede apropiarse de un email ajeno.

  Un invitado nunca recibe un negocio propio.
- **Una persona = un negocio**, porque la PK de `memberships` es `user_id`. Por eso no se puede invitar un email que ya tiene cuenta, y un email sólo puede estar invitado a un negocio a la vez. **(decisión de Claude)**
- **Quitar a un empleado:**
  - se borra su membresía, así que pierde el acceso en la siguiente request;
  - sus conversaciones tomadas vuelven al agente marcadas como derivadas, para que nadie quede sin atender.

  Al dueño no se lo puede quitar.
- **Notas:**
  - RLS por negocio y autor = usuario de la sesión;
  - entre 1 y 2000 caracteres;
  - el autor se guarda como email copiado al momento de escribir.

## Esquema (0016)
- Se reemplaza el check de `memberships.role` para que acepte `staff`. Es un `drop constraint` del check viejo: no borra datos.
- Tabla `team_invites`: sin acceso para `app_user`; sólo la usa el backend después de verificar al dueño.
- `handle_new_user` reescrito, más el trigger `on_auth_user_confirmed`.
- `app_member_role()`.
- Tabla `conversation_notes`.

## Pendiente
- Más roles (por ejemplo, sólo lectura), asignar una conversación a otra persona y avisos por persona.
