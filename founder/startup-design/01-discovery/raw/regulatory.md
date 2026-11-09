# A3: Regulatorio y Compliance (materialIA)

> **Insumo original de investigación, 09/11/2026.** Se conserva como antecedente, sin certificar sus afirmaciones. Para decisiones usar las síntesis y [correcciones posteriores](../corrections-2026-11-09.md); las tarifas de servicio de Meta y sus escenarios derivados quedaron retirados.

**Fecha de corte:** 09/11/2026 · **Agente:** A3 Regulatory & Compliance
**Aviso:** esto no es asesoramiento legal ni contable. Es un mapa para llevarle a un contador y a un abogado. Las normas y los montos en Argentina cambian cada pocos meses, así que hay que confirmar todo antes de firmar o facturar.

**Etiquetas:** [Data] = dato con fuente · [Estimate] = estimación con base en fuentes · [Assumption] = supuesto nuestro · [Opinion] = criterio del agente.
**Tiers de fuente:** T1 = fuente primaria oficial (ARCA, AAIP, Boletín Oficial, Meta, MP) · T2 = estudio jurídico o contable reconocido, o medio especializado · T3 = blog, medio general o vendor.

**Supuesto base [Assumption]:** los founders operan desde CABA. Si están en provincia de Buenos Aires u otra provincia, cambian los Ingresos Brutos y el registro societario (DPPJ en vez de IGJ).

---

## 1. Normas vigentes (resumen)

| Norma | Qué exige | A quién aplica | ¿Al lanzar o al escalar? | Costo | Plazo |
|---|---|---|---|---|---|
| **Ley 25.326 de Protección de Datos Personales** (+ Dec. 1558/2001) | Consentimiento informado, finalidad, seguridad (art. 9), confidencialidad (art. 10), derechos de acceso, rectificación y supresión, inscripción de bases (art. 21) y reglas para quien presta servicios de tratamiento por cuenta de terceros (art. 25) | Al comercio como responsable. A materialIA como encargado de los datos del comercio y como responsable de sus propias bases (clientes, leads) | **Al lanzar** | Inscripción en la AAIP gratuita [Data T1] | Online por TAD, sin vencimiento [Data T1] |
| **Res. AAIP 47/2018** (medidas de seguridad recomendadas) | Guía de controles de seguridad: accesos, backups, incidentes | Responsables y encargados | Al lanzar, como buena práctica | Costo interno (tiempo) | — |
| **Disp. DNPDP 60-E/2016** (transferencia internacional) | Para enviar datos a países sin nivel adecuado (EE.UU.: Supabase, OpenAI/Anthropic, Meta) hace falta consentimiento o contrato con las cláusulas modelo | Al comercio y a materialIA | **Al lanzar** (si los datos se alojan o procesan afuera) | $0 (cláusulas en el contrato) | — |
| **Res. AAIP 126/2024** (infracciones y sanciones) | Clasifica infracciones leves, graves y muy graves. Pagar dentro de los 20 días hábiles reduce la multa un 50% | Todos | Riesgo latente | Multas (topes de la Res. 244/2022, ej. $5.000.000 para graves) [Data T1/T2, montos de 2022: **desactualizados**] | Vigente desde el 01/06/2024 |
| **Ley 24.240 de Defensa del Consumidor** (arts. 4, 10 bis, 34, 40) | Información clara y veraz del precio, revocación en ventas a distancia (10 días), responsabilidad solidaria de la cadena (art. 40) | Al comercio como proveedor. A materialIA posiblemente como parte de la cadena [Opinion] | Al lanzar (riesgo indirecto) | — | — |
| **Disp. SSDCyLC 954/2025** (reemplaza a la Res. 424/2020) | Botón de arrepentimiento y botón de baja visibles en sitios web, sin registro previo. Código de baja dentro de 24 h. Atención mínima de 8 h hábiles si es solo electrónica | Al comercio que vende a distancia por web. **A materialIA respecto de su propio abono** (es un servicio contratable a distancia) | **Al lanzar** (el botón de baja del abono, si los comercios lo contratan por la web) | Desarrollo propio | BO 04/09/2025 [Data T2] |
| **Monotributo (Ley 24.977, mod. Ley 27.743)** | Inscripción, facturación electrónica tipo C, recategorización semestral | A cada founder, como persona humana | **Antes del primer cobro** | Cat. A: $49.527/mes nacional + IIBB CABA (ver §3) | Alta online el mismo día [Estimate] |
| **Términos de Meta para WhatsApp Business Platform** (últ. act. 23/09/2026) y **Business Messaging Policy** (últ. act. 23/09/2026) | IA permitida solo si es incidental o auxiliar al negocio. Opt-in. Escalamiento a humano. Fuera de las 24 h solo plantillas aprobadas | A materialIA (Tech Provider) y a cada comercio | **Al lanzar** | $0 en compliance, pero los mensajes se pagan | Verificación del negocio: días a semanas [Estimate] |
| **Términos de Mercado Pago Developers / OAuth** | App registrada, redirect_uri fija, guardado seguro del token, autorización explícita del vendedor | A materialIA como integrador | **Al lanzar** | $0 | Inmediato |

---

## 2. Datos personales

