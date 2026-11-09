# Lanzamiento: materialIA

> **Antecedente del 05/11/2026.** Para alcance, precio y próximos pasos leer [README](README.md) y la investigación del 09/11. Cifras, garantías, marca y calendario de este análisis no son acuerdos vigentes ni validación con clientes.

> Arranque: semana del **09/11/2026**. T = Tomás, M = Matías. Las líneas de éxito son **metas propuestas por nosotros**, no datos: el panel fue simulado (15% de compra, casi todos los «no» por WhatsApp). Si el piloto real da otra cosa, manda el piloto.

## 1. El test barato: 10 pilotos en zona sur del GBA
**Qué:** 10 ferreterías/sanitarios de una sola zona (Quilmes, Bernal, Lanús, Avellaneda, Lomas) con la oferta de `pricing.md`: **2 meses gratis y te lo dejamos andando nosotros con tu planilla**, a cambio de datos y testimonio. Desde el mes 3, **$35.000/mes + IVA**. No se gasta en anuncios hasta pasar la compuerta.

**Requisitos antes del primer piloto** (de `ops.md`): deploy decidido y andando, SMTP propio (Resend + dominio), términos y privacidad, cobro con cuenta MP de cada comercio.

**Líneas de éxito (escritas antes de empezar):**
| métrica | cómo se mide | meta | alarma |
|---|---|---|---|
| Conversaciones → pago verificado | panel: pedidos pagados verificados / conversaciones | ≥ 5% | < 2% |
| Días hasta la 1.ª venta verificada | fecha de alta vs. primer pago verificado | mediana ≤ 14 | > 30 o ninguna |
| Costo de IA por comercio | uso registrado × precio del modelo (`LLM_PRICE_*`) | ≤ USD 10/mes (supuesto del CFO) | > USD 20 |
| Retención al mes 3 | comercios que pagan el primer mes de $35.000 | ≥ 6 de 10 | ≤ 3 |
| **Link web vs. WhatsApp** | conversaciones que entran por link/widget ÷ (esas + consultas de producto por WhatsApp que el dueño anota en una semana de muestra con planilla de palotes) | ≥ 30% | < 15% |

El link se difunde **sólo por canales del dueño**: bio de Instagram, su web, cartel con QR en el mostrador y, si él quiere, el mensaje automático de su propio WhatsApp Business. Nosotros no mandamos nada a clientes finales.

Comparación con el panel: 15% simulado dijo que compraría. Si al mes 3 pagan menos de 2 de 10, el panel sobreestimó: volver a `/founder-offer` o `/founder-pricing`.

## 2. Cuenta regresiva
| semana | tarea | dueño | fecha límite |
|---|---|---|---|
| **09–13/11** | ★ Elegir hosting y deployar (staging = producción del piloto) | T | 13/11 |
| | ★ Resend + dominio + SMTP en Supabase Auth | T | 12/11 |
| | Reunión con contador: tipo de sociedad, ARCA, factura | M | 13/11 |
| | Lista de 30 comercios de zona sur (Google Maps, recorrida) | M | 13/11 |
| | Tablero de métricas del piloto (las 5 de arriba) | T | 13/11 |
| **16–20/11** | ★ Términos, privacidad y acuerdo de piloto (borrador con abogado) | M | 18/11 |
| | Visitas en persona: 30 comercios → 10 que firman | M + T | 20/11 |
| | Revisar inscripción AAIP (Ley 25.326) | M | 20/11 |
| | Topes de IA por comercio y alertas de caída | T | 20/11 |
| **23–27/11** | Soft open: 2 pilotos (rutina A de `ops.md`) | T + M | 27/11 |
| | Corregir lo que salga de esos 2 | T | 27/11 |
| **30/11–04/12** | ★ Altas de los 8 restantes (4 por socio) | T + M | 04/12 |
| | Cartel con QR y texto para bio, por comercio | M | 04/12 |
| **07/12** | **Día de lanzamiento: los 10 en vivo, contando** | ambos | 07/12 |

★ = camino crítico: si se atrasa, se corre el lanzamiento. Ojo con feriados (08/12 y los de noviembre: confirmar calendario oficial) y con que diciembre–enero puede bajar la actividad de los comercios. Marketing y marca: aplicar `marketing.md` y `brand.md` si ya existen; el piloto no los necesita para arrancar.

## 3. Run sheet del 07/12
| hora | qué | quién |
|---|---|---|
| 8:30 | Chequeo: API, worker, panel, webhooks MP, mail de acceso, cuota de IA | T |
| 9:00 | Llamada corta a cada dueño: el link está en su bio/web, el QR en el mostrador | M |
| 9:00–13:00 | Monitoreo en vivo de conversaciones y derivaciones | T |
| 10:00 | Primera visita: ver una venta real o simulada con el dueño | M |
| 13:00 | Repaso: errores del agente, precios mal cargados | ambos |
| 14:00–18:00 | Soporte y correcciones (sin deploys grandes) | T |
| 18:00 | Registrar números del día y primer palote de WhatsApp | M |
| guardia | T esa noche |

**Si algo se rompe** (riesgos de `ops.md`): caída → agente en derivación y aviso al dueño en 30 min; precio incorrecto → frenar el producto y corregir la planilla; pago dudoso → nunca marcar pagado sin verificación.

## 4. Los primeros 30 días
**Semanal:** conversaciones, % a pago verificado, comercios con al menos una venta, costo de IA por comercio, share link vs. WhatsApp, horas de soporte por comercio (`ops.md` supone 1 h/semana).

- **Día 7 (14/12):** ¿los 10 tienen el link visible? ¿Cuántas conversaciones por comercio? Si un comercio tiene 0 conversaciones, el problema es el canal, no el agente.
- **Día 14 (21/12):** ¿cuántos tienen la primera venta verificada? ¿Algún precio inventado o vencido llegó al cliente? (debe ser 0). ¿Costo de IA dentro de USD 10?
- **Día 30 (06/01/2027):** primera lectura de la compuerta. ¿Qué dicen los dueños sobre pagar $35.000 en febrero?
- **Mes 3 (≈ febrero 2027):** primer cobro. Retención real y decisión final.

## 5. Compuerta de decisión (día 30 y confirmación al mes 3)
- **WhatsApp primero** si el share link/WhatsApp queda **< 15%** en al menos 7 de 10 comercios, **o** si 6 o más dueños dicen que no pagan sin WhatsApp. Entonces se prioriza el canal WhatsApp: **requiere que los dos socios cambien por escrito el alcance del proyecto** (hoy «NO WhatsApp» es regla del proyecto), cuenta y verificación en Meta Business, y rehacer costos con el CFO. No se suman comercios hasta tenerlo.
- **Seguir con web y abrir otra zona** si el share es ≥ 30%, la conversión ≥ 5% y al mes 3 pagan 6 o más.
- **Zona gris** (entre ambos): ajustar la oferta (QR en mostrador, mensaje de bienvenida, precio $25.000 vs. $35.000) y medir 30 días más.

Siguiente: `/founder-plan`.
