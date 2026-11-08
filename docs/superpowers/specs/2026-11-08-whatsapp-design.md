# WhatsApp: el agente atiende en el número del local — diseño

**Fecha:** 08/11/2026. **Pidió:** Mati. **Aprobado como prioridad:** Tomás (WhatsApp habilitado por ambos socios).
**Estado:** borrador para revisión. Nada de esto está construido todavía.

## Por qué

Sin WhatsApp el producto no se puede vender: los clientes de un comercio argentino le escriben al
WhatsApp del local, no a una web. El panel simulado del PR #72 lo confirma: casi todos los «no»
fueron «mis clientes me escriben por WhatsApp». El objetivo de esta etapa es que el agente atienda
**en el WhatsApp del local** para salir a ofrecerlo gratis (o un mes gratis) a los primeros
comercios y aprender de ellos. El precio todavía no importa; importa que lo usen.

## Qué tiene que pasar (objetivo)

- Un local conecta **su propio número** desde el panel, solo, en unos 10 minutos, con una
  videollamada nuestra de acompañamiento. No vamos al local.
- El cliente le escribe al número de siempre y le contesta el agente, con el mismo cerebro que hoy
  atiende la web: catálogo y stock reales, carrito, pedido, cobro verificado, turnos, envío o retiro,
  fotos y audios.
- El dueño puede intervenir desde su celular o desde el panel **sin que el agente le conteste encima**.
- **Éxito:** un primer local real atendiendo clientes reales por WhatsApp.

## Qué no entra en esta versión

- Mensajes que inicia el negocio fuera de la ventana de 24 horas: plantillas de Meta, campañas
  reales, recordatorios. Van con el proyecto de campañas.
- Instagram, Facebook y Messenger.
- Varios números por local.
- Integración con correos (OCA, Correo Argentino, envíos en el día): proyecto aparte.
- Promociones manejadas por el dueño, Mercado Libre y facturación: proyectos aparte, en ese orden
  después de este.
- Intermediarios (Twilio, Infobip, 360dialog): no se usan.

## Lo que haría que esto salga mal aunque funcione

- Que el agente le conteste al cliente encima del dueño.
- Que un local quede conectado con una cuenta o un número que sea de Nexumartis y no suyo.
- Romper las reglas del producto: inventar precios o stock, o dar por pagado algo no verificado.
- Resolver el negocio a partir de algo que manda el cliente o el modelo. El negocio sale **sólo**
  del número de WhatsApp que recibió el mensaje (`phone_number_id`), registrado por nosotros.
- Perder o duplicar mensajes: Meta reintenta los avisos y puede mandar el mismo mensaje dos veces.
- Que el agente funcione como asistente de uso general. Desde el 15/01/2026 Meta lo prohíbe en la
  API de WhatsApp; los agentes de un negocio (ventas, pedidos, atención) sí están permitidos. El
  agente ya se limita al negocio; hay que mantenerlo así.

## Decisiones tomadas

| Decisión | Quién |
|---|---|
| Conexión **directa** con la Cloud API de Meta. Nexumartis se registra como **Tech Provider**. Sin intermediarios. | Mati |
| Cada local es **dueño** de su cuenta de Meta Business, su cuenta de WhatsApp Business (WABA) y su número. Los crea él mismo en el **Embedded Signup** (versión 4) durante el alta. Meta le cobra a **su** tarjeta, que es obligatoria para clientes de un Tech Provider. | Mati, siguiendo la estructura de Meta |
| El agente atiende en el **mismo número** que el local ya usa, con la **coexistencia** con la app WhatsApp Business: el dueño sigue usando la app en su celular. Si la coexistencia no anda en Argentina o para ese número, se usa un número nuevo sólo para el agente. | Mati (disponibilidad en AR sin confirmar) |
| Un solo backend y una sola base para todos los locales (lo multi-negocio que ya existe). | Ya existe |
| Manejo dueño/agente: el agente atiende por defecto; si el dueño escribe desde la app, el agente se pausa en **esa** conversación; un timer lo hace retomar; botones en el panel; avisos al dueño. | Mati |
| Desarrollo y pruebas con el **número de prueba** que Meta da a cualquier app de desarrollador, antes de terminar la verificación de Nexumartis. | Mati |
| Cuando el agente retoma, lee **toda** la conversación desde su último mensaje, escriba quien escriba (el dueño desde el celular o una persona desde el panel), sean 1 o 100 mensajes. | Mati |
| La pausa por un mensaje del dueño **vence sola** a las 2 horas sin mensajes del dueño. | Mati |
| Los audios del cliente **siempre se entienden**. El agente **no** contesta con voz por su cuenta: lo hace sólo si el cliente lo pide, porque la voz sintética se nota. | Mati |
| **Todo en planes gratis** por ahora (ElevenLabs, IA, Meta). Se paga cuando aparezca un límite real. | Mati |
| Se saca «NO WhatsApp» de `CLAUDE.md` y del README en este mismo cambio. | Mati y Tomás |