### 2.1 Qué datos toca materialIA
Nombre, teléfono y conversaciones de los clientes finales, pedidos, comprobantes de pago (pueden mostrar CBU/CVU, nombre del titular y DNI/CUIT), stock y precios del comercio. **No** son datos sensibles en el sentido del art. 2 de la Ley 25.326 (salud, religión, etc.), pero los comprobantes de pago son **datos financieros** y conviene tratarlos como de riesgo alto. [Opinion]

### 2.2 ¿Responsable o encargado?
- **Respecto de los clientes finales de cada comercio:** materialIA es **encargado del tratamiento** ("prestación de servicios informatizados de datos personales", art. 25 Ley 25.326). El comercio es el **responsable**: decide para qué se usan los datos y es el dueño de la relación con el cliente. [Opinion basada en el art. 25, Ley 25.326, T1]
- El art. 25 establece que el encargado **no puede usar los datos para otro fin** que el del contrato, **no puede cederlos** (ni siquiera para conservarlos) y, al terminar el contrato, **debe destruirlos** (salvo que haya autorización expresa para guardarlos, por ejemplo para eventuales servicios futuros, por hasta 2 años). [Data T1, texto de la ley de 2000, vigente]
- **Ojo:** si materialIA usa las conversaciones de todos los comercios para entrenar o mejorar su propio modelo, o para armar analytics cruzados, **pasa a ser responsable** de ese tratamiento y necesita su propia base legal. Además, la sección 4.7 de los términos de Meta **prohíbe** usar datos de la plataforma WhatsApp para entrenar o mejorar modelos de IA (salvo un ajuste fino para uso exclusivo de ese negocio). [Data T1 Meta, 23/09/2026]
- **Respecto de los propios clientes de materialIA** (los comercios y sus contactos), materialIA es **responsable**.

### 2.3 Inscripción en la AAIP (Registro Nacional de Bases de Datos)
- [Data T1] La inscripción se hace por **Trámites a Distancia (TAD)** con clave fiscal nivel 2 o superior. Es **gratuita**, **no vence** y tiene carácter de declaración jurada (si cambian los datos, se modifica). Primero se inscribe el **responsable** y después cada **base de datos**. Consultas: registrobasesdedatos@aaip.gob.ar. Fuente: argentina.gob.ar/servicio/inscribir-un-responsable-de-bases-de-datos-personales-privadas (consultada el 09/11/2026, sin fecha de actualización visible).
- **¿Es obligatoria para materialIA?** El art. 21 de la Ley 25.326 obliga a inscribir las bases privadas "destinadas a dar informes". La práctica de la AAIP es pedir la inscripción de toda base que exceda el uso personal. [Opinion]
  - **Recomendación [Opinion]:** inscribir a materialIA (o al founder monotributista mientras no haya SAS) como responsable de **su propia base de clientes y leads**. Es gratis y lleva unas horas.
  - Las bases de clientes finales las tiene que inscribir **cada comercio**, porque es el responsable. materialIA puede ofrecerle una guía o hacer el trámite como apoderado (valor agregado de onboarding).
  - Al pasar a SAS hay que inscribir la sociedad como nuevo responsable.

### 2.4 Transferencia internacional
Supabase, OpenAI/Anthropic y Meta procesan datos fuera de Argentina, sobre todo en EE.UU., que **no** figura entre los países con nivel adecuado. Hacen falta (a) el consentimiento del titular o (b) un contrato con las **cláusulas modelo de la Disp. 60-E/2016**. [Data T1 la norma; aplicación al caso: Opinion]. Mitigación barata: Supabase en una región con nivel adecuado (UE) [Assumption: verificar si el plan lo permite], más las cláusulas en el contrato con el comercio y aviso en el primer mensaje del bot.

### 2.5 Cláusulas mínimas del contrato con el comercio (DPA / acuerdo de encargo)
1. **Roles:** el comercio es responsable y materialIA es encargado (art. 25). El comercio garantiza que tiene base legal y opt-in para contactar a sus clientes (también lo exige Meta).
2. **Finalidad limitada:** atender consultas, tomar pedidos, generar links de pago y verificar pagos. Prohibido cualquier otro uso, incluido el entrenamiento de modelos con datos de un comercio para otro.
3. **Subencargados:** lista de Meta, Supabase, el proveedor de LLM, Google (Sheets) y Mercado Pago, con su ubicación y la autorización del comercio. Aviso si se agrega uno nuevo.
4. **Transferencia internacional:** cláusulas modelo de la Disp. 60-E/2016.
5. **Seguridad:** medidas técnicas en línea con la Res. AAIP 47/2018 (cifrado, control de accesos, logs, backups) y **aviso de incidentes** al comercio en un plazo X (ej. 48 h) [Opinion: hoy no hay un plazo legal fijo en la 25.326].
6. **Derechos de los titulares:** materialIA ayuda al comercio a responder pedidos de acceso, rectificación y supresión (plazos legales: 10 días corridos para acceso y 5 días hábiles para rectificación o supresión, arts. 14 y 16) [Data T1].
7. **Retención y borrado:** plazos de conservación y destrucción o devolución de los datos al terminar el contrato (art. 25).
8. **Confidencialidad** del personal (art. 10).
9. **Responsabilidad y límite:** el comercio responde por precios, stock, la venta y la atención al consumidor. materialIA responde por fallas del sistema hasta un tope (ej. 12 meses de abono). Indemnidad cruzada.
10. **IA:** el bot puede equivocarse, el comercio valida los precios en su Sheet y existe escalamiento a humano (también lo exige Meta).
11. **Credenciales de Mercado Pago:** autorización por OAuth, revocable por el comercio en cualquier momento. materialIA no toca los fondos.
12. **Baja del servicio:** cómo se da de baja (botón de baja, Disp. 954/2025) y qué pasa con los datos.

