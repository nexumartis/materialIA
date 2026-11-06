# materialIA ("Presupuesto Vivo", nombre de trabajo) · Business plan

**Verdict: Not yet**

- ✓ Each comercio-mes (suscripción) earns $17836.00 before fixed costs (51% contribution).
- ✓ Year 1 operating profit: $2,644,168.
- ✓ Break-even is 8 comercio-mes (suscripción)s a day against a capacity of 100000.
- ✗ 3 of 20 simulated buyers buy (15%, the bar is 25%).

| key number | |
| --- | ---: |
| Price | $35000.00 a comercio-mes (suscripción) |
| Profit margin at plan | 41% per comercio-mes (suscripción) |
| Break-even | 8 comercio-mes (suscripción)s a day |
| Year 1 operating profit | $2,644,168 |
| Startup spend | $300,000 |
| Cash needed before it pays for itself | $424,112 |
| Startup money earned back | month 7 |
| Buyer panel | 3 buy · 17 pass |

## The idea

- What it is: un agente de ventas por chat con IA que atiende a los clientes de un comercio y cierra la venta de punta a punta (consulta → carrito → entrega → cobro verificado), con el stock y los precios reales del negocio.
- Who it is for: dueños de comercios PyME de Argentina que hoy contestan consultas a mano por chat/WhatsApp/web y pierden ventas por responder tarde o fuera de horario. Multi-rubro: ferretería y sanitarios, ropa, comida, electrodomésticos/colchones/muebles (con entrega e instalación). Muchos no tienen tienda online; sí tienen un catálogo en planilla.
- What it sells, at what price: suscripción mensual (SaaS) al agente + panel del negocio. **Precio: sin definir** (hipótesis a testear). Referencia pública del competidor directo: notchatbot, «Planes desde USD 300/mes» en su ficha de la tienda de apps de Tiendanube.
- Where and how: online, Argentina. El negocio se registra solo, carga su catálogo (CSV o Google Sheets), configura el agente y pega una línea de código en su web (o comparte el link de su tienda). Hoy: chat web; WhatsApp todavía no.
- Budget and constraints: dos socios fundadores técnicos (Tomás y Matías), producto construido y funcionando en local, sin clientes pagos ni deploy. Presupuesto de marketing y capital: no informados. Reglas del producto: nunca inventar precios ni stock; un pedido es «pagado» sólo con pago verificado por el proveedor o transferencia cotejada por el dueño; sin WhatsApp ni mensajes salientes a clientes en esta fase.

## Summary

**Veredicto: Not yet.** Los números cierran, pero **sólo 3 de 20 compradores simulados compran (15%, la vara es 25%)**, y casi todos los que dicen que no dan la misma razón: *«mis clientes me escriben por WhatsApp»*. Lo que tiene que cambiar es **el canal** (o la evidencia de que el link alcanza), no el precio: eso lo decide la prueba real de `launch.md` (puerta de decisión al día 30) y, si falla, WhatsApp con cambio de alcance acordado entre los dos socios.

**Qué es:** un vendedor por chat con IA para la ferretería, casa de sanitarios o corralón de barrio sin tienda online. Cotiza con su lista y su stock reales, arma el pedido, coordina envío o retiro y cobra verificado.

**Los tres números** (proyecciones, ver `cfo.md`): a $35.000/mes cada comercio deja **$17.836 (51%)**; el equilibrio es de **8 comercios** pagando; el año 1 con 40 comercios al final da **$2,6 M de ganancia operativa, sin sueldos**. Con dos sueldos de $2 M/mes el equilibrio sube a **232 comercios** y el año 1 pierde ~$45 M.

**Directorio y panel coinciden** en el riesgo principal (WhatsApp) y en arrancar con un rubro y una zona. **Discrepan** en la durabilidad: el lente Monopoly cree que Meta Business AI, Tiendanube o notchatbot lo copian en meses; el panel no lo midió.

**Mayor riesgo:** que los compradores no salgan de WhatsApp (amenaza concreta: Meta Business AI, gratis dentro de la app que ya usa el ferretero). Respuesta: medirlo en 10 pilotos antes de construir más, con la puerta de decisión de `launch.md`.

**Para arrancar:** ~$0,42 M de caja sin sueldos (lanzamiento + primeros meses), el deploy con SMTP propio, contador y términos, y 10 ferreterías piloto en zona sur del GBA con 2 meses gratis y la carga hecha por los socios.

**Esta semana:** cerrar el deploy y conseguir las 2 primeras ferreterías piloto (visita en persona con la prueba de fotos de sus propios repuestos).

> El panel es de compradores simulados y los números son proyecciones con costos estimados (IA, hosting, sueldos no informados). Confirmar con compradores reales antes de gastar.

## What the board said

**Voto: 3 FUND IF, 0 PASS. Puntaje promedio: 4,7/10** (Offers 5, Monopoly 4, Product 5).

Nadie lo rechaza y nadie lo financia sin condiciones: el producto convence, el negocio todavía no está probado.

### Riesgos que marcaron dos o más miembros (van primero)
1. **Sin WhatsApp, el canal no está donde está la conversación** (los tres). El comprador argentino probablemente escribe por WhatsApp; un botón web sirve poco a comercios que ni tienen web. Hay que validar dónde conversan *los clientes del rubro elegido*.
2. **Multi-rubro / falta de foco** (los tres). Cuatro rubros y una docena de funciones no entran en una oración ni le hablan a nadie en particular.
3. **Cero clientes, cero datos reales** (los tres). No hay disposición a pagar medida, ni costo de adquisición, ni una sola venta real cobrada por el agente; el seed es sintético.
4. **Distribución sin resolver** (Offers y Monopoly): cómo llegan los primeros 10 y 100 comercios y cuánto cuesta cada uno.
5. **Costo de IA estimado, no medido** (Offers y Monopoly): USD 4–600/mes por negocio puede comerse el margen o impedir una garantía.

Desacuerdos que se mantienen:
- **Durabilidad.** Monopoly cree que lo pueden copiar notchatbot, Tiendanube o Mercado Pago en seis meses. Offers y Product ven el cierre en el chat como diferencia real hoy.
- **Implementación.** Offers propone hacerla ustedes («te lo dejamos vendiendo»). Product prioriza que el dueño llegue solo a la primera venta en minutos.

### Condiciones (checklist para el resto del pack)
- [ ] **Un rubro (y una zona) de entrada**, con promesa en una oración. Los tres sugieren ferretería/sanitarios. *(marketing, brand)*
- [ ] **Dónde conversa el comprador de ese rubro**: evidencia de que el botón web alcanza, o WhatsApp con fecha y alcance acordado. *(consumer, ops)*
- [ ] **3 a 10 pilotos con ventas reales cobradas**, midiendo % de conversaciones que llegan a pago verificado y espera tras una derivación. *(launch)*
- [ ] **Precio validado con plata**, no con encuestas. *(pricing, consumer)*
- [ ] **Costo de IA por conversación medido** y margen positivo en el segmento. *(cfo)*
- [ ] **Canal de distribución probado** con costo real del primer cliente (mayoristas, cámaras, software de gestión como posibles canales). *(marketing)*
- [ ] **Implementación casi sin esfuerzo para el dueño** (hecha por ustedes o en minutos). *(offer, ops)*
- [ ] **Garantía atada a resultado** (ventas cobradas en 30 días), sólo después de medir el costo de IA. *(offer, cfo)*
- [ ] **Tesis de durabilidad escrita**: qué activo crece con cada cliente (datos del rubro, integraciones, marca en el nicho). *(competitors, brand)*

