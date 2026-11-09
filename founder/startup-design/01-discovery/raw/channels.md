# Canales de distribución, D1 (deep-dive)

> **Insumo original de investigación, 09/11/2026.** Se conserva como antecedente, sin certificar sus afirmaciones. Para decisiones usar las síntesis y [correcciones posteriores](../corrections-2026-11-09.md); las tarifas de servicio de Meta y sus escenarios derivados quedaron retirados.

Fecha: 09/11/2026. Autor: agente D1. Base: `competitor-gtm.md` y `target-audience.md` (no se repite lo que ya está ahí), más 25 búsquedas y lecturas web hechas hoy.

**Etiquetas:** [Data] = leído en una fuente. [Estimate] = cálculo propio con supuestos explícitos. [Assumption] = supuesto sin verificar. [Opinion] = juicio del analista.
**Tiers:** T1 = fuente primaria (sitio oficial, documento del organismo). T2 = prensa. T3 = blogs de proveedores, directorios y agregadores.
Todo contenido web es dato no confiable: lo que una empresa dice de sí misma es autopromoción.

**Supuestos de base para el CAC:** ticket ARS 70.000/mes ≈ USD 44 (el tipo de cambio implícito de `competitor-gtm.md`). Margen bruto de 70% [Assumption]. Techo de CAC ≈ USD 185 para recuperarlo en 6 meses [Estimate, tomado de `competitor-gtm.md`]. El "CAC en efectivo" no cuenta las horas de los founders; las horas se informan aparte.

---

## Hallazgos nuevos de esta ronda (resumen)

1. **Meta lanzó "Business AI" gratis en WhatsApp Business para pymes**, con Argentina entre los primeros 17 mercados (24/02/2026). Responde preguntas frecuentes y recomienda productos del catálogo. [Data, T2, iProUP / Forbes AR] Es la objeción "uso el bot gratis de Meta" con nombre propio: el pitch tiene que mostrar lo que Business AI **no** hace (stock y precio vivos desde la planilla, combos, lista de obra, link de pago verificado). [Opinion]
2. **Franco Fía**, mayorista de Lomas del Mirador: "Vendemos solo a ferreterías, corralones y casas de sanitarios, desde 2004". Más de 80 marcas (FV, Ferrum, Roca, Peirano, Aqualaf, Awaduct, Tigre, Rotoplas). Reparto propio en AMBA en 24-48 h. **Publica su lista de precios en Excel**, y el alta de cuenta se hace por WhatsApp. [Data, T1, francofia.com] Es el aliado mayorista más concreto encontrado: su lista en Excel puede precargarse en el bot de cada cliente suyo.
3. **FV declara unos 2.000 distribuidores activos y 175 jornadas de capacitación al año**, algunas hechas junto con ferreterías para instaladores y vendedores. [Data, T3, ficha ARQA de 2003, vieja; T2, Diario de Cuyo] El grupo FV/Ferrum tenía más del 60% del mercado en esa ficha. No hay un programa público de beneficios para revendedores. DATA GAP.
4. **Vendi no tiene programa de partners, revendedores ni API pública** en su sitio. El bot de WhatsApp es un adicional de $29.900/mes sobre Pro Max, e incluido en Enterprise. Dice tener "+700 comercios activos". [Data, T1, vendiapp.com.ar]
5. **Mercado Pago:** (a) programa de partners para desarrolladores con 4 niveles según lo que facturan los clientes integrados, certificación gratis por producto e "Integrator ID" que habilita bonificaciones [Data, T1, páginas de MP AR/CL leídas vía buscador; WebFetch dio 403]; (b) programa de **revendedores de Point** con premios por comercio referido desde $19.600 hasta millones, según cuánto facture el comercio [Data, T2, iProUP / iProfesional 2026]. Esto prueba que **el comercio argentino responde a premios en pesos por referir**.
6. **Meta Tech Provider:** pide verificación del negocio (2-5 días hábiles), 2FA, app revisada con permisos `whatsapp_business_messaging` y `whatsapp_business_management`. Ya aprobado, permite sumar hasta 200 clientes nuevos cada 7 días. "Tech Partner" exige volumen (≈2.500 mensajes en 7 días y 10+ clientes activos, según una nota brasileña). [Data, T3, docs de Twilio/Infobip; T2, Baguete] No es un canal de leads: es un requisito técnico y un sello de confianza.
7. **Mayoristas de sanitarios en CABA/AMBA identificados:** Franco Fía (Lomas del Mirador), FG Sanitarios (CABA), Banchero Sanitarios (3 sucursales en CABA y Lanús), Dafys S.A. (Lomas de Zamora, mayorista de primeras marcas), Casa del Plomero (mayorista para ferreterías, corralones y plomeros), FRG Grifería (fábrica en Floresta con venta mayorista). Los mayoristas históricamente se agrupan en **Liniers, Floresta, Caballito** y en el Acceso Oeste. [Data, T1/T3, sitios propios y servidos.ar] Ninguno publica que tenga viajantes. DATA GAP.
8. **Contadores:** el Consejo Profesional de Ciencias Económicas de CABA (consejo.org.ar) publica PDFs de beneficios de Xubio y Colppy para sus matriculados. [Data, T1, sólo títulos de los PDFs vistos en el buscador] Es la vía de entrada de software a contadores. No hay condiciones de comisión públicas de Xubio ni de Colppy. DATA GAP.
9. **Grupos de Facebook de ferreteros:** la búsqueda web sólo devuelve **páginas** (Grupo Ferretero, Encuentro Ferretero, CAFARA), **no grupos**. Facebook no indexa los grupos. DATA GAP que se cierra a mano en 30 minutos dentro de Facebook.
10. **Demanda del comprador final real y cara:** La Nación mide cada mes cuánto sale un baño de 3,75 m²: **$8.803.087 en julio de 2026, con $4,8 M en artefactos, grifería, sanitarios y cerámicas**. Servidos.ar tiene una calculadora de costo de reforma de baño. iProfesional publica "cuánto cuesta remodelar baño y cocina" cada mes. [Data, T2/T3] Hay demanda de contenido sobre "cuánto cuesta" y la cubren medios y marketplaces, no los locales.