Además hacen falta una **política de privacidad pública** (también la exige el App Review de Meta) y **términos y condiciones** del servicio.

### 2.6 Proyecto de nueva ley
- [Data T2] El **Expediente 3397-D-2026** se presentó en Diputados el 16/07/2026. Reproduce, con modificaciones, el proyecto del Ejecutivo de 2023 (elaborado por la AAIP), que había perdido estado parlamentario. Agrega el interés legítimo con análisis previo documentado, el consentimiento desde los 16 años y cambios en transferencias internacionales y en el derecho de supresión. Está en etapa temprana y no se encontró dictamen. Fuentes: Allende & Brea (12/08/2026) y Marval.
- Las fuentes no coinciden en la autoría: una búsqueda atribuye el proyecto al diputado Agustín Rossi y la nota de Allende no nombra al autor. **DATA GAP:** confirmar la autoría en hcdn.gob.ar.
- [Opinion] Si se aprueba con la línea del proyecto de 2023 (tipo GDPR), probablemente traiga contrato obligatorio con el encargado, notificación de incidentes y multas más altas. Diseñar hoy con un DPA y un registro de incidentes deja a materialIA preparada.

---

## 3. Estructura legal y facturación

### 3.1 Escala del monotributo vigente (desde el 01/08/2026) [Data T1, arca.gob.ar/monotributo/categorias.asp]

| Cat. | Tope de ingresos anuales | Cuota mensual nacional (servicios) | ≈ Clientes a $70.000/mes [Estimate] |
|---|---|---|---|
| A | $12.009.410 | $49.527 | 14 |
| B | $17.595.183 | $56.379 | 20 |
| C | $24.670.494 | $66.020 | 29 |
| D | $30.628.651 | $84.613 | 36 |
| E | $36.028.231 | $119.811 | 42 |
| F | $45.151.659 | $150.784 | 53 |
| G | $53.995.799 | $230.313 | 64 |
| H | $81.924.660 | $522.707 | 97 |
| I | $91.699.762 | $963.748 | 109 |
| J | $105.012.519 | $1.167.300 | 125 |
| K | $126.610.839 | $1.614.446 | 150 |

- Desde la Ley 27.743 (2024), los servicios pueden llegar hasta la categoría K. [Data T2, cruzado con la tabla de ARCA, que muestra cuota de servicios en las 11 categorías]
- La próxima actualización de topes sería en **febrero de 2027** (ajuste semestral por IPC). [Estimate T2, iProfesional/Cronista]
- **IIBB CABA:** desde el 01/01/2026 el Régimen Simplificado de IIBB de CABA está **unificado** con el monotributo en un solo pago (RG Conjunta ARCA 5769/2025). Componente de IIBB vigente desde agosto de 2026: **≈ $30.025/mes en la categoría A** (en la K, ~$316.525) [Data T3, Blog del Contador; **verificar en AGIP**]. **Total en la cat. A ≈ $79.500/mes por persona.** [Estimate]
- **¿Un servicio de software entra en el monotributo?** Sí. Es una "locación o prestación de servicios", sin exclusión por la actividad. [Data T1, categorías de servicios en ARCA; Opinion sobre el caso]
- **Factura C:** el monotributista no discrimina IVA. Si el comercio es Responsable Inscripto, no puede computarse IVA crédito. Para un abono chico casi no importa, pero algunos clientes más grandes pueden pedir factura A. [Opinion]

### 3.2 ¿Pueden facturar los dos socios con monotributo cada uno?
- [Data T2/T3] **Las sociedades no pueden estar en el monotributo** (desde la reforma de 2018, Ley 27.430, incluidas las sociedades de hecho y la Sección IV). La Ley 27.743 no lo revirtió.
- Cada founder puede ser monotributista por su cuenta y facturar sus propios servicios. **El problema:** si en los hechos hay un negocio común (una marca, una cuenta de Meta, clientes compartidos, ganancias repartidas), ARCA puede considerar que existe una **sociedad de hecho** y reclamarle IVA y Ganancias por el régimen general. [Opinion; T3 menciona la práctica de "partir la facturación" como riesgosa]
- **Esquema prolijo para el arranque [Opinion]:** **un solo founder factura** (el que ya tiene monotributo) y el otro le factura a él como monotributista (ej. "servicios de desarrollo"), o el otro no factura hasta que exista la SAS. Hay que documentarlo con un **acuerdo de socios / pacto pre-societario** firmado: quién es dueño del código y la marca, cómo se reparte, y el compromiso de aportar todo a la SAS.
- El founder que no tiene nada se tiene que **inscribir** (CUIT, clave fiscal nivel 3, alta en monotributo, todo online y gratis). Si es menor de 25 años y estudiante, verificar si sigue como adherente en la obra social de sus padres, porque el monotributo trae obra social propia. [Assumption]

### 3.3 Monotributo vs SAS vs otras alternativas

