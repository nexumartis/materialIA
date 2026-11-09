# Panorama competitivo

> **Actualización del 09/11/2026:** leer [correcciones y límites](corrections-2026-11-09.md) junto con este documento. La investigación es insumo para validar; no acredita entrevistas, precios aceptados ni un piloto real.

**Phase:** 3 — Investigación de mercado (síntesis)
**Project:** materialia
**Date:** 2026-11-09
**Confidence:** Media (precios: alta, sacados de páginas oficiales; tracción de competidores nuevos: baja)

---

## Resumen
- **Mercado fragmentado, sin dueño en el mostrador** [Opinion]: hay muchos jugadores nuevos de 2025-26 y SaaS regionales en dólares, y dos gigantes con restricciones (Meta y Tiendanube).
- **Cambio importante respecto del 05/11:** el hueco que había encontrado Tommy ("nadie lee stock, arma el pedido y cobra en pesos sin tienda") **ya no está vacío**:
  - **AWAM** (USD 29) hace stock + carrito + link de Mercado Pago.
  - **Botias** cobra en pesos y verifica el pago.
  - **Meteor** verifica el pago por webhook.

  "Link de Mercado Pago + verificación" ya es algo que cualquiera ofrece [Data, B1].
- **Amenaza global: alta en lo genérico, media en el rubro.**

## Matriz
| Nombre | Qué hace | Precio de entrada | Para quién | Plata / tracción | Fuerte | Débil | Amenaza |
|---|---|---|---|---|---|---|---|
| **Meta Business AI** | Agente nativo en WhatsApp Business | En la app: gratis + Meta One USD 14,99–499 [Data T2]. Por API: ~USD 0,04–0,05 por mensaje del agente desde 01/08/2026 [Data T1] | Toda pyme | Meta / en AR desde feb-2026 | Viene instalado | Catálogo chico (100–500 productos según la fuente), no lee stock externo ni cobra | **Alta** a 6–24 meses |
| **AWAM** | Agente WA/IG + panel de stock, caja, ARCA; carrito + link MP | **USD 29** | Comercios chicos (ropa, gastronomía) | DATA GAP | Circuito completo y barato | No lee tu planilla (hay que migrar), sin reseñas ni verificación visible | **Alta** |
| **Tiendanube Chat Nube** | IA + carrito + cobro dentro del chat | AR$190–400 por conversación | Solo tiendas Tiendanube | USD 10M en IA; compró VICI | Cierra la venta en pesos | Exige tienda online | Alta, latente |
| **Prometheo** | CRM nativo de IA; cotiza y cierra | USD 50 | Pymes LatAm (inmobiliarias) | 600 pymes, ~USD 700k/año, sin inversión [Data T2, una sola fuente; iProUP decía USD 300k] | Tracción y precio | Generalista, sin stock visible | Media |
| **Botias** | Agente con link MP en pesos, confirma al acreditarse | USD 49 cobrado en ARS | Reservas y turnos | Bootstrapped | Pesos, API oficial, datos en AR | No maneja catálogos de productos | Media |
| **Vendi** | Sistema de gestión con bot de WhatsApp | AR$29.900 como adicional | Comercios, incluye ferreterías | "+700 comercios" | Ya tiene el stock del cliente | Sin API ni programa de socios | Media |
| **Meteor** | Agente + CRM; webhook de MP; stock vía Alegra/Shopify | USD 99 + implementación | Comercios con tienda o ERP | DATA GAP | Verificación de pago sólida | En USD, necesita tienda o ERP | Media-baja |
| **Vozia (DuoTach)** | Agente a medida con stock en vivo | USD 200 + USD 500–1.800 | Medianas; nombra corralones y mayoristas | DATA GAP | Conoce el rubro | Caro, a medida | Media (mayoristas) |
| **Cliengo / Botmaker / Leadsales / Kommo** | Chatbots y CRMs de WhatsApp | USD 35–220 [Data T1] | Pymes en general | Botmaker ~5.000 clientes [Data T2, 2022, VIEJO] | Marca, anuncios | Cobran en USD; quejas de bloqueos, soporte y cobros | Baja-media |
| **Darwin AI / notchatbot** | "Empleados IA" / CRM de e-commerce | USD 300+ o a consultar | Medianas, marcas | Darwin USD 7M+ | Producto maduro | No apuntan al mostrador | Baja |
| **Freelancer** | Bot a medida WA + Sheets | USD 30–1.200, pago único | Mayoristas, distribuidoras | Pedidos abiertos en Workana | A medida | Queda abandonado | Media (mayoristas) |
| **WhatsApp a mano + empleado** | Lo de siempre | Gratis o un sueldo (~$2 M/mes con cargas) | Todos | El 71,5% de los emprendedores vende por WA | Confianza y saber técnico | Catálogo de WA limitado, sin respuesta fuera de horario | **El rival principal** |

## Mapa de posicionamiento
- **Eje X:** responde y deriva ↔ cierra la venta con stock real.
- **Eje Y:** genérico ↔ especialista en el rubro.

| | Genérico | Especialista en el rubro |
|---|---|---|
| **Cierra la venta con stock real** | AWAM, Chat Nube (solo con tienda), Meteor | **Casi libre para el mostrador:** solo Vozia (caro, a medida, para medianas) y un prototipo de hackathon (Mostrador IA, Rosario, 01/11/2026) |
| **Responde y deriva** | Meta Business AI, Cliengo, Botmaker, Kommo, Prometheo | — |

