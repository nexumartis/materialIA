# materialIA (nombre de trabajo; candidato de marca: Hornel) · Business plan

**Verdict: Profitable**

- ✓ Each comercio-mes (suscripción) earns $17836.00 before fixed costs (51% contribution).
- ✓ Year 1 operating profit: $2,644,168.
- ✓ Break-even is 8 comercio-mes (suscripción)s a day against a capacity of 100000.
- ✓ 16 of 50 simulated buyers buy (32%, the bar is 25%).

| key number | |
| --- | ---: |
| Price | $35000.00 a comercio-mes (suscripción) |
| Profit margin at plan | 41% per comercio-mes (suscripción) |
| Break-even | 8 comercio-mes (suscripción)s a day |
| Year 1 operating profit | $2,644,168 |
| Startup spend | $300,000 |
| Cash needed before it pays for itself | $424,112 |
| Startup money earned back | month 7 |
| Buyer panel | 16 buy · 34 pass |

## The idea

- What it is: un agente de ventas con IA que atiende a los clientes de un comercio **dentro de su propio WhatsApp** (y también en su web/Instagram con un link) y cierra la venta de punta a punta: consulta → carrito → entrega → cobro verificado, con el stock y los precios reales del negocio.
- Who it is for: comercios PyME de Argentina que hoy contestan a mano por WhatsApp. Multi-rubro, con módulos que se prenden según el negocio: **ropa e indumentaria** (envío por correo, talles), **electro con entrega e instalación** (reparto propio, franjas, señas), **colchones y muebles** (entrega coordinada, medidas), **ferretería y sanitarios** (fotos de repuestos, stock), **muebles a medida** (seña antes de fabricar), **farmacia y perfumería** (sólo venta libre: lo que requiere receta no se vende por chat), **juguetería y regalería**, **comida y rotisería**, **librería** y **bazar/deco**. Muchos no tienen tienda online; sí un catálogo en planilla o un sistema de gestión.
- What it sells, at what price: suscripción mensual al agente + panel. Precio a testear: **$35.000/mes + IVA** (rango aceptable de un panel anterior: $10.000–$50.000). Aparte, los mensajes de WhatsApp que cobra Meta los paga **cada comercio en su propia cuenta de Meta**: responder a un cliente que escribió (ventana de 24 h) no tiene costo de Meta; las campañas (carritos abandonados, promociones) sí, y el panel avisa el costo antes de enviar (precios de Meta a verificar en su tabla vigente).
- Where and how: online, Argentina. El comercio se registra, conecta **su número de WhatsApp con la API oficial de Meta** (alta integrada, sin bots no oficiales que arriesgan el número), carga su catálogo (Excel/Google Sheets) y elige sus módulos. Los socios hacen la puesta en marcha de los primeros comercios.
- Budget and constraints: dos socios fundadores técnicos; producto construido en local (WhatsApp por integrar: requiere cuenta de Meta Business verificada y aprobación de la app). Sin clientes pagos ni deploy. Sueldos y presupuesto de marketing: no informados. Reglas del producto: nunca inventa precios ni stock; un pedido es «pagado» sólo con pago verificado.

## Summary

**Veredicto de la herramienta: Profitable** — con una advertencia grande: los números NO incluyen sueldos de los socios (no informados). Con dos sueldos de $2 M/mes el equilibrio es **232 comercios a $35.000** o **79 a $70.000**, y el año 1 pierde plata en ambos casos.

**Qué es:** un vendedor con IA dentro del WhatsApp del comercio (API oficial de Meta, su mismo número) que cotiza con su lista y stock reales, arma el pedido, coordina la entrega y cobra verificado. Multi-rubro con módulos.

**Los números** (proyección, costos estimados en `cfo.md`): a $35.000/mes cada comercio deja **$17.836 (51%)**, equilibrio sin sueldos **8 comercios**, año 1 **$2,6 M**. A **$70.000** (precio que propone `founder/README.md`): deja **$52.836 (75%)**, equilibrio **3**, año 1 **$11 M** sin sueldos.