## Cómo lo vive cada uno

### El cliente del local
- Le escribe al número del local y le contesta el agente con el nombre y el tono del perfil del local.
- **Productos:** las tarjetas de la web se traducen a WhatsApp. Cada producto con foto va como
  imagen con texto (nombre, precio, disponibilidad) y los que no tienen foto, como texto. Las
  acciones van como botones de respuesta (hasta 3, título de hasta 20 caracteres) o como una lista
  (hasta 10 filas). El agente ya arma su respuesta pensando en esto (`_card` y `_ui` en
  `agent/sales_agent.py`): cada botón manda un texto que el agente ya entiende («agregame la 2»,
  «comprar», «sí»), así que si el cliente lo escribe a mano funciona igual.
- **Fotos:** el cliente manda una foto y el agente la busca en el catálogo, como hoy en la web
  (`domain/vision.py`).
- **Audios:** el cliente manda una nota de voz (WhatsApp la manda en OGG/Opus) y el agente la
  transcribe con ElevenLabs. Esto funciona siempre, para todos los locales (hoy el audio sólo anda
  para un negocio de demo y sólo acepta WAV: hay que abrirlo a todos y aceptar OGG/Opus).
- **Respuesta con voz:** el agente contesta con texto. Manda una nota de voz sólo si el cliente se
  lo pide («mandámelo en audio»), y en ese caso con la respuesta que pidió. Nunca de forma
  automática.
- **Pago:** el link de pago o los datos de la transferencia van en el mensaje. La confirmación del
  pago verificado llega por el mismo chat.
- **Turnos, entregas y envíos:** los mismos pasos que en la web.
- Stickers, ubicación, contactos o documentos: el agente responde amablemente que por ahora entiende
  texto, fotos y audios.

### El dueño del local
- **Alta:** en el panel, «Conectar WhatsApp». Se abre la ventana de Meta: entra con su Facebook,
  crea o elige su cuenta de Meta Business, elige su número (en coexistencia, el que ya usa en la app
  WhatsApp Business), confirma con el código y le da permiso a la app de Nexumartis. Al volver, el
  panel muestra «WhatsApp conectado: +54 9 11 …» y un botón para desconectar.
- Necesita tener: cuenta de Facebook, el número en la app WhatsApp Business (si usa el WhatsApp
  común, primero lo pasa: es gratis y conserva los chats), el celular para el código y una tarjeta
  en su cuenta de Meta.
- **Día a día:** ve las conversaciones de WhatsApp en la bandeja del panel, igual que las de la web,
  con la marca del canal. Puede contestar desde el panel o desde la app en su celular.

### Nexumartis (una sola vez)
- Cuenta de Meta Business de Nexumartis **verificada** (razón social o CUIT, dirección, web con
  dominio propio).
- App de Meta de tipo empresa con el producto WhatsApp, alta como Tech Provider, revisión de la app
  para los permisos `whatsapp_business_messaging` y `whatsapp_business_management`, y la
  configuración del Embedded Signup.
- Política de privacidad y términos publicados en una URL (la revisión de Meta los pide).
- Backend publicado con HTTPS, porque Meta necesita una URL pública para avisar los mensajes. En
  desarrollo alcanza un túnel.

## Comportamiento detallado

### 1. Conexión de un local
- El panel abre el Embedded Signup con el SDK de Facebook. Al terminar, el navegador recibe un
  código de un solo uso y los identificadores de la WABA y del número.
- El backend cambia el código por el token de negocio del local, suscribe la app a la WABA del
  local, registra el número si hace falta (en coexistencia no) y guarda la conexión del local:
  WABA, `phone_number_id`, número visible y token.
- Un número ya conectado a otro local no se puede conectar de nuevo.
- Si Meta avisa que el local revocó el permiso o desconectó el número, el panel lo muestra como
  desconectado y el agente deja de mandar.

### 2. Mensajes que llegan
- Una sola ruta para todos los locales (por ejemplo `/webhooks/whatsapp`): el GET responde la
  verificación de Meta y el POST verifica la firma `X-Hub-Signature-256` con el secreto de la app
  **antes** de leer nada.
- Se responde 200 enseguida y el mensaje se procesa aparte. Cada mensaje se procesa **una sola vez**,
  usando su identificador de Meta.
- El negocio sale del `phone_number_id`. Si el número no está registrado, se descarta.
- Una conversación por cliente y por local, canal `whatsapp`. El cliente se identifica por su
  número en `customer_identities` (ya preparado: canal `whatsapp`, se guarda el hash) y se conecta
  con su memoria como en la web. Para poder contestarle hay que guardar su número; cómo y dónde se
  protege lo decide quien lo construye.