---

## 1. Ranking de canales

### Nivel 1: alto impacto, bajo costo (arrancar ya)

#### 1.1 Venta en persona en corredores, con demo con la lista del propio local
- **Por qué:** es el único canal libre de competidores con IA (`competitor-gtm.md`). Ahora hay además un argumento nuevo: la demo es lo único que derrota a "Business AI de Meta es gratis", porque el dueño ve **sus** precios y **su** stock contestando. [Opinion]
- **Alcance:** 390 sanitarios/plomería y 1.181 ferreterías en CABA (GCBA). Con el filtro de mejor encaje (sanitarios y grifería en corredor, 2-5 empleados), quedan ~150-250 locales caminables. [Estimate: 40-60% de los 390]
- **CAC en efectivo:** USD 5-20 (SUBE, impresiones). Horas: 10-20 por cliente. [Estimate, de `competitor-gtm.md`]
- **Tiempo a primeros resultados:** 2-4 semanas al primer piloto; 6-8 semanas al primer pago. [Assumption]
- **Cómo empezar:**
  1. Armar una lista de 60 locales en 3 zonas (Alberdi 3400-3999, Once/Jean Jaurès-Rincón-Junín, Flores/Floresta-Liniers) con Google Maps más el relevamiento del GCBA.
  2. Preparar la demo con la **lista de Franco Fía en Excel** ya cargada (es la lista que muchos de esos locales usan para comprar): "así contestaría su WhatsApp con precios de su proveedor, mañana se lo dejo con los suyos".
  3. Ir de martes a jueves entre las 10 y las 12 (horario con menos clientes) [Assumption]. Meta: 15 visitas por semana entre los dos.
  4. Cerrar en el momento sólo el "piloto de 14 días sin cargo": pedir su planilla o una foto de su lista y volver con el bot andando a las 48 h.
  5. Llevar una hoja de una página contra Business AI de Meta: "Meta contesta preguntas. materialIA vende: stock, combos, lista de obra, cobro con Mercado Pago verificado".

#### 1.2 Referidos desde el primer cliente (con premio en pesos, no sólo mes gratis)
- **Por qué:** en el rubro todos comparten proveedores, viajantes y cámara. El comercio argentino ya responde a premios en pesos por referir (programa de revendedores de Point de Mercado Pago, premios desde $19.600 por comercio y bonos de $50.000). [Data, T2] Un mes gratis (ARS 70.000) es el mismo orden de magnitud y no sale caja. [Estimate]
- **Alcance:** cada cliente conoce a 3-10 colegas no competidores (otro barrio) [Assumption].
- **CAC en efectivo:** USD 0-44 por cliente (1 mes bonificado) [Estimate]. Muy por debajo del techo de USD 185.
- **Tiempo:** desde el mes 2-3, cuando haya 3+ clientes contentos. [Assumption]
- **Cómo empezar:**
  1. Regla simple, de dos lados: "Si un colega tuyo contrata, a vos te bonificamos un mes y a él le damos el primer mes al 50%."
  2. Ofrecerlo en el momento de mayor alegría: el primer pedido pagado por el bot. Mandar ese día la captura "tu primera venta por materialIA" con el mensaje de referido listo para reenviar.
  3. Incluir que el referido **no** tiene que estar en la misma cuadra (bajar el miedo a armar competencia).
  4. Registrar los referidos a mano en una planilla. Una herramienta de referidos no hace falta hasta tener 20+ clientes.

