El carrito y la resolución final de referentes cumplen. **La aceptación live integral queda incompleta:** T6 usó fallback `mock` tras descartar dos respuestas del modelo.

Una conversación nueva; seis mensajes exactos, en orden y sin reenvíos. Latencias medidas desde Enviar hasta respuesta visible:

| T | Mensaje → respuesta visible compacta y tarjetas | Carrito lateral / total HTTP | Latencia |
|---|---|---|---|
| 1 | «¿Qué productos tenés?» → Grifería (6), Repuestos (2), Duchas (1), Sanitarios (1). Sin tarjetas. | Vacío / `null` | 7,944 s |
| 2 | «repuestos» → «Tengo estas opciones»: **1** flexible/par $6.800; **2** sifón $9.200. | Vacío / `null` | 7,801 s |
| 3 | «bien quiero un flexible y tambien quiero alguna canilla nueva negra o moderna que tengas» → Confirma 1 flexible. Tarjetas: **1** Aquaflux mate $89.900; **2** Hidrolar extraíble $129.000; **3** lavatorio Aquaflux $59.900; **4** dos llaves Aquaflux $74.500. Las últimas dos sin stock. | 1 flexible / $6.800 | 8,578 s |
| 4 | «quiero una monocomando negra mate» → «Hay 2 opciones que coinciden»: **1** Aquaflux mate; **2** Hidrolar extraíble, mismos precios. Pide elegir. | 1 flexible / $6.800 | 7,961 s |
| 5 | «si la aquaflux» → Confirma 1 Aquaflux mate y 1 flexible, $96.700. Sin tarjetas nuevas. | Ambos ×1 / $96.700 | 11,227 s |
| 6 | «la nro3» → «No tengo una opción 3 en la última lista: hay 2. ¿Cuál querés? Elegí entre 1 y 2.» Sin tarjetas nuevas. | Ambos ×1 / $96.700 | 4,475 s |

Eventos de página capturaron **6 POST de chat, todos HTTP 200**; `requires_human=false` en todos. `mode=live` en T1–T5; `mock` en T6. Sin tokens, cookies, headers ni IDs de acceso.

`trace`: T1 búsqueda de categorías; T2 búsqueda de dos productos; T3 agregado del flexible y búsqueda de cuatro; T4 **dos agregados rechazados por selección ambigua**; T5 agregado Aquaflux y consulta del carrito; T6 respuesta y reescritura descartadas por nombrar incorrectamente la opción 3.

Texto, tarjetas y productos HTTP coinciden. Carrito HTTP y lateral coinciden: **$6.800 + $89.900 = $96.700**, sin duplicados ni productos ajenos; sin pedidos ni pagos. La lista vigente tiene dos opciones; la histórica conserva cuatro.

[Captura final](assets/2026-10-28-venta-confiable.png).

Sólo Playwright MCP, UI4174/API8078; sin shell ni cambios de código. No amplié el límite42; su contador interno y DB55436 no son verificables desde estas respuestas. Markdown locales bloqueados. La code review estaba pendiente al capturar esta evidencia; luego [Claude aprobó el snapshot](2026-10-28-venta-confiable-claude.md).