- Tipos:
  - texto: va directo al agente (`handle_sales_message` con canal `whatsapp`);
  - respuesta de botón o de lista: se usa el texto que el botón tenía asignado;
  - imagen: se descarga y pasa por la misma descripción que las fotos de la web;
  - audio: se descarga y se transcribe;
  - lo demás: respuesta amable.
- Contactos bloqueados por el local (`privacy`): no se responde ni se gasta IA.
- Los topes de IA y los límites por cliente que ya existen se aplican igual.
- Los avisos de estado de Meta (enviado, entregado, leído, falló) se guardan al menos para los que
  fallan, y un fallo se muestra en la bandeja.

### 3. Mensajes que salen
- **Todo** mensaje hacia el cliente de una conversación de WhatsApp sale por WhatsApp, no sólo la
  respuesta del agente. Hoy hay varios lugares que escriben mensajes salientes: la respuesta del
  agente, la respuesta de una persona desde la bandeja (`domain/inbox.py`), la confirmación de pago
  (`payments/service.py`), los avisos del reparto (`domain/reparto.py`), los de envío por correo
  (`domain/shipping.py`) y la cotización (`main.py`). Todos pasan por
  `opportunities._add_message`, que es el lugar natural para encolar el envío en la misma
  transacción, con reintentos, siguiendo el mismo patrón de cola que ya usan los webhooks
  (`domain/webhooks.py` y el worker).
- La traducción de la respuesta del agente (`reply` + `ui`) a mensajes de WhatsApp sigue lo descrito
  en «El cliente del local». Un texto de WhatsApp admite hasta 4.096 caracteres.
- **Ventana de 24 horas:** sólo se le escribe a un cliente que escribió en las últimas 24 horas. Si un
  aviso (por ejemplo, «tu pedido salió») llega con la ventana cerrada, no se manda: queda marcado
  como no entregado y se avisa en el panel. Los avisos con ventana cerrada se resuelven en el
  proyecto de campañas, con plantillas.
- Los mensajes que el dueño manda desde su celular (ver punto 4) **no** se vuelven a mandar.

### 4. Dueño y agente en el mismo número
- Con coexistencia, Meta le avisa al backend de los mensajes que el dueño manda desde la app. Se
  guardan en la conversación como mensaje del negocio escrito por una persona.
- Cuando llega un mensaje del dueño, **el agente se pausa en esa conversación**.
- **Timer:** si el cliente vuelve a escribir y el dueño no le contesta dentro de la espera, el agente
  retoma. Cada mensaje nuevo del dueño reinicia la pausa. La espera es de 30 minutos por defecto y
  cada local la puede cambiar (el valor de 30 minutos es una propuesta para validar con los
  primeros locales).
- **Vencimiento:** si el dueño no escribe en 2 horas, la pausa vence sola y el agente atiende normal
  el próximo mensaje del cliente, sin esperar.
- **Al retomar, el agente lee todo** lo que pasó desde su último mensaje, escriba quien escriba (el
  dueño desde el celular o una persona desde el panel), y contesta en una sola respuesta todos los
  mensajes del cliente que se juntaron. Esto cambia lo que pasa hoy: los mensajes de una persona
  no entran al historial del modelo (`opportunities.get_recent_messages`). Para que entren sin
  romper la regla de honestidad, van marcados como escritos por el negocio: precios, stock y estados
  siguen saliendo sólo de la base. Si el dueño prometió algo que no está cargado (un descuento, una
  fecha), el agente no lo confirma por su cuenta y dice que lo confirma con el local.
- **Panel:**
  - «Tomar el control» y «Devolver al agente» funcionan como hoy (`inbox.take` y `inbox.release`):
    tomar el control no vence con el timer.
  - **«Pausar agente»** es un interruptor de todo el local: el agente deja de contestar en todas las
    conversaciones hasta que se vuelva a prender. Sirve para emergencias (precios mal cargados,
    feriado). Es una propuesta y no se habló en detalle.
  - La bandeja muestra en cada conversación si la atiende el agente, el dueño desde el celular (con
    el tiempo que falta para que el agente retome) o una persona desde el panel.
- **Avisos al dueño:** los que ya existen (derivación nueva, cliente sin respuesta) se usan también
  para WhatsApp.

### 5. Comprobantes y otras acciones del comprador
*Decisión de Claude, a revisar.*
- Si la conversación tiene un pedido esperando una transferencia, una foto o un PDF que manda el
  cliente se toma como **comprobante**: entra al mismo circuito de la web (`documents/store`, OCR y
  confirmación del dueño con `confirm_transfer`). Si no hay pedido esperando, la foto va a la
  búsqueda en el catálogo. Fuera de ese caso los PDF reciben la respuesta amable.
