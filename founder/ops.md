# Operaciones: materialIA

> SaaS de 2 socios, no un local. Precios vistos el 05/11/2026; lo marcado **ESTIMACIÓN** no está verificado. No es consejo legal ni impositivo.

## 1. El ciclo de cada día (★ = lo ve el comercio o su cliente)
1. Revisar alertas de la noche: caídas, errores del agente, pagos con webhook pendiente.
2. Mirar derivaciones (`requires_human`) sin respuesta del dueño y avisarle por su canal (no se escribe al cliente final).
3. ★ El agente atiende 24 h: consulta → carrito → link de pago → pago verificado.
4. ★ Soporte a dueños (horario fijo, ver §3).
5. Revisar costo de IA del día por comercio contra su tope (`AI_DAILY_*`).
6. Cierre: anotar incidentes y pedidos con pago no conciliado.

## 2. Proveedores
| insumo | proveedor (alternativas) | precio público | nota |
|---|---|---|---|
| Base + Auth | [Supabase Pro](https://supabase.com/pricing) | USD 25/mes, incluye USD 10 de cómputo, 8 GB, tope de gasto activo | alternativa: Postgres propio (más trabajo) |
| Hosting API + worker + web | Cloud Run (el código ya contempla `TRUSTED_PROXY_HOPS`), Render, Fly | **ESTIMACIÓN USD 25/mes**; precio de Cloud Run no verificado ([página](https://cloud.google.com/run/pricing) no cargó) | sin elegir: el deploy está pendiente |
| IA (texto y fotos) | [Ollama Cloud](https://ollama.com/pricing) (alt.: API compatible OpenAI) | Pro USD 20/mes con USD 60 de uso; Max USD 100 con USD 300; por token, p. ej. gpt-oss:120b USD 0,15 / 0,60 por millón | **Pro admite 3 pedidos simultáneos para TODA la cuenta**; con 10 pilotos puede encolar. Max: 10 |
| Voz | [ElevenLabs](https://elevenlabs.io/pricing/api) | Starter USD 6/mes; extra TTS USD 0,08/1K caracteres, STT USD 0,22/h | apagado (`AUDIO_DEMO_ENABLED`); no entra al costo del piloto |
| Cobro | Mercado Pago Checkout Pro / link | **6,29% + IVA al instante, 1,49% + IVA a 35 días** según [un comparador de terceros](https://app.spomsolutions.com/herramientas/comisiones-mercado-pago-2026); la tabla oficial dio 403 | lo paga el comercio en sus ventas; para nuestra suscripción, confirmar en mercadopago.com.ar |
| Mail (Auth, avisos) | [Resend](https://resend.com/pricing) (alt.: SES, Postmark) | Free 3.000/mes y 100/día; Pro USD 20 por 50.000 | SMTP propio es **requisito** antes de pilotos: el SMTP por defecto de Supabase no es para producción |
| Ubicación de zonas | Georef (datos.gob.ar) | gratis, sin clave | sin SLA: si cae, la zona se elige a mano |
| Dominio | NIC Argentina / registrador .com | **ESTIMACIÓN USD 2/mes** | |

**Cambio en `numbers.json`** (el CFO tiene que volver a correr):
- Mail: USD 10 (estimado) → Resend Pro USD 20 (público) + dominio USD 2 (ESTIMACIÓN) = $31.900.
- Nuevo fijo: Ollama Cloud Pro USD 20 = $29.000. El costo de IA variable de USD 10 por comercio queda como ESTIMACIÓN; parte puede quedar cubierta por los USD 60 incluidos, así que suma un poco de más a propósito.
- Comisión de la suscripción: 6% → **7,6% ESTIMACIÓN** (6,29% + 21% de IVA, fuente de terceros) = $2.664.
- Resultado: fijos $87.000 → $133.400/mes; contribución $18.400 → $17.836; equilibrio ≈ 8 comercios.

## 3. Personas (los dos socios)
Sueldos: **no informados** (el CFO usa $0). Cargas, monotributo o relación de dependencia: con el contador.

| | Tomás | Matías |
|---|---|---|
| Lun–vie 9–13 | implementación de comercios nuevos | soporte + revisar derivaciones |
| Lun–vie 14–18 | producto / correcciones | implementación / visitas |
| Guardia fuera de horario | semanas pares | semanas impares |

- **Mes 1 (10 pilotos):** ~4 h por implementación + 1 h/semana de soporte por comercio (**ESTIMACIÓN**) ≈ 40 h de alta + 10 h/semana.
- **A 40 comercios:** ~40 h/semana sólo de soporte si se mantiene 1 h/comercio. Medirlo en el piloto: decide si hace falta un tercero.
- Regla: un cambio a `main` lo revisa el otro socio; nunca deployar en guardia sin avisar.

## 4. Rutinas
**A. Alta de un comercio (objetivo: 1 visita + 1 día)**
1. Pedir la planilla (Excel/Google Sheets) y revisar columnas: SKU, nombre, precio, stock, vigencia del precio.
2. Importar; lo sin precio o vencido queda `requires_human`, nunca se completa a ojo.
3. Configurar zonas (Georef), retiro, franjas de entrega y medios de pago (cuenta MP del comercio o transferencia).
4. Pegar el widget en su web o generar el link de tienda para Instagram/bio.
5. Prueba: 5 consultas reales del rubro, 1 foto de repuesto, 1 pedido pagado en modo prueba.
6. Explicarle al dueño cómo confirmar una transferencia (`confirm_transfer`) y qué es una derivación.
7. Anotar fecha de alta para medir días a la primera venta verificada.

**B. Soporte diario** — responder en 2 h hábiles; si el agente dijo algo falso, se registra como incidente (C).

**C. Incidente**
1. Clasificar: caída / precio o stock incorrecto / pago no conciliado / fuga de datos.
2. Caída: comunicar al dueño en 30 min; agente en modo derivación si la IA falla.
3. Precio incorrecto: frenar ese producto, corregir planilla, avisar al dueño qué pedidos tocó.
4. Pago: nunca marcar pagado sin verificación del proveedor o cotejo del dueño.
5. Datos: ver §6 (Ley 25.326). Post mortem escrito en 48 h.

**D. Chequeo semanal (lunes)**: planillas sincronizadas (fecha de última carga por comercio; >7 días = llamar), productos con precio vencido, costo de IA por comercio vs. tope, pedidos con reserva vencida, backups de Supabase.

## 5. Herramientas
Supabase + hosting + Ollama + Resend + MP (§2). Gestión: el propio panel (CRM) para los pilotos; facturación: la que indique el contador vía ARCA (gratis en su web); monitoreo de uptime con un plan gratuito (**a elegir**).

## 6. Legal a CHEQUEAR (no afirmado)
- [ ] Tipo de sociedad (SAS, SRL o monotributo de cada socio) e inscripción en ARCA (ex AFIP); factura a cada comercio. Confirmar con contador.
- [ ] Ley 25.326: inscribir la base en el [Registro Nacional de Bases de Datos de la AAIP](https://www.argentina.gob.ar/node/53779) (trámite a distancia con clave fiscal nivel 2+, según su [instructivo](https://www.argentina.gob.ar/sites/default/files/instructivo_tad_inscripcionymodificacion_basesprivadas_3.pdf)). Definir quién es responsable y quién encargado del tratamiento de los datos de los clientes finales (comercio vs. nosotros).
- [ ] Términos de servicio, política de privacidad y contrato de encargado con cada comercio. Abogado.
- [ ] Términos de Mercado Pago para plataformas que generan cobros por terceros (cada comercio con su cuenta).
- [ ] Meta Business (verificación del negocio, WhatsApp Business Platform) **sólo si** se decide WhatsApp.
- [ ] Ingresos Brutos según jurisdicción. Las normas cambian; confirmar todo con la autoridad o un profesional.

## 7. Riesgos
| # | riesgo | prob. | impacto | plan |
|---|---|---|---|---|
| 1 | Los compradores no salen de WhatsApp: el link no se usa | alta | alto | medirlo en el piloto; compuerta en `launch.md` |
| 2 | Planilla desactualizada → precio viejo | alta | alto | vigencia del precio + chequeo semanal + derivación |
| 3 | Costo de IA mayor al estimado / cola por concurrencia de Ollama | media | alto | topes diarios por comercio; subir a Max o modelo más barato |
| 4 | Un socio enfermo o de baja | media | alto | rutinas escritas; guardia alternada |
| 5 | Caída del hosting o de Supabase | media | alto | uptime + derivación; backups diarios |
| 6 | Pago mal conciliado (webhook perdido) | media | alto | reconciliación diaria; nunca marcar pagado a mano |
| 7 | Mails de acceso que no llegan (sin SMTP propio) | alta sin Resend | medio | Resend + dominio antes del piloto |
| 8 | Incidente de datos personales | baja | muy alto | aislamiento por tenant, plan §4C, consultar AAIP |
| 9 | Meta/Tiendanube lanzan algo parecido | media | alto | foco en rubro y zona; testimonios |
| 10 | Soporte no escala (1 h/comercio) | media | medio | medir horas reales; FAQ para dueños |

## Preguntas abiertas
Proveedor de hosting y su precio real; tarifa oficial de MP; sueldos; tipo de sociedad; costo real de IA por comercio.
