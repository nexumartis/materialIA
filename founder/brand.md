# Marca: materialIA (nombre de trabajo)

> **Antecedente del 05/11/2026.** Para alcance, precio y próximos pasos leer [README](README.md) y la investigación del 09/11. Cifras, garantías, marca y calendario de este análisis no son acuerdos vigentes ni validación con clientes.

> Brief: posicionamiento A de `marketing.md` (el ferretero de barrio que quiere vender fuera de horario; cotiza con su lista real y cobra verificado, sin tienda online). Los socios descartaron los nombres genéricos (Vendí, Mostrador, Dale…).

## 1. Diez candidatos

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

## 2. Shortlist y chequeos a correr (los hacen ustedes)

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

## 3. Promesa, tagline y voz

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

## 4. La identidad, como brief

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

## 5. Las primeras cinco cosas que ve un cliente

1. **Inicio:** «Tu mostrador, abierto de noche.» Abajo, una demo rotulada «catálogo de ejemplo» y el botón «Quiero ser piloto (quedan N)», con el número real.
2. **El «envase»:** QR de mostrador y calco de vidriera para el comercio: «¿Cerrado? Pedí acá. Precio y stock reales.»
3. **La confirmación:** «Pago confirmado por Mercado Pago. Tu pedido está pagado.» o «Recibimos tu comprobante. El comercio está verificando la transferencia.» Nunca dice «pagado» antes de tiempo.
4. **Primer post:** «Qué es y qué no es Hornel», con «todavía no anda en WhatsApp» dicho de frente.
5. **Respuesta a la primera queja:** «Tenés razón, eso no estuvo bien. Lo revisamos hoy y te contamos qué pasó y qué cambiamos. Firma: Tomás.» Sin plantillas ni excusas.

Siguiente: `/founder-ops` y `/founder-launch` (ya existen: actualizarlos con el nombre cuando esté confirmado).