**El panel con WhatsApp: 16 de 50 compran (32%)**, contra 15% sin WhatsApp. WhatsApp sacó del medio la objeción número uno.

**Por rubro** (5 compradores cada uno: poco para concluir, sirve para elegir a quién visitar primero):

| rubro | compran |
|---|---|
| Electro con entrega e instalación | 4 de 5 |
| Bazar y deco | 3 de 5 |
| Colchones y muebles estándar | 3 de 5 |
| Ropa | 2 de 5 |
| Comida, juguetería, librería, farmacia | 1 de 5 cada uno |
| **Ferretería y sanitarios** | **0 de 5** |
| Muebles a medida | 0 de 5 |

**Atención:** el segmento que hoy propone `founder/README.md` (sanitarios de CABA) salió **último** en el panel simulado. No lo descarta (son 5 simulados), pero conviene que las charlas reales incluyan también electro con instalación y colchones/muebles.

**Por qué no compran (34):** confianza (18): «ya pagué sistemas que quedaron juntando polvo», miedo a que la IA diga un precio, talle, medida o fecha equivocada, o a perder el número; precio (6): otro gasto fijo, pagar sólo en temporada; hábito (4): «tengo mi sistema de gestión y no cargo otra lista»; necesidad (4): lo a medida igual vuelve al dueño.

**Lo que dio vuelta un «no», repetido:** verlo andar en un comercio conocido de su rubro; conexión directa a su sistema de gestión (sin planilla aparte); que lo dudoso (medidas, fechas, salud) siempre pase al dueño; poder pausarlo fuera de temporada; diferenciarse del asistente gratis de Meta.

**Precio** (Van Westendorp, 50): rango aceptable **$10.175 a $45.184**; medianas: barato $18.000, caro $35.000, demasiado caro $60.000. **$70.000 queda arriba del rango para la mayoría**, salvo electro y colchones/muebles (sus «demasiado caro» llegan a $110.000–$120.000).

**Lo próximo:** las charlas reales de `founder/README.md`, sumando electro y colchones; un caso de referencia por rubro; conexión a sistemas de gestión como prioridad de producto; y definir sueldos para que el CFO sea real.

> Compradores simulados (tienden a decir que sí: el 32% es un techo) y proyecciones con costos estimados. No reemplazan las charlas con dueños.

## The competition

> **Antecedente del 05/11/2026.** Para alcance, precio y próximos pasos leer [README](README.md) y la investigación del 09/11. Cifras, garantías, marca y calendario de este análisis no son acuerdos vigentes ni validación con clientes.

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

**16 buy · 34 pass** (32% buy) out of 50 simulated buyers. Seed 535679, so the same cards can be dealt again.

These are simulated buyers, not customers. Use this to find objections and weak spots, then confirm the big ones with real people before you spend.

### By segment

| group | buyers | buy rate |
| --- | ---: | ---: |
| Electro con entrega e instalación (reparto propio) | 5 | 80%  (thin) |
| Bazar, deco y artículos para el hogar | 5 | 60%  (thin) |
| Colchones y muebles estándar (entrega coordinada) | 5 | 60%  (thin) |
| Ropa e indumentaria (local + Instagram, envía por correo) | 5 | 40%  (thin) |
| Comida y rotisería (pedidos y delivery) | 5 | 20%  (thin) |
| Juguetería y regalería | 5 | 20%  (thin) |
| Librería, papelería y artículos escolares | 5 | 20%  (thin) |
| Farmacia y perfumería (sólo venta libre y perfumería por chat) | 5 | 20%  (thin) |
| Ferretería y sanitarios de barrio | 5 | 0%  (thin) |
| Muebles a medida (seña o anticipo antes de fabricar) | 5 | 0%  (thin) |

### By buying behaviour