## Lo que sigue libre
1. **Leer la planilla de Excel o Google Sheets de un local que no tiene ERP ni tienda online**, sin migrar nada. Algunos leen stock de otros sistemas: Meteor (Alegra, Shopify, Woo), Vendi (su propio sistema) y Vozia (a medida). Ningún SaaS barato lee la planilla tal como está; solo los freelancers y plantillas de n8n [Data, B1 y B2].
2. **Saber del rubro:** cotizar una lista de obra por foto o audio, armar combos técnicos (inodoro + depósito + flexible + llave) y manejar equivalencias. Nadie lo hace para el mostrador [Data, B1].
3. **Catálogos grandes:** el agente de Meta tiene un tope de 100–500 productos y una casa de sanitarios maneja cientos a miles [Data, B1 y B2].
4. **Instalación en persona y cobro en pesos.** Botias cobra en pesos pero es autoservicio; el resto cobra en USD o implementación aparte.

**Contradicción resuelta: tope del catálogo de Meta.** Una fuente dice 100 productos (Infogastronómica, sobre el agente) y otras dicen 500 (Leadsales, respond.io, Tiendanube, sobre el catálogo de WhatsApp). Pueden ser límites distintos. **En los dos casos queda corto para el rubro.**

**Contradicción resuelta: AWAM y Vendi.** El agente D2 no los encontró, pero B1, B3 y D1 leyeron sus sitios (awam.lat, vendiapp.com.ar). Le creemos a la lectura directa.

## Cómo consiguen clientes los competidores
- **Saturado:** anuncios de Meta (Kommo ~61, Darwin ~37 y Cliengo ~22 activos en AR), contenido genérico, registro solo y la tienda de apps de Tiendanube [Data, B3, Biblioteca de anuncios].
- **Libre:** la venta en persona en el local. Ningún competidor con IA va a la ferretería.
- **Para copiar:**
  - Vender el acompañamiento humano ("un experto dedicado", Cliengo).
  - Contar una historia de origen del rubro ("nació en la ferretería de mi viejo", Vendi).
  - Prueba sin tarjeta.
  - Comisión recurrente para quien refiere (Kommo).

## Riesgo de plataforma
| Plataforma | Probabilidad de copiar el núcleo | Plazo | Mitigación |
|---|---|---|---|
| Meta | 65–75% de cerrar ventas con link; 35–45% de leer stock externo de una pyme | 6–24 meses (central 12–18) | No competir en "responder"; ser el conector con el stock y el rubro, montado sobre la API oficial |
| Tiendanube | 30–40% de abrir Chat Nube sin tienda | 12–24 meses | Apuntar al local que no quiere tienda online; cotizar listas de obra |
| Sistemas de gestión (Dux, Vendi, Tango) | 25–35% de sumar su propio vendedor IA | 18–24 meses | Integrarse y usarlos como canal |
| Mercado Libre / MP | 15–25% | 18–36 meses | Tener la transferencia verificada como alternativa |
| Google | <15% | 24+ meses | Monitorear |

Todas las probabilidades son [Estimate] del agente B2.

## Costo de cambio
- **Lo que ata al local:** el número de WhatsApp y su historial (mitigado por la "coexistencia" de Meta, que en Argentina confirman solo los proveedores), el hábito, el empleado y el sistema de gestión ya pago.
- **Lo que lo hace cambiar:** no tener que cargar nada nuevo, ver una venta cobrada en 2 semanas, instalación en persona y un vecino que ya lo usa.

## Defensa
- **En tecnología, baja:** el stack de agente + MP + WhatsApp lo copian 5 o más jugadores, y a AWAM o Prometheo sumar Sheets les llevaría semanas [Opinion].
- **Puede ser media si se construye:**
  - una base de conocimiento del rubro que mejore con cada local;
  - la relación en persona con los corredores de CABA;
  - un canal con mayoristas.

## Data gaps
- AWAM: quién está detrás, tracción y si usa la API oficial.
- Tracción real de Botias, Meteor y Vozia.
- Precio actual de Darwin.
- Tarifa oficial del agente de Meta en AR.
- Si Business AI lee stock o arma pedidos: hay que probarlo con una cuenta.

## Conexiones estratégicas
- Los tres dolores del comprador (ver `target-audience.md`: silencio, precio viejo, listas sin cotizar) caen justo en el hueco libre: stock y precio reales + cotización de listas.
- La ventana (6–24 meses, central 12–18; ver `industry-trends.md`) pide moverse ya, chico y concentrado en el rubro.

---

## Flags

**Red Flags:**
- **El hueco original se achicó:** AWAM cubre gran parte del circuito por USD 29 (menos que $70.000) y Meta lo regala para lo básico. Sin la especialización en el rubro, materialIA es una más.

**Yellow Flags:**
- Defensa tecnológica baja; la ventaja es servicio y rubro, y eso cuesta horas.
- Prototipo del mismo rubro en un hackathon (01/11/2026): otros ven la misma idea.

## Sources
- `raw/direct-competitors.md`, `raw/indirect-competitors.md`, `raw/competitor-gtm.md`, `raw/channels.md` (con links y tiers).
- Páginas de precios oficiales vistas el 09/11/2026 (T1); Cronista, Forbes AR, iProUP, TechCrunch (T2); Biblioteca de anuncios de Meta (T1).