| Concepto | Monotributo (1 founder factura) | SAS (CABA, IGJ) | SRL | Sociedad simple / de hecho |
|---|---|---|---|---|
| Costo de alta | $0 [Data T1] | Tasas IGJ ≈ $30.000–60.000 [Estimate T3, 2026]; total con profesional ≈ $50.000–150.000 o más (estimación de 2025) [Estimate T3]; con estatuto modelo puede salir más barato [Estimate] | Mayor que la SAS (más trámites y gerencia) [Opinion] | $0 formal |
| Capital mínimo | — | 2 SMVM (≈ $800.000 a principios de 2026), se integra mínimo el 25% al suscribir [Estimate T3] | Sin mínimo legal fijo, pero la IGJ exige que sea adecuado [Opinion] | — |
| Tiempo | Mismo día | 24 h a 15 días hábiles con estatuto modelo. Con observaciones, 30 a 90 días [Estimate T3]. La RG IGJ 11/2026 (vigente desde el 23/09/2026) simplifica la constitución, elimina la precalificación profesional como regla y flexibiliza objeto y aportes [Data T2, Colegio de Escribanos] | Semanas | — |
| IVA | No (factura C) | 21% sobre el abono (factura A/B) [Data, Ley de IVA] | 21% | 21% (régimen general) |
| Ganancias | Incluido en la cuota | Escala para sociedades 25%–35% sobre la utilidad (Ley 27.630) [Data T2, verificar montos de los tramos 2026] | Igual | Los socios por persona humana |
| IIBB CABA | Incluido (simplificado, ≈ $30.025/mes en cat. A) | Régimen general: **3%** para servicios informáticos/software hasta ≈ $2.154 M anuales (Ley 6948, vigente desde el 01/06/2026) [Data T3, verificar NAES] | Igual | Igual |
| Contador | Opcional, ≈ $0–40.000/mes [Assumption] | ≈ $120.000–250.000/mes (Indicadores.ar), $200.000–500.000 (Contablix) [Estimate T3, 2026] | Similar o mayor | Similar a la SAS |
| Aporte del administrador | — | Autónomo del administrador ≈ $85.000/mes (Contablix) [Estimate T3]. Si el administrador sigue en el monotributo, la consulta va al contador | Igual | — |
| Responsabilidad | Ilimitada (personal) | Limitada al capital | Limitada | **Ilimitada y solidaria** |
| Meta / MP | Verificación con constancia de CUIT de una persona física [Assumption, verificar] | Verificación como empresa, más fácil para quedar como Tech Provider [Opinion] | Igual | Difícil |
| Inversión | No permite repartir equity | Admite acciones, varias clases y vesting | Cuotas, menos flexible | No |

**¿Cuándo pasar a SAS? [Opinion + Estimate]**
- El costo fijo extra de la SAS (contador, autónomo del administrador y tasas) ronda los **$250.000–600.000/mes** [Estimate]. Además se suman el 21% de IVA y el 3% de IIBB sobre la facturación.
- **Disparadores razonables:** (a) **~25–40 comercios pagos** (≈ $1,75–2,8 M/mes, categorías C–E), (b) que el founder que factura llegue a la categoría F o G, donde la cuota sube fuerte ($150k → $230k → $523k en la H), (c) que entre un tercer socio o un inversor, (d) que Meta o los clientes exijan una entidad, o (e) que se quiera **limitar la responsabilidad personal** (por los datos y el riesgo de reclamos, este punto puede adelantar la decisión).
- **Regla práctica:** lanzar con monotributo y empezar la SAS en paralelo cuando haya **~15–20 clientes pagos** (≈ $1–1,4 M/mes), así la SAS está lista antes de pasar los ~$30 M anuales (categoría D).
- **Ojo con el IVA:** el abono de $70.000 con factura C pasa a $70.000 + IVA con la SAS ($84.700 final) o se come el margen. Conviene definir desde ahora si el precio es "+ IVA".

---

## 4. Impuestos sobre el servicio y sobre los costos

### 4.1 Lo que cobra materialIA
- **Con monotributo:** solo la cuota fija (impuesto integrado, aportes y IIBB unificado). Factura C. No hay IVA. [Data T1/T2]
- **Con la SAS:** IVA 21% (la economía del conocimiento puede dar beneficios, pero exige requisitos de inscripción, ver §7), IIBB CABA 3% [Data T3], Ganancias 25–35%.
- **Retenciones y percepciones de IIBB:** al cobrar con Mercado Pago o a través de bancos, y con la SAS como RI, aparecen las percepciones y retenciones de IIBB (padrones de AGIP/ARBA y SIRCREB). Con el monotributo unificado de CABA suelen no aplicarse o ser menores. **DATA GAP:** confirmar la situación del régimen simplificado frente al SIRCREB y las retenciones de MP en 2026.

### 4.2 Lo que paga materialIA en dólares (Meta, OpenAI/Anthropic, Supabase)
- **IVA a servicios digitales del exterior: 21%** (Ley 27.430, Título IV). Lo percibe la tarjeta cuando el proveedor está en el listado de ARCA (OpenAI, Anthropic y Meta lo están; Supabase es probable). [Data T1 la norma; Estimate la inclusión de cada proveedor]
- **Percepción del 30% (RG 5617/2024):** desde el **02/01/2026** ARCA dejó de aplicarla sobre consumos con tarjeta en moneda extranjera o con proveedores del exterior, salvo los **servicios turísticos pagados en pesos**. [Data T2/T3: Diario Popular, Infoviajera, El Liberal, enero de 2026]
  - **Contradicción:** otra nota (Blog del Contador) dice que siguen alcanzados "la adquisición de servicios prestados por no residentes". **DATA GAP:** confirmar con el resumen de la tarjeta o con el contador si hoy aparece una percepción sobre los SaaS en USD. El número de la RG modificatoria no está confirmado (las fuentes mencionan la RG 5672).
