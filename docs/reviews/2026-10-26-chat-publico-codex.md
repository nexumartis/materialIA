# Revisión cruzada R3 — chat público

Registro del orquestador: Codex personal CLI 0.163.0; gpt-6.1-sol y high confirmados en cabecera. Revisión estática del paquete fijado contra 3d0a97a. Informe del revisor a continuación.

**Aprobado el corte R2/R2c para el alcance demo. No encuentro bloqueos P1/P2 concretos en el paquete congelado contra `3d0a97a`.** No quedan correcciones bloqueantes para devolver a Claude en esta pasada.

R3: revisión cruzada estática, sin comandos, ediciones ni ejecución de pruebas. Modelo/esfuerzo solicitados: `gpt-6.1-sol/high`; la cabecera efectiva no está expuesta aquí y debe registrarla el orquestador. Apliqué las instrucciones adjuntas de code-review-and-quality y Supabase, respetando la restricción de trabajar sobre fuentes y evidencia incluidas.

La revisión del estado y las invariantes confirma que siguen vigentes los límites documentados. Los conteos iniciales de R2 —131 pruebas— y R2b —134— son históricos; el resultado final informado para backend es R2c, con 136.

La aceptación queda respaldada por estos cambios:

- **Pertenencia y acceso alternativo.** El servidor emite un token aleatorio por conversación, persiste únicamente su hash y exige UUID, tenant y token para GET/POST públicos. Las comprobaciones preceden al acceso al agente y a los datos. Para C/D, el sandbox rechaza conversaciones protegidas y sus pedidos/oportunidades; también excluye estas últimas del listado SQL. Las pruebas comprueban que los intentos rechazados no modifican el carrito, el pedido ni la oportunidad. No identifico otra ruta incluida que permita usar solamente la UUID para alcanzar esos datos.
- **Recuperación por tienda.** La referencia `{id, token}` se guarda con una clave por slug. El montaje recupera el hilo y el cambio A–B–A crea instancias separadas de la vista. Una referencia rechazada con 404 se descarta. El harness cubre recarga después del checkout y recuperación independiente entre tiendas.
- **Respuestas pendientes.** Reiniciar y desmontar incrementan la generación. Los resultados y errores de POST se comprueban antes de guardar credenciales o modificar la vista; los GET comprueban generación y secuencia antes de actualizarla o borrar la referencia. Esto cierra tanto la restauración tardía como el borrado tardío de credenciales de una conversación nueva.
- **Compra y pago simulado.** Conservan su recorrido sin habilitar administración sandbox. El checkout mediante su enlace mantiene el comportamiento demo conocido; esa excepción no abre lectura de mensajes ni avance operativo de pedidos protegidos.

La evidencia **de Claude**, no ejecutada por mí, informa **136 pruebas aprobadas, sin fallos ni saltos**, build correcto y **36 comprobaciones Chrome aprobadas**, incluida la vista de 390 px. Las regresiones backend y el harness ahora están incorporados al repositorio, con preparación, variables y requisitos documentados. Es razonable conservar build/E2E de R2b para R2c dado el frontend congelado y el cambio posterior limitado al gate, configuración y pruebas backend. Los logs externos no forman parte de lo inspeccionado aquí.

Esta aprobación cubre la demo y este diff. No acredita producción, Auth completo, Supabase remoto ni pagos reales. Permanecen declarados el token accesible desde JavaScript, la ausencia de vencimiento/revocación y los datos anteriores a 0006. La migración remota y cualquier publicación requieren su autorización correspondiente.