### La versión más fuerte que ve el directorio
No es «un agente de ventas multi-rubro». Es **el vendedor por chat de la ferretería y el corralón de barrio**: el comercio sin tienda online que hoy contesta a mano consultas de stock, medidas y precios. Le cierra la venta con su planilla de siempre, le cobra verificado y le coordina la entrega o la medición, instalado por ustedes en días. Empieza en una sola zona, con 10 comercios que vendan de verdad, y suma WhatsApp apenas el piloto lo pida. Es más chico que lo que se presentó, y a propósito: es un mercado que pueden dominar antes de que los grandes lo miren.

## The competition

Segmento: dueño de ferretería, sanitarios o corralón en Argentina, sin tienda online, que hoy contesta chats a mano. Ítem comparable: un plan mensual de asistente de ventas por chat con IA, o lo que el dueño hace en su lugar. Fuentes públicas vistas el 05/11/2026; detalle y links en `competitors.csv`.

### Tabla (de más a menos directo)

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

### Rango de precios (sólo planes mensuales con IA verificados, en USD)

- **Más bajo: USD 35**, Kommo Advanced por un usuario, pero se paga adelantado un mínimo de 6 meses (USD 210).
- **Mediana: USD 149**, Botmaker Standard, sobre Kommo 35, Cliengo 119, Botmaker 149, Leadsales 220 y notchatbot 300.
- **Más alto: USD 300**, notchatbot. Darwin, con $350, quedó fuera porque no se confirma la moneda.

Por uso: Chat Nube cobra AR$95.000–200.000 por 500 conversaciones al mes, en pesos (cuenta propia sobre su tarifa). Meta cobra unos USD 20–25 por 500. Frente a eso, el sustituto es gratis o cuesta un sueldo de AR$1,35M. Todos los SaaS puros cobran en dólares, y sólo Chat Nube cobra en pesos.

### Mapa de posicionamiento

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

### Quejas, de más a menos frecuentes

La muestra es chica y global, no de ferreterías argentinas; Trustpilot avisa que estos perfiles no invitan a reseñar.