- **Percepciones de IIBB sobre servicios digitales:** CABA y otras provincias aplican percepciones de IIBB a los pagos con tarjeta a prestadores del exterior (en CABA históricamente ~2%). [Estimate, **DATA GAP**: confirmar la alícuota 2026 en AGIP]
- [Opinion] Hoy el "recargo" efectivo sería ≈ 21% de IVA más ~2% de IIBB si no hay percepción de Ganancias. Con la SAS como RI, ese IVA del 21% **puede computarse como crédito fiscal**, una ventaja extra de la SAS.

---

## 5. Políticas de Meta (WhatsApp Business Platform)

- **IA (Términos de Meta para WhatsApp Business Platform, sección 4.7, última actualización 23/09/2026) [Data T1]:** los "proveedores de IA" (LLMs, IA generativa, asistentes de uso general) **no pueden** usar la plataforma cuando la IA es la **funcionalidad principal**. Se permite cuando es **incidental o auxiliar** al negocio, y **Meta decide a su criterio** qué cuenta como principal. Rige para todos los usuarios desde el **15/01/2026** (para los nuevos, desde el 15/10/2025) [Data T2: TechCrunch, respond.io].
  - **Encuadre de materialIA [Opinion]:** un vendedor de un comercio que responde sobre su stock, precios y pedidos es un caso de **ventas y soporte del negocio**, que está permitido. **Riesgo:** que el bot conteste cualquier cosa ("contame un chiste", "haceme la tarea"). Mitigación: system prompt restringido al catálogo y al rubro, rechazo de temas fuera de dominio y logs que lo demuestren.
  - **Prohibido** usar los datos de WhatsApp para entrenar o mejorar modelos. Solo se permite el ajuste fino para uso exclusivo de ese negocio. [Data T1]
- **Business Messaging Policy (última actualización 23/09/2026) [Data T1]:**
  - Opt-in explícito. El negocio es "el único responsable" de obtenerlo.
  - Fuera de la ventana de 24 h, solo plantillas aprobadas.
  - Con automatización hay que tener **vías de escalamiento claras y rápidas** (ej. derivar a un humano). → **El handoff a humano es obligatorio en la práctica.**
  - Comercio: el negocio es "el único responsable de tus transacciones" y de los impuestos. WhatsApp no procesa ni concreta ventas.
  - Sanciones: limitar o interrumpir el acceso y, en caso de cancelación, **prohibir a la persona y a su organización** volver a usar los productos. La sección 5.3 de los Términos permite suspender por infracciones "tuyas o de tus Clientes": **una infracción de un comercio puede afectar a materialIA como Tech Provider.** [Data T1]
- **Tech Provider / Embedded Signup [Data T1, developers.facebook.com]:** se requiere **verificación del negocio** antes del App Review (nombre, dirección, teléfono, email, **sitio web** y documentación), App Review con 2 videos, política de privacidad en la app y Advanced Access a `whatsapp_business_messaging` y `whatsapp_business_management`. Los clientes cargan su propia tarjeta en su WABA (pagan sus mensajes).
  - Después de la verificación, el App Review y el Access Verification: hasta **200 clientes nuevos cada 7 días** (Twilio FAQ) [Data T3]. Si el negocio deja de estar verificado o queda restringido, se pierde el estado de Tech Provider. [Data T3]
  - Los negocios no verificados quedan limitados a **250 conversaciones iniciadas por el negocio / usuarios únicos cada 24 h**. [Data T3]
  - **DATA GAP:** cuántos clientes se pueden onboardear antes de verificar, y si Meta acepta un monotributista (persona física) como negocio verificado. [Assumption: suele aceptar la constancia de CUIT/ARCA más dominio y web propios; hay que probarlo.]
- **Cuentas restringidas por "automatización":** no se encontró una política específica con ese nombre. Las restricciones aparecen por mala calidad (bloqueos o reportes de usuarios), mensajes sin opt-in o violaciones de política. Con la API oficial (no con librerías no oficiales tipo WhatsApp Web) el riesgo de baneo "por bot" es bajo. [Opinion]

---

## 6. Mercado Pago

- [Data T1, MP Developers] Una plataforma **sí puede** operar en nombre del comercio con **OAuth (authorization code)**: el comercio entra a su cuenta de MP y autoriza a la app de materialIA, y materialIA recibe un **access token del vendedor**, válido por **180 días** y renovable con el refresh token sin que el vendedor vuelva a autorizar. Requisitos: app creada en MP (client_id/secret), **redirect_uri fija**, `state` único, PKCE recomendado, tokens guardados de forma segura en el servidor y nunca en la URL.
- Con ese token se crean preferencias o links de pago **a nombre del comercio**: la plata entra directo a la cuenta del comercio. [Estimate: la doc confirma el acceso "en nombre de", no confirma endpoint por endpoint]
- Comisiones: si materialIA quisiera cobrar un porcentaje por venta, existe el `marketplace_fee` (modelo marketplace). **Recomendación [Opinion]:** **no** cobrar porcentaje de las ventas al principio. Mientras el modelo sea solo un abono, materialIA no intermedia fondos y evita quedar como agregador o PSP (eso traería regulación del BCRA y responsabilidad del consumidor más fuerte).
- **Anti-patrón:** pedirle al comercio que pase su access token de producción a mano. Es inseguro y probablemente contrario a los términos de MP. Usar OAuth.
- La verificación de pagos tiene que hacerse por webhook o consultando la API con el token del comercio. **No** validar "comprobantes" que manda el cliente por foto como prueba final, porque es el fraude más común. [Opinion]