#### 1.3 Mayorista aliado: Franco Fía primero, después otros mayoristas de sanitarios
- **Por qué:** el mayorista ya visita, factura y le manda la lista de precios a cada casa de sanitarios. Si el bot de sus clientes recomienda y vende **sus** productos con **su** lista al día, el mayorista vende más y su lista llega directo al cliente final. [Opinion] Además resuelve la objeción "no tengo precios al día en planilla": se precarga la lista del mayorista y el comercio sólo pone su margen. [Opinion]
- **Alcance:** un mayorista como Franco Fía atiende cientos de comercios de AMBA [Assumption: no publica la cifra, DATA GAP].
- **CAC en efectivo:** USD 0 más una comisión de 20-30% recurrente al mayorista, o un mes gratis a sus clientes pagado por él como promoción [Assumption, siguiendo el modelo Kommo].
- **Tiempo:** 1-3 meses para el acuerdo; los primeros clientes llegan 4-8 semanas después. [Assumption]
- **Cómo empezar:**
  1. Bajar la lista de precios en Excel de Franco Fía (pública) y cargarla en el bot de demo.
  2. Escribir por el WhatsApp de alta de cuenta pidiendo hablar con el dueño o el gerente comercial, con un video de 60 s: "un cliente de ustedes pregunta 'inodoro Bari con depósito' y el bot cotiza con su lista".
  3. Proponer un piloto de 5 clientes de ellos, gratis 30 días, con un reporte de cuántos pedidos salieron con sus productos.
  4. En paralelo, sondear FG Sanitarios, Banchero y Dafys con el mismo guion.

### Nivel 2: impacto medio o plazo más largo (meses 2-4)

#### 2.1 CAFARA y Revista Ferreteros (nota sobre el caso, no aviso pago)
- **Por qué:** legitimidad en el rubro y llegada a todo el país. Sus medios son la revista, un newsletter digital, el sitio web y una síntesis de noticias del gremio. [Data, T2/T3] Ninguna fuente muestra notas de IA para ventas en el mostrador. [Data, búsqueda negativa]
- **Alcance:** ~300 socios (T3) más los lectores de la revista. Cuota y tarifas de avisos: **DATA GAP** (no están publicadas).
- **CAC:** USD 0 si se consigue una nota editorial; la cuota de socio es desconocida.
- **Tiempo:** 2-4 meses (hace falta un caso con números).
- **Cómo empezar:** (1) con 2 clientes y números reales (consultas atendidas fuera de horario, pedidos cobrados), escribir a la redacción por el contacto de cafara.org.ar con una nota propuesta: "Cómo una casa de sanitarios de Alberdi vende por WhatsApp de noche". (2) Preguntar la cuota de socio adherente para proveedores y si hay charlas de capacitación (dan cursos técnicos y de gestión). (3) Ofrecer una charla gratis "WhatsApp que vende para ferreterías".

#### 2.2 Comunidades: grupos de Facebook y WhatsApp, centros comerciales barriales
- **Por qué:** gratis y con segmentación perfecta, pero sin datos. La búsqueda web no encontró **grupos**, sólo páginas (DATA GAP). Lo más cercano a una cámara zonal es el **Centro Comercial Abierto de Liniers** (692 comercios según el GCBA, nota de archivo sin fecha) y la Federación de Comercio e Industria de la Ciudad. [Data, T1, nota vieja]
- **Reglas de autopromoción:** sin datos de reglas de grupos concretos. [Assumption] La norma habitual en grupos de rubro es no aceptar publicidad directa, así que entrar aportando (por ejemplo, "planilla gratis para actualizar precios con inflación") y responder preguntas; vender sólo por mensaje privado si alguien pregunta.
- **CAC:** ~USD 0. Horas: 2-3 h por semana.
- **Tiempo:** 1-2 meses para tener reputación.
- **Cómo empezar:** (1) buscar en Facebook con la sesión iniciada "ferreteros", "ferretería Argentina", "sanitaristas", "casa de sanitarios", "corralones", y anotar miembros, actividad y reglas; (2) sumarse a 3-5 grupos; (3) publicar una herramienta útil y gratis (plantilla de lista de precios con aumento por porcentaje); (4) contactar al Centro Comercial de Liniers para una charla o un beneficio para socios.

