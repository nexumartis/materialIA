# Competidores: el vendedor por chat de la ferretería sin tienda online

> **Antecedente del 05/11/2026.** Para alcance, precio y próximos pasos leer [README](README.md) y la investigación del 09/11. Cifras, garantías, marca y calendario de este análisis no son acuerdos vigentes ni validación con clientes.

Segmento: dueño de ferretería, sanitarios o corralón en Argentina, sin tienda online, que hoy contesta chats a mano. Ítem comparable: un plan mensual de asistente de ventas por chat con IA, o lo que el dueño hace en su lugar. Fuentes públicas vistas el 05/11/2026; detalle y links en `competitors.csv`.

## Tabla (de más a menos directo)

| # | Nombre | Tipo | Precio del ítem comparable | Rating (n) |
|---|---|---|---|---|
| 1 | [notchatbot](https://www.tiendanube.com/tienda-aplicaciones-nube/notchatbot1) | Directo | «Planes desde USD 300/mes»; implementación con llamada | 5,0 (11) en la app store de Tiendanube |
| 2 | [Meta Business AI](https://www.cronista.com/infotechnology/it-business/asi-funciona-la-novedad-de-whatsapp-que-usan-las-pymes-para-vender-mas-sin-sumar-personal/) (en WhatsApp Business) | Directo, emergente | USD 2 por millón de tokens, unos USD 0,04–0,05 por conversación ([Enter.co](https://www.enter.co/?p=584990)) | sin dato |
| 3 | [Tiendanube Chat Nube](https://www.tiendanube.com/soluciones/chat-nube) | Directo, sólo con tienda Tiendanube | AR$400–190 por conversación, sin abono | sin reseñas encontradas |
| 4 | [Darwin AI](https://getdarwin.ai/) | Directo | $350/mes por 500 conversaciones (moneda sin nombrar, [página promo 2025](https://www.getdarwin.ai/en/soluciones/cyber-week)) | no accesible |
| 5 | [Botmaker](https://botmaker.com/es/precios) | Indirecto | USD 149/mes (Standard) | G2 4,5 (289); Trustpilot 3,3 (4) |
| 6 | [Leadsales](https://leadsales.io/precios/) | Indirecto | USD 133 + agente de IA USD 87 = USD 220/mes | Trustpilot 3,0 (4) |
| 7 | [Cliengo](https://www.cliengo.com/pricing) | Indirecto | USD 119/mes (Premium) | Capterra 4,3 (13); Comparasoftware 1,0 (2) |
| 8 | [Kommo](https://www.kommo.com/pricing/) | Indirecto | USD 35 por usuario/mes, mínimo 6 meses | Trustpilot 2,7 (67) |
| — | [WhatsApp Business a mano](https://blog.whatsapp.com/10000637/?%2529&l=ar) (e Instagram DM) | Sustituto | gratis | sin dato |
| — | [Empleado de comercio, Vendedor B](https://calcularsueldo.com.ar/?p=16046) | Sustituto | AR$1.346.349/mes bruto, sin cargas | — |

Los ratings de G2 y Capterra salen de resúmenes de búsqueda, porque esas páginas devolvieron 403. Descartados: Treble, Yalo, Jelou y Zenvia, que son enterprise o no publican precio para pymes; Chatealo, con 0 reseñas y sin precio. Tampoco encontré un software de gestión para ferreterías argentinas que incluya chat y tenga precio público. Mercado Pago y Mercado Libre no se revisaron a fondo.

## Rango de precios (sólo planes mensuales con IA verificados, en USD)

- **Más bajo: USD 35**, Kommo Advanced por un usuario, pero se paga adelantado un mínimo de 6 meses (USD 210).
- **Mediana: USD 149**, Botmaker Standard, sobre Kommo 35, Cliengo 119, Botmaker 149, Leadsales 220 y notchatbot 300.
- **Más alto: USD 300**, notchatbot. Darwin, con $350, quedó fuera porque no se confirma la moneda.

Por uso: Chat Nube cobra AR$95.000–200.000 por 500 conversaciones al mes, en pesos (cuenta propia sobre su tarifa). Meta cobra unos USD 20–25 por 500. Frente a eso, el sustituto es gratis o cuesta un sueldo de AR$1,35M. Todos los SaaS puros cobran en dólares, y sólo Chat Nube cobra en pesos.

## Mapa de posicionamiento

Eje X: **sólo responde o deriva ↔ cierra la venta en el chat** (carrito, cobro). Eje Y: **precio y esfuerzo de puesta en marcha** (bajo ↔ alto).

```
 esfuerzo/precio ALTO
   Botmaker (USD 149 + alta WA USD 99)       Darwin (demo, ~$350)
   Leadsales (USD 220)                       notchatbot (USD 300, llamada, requiere ecommerce)
   Cliengo (USD 119)  Kommo (6 meses adel.)
 responde/deriva ─────────────────────────────────────────── cierra en el chat
   Empleado (AR$1,35M; lento, sólo en horario)  Chat Nube (por uso, en pesos; SÓLO con tienda Tiendanube)
   WhatsApp Business a mano (gratis)
   Meta Business AI (centavos; recomienda y deriva, sin carrito)
 esfuerzo/precio BAJO
```

El cuadrante de abajo a la derecha (barato, fácil y que cierra la venta) lo ocupa sólo Chat Nube, y sólo para quien ya tiene tienda Tiendanube. La ferretería sin tienda no puede usarlo.

## Quejas, de más a menos frecuentes

La muestra es chica y global, no de ferreterías argentinas; Trustpilot avisa que estos perfiles no invitan a reseñar.

1. **Fallas y bloqueos de WhatsApp: 6 reseñas.** Entran Kommo (3), Botmaker (1), Cliengo (1) y Leadsales (1). «We have been experiencing a WhatsApp synchronization issue on our Kommo account for the past 5 days» ([Kommo](https://www.trustpilot.com/review/kommo.com)). «Mande 7 mensajes y whataspp me bloqueo la cuenta» ([Leadsales](https://www.trustpilot.com/review/leadsales.io)).
2. **Soporte malo o lento: 7 leídas,** de Kommo (5), Botmaker (1) y Cliengo (1). G2 suma otras 4 sobre Botmaker, que no leí textuales. «Support is awful. They want you to sit and wait for their reply in their chat which can take 24-48 hours» ([Kommo](https://www.trustpilot.com/review/kommo.com)). «Software lleno de probles y pesima atencion» ([Botmaker](https://www.trustpilot.com/review/botmaker.com)).
3. **Cobros sorpresa o caro para lo que da: 5 reseñas,** de Kommo (3), Cliengo (1) y Leadsales (1). «I was automatically charged $400 without requesting the renewal of any service» (Kommo, reseña desde AR, [Trustpilot](https://www.trustpilot.com/review/kommo.com)). «Es caro para lo que ofrece» ([Cliengo](https://www.comparasoftware.com/cliengo)).
4. **El bot se equivoca: 1 reseña, thin.** «El bot se equivoca con frecuencia» ([Cliengo](https://www.comparasoftware.com/cliengo)).
5. **Configuración compleja: thin y de segunda mano** (resumen de G2 sobre Botmaker y de Capterra sobre Kommo; no hay citas textuales).

notchatbot tiene 11 reseñas, todas de 5 estrellas y todas fechadas el 28/01/2026. No hay quejas públicas que leer.

## LA BRECHA

Ninguno vende hoy **un vendedor por chat que lea el stock y el precio de la planilla del comercio, arme el pedido y lo cobre de forma verificada, sin tienda online, en pesos y sin llamada de implementación**:
- Chat Nube cierra la venta, pero se activa desde el panel de una tienda Tiendanube y usa su catálogo ([Chat Nube](https://www.tiendanube.com/soluciones/chat-nube)).
- notchatbot integra plataformas de ecommerce, cuesta USD 300 y arranca con una llamada.
- Meta Business AI es casi gratis, pero según Tiendanube (fuente interesada) no conoce el stock real ni crea carritos: «Desconectado. Solo lee lo que se le carga manualmente a WhatsApp» ([Tiendanube](https://ayuda.tiendanube.com/es_MX/responde-con-chat-nube/por-que-elegir-chat-nube-frente-a-la-ia-de-whatsapp-business)).
- El resto son bandejas o CRMs en dólares, y las quejas se concentran en WhatsApp inestable, soporte y cobros.

**El problema: la brecha está en el canal equivocado.** Todos los competidores atienden por WhatsApp, y el producto hoy es chat web. Una ferretería sin tienda online probablemente tampoco tiene una web donde pegar el widget. Sin WhatsApp, la brecha existe en el papel pero no hay dónde ocuparla.

## LA AMENAZA

**Meta**, la más rápida. Su agente ya vive gratis dentro de la app que el ferretero usa, llegó primero a Argentina, aprende del catálogo y cuesta centavos por conversación. Si suma carrito y cobro (WhatsApp Pay ya funciona en Brasil, según [DPL News](https://dplnews.com/comercio-agentico-tiendanube-mexico-lanza-chat-con-ia-en-whatsapp/)), el producto se vuelve una función. Le siguen **Tiendanube**, que podría abrir Chat Nube a comercios sin tienda con un catálogo en planilla y ya cobra en pesos por uso, y **notchatbot**, que podría sumar un conector de Google Sheets y bajar el precio.