---

## 7. Defensa del consumidor (ventas por chat)

- **¿Quién responde ante el consumidor final?** El **comercio** es el proveedor (arts. 2 y 4 de la Ley 24.240). **Pero** el art. 40 establece una responsabilidad **solidaria** de toda la cadena de comercialización por daños derivados del producto o servicio, y hay jurisprudencia que extendió responsabilidad a plataformas que intermedian (ej. casos contra marketplaces). [Data T1 la ley; Opinion la extensión a materialIA]
  - **Riesgo concreto [Opinion]:** que el bot informe un precio incorrecto (Sheet desactualizada o alucinación) y el consumidor reclame que se respete (art. 7: la oferta obliga). Mitigación: el bot solo cita precios leídos de la Sheet, con fecha de vigencia y la leyenda "precio sujeto a confirmación del comercio". Una cláusula del contrato debe dejar al comercio como responsable de los precios cargados.
- **Información de precios:** precio final en pesos, con impuestos incluidos, para consumidores finales (art. 4 de la Ley 24.240 y normas de exhibición de precios). **DATA GAP:** no se verificó una norma de 2026 específica sobre precios en canales de mensajería.
- **Arrepentimiento:** derecho de revocar en 10 días las ventas a distancia (art. 34 de la Ley 24.240 y art. 1110 del CCyCN). La **Res. 424/2020 está derogada** y la reemplazó la **Disp. 954/2025** (BO 04/09/2025), que exige el botón en **sitios web** [Data T2 Allende/Contadores en Red; algunos sitios (Tiendanube, SIAP) todavía citan la 424, desactualizados].
  - Para WhatsApp la norma no dice nada explícito. **[Opinion]** El derecho de revocación existe igual (es ley), así que el bot debería informar cómo arrepentirse y el **widget web** del comercio debería tener el link de arrepentimiento si se vende por la web.
  - **Para el propio abono de materialIA:** si los comercios contratan desde la web, materialIA debe tener un **botón de baja**. El comercio suele contratar como empresa y no como consumidor final (el art. 2 excluye a quien adquiere para integrar a un proceso productivo), pero un comercio chico puede ser considerado consumidor. [Opinion]

---

## 8. Regulación de IA en Argentina

- **No hay ley nacional de IA vigente.** [Data T2] En Diputados hay entre 19 y 43 proyectos según la fuente. El 31/07/2026 Diario Judicial informó la presentación de un nuevo proyecto (que propone un programa federal de IA, robótica y automatización). El debate se postergó en Diputados a fines de 2025 y no se encontró dictamen en 2026. El gobierno nacional se mostró reticente a una regulación fuerte (iProUP, DPL News).
- **Provincia de Buenos Aires:** el Decreto 742/2026 regula el uso de IA en la administración pública bonaerense. No aplica a privados. [Data T3]
- Lo que aplica hoy a la IA de materialIA: la **Ley 25.326** (datos), la **Ley 24.240** (información veraz al consumidor) y los **términos de Meta**. [Opinion] Buena práctica: avisar en el primer mensaje que es un asistente automático del comercio y que se puede pedir hablar con una persona.

---

## 9. Cambios que vienen

| Cambio | Estado al 09/11/2026 | Impacto |
|---|---|---|
| Nueva ley de datos personales (Expte. 3397-D-2026) | Presentada el 16/07/2026, sin dictamen [Data T2] | Medio: DPA obligatorio, notificación de incidentes, multas mayores |
| Ley de IA | Proyectos sin dictamen [Data T2] | Bajo a corto plazo |
| Actualización del monotributo | Febrero de 2027 (semestral por IPC) [Estimate] | Topes y cuotas suben ~10–15% [Estimate] |
| Cambios de Meta | Los términos y la policy se actualizaron el 23/09/2026. Meta los cambia sin aviso [Data T1] | Alto: revisar cada trimestre |
| RG IGJ 11/2026 | Vigente desde el 23/09/2026 [Data T2] | Positivo: SAS más rápida y barata |
| IIBB CABA (Ley 6948) | Vigente desde el 01/06/2026, ajusta topes y alícuotas [Data T3] | Bajo |

---

## 10. Costo mínimo de cumplimiento para lanzar