#### 2.3 Contenido local para compradores finales (SEO) como puerta de entrada al local
Ver la sección 2. Es un canal del cliente del cliente: no nos trae comercios directo, pero se convierte en un argumento de venta ("además le armamos una página que trae consultas") y en retención. [Opinion]

#### 2.4 Contadores de comercios
- **Por qué:** el contador ve el problema de caja y de facturación del comercio, y ya recomienda software. El Consejo Profesional de CABA publica beneficios de Xubio y Colppy para matriculados. [Data, T1, títulos de PDFs] No hay condiciones de comisión públicas. DATA GAP.
- **CAC:** comisión del 10-20% el primer año [Assumption; Loggro en Colombia paga 10% de una vez, T3].
- **Tiempo:** 3-6 meses. Encaje medio: el contador no vive el WhatsApp del mostrador. [Opinion]
- **Cómo empezar:** preguntar a cada cliente quién es su contador y ofrecerle una comisión por referir. No buscar contadores en frío antes del mes 4.

### Nivel 3: más adelante o como apoyo (mes 4+)

#### 3.1 Sistemas de gestión: Vendi, Dux, Tango, Líder Gestión
- **Vendi:** sin programa de partners ni API pública; ya vende su propio bot por $29.900. [Data, T1] Hoy es competidor. Acercarse sólo con tracción, para proponer integración ("vos tenés el stock, nosotros vendemos por chat"). [Opinion]
- **Dux (Córdoba):** más de 2.000 clientes en una nota sin fecha; partner Platinum de Mercado Libre; integra Tiendanube, ML y WooCommerce. [Data, T2/T3] No se encontró programa de partners propio (el sitio dio 403). DATA GAP.
- **Tango (Axoft, hoy de Vela LatAm):** ~70.000 clientes históricos y ~13.000 que actualizan por año. Modelo de apertura a terceros que desarrollan soluciones sobre X-TANGO y se publican en el sitio de Axoft, más una red de consultoras que lo implementan (por ejemplo, Seincomp). [Data, T1/T2, documento de Axoft y nota de ITSitio, fecha vieja] El canal real son **las consultoras de Tango por zona**, no Axoft. [Opinion]
- **Líder Gestión:** no apareció nada en la búsqueda. DATA GAP.
- **CAC:** USD 0 en efectivo, pero meses de desarrollo de integraciones. **Tiempo:** 6+ meses.

#### 3.2 Mercado Pago (programa de partners para desarrolladores)
- **Qué da:** certificación gratis (Checkout Pro), insignia, "Integrator ID" y bonificaciones según lo que procesen los comercios integrados; 4 niveles. [Data, T1 vía buscador] Una nota de Emol (Chile, 24/09/2026) dice que los profesionales cobran por cada comercio que empieza a procesar con MP. [Data, T2]
- **Para nosotros:** ingreso extra por comercio y sello "Partner certificado de Mercado Pago" en la demo. No trae leads. [Opinion]
- **Cómo empezar:** certificarse en Checkout Pro (el producto ya lo usa) y poner el Integrator ID en las preferencias de pago. Es 1-2 días de trabajo. [Estimate]

#### 3.3 Meta (Tech Provider)
- **Qué da:** onboarding propio de números (Embedded Signup), hasta 200 clientes nuevos cada 7 días, credibilidad. Para ser "Tech Partner" hace falta volumen (≈10+ clientes activos). [Data, T3/T2]
- **Para nosotros:** requisito operativo, no canal. Hacer la verificación del negocio cuando se cierre el primer piloto pago. [Opinion]

#### 3.4 Marcas (FV, Ferrum, Roca, Hydros)
- FV capacita a instaladores y vendedores junto con ferreterías y declara ~2.000 distribuidores. Roca tiene en España el club "Roca Pro" para instaladores (puntos, formación). [Data, T2/T3] **No se encontró un programa para revendedores en Argentina.** DATA GAP.
- **Para nosotros:** a largo plazo, el bot como vidriera de marca ("el asistente recomienda FV cuando aplica"). Hoy no hay escala para interesarles. [Opinion]

### Canales a evitar (por ahora)

| Canal | Por qué evitarlo | Cuándo revisar |
|---|---|---|
| Anuncios de Meta y clic a WhatsApp | Saturado (Kommo, Darwin, Cliengo). Con USD 100/mes en total no hay presupuesto para aprender. Además, el comerciante no busca el producto. | Con 10+ clientes y un caso con números, probar USD 50 dirigidos a "dueños de ferretería/sanitarios". |
| Google Ads | Demanda de búsqueda débil (nadie busca "bot para ferretería"). | No antes de tener la página de comparación de Business AI vs. materialIA. |
| Autoservicio, prueba por registro (PLG) | El dueño de 45-60 no se registra solo. | Como paso posterior a la demo, no como canal. |
| App store de Tiendanube | El cliente objetivo no tiene Tiendanube. | Nunca para este segmento. |
| Stand en ExpoFerretera | No hay edición 2026; un stand se come varios años del presupuesto. | Ir como visitante a la edición 2027. |
| Contenido genérico ("chatbot WhatsApp") | Cliengo y Kommo dominan con micrositios enteros. | Nunca: sólo nicho local. |
| Aviso pago en la Revista Ferreteros | Tarifa desconocida y sin caso que mostrar. | Mes 6+, si la nota editorial no sale. |

