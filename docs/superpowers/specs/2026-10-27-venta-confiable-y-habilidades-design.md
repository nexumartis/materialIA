# Venta confiable y habilidades del vendedor

## Pedido y evidencia

El 27/10 el usuario pidió corregir las mejoras propuestas tras seis conversaciones de Claude/Codex personal y agregó su propio recorrido: catálogo → repuestos → flexible más consulta de canilla negra → monocomando negra mate → «si la aquaflux» → «la nro3». Quiere atención natural y habilidades internas como las guías que usa con agentes de desarrollo. Autorizó probar Ollama Cloud; `gpt-oss:120b-cloud` respondió la prueba mínima en 0,86 s. Ese dato no mide todavía una conversación comercial completa.

Alcance de este corte: consentimiento, cantidades y selección contextual, más tres guías procedurales de venta integradas al planner existente. Claude implementa; Codex personal revisa; root sólo documentación/coordinación. Base `de7abbe`. Las decisiones de implementación siguientes son del orquestador, usando Ponytail, no acuerdos adicionales atribuidos al usuario.

## Comportamiento

1. **Consultar no cambia carrito.** Negativas y preguntas hipotéticas/de disponibilidad no agregan ni preparan una compra. «Dale/sí» sólo ejecuta la última propuesta explícita de agregar/comprar con referente y cantidad, nunca una derivación o saludo. Mantener el resumen y confirmación de compra actuales, el pago verificado y el aislamiento por negocio.
2. **Cantidades inequívocas.** Distinguir sumar, fijar N, restar N y eliminar una línea. Medidas y precios («500 g», «40 cm», «$18.500») no son unidades. Si hay varios productos posibles, pedir una aclaración sin modificar estado. Cotizar cantidades antes de agregar es una lectura. Un mensaje con agregar y pedir total procesa ambas cosas en orden y muestra el total de la base.
3. **Referentes vigentes.** Resolver nombres/marca/características en las opciones que se están discutiendo antes de iniciar otra búsqueda. «La nro3», «la nro 3», «nro. 3» y variantes de la elección inequívoca seleccionan el ítem 3 de la última lista válida, sin interpretarlo como cantidad. Opción inválida pide aclaración y no muta. Mantener filtros pertinentes; un cambio de tipo no hereda restricciones ajenas. Una marca que todavía deja dos opciones exige aclarar, no elegir por azar.

   Resolución del builder check (criterio del orquestador): una orden directa inequívoca de agregar autoriza el carrito sin una confirmación extra. Una selección breve («sí, la Aquaflux», «la nro3») autoriza agregar una unidad sólo cuando responde a la propuesta vigente de agregar opciones/producto, con cantidad propuesta o una unidad por defecto; si la pregunta anterior era sólo informativa, enfoca el producto y pide aclaración/permiso para agregar. «Dale» después de derivación nunca es autorización comercial. En el recorrido, al resolver la mate se muestra su precio/stock y se propone agregar una, para que «sí, la Aquaflux» tenga ese antecedente explícito. La confirmación de pago/pedido sigue siendo posterior e independiente.
4. **Pedido compuesto del usuario.** En una lista que contiene un único flexible identificable, «quiero un flexible y también quiero alguna canilla nueva negra o moderna» agrega una unidad del flexible y continúa la exploración de canillas; no añade una canilla por explorar. La elección posterior unívoca de la monocomando negra mate/Aquaflux conserva el flexible. Si falta ambiente/dato necesario, hace una pregunta concreta. El último «nro3» del chat original se evalúa contra la lista que realmente produjo la versión corregida: si ya no existe esa posición, no inventar un ítem ni duplicar lo agregado. Probar aparte una lista válida de tres opciones con «la nro3».
5. **Persona y cierre.** Petición humana explícita recibe respuesta pertinente y `requires_human`; conservar/usar registro existente si corresponde y no afirmar una notificación o un canal inexistentes. Despedida sola no busca productos ni deriva. La bandeja humana completa es otro corte.
6. **Entrada al catálogo.** «¿Qué productos tenés?» presenta categorías/opciones reales o una pregunta útil que ayude a elegir; no repite el saludo ni supone productos por el nombre del rubro. Mantener respuestas compactas y selección posterior vinculada a la lista que se mostró.