| Ítem | Costo | Tipo |
|---|---|---|
| Alta en el monotributo del founder que factura (ya existe; recategorizar si hace falta) | $0 | [Data T1] |
| Cuota del monotributo cat. A + IIBB CABA unificado | ≈ $79.500/mes ($49.527 + ~$30.025) | [Data T1 + T3] |
| (Opcional) monotributo del 2.º founder, si le factura al 1.º | ≈ $79.500/mes | [Estimate] |
| Inscripción en la AAIP como responsable y de la base propia | $0 | [Data T1] |
| Verificación de negocio de Meta, App Review y app de MP | $0 (necesita dominio, web y casilla en el dominio: ≈ USD 15–30/año) | [Data T1 / Estimate] |
| Redacción de T&C, política de privacidad y contrato o DPA con el comercio (abogado, una vez) | ≈ $300.000–800.000 | [Assumption: no se encontró una fuente de honorarios 2026; pedir 2–3 presupuestos] |
| Pacto pre-societario o acuerdo de founders | ≈ $150.000–400.000 (o incluido en el ítem anterior) | [Assumption] |
| Consulta inicial con contador | ≈ $50.000–150.000 | [Assumption] |
| **Total de arranque** | **≈ $500.000–1.350.000 únicos + ≈ $80.000–160.000/mes** | [Estimate] |
| SAS (cuando corresponda) | Alta ≈ $50.000–150.000 + capital (2 SMVM, 25% integrado) + ≈ $250.000–600.000/mes | [Estimate T3] |

---

## 11. Nivel de riesgo

| Área | Riesgo | Por qué |
|---|---|---|
| Meta / WhatsApp (bloqueo de cuenta o de Tech Provider) | **ALTO** | Es el canal principal. Meta decide a su criterio qué es una IA "principal" y una infracción de un cliente puede afectar a materialIA. No hay apelación garantizada. |
| Datos personales | **MEDIO** | Comprobantes y teléfonos de terceros, servidores en EE.UU. y hoy poca fiscalización de la AAIP. El riesgo real es una filtración y el daño reputacional. |
| Defensa del consumidor | **MEDIO-BAJO** | El responsable principal es el comercio. El riesgo son los precios mal informados por el bot. |
| Fiscal y societario | **MEDIO** | Dos socios con un solo monotributo pueden configurar una sociedad de hecho. Hay que ordenarlo con un pacto y planificar la SAS. |
| Mercado Pago | **BAJO** | Con OAuth y sin intermediar fondos. |
| IA (regulación local) | **BAJO** | No hay ley. |
| **Global** | **MEDIO** | El riesgo existencial es la dependencia de Meta, no el regulatorio local. |

---

## 12. Preguntas para el contador / abogado

1. Con dos founders y un solo monotributo: ¿cuál es el esquema más seguro para no configurar una sociedad de hecho? ¿El 2.º founder le factura al 1.º? ¿Firmamos un pacto pre-societario?
2. ¿En qué categoría está hoy el founder monotributista y cuánto margen le queda contando sus otros ingresos?
3. Si ese founder después es socio o administrador de la SAS, ¿puede seguir en el monotributo por otras actividades? (Ojo con la RG ARCA 5866/2026 y los honorarios de directores, según fuente T3.)
4. ¿A partir de qué facturación mensual conviene la SAS, con números reales de contador, autónomos e IIBB?
5. ¿Nos conviene inscribirnos en el **Régimen de Economía del Conocimiento** (Ley 27.506) una vez que tengamos la SAS? ¿Requisitos para micro?
6. Con el monotributo unificado de CABA, ¿nos retiene IIBB Mercado Pago o el banco (SIRCREB)?
7. ¿Hoy hay percepción de Ganancias o IIBB al pagar OpenAI, Anthropic, Supabase y Meta con tarjeta argentina? ¿Conviene pagar con dólares propios?
8. ¿El precio del abono lo publicamos "+ IVA" desde ya, pensando en la SAS?
9. (Abogado) ¿Alcanza el art. 25 de la Ley 25.326 más las cláusulas modelo de la Disp. 60-E/2016 para la transferencia a EE.UU., o pedimos también consentimiento en el primer mensaje?
10. (Abogado) ¿Qué tope de responsabilidad es razonable en el contrato con el comercio por un precio mal informado por el bot?
11. (Abogado) ¿Nos alcanza el botón de baja de la Disp. 954/2025 para el abono si el comercio contrata como empresa?
12. ¿Inscribimos la base en la AAIP a nombre del founder ahora y después la migramos a la SAS?

---

## 13. Data gaps

- **DATA GAP:** número exacto y texto de la RG de ARCA que eliminó la percepción del 30% desde el 02/01/2026, y si alcanza a servicios digitales B2B pagados con tarjeta. Las fuentes se contradicen.
- **DATA GAP:** alícuota 2026 de la percepción de IIBB CABA sobre servicios digitales del exterior.
- **DATA GAP:** tabla oficial de AGIP del componente IIBB del monotributo unificado desde agosto de 2026 (solo hay un dato T3 de la cat. A, $30.025).
- **DATA GAP:** tasas IGJ 2026 exactas para constituir una SAS (no se encontraron en una fuente oficial; usar la calculadora de tasas de la IGJ).
- **DATA GAP:** si Meta acepta a una persona física monotributista como negocio verificado para ser Tech Provider, y cuántos clientes se pueden onboardear antes de verificar.
- **DATA GAP:** montos actualizados de las multas de la AAIP (los últimos topes encontrados son de la Res. 244/2022).
- **DATA GAP:** autor y estado de comisión del Expte. 3397-D-2026.
- **DATA GAP:** honorarios 2026 de abogados para T&C y DPA (los montos de la §10 son supuestos).
- **DATA GAP:** norma 2026 específica sobre información de precios en canales de mensajería.

---

## 14. Fuentes (consultadas el 09/11/2026)