| group | buyers | buy rate |
| --- | ---: | ---: |
| Quiere crecer y vender más | 8 | 100% |
| Contesta todo él mismo por WhatsApp | 13 | 38% |
| Cuida cada peso | 10 | 30% |
| Desconfiado de la tecnología | 7 | 0%  (thin) |
| Fiel a su sistema de gestión | 7 | 0%  (thin) |
| Delega en un hijo o empleado | 5 | 0%  (thin) |

### By income

| group | buyers | buy rate |
| --- | ---: | ---: |
| $23,034,000 and up | 17 | 41% |
| $12,991,000 to $23,034,000 | 17 | 29% |
| under $12,991,000 | 16 | 25% |

### Why they pass

| reason | buyers | in their words |
| --- | ---: | --- |
| trust | 18 | "Ya pagué sistemas que quedaron juntando polvo, y con las ventas como están no me cargo otro gasto fijo por algo que no vi andar con mis clientes. Si me lo dejan los dos meses gratis capaz lo pruebo, pero pagar, hoy no." (P002) · "Mis clientes me conocen hace años y me mandan una foto de un cuerito o una canilla vieja; si les contesta una máquina que se equivoca de medida, el que queda mal soy yo. Aunque sea gratis dos meses, no le entrego mi número a algo que no vi andar." (P003) |
| price | 6 | "Con las ventas como están, no sumo otro gasto fijo mensual para algo que hoy hago yo misma desde el celular. Los dos meses gratis los probaría capaz, pero pagar $35.000 más IVA todos los meses después no lo veo." (P001) · "A mí el WhatsApp me explota en Día del Niño, Navidad y vuelta a clases; el resto del año lo contesto yo sin drama. Pagar $35.000 más IVA todos los meses por algo que necesito tres o cuatro meses al año no me cierra, y lo de los 2 meses gratis lo pruebo capaz, pero no me comprometo a pagar después." (P006) |
| habit | 4 | "La plata no es el problema, pero mi stock y mis precios viven en mi sistema de gestión y no voy a mantener otra lista aparte. Además, en electro con instalación, si la IA le promete al cliente un día de entrega o que la heladera entra en un hueco, el que queda mal soy yo." (P023) · "Ya tengo mi sistema de stock y facturación y no pienso cargar miles de artículos de librería otra vez en otro lado; dice 'desde tu sistema' pero no dice cuál, y si termino manteniendo dos catálogos me genera más trabajo del que me ahorra. Además mis clientes, sobre todo en temporada escolar, quieren hablar con una persona." (P026) |
| need | 4 | "Yo hago muebles a medida: casi todo lo que me consultan es a medida, así que este vendedor me lo va a pasar a mí igual y termino contestando yo. Ya pagué sistemas que quedaron juntando polvo, y no voy a meter otro para que me reenvíe mensajes." (P027) · "Lo mío es casi todo a medida: cada mueble lo tengo que medir y presupuestar yo, así que el bot me pasaría la mayoría de las consultas igual. Y la tecnología no la manejo yo; si nadie de confianza me lo recomienda, no lo pruebo por un anuncio." (P035) |
| convenience | 2 | "Que me lo carguen la primera vez está bien, pero en ropa cada prenda tiene talles y colores que se agotan todos los días, y la mitad lo vendo en el local. No tengo tiempo de andar actualizando una planilla para que el bot no le venda a alguien un talle que ya no tengo." (P025) · "Dice 'desde tu sistema', pero no me dice si es el mío; si termino cargando el menú y los precios otra vez en un Excel aparte, no lo quiero, ni gratis. Y $35.000 más IVA todos los meses para una rotisería es plata que tiene que volver en pedidos, no en promesas." (P031) |

### Why they buy