---

## 2. Oportunidad de SEO y contenido: el agente como puerta de entrada al local

**Lo que hay:** el comprador final busca "cuánto cuesta" y lo responden medios (La Nación mide el baño de 3,75 m² cada mes: $8,8 M en julio de 2026, con $4,8 M en artefactos y grifería), marketplaces (Servidos.ar, con calculadora de costo de reforma de baño y una nota "cuánto cuesta cambiar la grifería del baño en Buenos Aires") y Mercado Libre y Easy en las búsquedas de producto ("inodoro Ferrum Bari": de $208.320 a $525.000 según el modelo y el vendedor). [Data, T2/T3] **Ningún local de barrio aparece en esas búsquedas.** [Data, búsqueda con resultados de ML, Easy y medios]

**Volumen de búsqueda:** sin datos. Ni "precio inodoro ferrum" ni "presupuesto baño completo" devolvieron volúmenes; hace falta Google Keyword Planner o Semrush. **DATA GAP.**

**La oportunidad (para el comercio, no para materialIA):** [Opinion]
- Una **página por local** generada desde su planilla: "Presupuesto de baño en Flores, con precios de hoy, y cotizá por WhatsApp". Combina lo que el comprador busca (precio actual y zona) con lo que el local tiene (stock y precio vivos), y termina en el bot.
- Una **calculadora "lista de obra del baño"** (inodoro + depósito + bidet + grifería + flexibles + sellador) que arma el combo con los precios del local. Es justamente lo que el agente ya sabe hacer.
- **Ficha de Google Business** del local con el link de WhatsApp del bot: es el SEO local más barato. Las búsquedas tipo "sanitarios cerca" se resuelven en Maps. [Assumption]
- Riesgo: los precios cambian cada semana con la inflación; la página **tiene** que leer la planilla viva o queda desactualizada (es la regla de honestidad del producto).

**Para vender materialIA:** una sola página de nicho, "Bot de WhatsApp para casas de sanitarios y ferreterías: diferencia con el Business AI gratis de Meta". Hay poca competencia en ese término y sirve como material para mandar después de la visita. [Opinion]

**Prioridad:** Nivel 2. No trae clientes en 90 días, pero sube el valor percibido ("le traigo consultas, no sólo le contesto las que ya tiene"). [Opinion]

---

## 3. Alianzas

| Socio | Qué gana él | Qué ganamos nosotros | Cómo acercarse | Prioridad |
|---|---|---|---|---|
| **Franco Fía** (mayorista, Lomas del Mirador; vende solo a comercios; FV, Ferrum, Roca y 80+ marcas; lista en Excel) | Más pedidos de sus clientes; su lista de precios al día dentro del WhatsApp de cada local; diferenciación frente a otros mayoristas | Acceso a cientos de casas de sanitarios de AMBA; una lista de precios lista para precargar (resuelve "no tengo precios en planilla") | WhatsApp de alta de cuenta → pedir al gerente comercial; video de 60 s con su lista; piloto de 5 clientes gratis 30 días | **Alta (la n.º 1)** |
| Otros mayoristas de sanitarios (FG Sanitarios, Banchero, Dafys, Casa del Plomero; zona Liniers/Floresta/Caballito) | Lo mismo | Más cobertura; no depender de uno | Mismo guion después de tener el caso con Franco Fía | Alta |
| MaxiFer / Ferretería General Paz (mayoristas que anuncian a ferreteros) | Lo mismo, del lado ferretería | Llegada a ferreterías (segmento secundario) | Igual que arriba, en el mes 3+ | Media |
| Clientes actuales (referidos) | 1 mes bonificado por referido que pague | CAC ≤ USD 44 | Oferta el día de la primera venta por el bot | **Alta** |
| CAFARA / Revista Ferreteros | Contenido sobre innovación para sus socios | Legitimidad y llegada nacional | Nota con un caso real; preguntar la cuota de proveedor | Media |
| Mercado Pago (programa para desarrolladores) | Más volumen procesado | Bonificación por comercio, sello de partner | Certificación en Checkout Pro + Integrator ID | Media (es fácil y rápido) |
| Meta (Tech Provider) | Más negocios en la API | Onboarding propio, credibilidad | Verificación del negocio + revisión de la app | Media (requisito, no canal) |
| Consultoras de Tango por zona | Un servicio más para vender a su cartera | Llegada a comercios con stock en Tango | Con 5+ clientes; ofrecer un 20% recurrente | Baja |
| Vendi | Integración en lugar de desarrollar su bot | Stock y precio desde un sistema que ya usan 700+ comercios | Sólo con tracción; propuesta de integración | Baja (hoy es competidor) |
| Dux | Lo mismo | Lo mismo (2.000+ clientes) | Buscar su contacto de partners (el sitio dio 403) | Baja |
| Contadores de los clientes | Comisión por referir | Referidos calificados | Preguntarle a cada cliente quién es su contador | Baja |
| FV / Ferrum / Roca / Hydros | Vidriera de su marca en el chat | Contenido técnico, capacitación conjunta | Con escala (20+ locales), vía sus jornadas de capacitación | Baja |
| Centro Comercial de Liniers / Federación de Comercio de CABA | Un beneficio para sus socios | Charla con decenas de comercios de una vez | Escribir a la comisión directiva | Baja-media |