Baseline cloud previo al arreglo: 13 mensajes por UI, 1,7–8,1 s, reproduce pérdida del flexible y agrega tres canillas; cambiar cantidades terminó bien pero mostró «carrito vacío» entre quitar/agregar. El texto del modelo redujo una lista a dos opciones mientras la referencia numérica seguía apuntando a una lista anterior. Por tanto texto, tarjetas y referentes deben corresponderse: no permitir renumeración/subconjuntos arbitrarios que desincronicen la selección; preferir la representación canónica existente. Una operación de cantidad debe producir un único resultado coherente, sin intermedios vacíos visibles ni quitar/reagregar en transacciones separadas.

## Habilidades internas — decisión mínima

Tres guías versionadas con el producto: `asesorar_catalogo`, `gestionar_carrito`, `cerrar_o_derivar`. Cada una indica cuándo actuar, pasos, datos/herramientas permitidos, cuándo preguntar y límites. Son instrucciones de negocio, no Superpowers/TDD/terminal ni código descargable. Se integran al prompt del planner actual, reemplazando repeticiones existentes; máximo orientativo 600 palabras entre las tres para cuidar contexto.

Reutilizar `_TOOLS`, perfil por negocio, políticas, documentos y memoria agregados por Tomi. Un módulo pequeño `backend/app/agent/sales_skills.py` puede conservar las guías y su renderizado; preferir esa forma sin nuevos paquetes, tablas, servicios ni cargador de plugins. No añadir un editor de skills al panel. El perfil configura datos/políticas; no permite romper invariantes ni habilitar herramientas desactivadas.

Las guías orientan al modelo en modo live; el modo mock necesita las correcciones de acción/contexto y no se vuelve inteligente por cargar texto. El modelo expresa y propone; el servidor controla precios, stock, pedidos, mutaciones y confirmaciones. No garantizar detección universal de intención mediante regex ni naturalidad humana por tener tres guías.

## Pruebas de aceptación

- «Dale, ¿cómo me avisan?» tras pedir humano y «No quiero armar carrito todavía. ¿Hay dos disponibles para comprar hoy?» dejan carrito/pedidos iguales, también ante planner guionado que proponga mutar esos casos.
- Con 3 unidades: «dejame dos» deja 2; «sacá una» deja 1; «sacá todas» elimina la línea. Sin tocar otras líneas ni stock reservado de pedidos confirmados.
- «Un martillo de 500 g, uno solo, por $18.500» usa cantidad 1. Cotizar dos a $18.500 informa $37.000 sin crear carrito/pedido. Una suma explícita posterior sí suma.
- Recorrido del usuario en catálogo con marcas reales de fixture: flexible $6.800 + canilla mate $89.900 ⇒ 1 de cada, $96.700, sin artículos ajenos. Elección por marca ambigua pregunta; elección 3 válida selecciona exactamente ese ID una vez.
- Preservar confirmación explícita, políticas del negocio, precios/stock reales, estado tras pagar, tokens del chat, evaluaciones en dry-run y herramientas desactivadas.
- Verificar integración de guías en planner guionado y evaluar comportamiento, no sólo presencia de frases en el prompt. Prueba real acotada con Ollama Cloud y los mismos mensajes; registrar tiempos, modo y fallos. Mantener fallos anteriores como evidencia.

Tests en contenedor descartable `materialia-test-20261026`, loopback 55436, migraciones 0001–0007. No correr tests/reset/seed sobre la demo activa (54322) ni remoto. Navegador de aceptación aislado en API 8078/web 4174 si hay cambios locales, evitando cambiar la demo hasta revisión. Sin migraciones nuevas, OCR, WhatsApp, cobros reales, autoentrenamiento ni publicación automática de este corte.