1. **Fallas y bloqueos de WhatsApp: 6 reseñas.** Entran Kommo (3), Botmaker (1), Cliengo (1) y Leadsales (1). «We have been experiencing a WhatsApp synchronization issue on our Kommo account for the past 5 days» ([Kommo](https://www.trustpilot.com/review/kommo.com)). «Mande 7 mensajes y whataspp me bloqueo la cuenta» ([Leadsales](https://www.trustpilot.com/review/leadsales.io)).
2. **Soporte malo o lento: 7 leídas,** de Kommo (5), Botmaker (1) y Cliengo (1). G2 suma otras 4 sobre Botmaker, que no leí textuales. «Support is awful. They want you to sit and wait for their reply in their chat which can take 24-48 hours» ([Kommo](https://www.trustpilot.com/review/kommo.com)). «Software lleno de probles y pesima atencion» ([Botmaker](https://www.trustpilot.com/review/botmaker.com)).
3. **Cobros sorpresa o caro para lo que da: 5 reseñas,** de Kommo (3), Cliengo (1) y Leadsales (1). «I was automatically charged $400 without requesting the renewal of any service» (Kommo, reseña desde AR, [Trustpilot](https://www.trustpilot.com/review/kommo.com)). «Es caro para lo que ofrece» ([Cliengo](https://www.comparasoftware.com/cliengo)).
4. **El bot se equivoca: 1 reseña, thin.** «El bot se equivoca con frecuencia» ([Cliengo](https://www.comparasoftware.com/cliengo)).
5. **Configuración compleja: thin y de segunda mano** (resumen de G2 sobre Botmaker y de Capterra sobre Kommo; no hay citas textuales).

notchatbot tiene 11 reseñas, todas de 5 estrellas y todas fechadas el 28/01/2026. No hay quejas públicas que leer.

### LA BRECHA

Ninguno vende hoy **un vendedor por chat que lea el stock y el precio de la planilla del comercio, arme el pedido y lo cobre de forma verificada, sin tienda online, en pesos y sin llamada de implementación**:
- Chat Nube cierra la venta, pero se activa desde el panel de una tienda Tiendanube y usa su catálogo ([Chat Nube](https://www.tiendanube.com/soluciones/chat-nube)).
- notchatbot integra plataformas de ecommerce, cuesta USD 300 y arranca con una llamada.
- Meta Business AI es casi gratis, pero según Tiendanube (fuente interesada) no conoce el stock real ni crea carritos: «Desconectado. Solo lee lo que se le carga manualmente a WhatsApp» ([Tiendanube](https://ayuda.tiendanube.com/es_MX/responde-con-chat-nube/por-que-elegir-chat-nube-frente-a-la-ia-de-whatsapp-business)).
- El resto son bandejas o CRMs en dólares, y las quejas se concentran en WhatsApp inestable, soporte y cobros.

**El problema: la brecha está en el canal equivocado.** Todos los competidores atienden por WhatsApp, y el producto hoy es chat web. Una ferretería sin tienda online probablemente tampoco tiene una web donde pegar el widget. Sin WhatsApp, la brecha existe en el papel pero no hay dónde ocuparla.

### LA AMENAZA

**Meta**, la más rápida. Su agente ya vive gratis dentro de la app que el ferretero usa, llegó primero a Argentina, aprende del catálogo y cuesta centavos por conversación. Si suma carrito y cobro (WhatsApp Pay ya funciona en Brasil, según [DPL News](https://dplnews.com/comercio-agentico-tiendanube-mexico-lanza-chat-con-ia-en-whatsapp/)), el producto se vuelve una función. Le siguen **Tiendanube**, que podría abrir Chat Nube a comercios sin tienda con un catálogo en planilla y ya cobra en pesos por uso, y **notchatbot**, que podría sumar un conector de Google Sheets y bajar el precio.

## The buyer panel

**3 buy · 17 pass** (15% buy) out of 20 simulated buyers. Seed 184954, so the same cards can be dealt again.

These are simulated buyers, not customers. Use this to find objections and weak spots, then confirm the big ones with real people before you spend.

### By segment

| group | buyers | buy rate |
| --- | ---: | ---: |
| Comercio con local y algo de web/Instagram activo | 3 | 33%  (thin) |
| Sanitarios/corralón mediano (3 a 8 empleados) | 8 | 12% |
| Ferretería de barrio chica (dueño + 1 empleado) | 9 | 11% |

### By buying behaviour

| group | buyers | buy rate |
| --- | ---: | ---: |
| Quiere crecer y vender más | 3 | 100%  (thin) |
| Cuida cada peso | 4 | 0%  (thin) |
| Desconfiado de la tecnología | 3 | 0%  (thin) |
| Fiel a su sistema de gestión | 3 | 0%  (thin) |
| Contesta todo él mismo por WhatsApp | 5 | 0%  (thin) |
| Delega en el hijo o un empleado | 2 | 0%  (thin) |

### By income

| group | buyers | buy rate |
| --- | ---: | ---: |
| $10,296,000 to $33,294,000 | 7 | 29%  (thin) |
| under $10,296,000 | 6 | 17%  (thin) |
| $33,294,000 and up | 7 | 0%  (thin) |

### Why they pass

| reason | buyers | in their words |
| --- | ---: | --- |
| convenience | 5 | "Mis clientes me escriben por WhatsApp, no por una web que no tengo. Y la lista de precios la cambio cada dos por tres; si el bot depende de que yo tenga la planilla al día, no tengo tiempo de mantenerla y termina pasando precios viejos." (P002) · "Mis clientes me escriben todos por WhatsApp y no tengo web; si no anda ahí, es mandarlos a un link que la mitad no va a abrir y yo sigo contestando igual desde el celular. Encima no me la juego con que le pase un precio mal a un cliente y después tenga que bancarlo yo." (P008) |
| trust | 5 | "Ya pagué sistemas que quedaron juntando polvo y esto me suena igual: mis clientes me mandan las fotos por WhatsApp, no a una web que no tengo. Capaz pruebo los 14 días gratis si me lo dejan cargado ustedes, pero pagar, por ahora no." (P004) · "Ya pagué sistemas que quedaron juntando polvo, y acá el cliente me pregunta por un repuesto o una medida y quiere que le conteste alguien que sepa. Encima mis clientes me escriben por WhatsApp, y si no anda ahí no sé quién va a usar el chat ese." (P006) |
| habit | 5 | "Mis clientes me escriben por WhatsApp, no entran a ninguna web ni a un link de tienda, y ya tengo mi sistema de stock y facturación; no voy a andar manteniendo además una planilla aparte para que el chat sepa los precios. Y $45.000 por mes para un negocio chico como el mío es mucha plata por algo que no está donde están mis clientes." (P005) · "Mis clientes me escriben por WhatsApp, no por una web que no tengo, y encima tendría que mantener los precios y el stock en una planilla aparte de mi sistema de gestión. Cargar todo dos veces con el mostrador lleno no lo voy a hacer, ni con la prueba gratis." (P010) |
| need | 2 | "Mis clientes me escriben por WhatsApp y quieren hablar conmigo, sobre todo por medidas y repuestos; un chat en una web que no tengo no me saca trabajo. Y $45.000 por mes para un negocio de dos personas es mucha plata para algo que no está donde está mi gente." (P009) · "Mis clientes me escriben por WhatsApp, no tengo web y por Instagram casi no me compran; un chat en un link que nadie va a abrir no me sirve. Y $45.000 por mes para mí es plata, ya pagué sistemas que quedaron juntando polvo." (P011) |

### Why they buy

| reason | buyers | in their words |
| --- | ---: | --- |
| need | 3 | "Me escriben a toda hora con fotos de repuestos y de noche no contesto, así que vendo menos. Si me lo dejan andando ustedes y la prueba es gratis sin tarjeta, lo pruebo con el link en Instagram, y si en dos semanas me cierra aunque sea un par de ventas fuera de horario, $45.000 los pago." (P001) · "Quiero vender fuera de horario y el Instagram ya me trae consultas que contesto tarde. Si me lo dejan andando con mi planilla y la prueba es gratis sin tarjeta, lo pruebo; si en los 14 días me cierra ventas de noche, pago los 45 mil." (P003) |

### What would flip a no

- Que funcione dentro de WhatsApp y que ustedes me mantengan la lista de precios al día a partir de lo que me mandan los proveedores, sin que yo toque nada.
- Que funcione dentro de WhatsApp y verlo andando con mis propios repuestos: que un cliente mande la foto de una pieza rota y el chat le encuentre la correcta de mi stock sin que yo toque nada.
- Que ande dentro de WhatsApp y que tome los precios y el stock directo de mi sistema de gestión, sin planilla aparte.
- Ver que ande en WhatsApp y que en la prueba gratis me cierre ventas de verdad en mi negocio, con mis clientes, sin que yo tenga que andar arreglándole la planilla.
- Que funcione dentro de WhatsApp y que en la prueba vea con mis propias fotos de repuestos que acierta o me pasa la charla cuando duda.
- Que funcione dentro de mi WhatsApp y que yo pueda ver y aprobar el precio antes de que salga al cliente, al menos el primer mes.
- Que ande en mi mismo WhatsApp, contestando lo fácil de noche (precio y si hay stock) y dejándome a mí lo de medidas, a un precio bastante más bajo.
- Que tome precios y stock directo de mi sistema de gestión sin cargar nada a mano y que conteste dentro de mi WhatsApp.
- Que funcione dentro de mi WhatsApp y verlo andando en otra ferretería como la mía, vendiendo de verdad, antes de pagar un peso.
- Que me lo recomiende otro ferretero de la zona que ya lo use y le ande bien, y que funcione dentro de WhatsApp.
- Que funcione dentro de mi WhatsApp leyendo mi planilla de precios. Ahí probaría los 14 días gratis.
- Que conteste directo en mi WhatsApp de siempre y que me lo dejen andando con mis precios sin que yo tenga que armar ninguna planilla.

Buyers say they would buy **1.0 times** in the first month on average.

20 buyers gave all four price answers. Run founder-pricing's van_westendorp.py on the answers folder.

## Pricing

> Respuestas de compradores simulados: sirven para elegir qué probar, no son prueba.

### 1. El precio: $35.000 por mes (antes de IVA), para probar
- **Panel (Van Westendorp, 20 respuestas):** rango aceptable **$10.225 a $49.888**; menor resistencia $10.225; punto de equilibrio barato/caro **$25.101**. Medianas: barato $20.000, empieza a ser caro $40.000, demasiado caro $60.000. Ver `pricing-curve.md`.
- **Competencia** (`competitors.md`): planes con IA de USD 35 (Kommo, por usuario, 6 meses mínimo) a USD 300 (notchatbot); mediana USD 149. A ~USD 24, $35.000 queda debajo de todos en pesos y sin contrato.
- **Margen** (`cfo.md`): a $35.000 cada comercio deja $18.400 (53%); a $25.000, $8.400 (34%); a $45.000, $28.400 (63%). Con el costo de IA sin medir, **$25.000 deja poco colchón**.
- **Por qué no $45.000:** es el precio del pitch y 4 de los 20 lo pusieron en «no compro» o encima de su caro; además el objetor principal (WhatsApp) no se resuelve con precio.

### 2. La escalera
| plan | precio/mes | qué incluye | por qué subir |
|---|---:|---|---|
| Mostrador | $25.000 | Chat en la web/link, catálogo desde planilla, hasta ~300 conversaciones | entrada para el chico que cuida cada peso |
| Vendedor | $35.000 | + cobro verificado, envíos y franjas, fotos, campañas | cierra ventas, no sólo responde |
| Sucursal | $60.000 | + equipo/roles, reparto propio con hoja de ruta, más conversaciones | corralón con camioneta y empleados |
(Los topes de conversaciones protegen el costo de IA; fijarlos después de medirlo.)

### 3. Oferta de lanzamiento
**Primeros 10 comercios piloto: 2 meses gratis y te lo dejamos andando nosotros con tu planilla**, a cambio de datos reales y un testimonio si funciona. Termina cuando se completan los 10 (sin fecha falsa ni «antes $X»).

### 4. Qué probar con compradores reales
- **$25.000 vs $35.000** para el plan Vendedor: dos landings con precio, mismo pitch, medir pedidos de prueba y cuántos pasan a pagar al mes 3 de los pilotos.
- Medir **costo de IA real por comercio** en los pilotos antes de fijar el plan Sucursal.

### 5. Objeciones de precio del panel (textuales)
- «Y $45.000 por mes para un negocio chico como el mío es mucha plata por algo que no está donde están mis clientes.» (P005)
- «$45.000 por mes para un negocio de dos personas es mucha plata para algo que no está donde está mi gente.» (P009)
- «$45.000 por mes para mí es plata, ya pagué sistemas que quedaron juntando polvo.» (P011)

## The offer

> Método: la lente de Ofertas del directorio (resumen del marco de *$100M Offers*). Las objeciones vienen del panel **simulado** (20 compradores, 15% compra); sirven para diseñar, no prueban demanda.

### 1. Problemas del comprador (en sus palabras)

- **Antes:** (1) «mis clientes me escriben por WhatsApp, no por una web que no tengo» (casi todos los «no»); (2) «no voy a mantener una planilla aparte de mi sistema»; (3) «la lista la cambio seguido, va a pasar precios viejos»; (4) «ya pagué sistemas que juntan polvo»; (5) «$45.000 es mucha plata para un negocio de dos»; (6) «quiero verlo andar en una ferretería como la mía»; (7) «no me la juego a que pase un precio mal»; (8) «no tengo tiempo de configurarlo»; (9) la competencia cobra en dólares, con llamada o 6 meses mínimos (`competitors.md`).
- **Durante:** (10) «un link que la mitad no va a abrir»; (11) «por un repuesto o medida quieren a alguien que sepa»; (12) «¿y si duda?»; (13) «¿y si marca pagado algo que no se pagó?»; (14) «¿quién coordina la camioneta?».
- **Después:** (15) «¿y si a los dos meses no vendió nada?»; (16) «si contesta mal, quedo mal yo»; (17) cobros sorpresa y soporte lento (quejas públicas de Kommo, Botmaker, Cliengo).

### 2. Soluciones, con puntaje (valor 1-5 / costo 1-5)

| # | Solución | Problemas | Valor | Costo | ¿Queda? |
|---|---|---|---:|---:|---|
| A | **Lo dejamos andando nosotros:** nos mandás tu lista y la cargamos | 2, 8 | 5 | 2 (horas de los socios) | Sí |
| B | **Actualización de lista incluida:** reenviás la lista nueva y la subimos (tope a fijar tras el piloto) | 2, 3 | 5 | 2-3 | Sí |
| C | **Precios con vencimiento:** si tu lista venció, el agente no cotiza y te pasa la charla | 3, 7 | 4 | 1 (ya existe) | Sí |
| D | **Kit «link donde ya te escriben»:** tu link en el mensaje de ausencia de tu WhatsApp Business, la bio de Instagram, Google Maps y un QR de mostrador (lo redactamos; lo pegás vos) | 1, 10 | 4 | 1 | Sí |
| E | **Prueba con tus fotos:** antes de firmar, mandás fotos de repuestos de tu local y ves si acierta o te deriva | 6, 11, 12 | 5 | 1 (ya existe) | Sí |
| F | Core ya construido: deriva con resumen si duda; «pagado» sólo verificado; entrega en franjas o retiro | 11-14, 16 | 4 | 1 | Sí |
| I | Garantía de primera venta (abajo) | 4, 15 | 5 | 2 | Sí |
| J | En pesos, mes a mes, sin permanencia ni tarjeta en la prueba | 5, 9, 17 | 4 | 1 | Sí |
| K | Soporte por los socios con respuesta en el día hábil | 16, 17 | 4 | 3 | Sí, sólo pilotos |
| L | Que funcione dentro de WhatsApp | 1 | 5 | fuera de alcance | **No se promete** |
| M | Conexión directa al sistema de gestión | 2 | 5 | 5 | **No.** A cambio, A y B |
| N | Aprobar cada precio antes de que salga | 7 | 3 | ? | **No** (no verificado en el producto) |

### 3. El stack: «Piloto Vendedor Fuera de Horario»

**Core:** de noche o con el mostrador lleno, el agente contesta con tu precio y stock, arma el pedido, coordina camioneta o retiro y cobra (Mercado Pago o transferencia). A la mañana ves los pedidos pagados, verificados.

**Bonos (cada uno mata una objeción):**
1. **Carga y actualización hechas por nosotros** (A + B), contra «no voy a mantener otra planilla».
2. **Kit «link donde ya te escriben»** (D), contra «mis clientes están en WhatsApp». Dicho claro: **el agente no contesta dentro de WhatsApp.**
3. **Prueba con tus fotos de repuestos** (E), contra «quiero verlo andar con lo mío».

**Garantía de primera venta:** si en tu primer mes pago el agente no cerró al menos **una venta cobrada y verificada**, te devolvemos ese mes entero. Además, cancelás cuando quieras.
- *Costo (herramienta del CFO, `numbers.json` vigente), en el peor caso de reclamos todos los meses:* 10% de reclamos → precio efectivo $31.500, contribución $14.336 (46%), equilibrio 9 comercios, año 1 $1,8 M; 20% → $28.000, $10.836 (39%), 12 comercios, $1,0 M; 30% → $24.500, $7.336 (30%), 18 comercios, $0,1 M. Aplica sólo al primer mes pago, así que el costo real es mucho menor; se banca hasta ~20%.
- *Condición del directorio:* activarla recién con el costo de IA medido en los pilotos (hoy, estimación de USD 10/mes). En el piloto no hace falta: los 2 meses son gratis.

**Urgencia real:** sólo **10 lugares de piloto**: los socios cargan a mano y no dan para más. Cierra al completarse; sin fecha falsa ni «antes $X».

**Precio:** piloto 2 meses gratis, sin tarjeta; después **$35.000 por mes + IVA** (plan Vendedor, `pricing.md`). A cambio: datos reales y, si funciona, permiso para contar el caso.

**Costo del piloto:** IA estimada en $14.500 × 2 meses × 10 comercios = **$290.000** + horas de los socios (no valuadas). Sumarlo en `/founder-cfo`.

### 4. Ecuación de valor (1-10, antes → después)

| Elemento | Antes | Después | Qué lo mueve |
|---|---:|---:|---|
| Resultado soñado («vendo de noche sin estar») | 6 | 7 | Core contado como resultado |
| Probabilidad percibida | 3 | 6 | Prueba con tus fotos, garantía, precio con vencimiento; sin WhatsApp ni casos reales no sube más |
| Tiempo hasta el resultado | 5 | 7 | Instalación nuestra + kit de link |
| Esfuerzo y sacrificio (10 = mínimo) | 3 | 7 | Carga y actualización nuestras, sin tarjeta ni permanencia |

El techo lo pone el canal: sin WhatsApp, la probabilidad queda en ~6 para el que contesta todo por WhatsApp (25% del cliente objetivo).

### 5. Re-test

**No se re-testeó** con `/founder-consumer --quick`: se omitió por costo. Pitch nuevo en `pitch.md`, anterior en `pitch-v1.md`. **No hay tasa de compra «después».**

Expectativa sin dato: los bonos atacan planilla, «juntan polvo» y precio, pero **no «no está en WhatsApp»**, presente en casi todos los «no». Si el 15% no se mueve, el problema es el canal, no la oferta. La prueba real: cuántos de 10 pilotos llegan a una venta verificada.

Siguiente: `/founder-cfo` con el costo del piloto, después `/founder-marketing`.

## The numbers

> Nota: la herramienta dice «a day»; acá la unidad es **un comercio pagando un mes** y el volumen es **por mes**. No es consejo financiero, impositivo ni legal: un contador tiene que revisar la estructura, el IVA (los precios son antes de impuestos) y la facturación antes de cobrar.

### Nota del CFO (actualizada con los costos de operaciones: Resend, Ollama Cloud Pro, comisión 7,6%)
- **El margen:** a $35.000/mes cada comercio deja **$17.836** (51%) después de su IA y la comisión de cobro. Con 40 comercios al final del año 1: margen 41% y **$2,6 M de ganancia operativa en el año**, *sin sueldos*.
- **La línea a mirar: los sueldos y la escala.** Con dos sueldos de $2 M/mes (escenario, no informado) el punto de equilibrio sube a **232 comercios a $35.000** o **149 a $45.000**, y el año 1 pierde ~$45 M. Hoy el negocio no paga dos sueldos con 40 clientes.
- **La segunda línea: el costo de IA** (estimado USD 10 por comercio/mes, no medido). Es el 41% del precio de $35.000. Si un comercio grande gasta USD 30, deja de ser rentable a ese precio.
- **Caja:** sin sueldos, hacen falta ~**$0,42 M** antes de que se pague solo (lanzamiento + primeros meses). Con sueldos, ~**$45 M**.
- **Tres formas de mejorar el margen (corridas con la herramienta):**
  1. Precio $45.000 en vez de $35.000: contribución $27.836 (62%), equilibrio sin sueldos 5 comercios, año 1 $5,0 M.
  2. Medir y bajar el costo de IA (modelo más barato, cortar conversaciones largas): cada USD 1 menos por comercio son $1.450 más de contribución por mes.
  3. Plan por uso o con tope de conversaciones para comercios grandes, así el costo de IA no se come el precio fijo.
- **Condiciones del directorio sobre plata:** «costo de IA medido» ❌ (es estimación), «margen positivo en el segmento» ✅ sólo sin sueldos, «precio validado con plata» ❌ (panel simulado).

## Unit economics: materialIA (SaaS: agente de ventas por chat para comercios)

Every number below comes from the input file. Nothing is looked up or guessed.

### One comercio-mes (suscripción)

| line | per comercio-mes (suscripción) |
| --- | ---: |
| Price | $35,000.00 |
| IA por comercio por mes (ESTIMACIÓN: ~USD 10 a 1 USD = ARS 1.450) | -$14,500.00 |
| Comisión de cobro de la suscripción (ESTIMACIÓN 7,6%: 6,29% + IVA al instante, comparador de terceros, sin confirmar en MP; ops.md) | -$2,664.00 |
| Soporte e implementación prorrateados (ESTIMACIÓN: 1 h/mes a ARS 0, la hacen los socios) | -$0.00 |
| **Contribution** (what each comercio-mes (suscripción) leaves to pay the fixed costs) | **$17,836.00** (51%) |

### The margin that matters

Fixed costs: $133,400 a month (Base de datos Supabase Pro (USD 25, precio público supabase.com/pricing 05/11/2026) $36,250, Hosting de API, worker y web (ESTIMACIÓN USD 25) $36,250, Mail Resend Pro USD 20 (precio público, resend.com/pricing 05/11/2026) + dominio ESTIMACIÓN USD 2 $31,900, IA: Ollama Cloud Pro USD 20 (precio público, ollama.com/pricing 05/11/2026; incluye USD 60 de uso) $29,000, Sueldos de los socios (NO INFORMADO: 0 en este escenario) $0).

- **Break-even: 8 comercio-mes (suscripción)s a day.** Below that you lose money every month.
- **Profit margin at your plan** (40 a day): **41%** of every sale, after every cost.
- Capacity: 100000 a day.

### Year 1, month by month

| month | comercio-mes (suscripción)s a day | revenue | profit | cumulative (after $300,000 startup) |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 3 | $105,000 | -$79,892 | -$379,892 |
| 2 | 5 | $175,000 | -$44,220 | -$424,112 |
| 3 | 8 | $280,000 | $9,288 | -$414,824 |
| 4 | 11 | $385,000 | $62,796 | -$352,028 |
| 5 | 14 | $490,000 | $116,304 | -$235,724 |
| 6 | 17 | $595,000 | $169,812 | -$65,912 |
| 7 | 20 | $700,000 | $223,320 | $157,408 |
| 8 | 24 | $840,000 | $294,664 | $452,072 |
| 9 | 28 | $980,000 | $366,008 | $818,080 |
| 10 | 32 | $1,120,000 | $437,352 | $1,255,432 |
| 11 | 36 | $1,260,000 | $508,696 | $1,764,128 |
| 12 | 40 | $1,400,000 | $580,040 | $2,344,168 |

- **Year 1 operating profit: $2,644,168** on $8,330,000 of revenue.
- After the $300,000 startup spend: $2,344,168.
- Startup money earned back: month 7.
- Cash you need before it pays for itself: **$424,112**.

### What if

| scenario | margin at plan | break-even a day | year 1 profit |
| --- | ---: | ---: | ---: |
| Base plan | 41% | 8 | $2,644,168 |
| Price -10% | 35% | 10 | $1,811,168 |
| Volume -20% | 39% | 8 | $1,795,174 |
| Unit costs +15% | 34% | 9 | $2,031,413 |

No red flags in these numbers. They are only as good as the inputs: check every cost against a real quote.

## Marketing

> Citas y tasas: panel **simulado** de 20 compradores. Son investigación, nunca testimonios. Oferta: `offer.md`; precio: `pricing.md`.

### 1. Posicionamiento

**Recomendada (A):**
> Para el ferretero de barrio que quiere vender más y hoy contesta tarde las consultas que le llegan fuera de horario, materialIA es el vendedor por chat que cotiza con su lista y su stock reales, arma el pedido y lo cobra verificado sin tienda online, a diferencia de contestar a mano desde el celular cuando se puede.

- **Por qué:** los 3 compradores del panel dan la misma razón: vender fuera de horario y consultas de Instagram contestadas tarde. «Quiere crecer» compró 3 de 3 (muestra mínima).
- **B (contra Chat Nube):** «…el único que cierra la venta en el chat sin tienda Tiendanube». Cierto (`competitors.md`), pero el ferretero no compara contra Chat Nube.
- **C (contra un empleado):** «…atiende a toda hora por menos de un día de sueldo de un vendedor» (~$61.000/día). Argumento, no ancla.

**No decimos:** «en WhatsApp», «nunca se equivoca», «vendé el doble». **Sí:** «no inventa precios ni stock».

**Sobre WhatsApp, frase única aprobada:** «Hoy funciona como chat web o link. No contesta dentro de WhatsApp. Si es lo único que te sirve, dejanos tu contacto y te escribimos nosotros cuando esté, sin fecha prometida.»

### 2. Canales

| Canal | Por qué le sirve a este comprador | Costo aprox. | Cómo sé que funcionó |
|---|---|---|---|
| **1. Visitas en persona en una zona** (martes a viernes, 10 a 12 o 15 a 17; nunca sábado a la mañana) | Desconfía de lo que no ve; prueba con sus fotos en la visita | Nafta y viáticos, ~$100.000 el mes | ≥1 piloto firmado cada 5 visitas |
| **2. Instagram**: perfil propio, DMs uno a uno a ferreterías de la zona con Instagram activo y anuncios chicos en Meta | El segmento que compra ya recibe consultas ahí | Anuncios $120.000 | Demos agendadas por DM o anuncio y costo por demo |
| 3. (exploración) Mayoristas y viajantes de ferretería | Canal que propone el directorio; ya visitan ferreterías | $0, 2 o 3 charlas | Que uno acepte presentar el piloto |

**No hacemos ahora:** Google Ads (nadie busca «chatbot para ferretería»), TikTok e influencers (no es donde decide un dueño de 30 a 60), cámaras (cuando haya casos reales).

### 3. Calendario (L = lunes 23/11/2026: abre la convocatoria y el soft open de `launch.md`; los 10 en vivo el 07/12. Se corre si no está el deploy)

| Fecha | Canal | Qué sale y con qué mensaje |
|---|---|---|
| 09/11 (L-14) | Interno | Zona sur del GBA (`launch.md`): listar 40 ferreterías y sanitarios |
| 10/11 | Instagram | Perfil + post 1: «Qué es y qué no es» (sin WhatsApp, dicho claro) |
| 11 a 13/11 | Interno | Demo con catálogo de ejemplo; QR y folleto impresos |
| 12/11 | Instagram | Video de 30 s rotulado «demo con catálogo de ejemplo»: foto de repuesto → ítem o derivación (hook 5) |
| 16 y 17/11 | Mayoristas | 2 charlas con viajantes de la zona |
| 17 a 20/11 | Visitas | 10 visitas para ajustar el guion; registrar objeciones |
| 19/11 | Instagram | Detrás de escena: «así cargamos una lista de precios» |
| **23/11 (L)** | Todos | Abre el **Piloto: 10 lugares, 2 meses gratis**. Post + anuncio (hook 2) |
| 23/11 a 04/12 | Visitas + DMs | 30 visitas y 40 DMs (hooks 3, 4, 8); instalar pilotos con el kit de link |
| 24/11 | Meta | Zona de 5 km, intereses ferretería/construcción, $4.000/día hasta $120.000 (hook 1) |
| 26/11 y 03/12 | Instagram | «Pagado es pagado» (hook 6) · «Si tu precio venció, no lo inventa» (hook 4) |
| 01/12 | Instagram | «Quedan N lugares de piloto», sólo el número real |
| 07 a 09/12 (L+14 a L+16) | Todos | Los 10 en vivo (`launch.md`). Revisión con la sección 5; un caso real se cuenta sólo con autorización escrita |

**Sin novedades:** cómo se carga una lista, qué hace cuando duda, la zona que recorremos.

### 4. Diez hooks

1. (Video, 3 s) «¿Cuántas consultas te quedaron sin contestar anoche?» → razón de compra: fuera de horario.
2. (Anuncio) «Que tu ferretería pueda vender de noche, con tu lista de precios.» → razón de compra.
3. (Anuncio) «Tu lista la cargamos nosotros. Vos no tocás una planilla.» → planilla aparte.
4. (Post) «Si tu precio venció, no lo inventa: te pasa la charla.» → precio mal.
5. (Video, 3 s) «Mandale la foto del repuesto roto y mirá qué contesta.» → verlo con lo mío.
6. (Post) «Figura pagado sólo cuando Mercado Pago lo confirma o vos cotejaste la transferencia.» → confianza.
7. (Visita) «Si en tu primer mes pago no vende nada, te devolvemos el mes.» → «juntan polvo». *Usar sólo con la garantía activa (ver `offer.md`).*
8. (DM) «No contesta dentro de WhatsApp. Pero tu link sí puede estar en tu mensaje de ausencia.» → WhatsApp, honesto.
9. (Anuncio) «En pesos, mes a mes, sin tarjeta para probar.» → precio en dólares.
10. (Cartel de mostrador del piloto, con QR) «¿Cerrado? Pedí acá, con precio y stock reales. Envío o retiro.» → link que nadie abre.

### 5. Presupuesto y números

**Reparto de los $300.000 de lanzamiento** (`numbers.json`, estimación): visitas $100.000 · Meta $120.000 · impresión de QR y folletos $60.000 · reserva $20.000. **Aparte:** IA de los pilotos, ~$290.000 (`offer.md`).

**Lo máximo que se puede pagar por cliente:** contribución de $17.836 por mes (`cfo.md` vigente) × 1,0 compra por comprador en el primer mes (panel) = **$17.836** para recuperarlo en el primer mes pago. Sin dato de retención, a 3 meses pagos: 3 × $17.836 = $53.508, menos $29.000 de IA del piloto gratis = **tope de ~$24.500 por piloto que pasa a pagar.**

**Tres números por semana:**
1. **Visitas o DMs → pilotos firmados.** Menos de 1 cada 10 → cambiar mensaje o zona. Contar cuántos dicen «sin WhatsApp, no» (evidencia que pide el directorio).
2. **Ventas verificadas por piloto.** Día 14 sin ninguna → revisar dónde está el link y cuántas conversaciones entran.
3. **Costo de IA por comercio.** Alarma si pasa de USD 2,5/semana (supuesto del CFO: USD 10/mes).

Siguiente: `/founder-brand`, después `/founder-launch`.

## Brand

> Brief: posicionamiento A de `marketing.md` (el ferretero de barrio que quiere vender fuera de horario; cotiza con su lista real y cobra verificado, sin tienda online). Los socios descartaron los nombres genéricos (Vendí, Mostrador, Dale…).

### 1. Diez candidatos

| Nombre | Estilo | Qué dice | En voz alta / en un cartel o ícono | Riesgo |
|---|---|---|---|---|
| **Hornel** | Evocativo (hornero) | El pájaro que se construye la casa con barro: laburo, obra, algo de acá | «or-NÉL», corto; el hornero como mascota se lee a 32 px | Parecido a Hormel (alimentos, otra clase); puede sonar a panadería |
| **Pingüe** | Palabra real | «Abundante, que rinde» (ganancia pingüe); el pingüino como mascota | Simpático, pero muchos no conocen la palabra | La ü: dominio y handles quedan «pingue»; pingue.com parece tomado |
| **Dinga** | Inventado (campanita de mostrador, «ding») | Te avisa que entró una venta | Suena bien y es corto | dinga.app parece tomado; revisar si tiene otra acepción regional |
| **Toquín** | Inventado (el toque de la campanita) | Diminutivo cálido | Se pronuncia fácil; la tilde se pierde en dominios | Poco claro sin la mascota |
| Presupuesto Vivo | Descriptivo | Precio actualizado | Largo para ícono | Genérico; difícil de registrar |
| materialIA | Descriptivo + «IA» | Materiales + inteligencia artificial | Se lee raro en voz alta | «IA» envejece; suena a corralón |
| Bulón | Evocativo (rubro) | Pieza de ferretería | Muy de mostrador | Palabra común; difícil de registrar sola |
| Yunque | Evocativo | Sólido, de taller | Fuerte | No dice nada de vender |
| Cuadra | Lugar | El comercio de tu cuadra | Cercano | Genérico; seguro registrado en otras clases |
| TomMa | Nombre de los socios | Tomás + Matías | Se lee confuso | No dice nada al ferretero |

### 2. Shortlist y chequeos a correr (los hacen ustedes)

**Shortlist: Hornel, Pingüe, Toquín.** Dinga queda de reserva, porque dinga.app ya tiene servidores de nombres.

Señal de DNS que corrí el 05/11/2026 (`dig NS`). Que un dominio no tenga NS **no prueba que esté libre**:
- hornel.com, hornel.com.ar, hornel.app: sin NS.
- pingue.com: **tiene NS (probablemente tomado)**. pingue.com.ar y pingue.app: sin NS.
- toquin.com.ar, toquin.app: sin NS. toquin.com: no lo pude chequear (el whois no respondió).

**Chequeos, para cada nombre de la shortlist:**
1. **Marca en INPI Argentina** (argentina.gob.ar/inpi, búsqueda de marcas en su portal de trámites). Buscar idéntico y fonético en la **clase 9** (software), la **35** (venta, gestión comercial, publicidad) y la **42** (software como servicio, sugerida). Si piensan salir afuera: EUIPO o USPTO, mismas clases.
2. **Dominios:** .com.ar en nic.ar; .com y .app con un registrador o en lookup.icann.org. Alternativas: hornel.ar, holahornel.com, hornel.chat.
3. **Handles:** Instagram, TikTok, X, YouTube y Facebook. Si el exacto está tomado: @hornel.ar o @holahornel.
4. **Confusión con competidores:** ninguno se parece a notchatbot, Chat Nube, Darwin, Botmaker, Leadsales, Cliengo ni Kommo.

Esto son búsquedas públicas, no asesoramiento legal. Una agente o un abogado de marcas tiene que confirmarlo, y **nada está registrado hasta que ustedes lo registren**.

**Recomendado: Hornel.** El hornero construye, igual que el cliente del corralón. Es local sin caer en lo genérico, la mascota funciona en un ícono de 32 px, no tiene caracteres raros y las tres terminaciones dieron limpio en DNS. Contra: si mañana van a ropa o comida, la imagen de obra achica. Pero el directorio pidió un solo rubro.

### 3. Promesa, tagline y voz

**Promesa:** atiende tu negocio cuando vos no llegás, y nunca inventa un precio.

**Taglines:**
1. «Tu mostrador, abierto de noche.» (recomendada)
2. «Vende con tus precios. No inventa.»
3. «Laburá menos con el celular.»

**Voz:**
| Adjetivo | Sí | No |
|---|---|---|
| **De mostrador** | Hablar como el ferretero: «¿tenés el flexible de 40?» | «Soluciones omnicanal con IA conversacional» |
| **Honesta** | «Todavía no anda en WhatsApp.» | «Integración total», «nunca se equivoca» |
| **Laburadora** | Mostrar el trabajo hecho: «3 pedidos pagados anoche» | Prometer ganancias o «vendé el doble» |

**Antes** (`pitch-v1.md`): «Un vendedor por chat para tu ferretería que atiende a tus clientes las 24 horas con tu lista de precios y tu stock reales.»
**Después:** «Mientras dormís, Hornel les contesta a tus clientes con tus precios de verdad. Si duda, te espera.»

### 4. La identidad, como brief

**Colores:**
| Rol | Hex | Uso | Contraste |
|---|---|---|---|
| Barro (primario) | `#8C3B12` | Logo, botones, títulos | Sobre crema 7,1:1; texto blanco encima 7,6:1 (AA) |
| Crema (fondo) | `#FBF6EE` | Fondos, cartel | Tinta `#1E1A16` encima: 16:1 |
| Verde pagado | `#1F6B3A` | **Sólo** el estado «pagado verificado» | Blanco encima 6,5:1 (AA) |
| Ocre (acento) | `#E8A33D` | Detalles, campanita | Sólo con texto oscuro (8:1). **Blanco encima falla (2,2:1)** |

Falta chequear que no se parezca a las paletas de los competidores. No las revisé.

**Tipografía:** Bricolage Grotesque para títulos y Atkinson Hyperlegible para texto. Las dos son libres (licencia OFL) y están en Google Fonts. Atkinson se lee bien en un celular viejo, que es el que tiene este comprador.

**Logo:** un hornero sobre su nido de barro, con el nido en forma de globo de chat. Tiene que funcionar a 32 px (ícono y botón del chat), en un QR de mostrador impreso en blanco y negro y en una vidriera. Evitar robots, cerebros, chispas de «IA», tornillos y martillos genéricos, y cualquier parecido con logos de competidores. No tengo una herramienta de imágenes en esta sesión. Si generan conceptos con una, son conceptos, no un logo final.

**El cliente final ve la marca del comercio.** Hornel aparece chico («con Hornel»), porque el que vende es la ferretería.

### 5. Las primeras cinco cosas que ve un cliente

1. **Inicio:** «Tu mostrador, abierto de noche.» Abajo, una demo rotulada «catálogo de ejemplo» y el botón «Quiero ser piloto (quedan N)», con el número real.
2. **El «envase»:** QR de mostrador y calco de vidriera para el comercio: «¿Cerrado? Pedí acá. Precio y stock reales.»
3. **La confirmación:** «Pago confirmado por Mercado Pago. Tu pedido está pagado.» o «Recibimos tu comprobante. El comercio está verificando la transferencia.» Nunca dice «pagado» antes de tiempo.
4. **Primer post:** «Qué es y qué no es Hornel», con «todavía no anda en WhatsApp» dicho de frente.
5. **Respuesta a la primera queja:** «Tenés razón, eso no estuvo bien. Lo revisamos hoy y te contamos qué pasó y qué cambiamos. Firma: Tomás.» Sin plantillas ni excusas.

Siguiente: `/founder-ops` y `/founder-launch` (ya existen: actualizarlos con el nombre cuando esté confirmado).

## Operations

> SaaS de 2 socios, no un local. Precios vistos el 05/11/2026; lo marcado **ESTIMACIÓN** no está verificado. No es consejo legal ni impositivo.

### 1. El ciclo de cada día (★ = lo ve el comercio o su cliente)
1. Revisar alertas de la noche: caídas, errores del agente, pagos con webhook pendiente.
2. Mirar derivaciones (`requires_human`) sin respuesta del dueño y avisarle por su canal (no se escribe al cliente final).
3. ★ El agente atiende 24 h: consulta → carrito → link de pago → pago verificado.
4. ★ Soporte a dueños (horario fijo, ver §3).
5. Revisar costo de IA del día por comercio contra su tope (`AI_DAILY_*`).
6. Cierre: anotar incidentes y pedidos con pago no conciliado.

### 2. Proveedores
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

### 3. Personas (los dos socios)
Sueldos: **no informados** (el CFO usa $0). Cargas, monotributo o relación de dependencia: con el contador.

| | Tomás | Matías |
|---|---|---|
| Lun–vie 9–13 | implementación de comercios nuevos | soporte + revisar derivaciones |
| Lun–vie 14–18 | producto / correcciones | implementación / visitas |
| Guardia fuera de horario | semanas pares | semanas impares |

- **Mes 1 (10 pilotos):** ~4 h por implementación + 1 h/semana de soporte por comercio (**ESTIMACIÓN**) ≈ 40 h de alta + 10 h/semana.
- **A 40 comercios:** ~40 h/semana sólo de soporte si se mantiene 1 h/comercio. Medirlo en el piloto: decide si hace falta un tercero.
- Regla: un cambio a `main` lo revisa el otro socio; nunca deployar en guardia sin avisar.

### 4. Rutinas
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

### 5. Herramientas
Supabase + hosting + Ollama + Resend + MP (§2). Gestión: el propio panel (CRM) para los pilotos; facturación: la que indique el contador vía ARCA (gratis en su web); monitoreo de uptime con un plan gratuito (**a elegir**).

### 6. Legal a CHEQUEAR (no afirmado)
- [ ] Tipo de sociedad (SAS, SRL o monotributo de cada socio) e inscripción en ARCA (ex AFIP); factura a cada comercio. Confirmar con contador.
- [ ] Ley 25.326: inscribir la base en el [Registro Nacional de Bases de Datos de la AAIP](https://www.argentina.gob.ar/node/53779) (trámite a distancia con clave fiscal nivel 2+, según su [instructivo](https://www.argentina.gob.ar/sites/default/files/instructivo_tad_inscripcionymodificacion_basesprivadas_3.pdf)). Definir quién es responsable y quién encargado del tratamiento de los datos de los clientes finales (comercio vs. nosotros).
- [ ] Términos de servicio, política de privacidad y contrato de encargado con cada comercio. Abogado.
- [ ] Términos de Mercado Pago para plataformas que generan cobros por terceros (cada comercio con su cuenta).
- [ ] Meta Business (verificación del negocio, WhatsApp Business Platform) **sólo si** se decide WhatsApp.
- [ ] Ingresos Brutos según jurisdicción. Las normas cambian; confirmar todo con la autoridad o un profesional.

### 7. Riesgos
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

### Preguntas abiertas
Proveedor de hosting y su precio real; tarifa oficial de MP; sueldos; tipo de sociedad; costo real de IA por comercio.

## Launch plan

> Arranque: semana del **09/11/2026**. T = Tomás, M = Matías. Las líneas de éxito son **metas propuestas por nosotros**, no datos: el panel fue simulado (15% de compra, casi todos los «no» por WhatsApp). Si el piloto real da otra cosa, manda el piloto.

### 1. El test barato: 10 pilotos en zona sur del GBA
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

### 2. Cuenta regresiva
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

### 3. Run sheet del 07/12
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

### 4. Los primeros 30 días
**Semanal:** conversaciones, % a pago verificado, comercios con al menos una venta, costo de IA por comercio, share link vs. WhatsApp, horas de soporte por comercio (`ops.md` supone 1 h/semana).

- **Día 7 (14/12):** ¿los 10 tienen el link visible? ¿Cuántas conversaciones por comercio? Si un comercio tiene 0 conversaciones, el problema es el canal, no el agente.
- **Día 14 (21/12):** ¿cuántos tienen la primera venta verificada? ¿Algún precio inventado o vencido llegó al cliente? (debe ser 0). ¿Costo de IA dentro de USD 10?
- **Día 30 (06/01/2027):** primera lectura de la compuerta. ¿Qué dicen los dueños sobre pagar $35.000 en febrero?
- **Mes 3 (≈ febrero 2027):** primer cobro. Retención real y decisión final.

### 5. Compuerta de decisión (día 30 y confirmación al mes 3)
- **WhatsApp primero** si el share link/WhatsApp queda **< 15%** en al menos 7 de 10 comercios, **o** si 6 o más dueños dicen que no pagan sin WhatsApp. Entonces se prioriza el canal WhatsApp: **requiere que los dos socios cambien por escrito el alcance del proyecto** (hoy «NO WhatsApp» es regla del proyecto), cuenta y verificación en Meta Business, y rehacer costos con el CFO. No se suman comercios hasta tenerlo.
- **Seguir con web y abrir otra zona** si el share es ≥ 30%, la conversión ≥ 5% y al mes 3 pagan 6 o más.
- **Zona gris** (entre ambos): ajustar la oferta (QR en mostrador, mensaje de bienvenida, precio $25.000 vs. $35.000) y medir 30 días más.

Siguiente: `/founder-plan`.

_The panel is simulated buyers and the numbers are projections from your inputs. Confirm demand with real customers and costs with real quotes before you spend. Not financial, legal or tax advice._