---

## 4. Plan de canales de 90 días (desde el 10/11/2026)

### Semanas 1-4 (10/11 al 07/12): demo y primeras visitas
- Cargar en el bot de demo la lista pública en Excel de Franco Fía (o la de un mayorista equivalente) y probar 10 preguntas reales ("inodoro Bari con depósito", "grifería de cocina FV monocomando").
- Armar la hoja "materialIA vs. Business AI gratis de Meta" (1 página).
- Lista de 60 locales en 3 corredores. Visitas: 15 por semana entre los dos (60 en total).
- Meta: 4-6 pilotos de 14 días instalados.
- Buscar a mano en Facebook grupos de ferreteros y sanitaristas; anotar 5 con reglas y actividad. Sumarse.
- Certificarse en Checkout Pro de Mercado Pago (1-2 días).

### Semanas 5-8 (08/12 al 04/01): convertir y abrir el mayorista
- Convertir pilotos en pagos. Meta: 2-3 clientes pagos.
- Lanzar la regla de referidos el día de la primera venta de cada cliente.
- Contactar a Franco Fía con el video y 1 caso real; proponer piloto de 5 clientes de ellos.
- Seguir visitas (10 por semana; diciembre y las fiestas bajan la atención del dueño [Assumption]).
- Publicar en los grupos la plantilla gratis de lista de precios (aportar, no vender).
- Iniciar la verificación del negocio en Meta (para Tech Provider) si hay 1+ cliente pago.

### Semanas 9-12 (05/01 al 01/02): replicar
- Meta: 5-8 clientes pagos en total, con 1-2 llegados por referido.
- Cerrar el acuerdo con un mayorista (o descartarlo con la razón anotada) y abrir conversación con un segundo (FG Sanitarios, Banchero o Dafys).
- Escribir a CAFARA y a la Revista Ferreteros con el caso de 2 clientes (números reales).
- Página de nicho "Bot de WhatsApp para casas de sanitarios vs. Business AI de Meta" y página de "presupuesto de baño" de un cliente como prueba de SEO local.
- Revisión: CAC real por canal (horas + pesos) y decisión de si probar USD 50 de anuncios dirigidos en el mes 4.

**Métrica de control semanal:** visitas → demos → pilotos → pagos, por corredor y por canal. [Opinion]

---

## 5. Data gaps

- Cuota de CAFARA, tarifas de avisos de la Revista Ferreteros y contacto de la redacción.
- Grupos de Facebook y WhatsApp de ferreteros y sanitaristas: la web no los indexa; hay que buscarlos con la sesión iniciada.
- Cantidad de clientes y viajantes de Franco Fía, FG Sanitarios, Banchero y Dafys; si trabajan con viajantes.
- Programas de partners de Dux (sitio con 403), Líder Gestión (sin resultados) y Tango/Axoft (sin condiciones públicas).
- Condiciones vigentes del programa de partners de Mercado Pago en Argentina (las páginas dieron 403; los datos vienen de los resúmenes del buscador y de la página de Chile).
- Programas de FV, Ferrum, Roca e Hydros para revendedores en Argentina: no se encontró ninguno.
- Volumen de búsqueda de "precio inodoro ferrum", "presupuesto baño completo", etc.: requiere Keyword Planner o Semrush.
- CPC de Google Ads en Argentina para 2026: el último dato concreto es de mayo de 2023 (USD 0,19, Statista/Semrush). El CPC de Meta en Argentina rondó USD 0,19 de mediana en 2026 (superads.ai, T3). Costo por lead de clic a WhatsApp en LATAM: USD 1-8 según rubro (Cliengo, T3, 13/10/2026); costo por lead B2B en Meta: USD 8-63 según la fuente (T3). Ninguno es específico de software para ferreterías.
- Condiciones de referidos de contadores en Xubio y Colppy.
- Cifras actuales del Centro Comercial de Liniers (la nota del GCBA es de archivo y sin fecha).
- Precio oficial de Meta por mensaje en Argentina y si Business AI tiene costo: sólo hay fuentes de terceros.