**T1 (oficiales / primarias)**
- ARCA, categorías del monotributo (vigente desde el 01/08/2026): https://www.arca.gob.ar/monotributo/categorias.asp
- AAIP, inscripción de responsable de bases privadas: https://www.argentina.gob.ar/servicio/inscribir-un-responsable-de-bases-de-datos-personales-privadas
- AAIP, trámites de datos personales: https://www.argentina.gob.ar/aaip/datospersonales/tramites
- Instructivo TAD de la AAIP: https://www.argentina.gob.ar/sites/default/files/instructivo_tad_inscripcionymodificacionresponsable_basesprivadas_3.pdf
- Res. AAIP 244/2022: https://www.argentina.gob.ar/normativa/nacional/norma-376196/texto
- Meta, Términos para WhatsApp Business Platform (act. 23/09/2026): https://www.facebook.com/legal/Meta-Terms-for-WhatsApp-Business-Platform
- WhatsApp Business Messaging Policy (act. 23/09/2026): https://whatsappbusiness.com/es-la/policy/
- Meta, Get started for Tech Providers: https://developers.facebook.com/docs/whatsapp/solution-providers/get-started-for-tech-providers
- Mercado Pago, OAuth: https://www.mercadopago.com.ar/developers/es/docs/security/oauth/creation.md
- Res. SCI 424/2020 (derogada), Boletín Oficial: https://www.boletinoficial.gob.ar/detalleAviso/primera/235729/20201005

**T2 (estudios y medios especializados)**
- Allende & Brea, Expte. 3397-D-2026 (12/08/2026): https://allende.com/privacidad-y-ciberseguridad/se-reintroduce-en-el-congreso-el-proyecto-de-reforma-integral-del-regimen-argentino-de-proteccion-de-datos-personales-08-12-2026/
- Marval, nuevo proyecto de ley de datos: https://www.marval.com/publicacion/nuevo-proyecto-de-ley-de-proteccion-de-datos-17691
- Allende & Brea, Disp. 954/2025: https://allende.com/administrativo/el-gobierno-refuerza-la-proteccion-al-consumidor-en-el-comercio-electronico-09-05-2025/
- Marval, Res. AAIP 126/2024: https://www.marval.com/publicacion/novedades-en-la-clasificacion-de-infracciones-y-en-el-regimen-de-graduacion-de-sanciones-16832
- Colegio de Escribanos, RG IGJ 11/2026: https://www.colegio-escribanos.org.ar/2026/09/24/igj-resolucion-general-11-26/
- TechCrunch, prohibición de chatbots de propósito general: https://techcrunch.com/2025/10/18/whatssapp-changes-its-terms-to-bar-general-purpose-chatbots-from-its-platform
- iProfesional, topes del monotributo septiembre 2026: https://www.iprofesional.com/impuestos/463297-arca-definio-el-monotributo-cuanto-se-paga-en-septiembre-2026-y-cuales-son-nuevos-topes.amp
- Diario Judicial, proyecto de IA (31/07/2026): https://www.diariojudicial.com/news-97386-regular-la-ia
- DPL News, ley de IA en el Congreso: https://dplnews.com/?p=298984

**T3 (blogs, medios generales, vendors)**
- Blog del Contador, monotributo unificado CABA: https://blogdelcontador.com.ar/news-46447-nuevo-monotributo-unificado-en-caba-claves-del-regimen-simplificado-vigente-desde-enero-de-2026
- Blog del Contador, RG 5617 (nota del 19/12/2024, **vieja**): https://blogdelcontador.com.ar/arca-percepcion-ganancias-operaciones-en-moneda-extranjera
- Diario Popular, fin del 30% (enero de 2026): https://www.diariopopular.com.ar/economia/dolar-tarjeta-arca-elimina-ese-30-adicional-pero-no-todos-los-consumos-n878910
- Infoviajera, fin del recargo del 30%: https://www.infoviajera.com/2025/12/desde-enero-ya-no-regira-el-recargo-del-30-por-compras-con-tarjeta-en-dolares/
- Contadores en Red, baja de alícuotas de IIBB CABA desde junio de 2026: https://contadoresenred.com/ingresos-brutos-caba-baja-en-las-alicuotas-a-partir-de-junio-2026-a-quienes-beneficia/amp/
- Blog del Contador SIAP, alícuotas de IIBB CABA: https://siap.blogdelcontador.com.ar/rubro_normativa/alicuotas-ingresos-brutos-caba/
- Indicadores.ar, costo de crear una empresa: https://indicadores.ar/crear-empresa
- Contablix, guía de la SAS: https://contablix.ar/blog/sas-en-argentina-todo-lo-que-necesitas-saber-antes-de-armar-una-sociedad-guia-completa-2025
- Blog del Contador, capital mínimo de la SAS: https://blogdelcontador.com.ar/aumenta-el-capital-minimo-para-constituir-una-sas
- Twilio, FAQ del Tech Provider Program: https://twilio.com/docs/whatsapp/tech-provider-program/faq
- respond.io, política de chatbots de WhatsApp 2026: https://respond.io/blog/whatsapp-chatbot-policy-2026
- Ecosistema Startup, Decreto PBA 742/2026: https://ecosistemastartup.com/?p=110054
- Cronista, el monotributo y los profesionales en sociedad: https://www.cronista.com/economia-politica/monotributo-dudan-si-los-profesionales-podran-seguir-si-forman-sociedad
- Blog del Contador SIAP, honorarios de directores y monotributo (RG 5866/2026): https://siap.blogdelcontador.com.ar/?p=117263