- Cancelar un pedido y la encuesta se hacen por texto o botones dentro del chat, como hoy en la web.
- La constancia de compra en PDF se manda como documento de WhatsApp cuando se genera.

### 6. Puesta en marcha
*Decisión de Claude, siguiendo el plan de lanzamiento de `founder/launch.md`.*
- El piloto necesita el sistema publicado. Para no mezclar teléfonos de clientes reales con datos de
  prueba, va en un proyecto de Supabase **de producción, aparte** del de desarrollo
  (`zfmjcturyhxytyfzmcha`). El backend y el worker van en Railway o Render y el panel en Vercel.
- Los mensajes salientes se mandan apenas se guardan, sin esperar la vuelta del worker (cada 60 s);
  el worker sólo reintenta los que fallaron.

## Seguridad y privacidad
- El token de cada local es un secreto: cifrado en la base, nunca se manda al navegador ni sale en
  los logs.
- El secreto de la app de Meta y el token de verificación del webhook van en variables de entorno.
- La firma de Meta se verifica antes de procesar cualquier aviso.
- Las fotos y los audios no se guardan, igual que hoy en la web.
- El número del cliente es un dato personal: entra en el bloqueo, el borrado y la redacción que ya
  existen (`domain/privacy.py`).

## Orden sugerido
1. Recibir y responder texto con el número de prueba de Meta: firma, negocio por `phone_number_id`,
   cola de salida.
2. Botones y listas, fotos y audios.
3. Dueño y agente: mensajes del dueño desde la app, pausa, timer, estados en la bandeja e interruptor
   del local.
4. Pantalla de conexión con el Embedded Signup y desconexión.
5. Piloto con un local real, que de paso confirma si la coexistencia anda en Argentina.

## Lo que decide quien lo construye
Las tablas y columnas, cómo se cifran los tokens, la versión de la Graph API, cómo se traduce cada
`ui` a mensajes, los tiempos de reintento, cómo se descargan los archivos de Meta y las pruebas.

## Situación del lado de Meta (08/11/2026)
No hay nada creado: ni cuenta de Meta Business de Nexumartis ni app de desarrollador. Es el primer
paso y lo hacen los socios (las cuentas no las puede crear un agente). La cuenta de Meta Business se
crea **desde el Facebook personal de uno de los socios**, que queda como administrador. No se crea un
Facebook falso «de la empresa»: Meta los da de baja y puede bloquear el negocio. Después se suma al
otro socio como administrador.

## Riesgos y cosas sin confirmar
- **Planes gratis:** el plan gratis de ElevenLabs no permite uso comercial de lo que genera (según
  terceros; verificar en sus términos). Para entender audios en desarrollo alcanza; para el piloto
  con un local real hay que revisarlo.
- **Coexistencia en Argentina:** la documentación de Meta no menciona países. Se confirma con el
  primer local. Sus límites conocidos: los grupos no se sincronizan, las listas de difusión se
  apagan, se desconectan los dispositivos vinculados (se pueden volver a vincular hasta 4, sin
  WhatsApp para Windows) y el número queda en 20 mensajes por segundo.
- **Tiempos de Meta:** la verificación de Nexumartis y la revisión de la app pueden tardar días o
  semanas. Conviene arrancarlas ya, en paralelo con el código.
- **Costo para el local:** desde el 1/10/2026 Meta da 1.000 respuestas gratis por número y por mes y
  cobra desde la 1.001. Las plantillas de utilidad dentro de la ventana también se cobran. Lo paga
  el local en su cuenta de Meta.
- **Embedded Signup:** la versión 2 dejó de funcionar el 15/10/2026. Construir sobre la 4.
- **Concurrencia de IA:** el plan Pro de Ollama Cloud admite 3 pedidos simultáneos para toda la
  cuenta. Con varios locales atendiendo a la vez puede encolar.
- **El backend no está publicado:** sin una URL pública Meta no puede avisar los mensajes.

## Fuentes
- Meta: [Embedded Signup](https://developers.facebook.com/documentation/business-messaging/whatsapp/embedded-signup/overview/),
  [alta como Tech Provider](https://developers.facebook.com/documentation/business-messaging/whatsapp/embedded-signup/onboarding-customers-as-a-tech-provider),
  [coexistencia](https://developers.facebook.com/documentation/business-messaging/whatsapp/embedded-signup/onboarding-business-app-users),
  [precios](https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing),
  [Embedded Signup v3 y fin de la v2](https://developers.facebook.com/documentation/business-messaging/whatsapp/embedded-signup/version-3-public-preview/).
- Política sobre asistentes de uso general: [TechCrunch](https://techcrunch.com/2025/10/18/whatssapp-changes-its-terms-to-bar-general-purpose-chatbots-from-its-platform),
  [respond.io](https://respond.io/blog/whatsapp-chatbot-policy-2026).