---

## 6. Fuentes (vistas el 09/11/2026)

**Alianzas y programas**
- [Vendi, sitio oficial](https://www.vendiapp.com.ar/) (T1)
- [Infonegocios, Dux Software 2.000 clientes y partner Platinum de ML](https://infonegocios.info/nota-principal/dux-software-la-socia-platinum-de-mercado-libre-es-cordobesa-y-paso-de-1-000-a-2-000-clientes-en-un-ano) (T2, sin fecha); [CB Insights, Dux](https://www.cbinsights.com/company/dux-software) (T3); [Tiendanube, integración con Dux](https://ayuda.tiendanube.com/es_AR/139131-aplicaciones-de-gestion-y-facturacion/como-integrar-dux-software-con-mi-tienda) (T1)
- [Axoft, consideraciones comerciales (PDF)](https://descargas.axoft.com/ftp/manuales/9.90/Gestion/AC.pdf) (T1); [ITSitio, Tango](https://www.itsitio.com/?p=2899) (T2); [Bruchou, Vela LatAm compra Axoft](https://bruchoufunes.com/asesoramos-en-la-adquisicion-de-axoft-argentina-por-vela-latam/) (T2)
- [Mercado Pago, Partners Program AR](https://mercadopago.com.ar/partners/developers/en/details) (T1, 403 al leer); [MP Chile, Partners Program](https://www.mercadopago.cl/partners/developers/es/details) (T1, 403 al leer); [MP Chile, certificación](https://www.mercadopago.cl/partners/developers/es/developer-program) (T1); [Emol, MP Partners Program, 24/09/2026](https://www.emol.com/noticias/Tendencias/2026/09/24/1212311/mercado-pago-partners-program.html) (T2)
- [iProUP, ganar dinero con Mercado Pago (revendedores Point)](https://www.iproup.com/economia-digital/57481-como-ganar-ganar-un-sueldo-extra-de-hasta-un-millon-de-pesos-con-mercado-pago) (T2); [iProfesional, MP con poca inversión 2026](https://www.iprofesional.com/negocios/446951-mercado-pago-como-ganar-dinero-con-poca-inversion-2026) (T2)
- [Twilio, WhatsApp Tech Provider Program](https://www.twilio.com/docs/whatsapp/tech-provider-program) (T3); [Twilio, FAQ](https://www.twilio.com/docs/whatsapp/isv/tech-provider-program/faq) (T3); [Infobip, Tech Provider setup](https://www.infobip.com/docs/whatsapp/tech-provider-program/setup-and-integration) (T3); [Baguete, Tech Partners de Meta](https://www.baguete.com.br/noticias/tech-partners-e-sua-chance-no-ecossistema-meta) (T2)
- [iProUP, cómo funciona Business AI](https://www.iproup.com/coffee-break/65197-como-funciona-business-ai-el-nuevo-bot-de-whatsapp-que-te-ayuda-a-vender-mas) (T2); [Forbes AR, Meta vs. Google y WhatsApp](https://www.forbesargentina.com/negocios/la-nueva-guerra-meta-google-imperio-whatsapp-plan-reconfigurar-tradicional-modelo-comercio-digital-n92042) (T2); [Cronista, novedad de WhatsApp para pymes](https://www.cronista.com/infotechnology/it-business/asi-funciona-la-novedad-de-whatsapp-que-usan-las-pymes-para-vender-mas-sin-sumar-personal/) (T2); [Diego Ceredi, IA que vende en WhatsApp Business](https://www.diegoceredi.com/blog/ia-vende-sola-whatsapp-business-argentina) (T3)
- [Franco Fía, mayorista](https://www.francofia.com/) (T1); [FG Sanitarios](https://fgsanitarios.com.ar/) (T1); [Banchero Sanitarios](https://www.bancherosanitarios.com.ar/) (T1); [FRG Grifería, Floresta](https://www.redargentina.com.ar/frg-griferia-fabrica-y-comercializacion-de-griferia-y-articulos-sanitarios-F120FC6021DD242) (T3); [Servidos, distribuidores de plomería en Buenos Aires](https://servidos.ar/donde-comprar/plomeria) (T3)
- [ARQA, ficha FV S.A.](https://arqa.com/empresas/fichas/fv-s-a) (T3, 2003); [Diario de Cuyo, FV capacitó instaladores](https://www.diariodecuyo.com.ar/noticias/griferias-fv-capacito-instaladores-905645.html) (T2); [Alimarket, Roca Pro](https://www.alimarket.es/construccion/noticia/430775/roca-lanza-el-club-profesional-para-instaladores-roca-pro) (T2, España)
- [Consejo Profesional CABA, Colppy (PDF)](https://www.consejo.org.ar/storage/attachments/Colppy.pdf-sgt7INT0zM.pdf) (T1); [Consejo Profesional CABA, Xubio (PDF)](https://www.consejo.org.ar/storage/attachments/Xubio%20PDF%202023.pdf-jZOncwSdsl.pdf) (T1); [Loggro, brochure contadores](https://loggro.com/download/brochure-loggro-contadores-2022.pdf) (T3, Colombia); [Softland AR, programa de referidos](https://softland.com/ar/conoces-nuestro-programa-de-referidos/) (T1)

**Comunidades**
- [CAFARA en Facebook](https://www.facebook.com/cafara.org.ar/) (T1); [Grupo Ferretero (página)](https://www.facebook.com/grupoferretero1/) (T3); [Encuentro Ferretero](https://www.facebook.com/encuentroferretero/) (T3)
- [Misiones Online, Día del Ferretero (medios de CAFARA)](https://misionesonline.net/2021/09/03/dia-del-ferretero-2/) (T2); [ZoomInfo, CAFARA](https://www.zoominfo.com/c/cafara/556470211) (T3)
- [GCBA, Centro Comercial Abierto de Liniers](https://buenosaires.gob.ar/gcaba_historico/noticias/visitamos-el-centro-comercial-abierto-de-liniers) (T1, archivo sin fecha)
- [El Doce, ferretero cordobés viral](https://eldoce.tv/tendencias/2024/10/26/los-secretos-del-ferretero-cordobes-viral-por-su-consejo-para-eliminar-el-mal-olor-del-bano) (T2, 26/10/2024)

**Costos de anuncios**
- [Statista, CPC de búsqueda en Argentina](https://www.statista.com/statistics/1402572/search-advertising-cpc-argentina/) (T3, mayo de 2023); [Superads, CPC de Facebook en Argentina](https://www.superads.ai/facebook-ads-costs/cpc-cost-per-click/argentina) (T3); [Synter, benchmark de CPC de Google Ads 2026 H1](https://syntermedia.ai/benchmarks/2026-h1/google-ads/cpc) (T3, global)
- [Cliengo, costo de un lead clic a WhatsApp 2026](https://guiawabusiness.cliengo.com/costo-lead-click-to-whatsapp) (T3, 13/10/2026, fuente interesada); [Sotros, CPL clic a WhatsApp B2B 2026](https://sotrosinfotech.pages.dev/blog/whatsapp-click-to-chat-ads-b2b-lead-generation-2026/) (T3); [Ryze, CPL B2B en Meta](https://www.get-ryze.ai/blog/meta-ads-cost-lead-generation-b2b-benchmarks) (T3); [ChatDaddy, precios de la API de WhatsApp 2026](https://chatdaddy.tech/blog/whatsapp-business-api-pricing-calculator) (T3)

**SEO / demanda del comprador final**
- [La Nación, cuánto cuesta remodelar un baño en agosto 2026](https://www.lanacion.com.ar/propiedades/construccion-y-diseno/cuanto-cuesta-remodelar-un-bano-en-agosto-2026-segun-cada-presupuesto-nid06082026/) (T2); [iProfesional, remodelar baño y cocina, junio 2026](https://www.iprofesional.com/realestate/456748-cuanto-cuesta-remodelar-bano-cocina-junio-2026-costos-refaccion) (T2); [Servidos, calculadora de reforma de baño](https://servidos.ar/calculadora-costo-reforma-bano) (T3); [Servidos, cambiar grifería del baño en Buenos Aires](https://servidos.ar/blog/cuanto-cuesta-cambiar-griferia-bano-buenos-aires) (T3)
- [MejoresCompras, inodoro Ferrum Bari](https://mejorescompras.com.ar/precio/MLA51245458--inodoro-largo-con-deposito-apoyo-dual-tapa-ferrum-bari-color-blanco) (T3); [Mercado Libre, mochilas más vendidas](https://www.mercadolibre.com.ar/blog/mas-vendidos/mochilas-inodoros) (T3)