| reason | buyers | in their words |
| --- | ---: | --- |
| convenience | 8 | "Contesto todo yo desde el celular entre cliente y cliente y de noche sigo respondiendo precios y stock; si me lo dejan andando con mi lista y los dos primeros meses son gratis, lo pruebo. Después de eso, $35.000 + IVA lo pago sólo si de verdad me saca las consultas repetidas de encima." (P008) · "Me paso el día contestando precios entre cliente y cliente y de noche sigo con lo que quedó; si me lo dejan andando gratis dos meses, lo pruebo. Pero lo pruebo, no lo compro todavía: si al tercer mes no vi que vendió solo, lo corto." (P014) |
| need | 7 | "Se viene Navidad y de noche me escriben preguntando si tengo tal juguete y a qué precio, y para cuando contesto ya compraron en otro lado. Con dos meses gratis y que me lo dejen andando, lo pruebo justo en la temporada fuerte." (P005) · "Me paso las noches contestando lo que quedó del día, y si me lo dejan andando con mi lista y dos meses gratis, lo pruebo; $35.000 al mes es menos de lo que pierdo en una heladera que se va a otro negocio porque contesté tarde. Pero lo pruebo con la mano en el freno, no lo largo solo." (P009) |
| price | 1 | "Si son dos meses gratis y me lo dejan andando con mi lista, lo pruebo; no pierdo nada y me saco de encima las consultas de precio y de cuándo llega la heladera. Pero lo pruebo con el dedo en el botón de dar de baja." (P019) |

### What would flip a no

- Que en los meses gratis me demuestre con números que entraron pedidos de noche que yo hoy pierdo, y que actualizar el menú del día me lleve un minuto desde el celular.
- Verlo funcionando con mi propio catálogo y mis clientes reales en los meses gratis, sin dejar tarjeta, y que en temporada (Día del Niño, Navidad) me haga vender más de lo que cuesta.
- Verlo andando en otra ferretería de barrio que conozca, y poder seguir contestando yo desde mi celular cuando quiera, con el robot sólo de noche.
- Probarlo con mi menú real un fin de semana de mucho movimiento y ver que nunca promete un horario de entrega ni toma un pedido especial sin pasármelo a mí y sin seña.
- Poder pagarlo sólo los meses de temporada (activarlo y pausarlo sin penalidad) y ver en la prueba gratis que me cerró ventas que yo no hubiera llegado a contestar.
- Verlo funcionando con mi catálogo durante la prueba gratis y comprobar que en lo a medida no promete nada, sólo cobra la seña y me lo pasa a mí con el resumen.
- Un precio cerrado en pesos sin nada por consumo, que pueda pagar sólo en los meses de temporada escolar (febrero-marzo), y verlo armar bien un pedido a partir de la foto de una lista de útiles.
- Que me muestren funcionando con mi propio sistema de gestión, leyendo el stock de ahí sin cargar nada a mano, y poder ver conversaciones reales de otro comercio donde el cliente no note que es un robot.
- Verlo andando en otra farmacia conocida, con la opción de que sólo conteste precio, stock y envíos y que todo lo que sea consulta de salud me lo pase a mí sin responder nada.
- Ver funcionando a otra tienda de ropa como la mía, con su número, y que yo pueda probarlo primero sólo de noche con las consultas que quedan sin contestar, apagándolo cuando quiera.
- Que otro librero que conozco lo use y me diga que le sirvió en temporada escolar, y que ustedes me carguen el catálogo y mi hijo lo pueda manejar sin depender de mí.
- Verlo andar una semana con mi catálogo real, en mis consultas de verdad, y que me muestren lado a lado qué hace que el asistente gratis de Meta no hace, sin que se equivoque en precios.

Buyers say they would buy **1.0 times** in the first month on average.

50 buyers gave all four price answers. Run founder-pricing's van_westendorp.py on the answers folder.

## The numbers

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

## Not done yet

- What the board said: run /founder-board
- Pricing: run /founder-pricing
- The offer: run /founder-offer
- Marketing: run /founder-marketing
- Brand: run /founder-brand
- Operations: run /founder-ops
- Launch plan: run /founder-launch

_The panel is simulated buyers and the numbers are projections from your inputs. Confirm demand with real customers and costs with real quotes before you spend. Not financial, legal or tax advice._
