# CFO: materialIA

> **Antecedente del 05/11/2026.** Para alcance, precio y próximos pasos leer [README](README.md) y la investigación del 09/11. Cifras, garantías, marca y calendario de este análisis no son acuerdos vigentes ni validación con clientes.

> Nota: la herramienta dice «a day»; acá la unidad es **un comercio pagando un mes** y el volumen es **por mes**. No es consejo financiero, impositivo ni legal: un contador tiene que revisar la estructura, el IVA (los precios son antes de impuestos) y la facturación antes de cobrar.

## Nota del CFO (actualizada con los costos de operaciones: Resend, Ollama Cloud Pro, comisión 7,6%)
- **El margen:** a $35.000/mes cada comercio deja **$17.836** (51%) después de su IA y la comisión de cobro. Con 40 comercios al final del año 1: margen 41% y **$2,6 M de ganancia operativa en el año**, *sin sueldos*.
- **La línea a mirar: los sueldos y la escala.** Con dos sueldos de $2 M/mes (escenario, no informado) el punto de equilibrio sube a **232 comercios a $35.000** o **149 a $45.000**, y el año 1 pierde ~$45 M. Hoy el negocio no paga dos sueldos con 40 clientes.
- **La segunda línea: el costo de IA** (estimado USD 10 por comercio/mes, no medido). Es el 41% del precio de $35.000. Si un comercio grande gasta USD 30, deja de ser rentable a ese precio.
- **Caja:** sin sueldos, hacen falta ~**$0,42 M** antes de que se pague solo (lanzamiento + primeros meses). Con sueldos, ~**$45 M**.
- **Tres formas de mejorar el margen (corridas con la herramienta):**
  1. Precio $45.000 en vez de $35.000: contribución $27.836 (62%), equilibrio sin sueldos 5 comercios, año 1 $5,0 M.
  2. Medir y bajar el costo de IA (modelo más barato, cortar conversaciones largas): cada USD 1 menos por comercio son $1.450 más de contribución por mes.
  3. Plan por uso o con tope de conversaciones para comercios grandes, así el costo de IA no se come el precio fijo.
- **Condiciones del directorio sobre plata:** «costo de IA medido» ❌ (es estimación), «margen positivo en el segmento» ✅ sólo sin sueldos, «precio validado con plata» ❌ (panel simulado).

# Unit economics: materialIA (SaaS: agente de ventas por chat para comercios)

Every number below comes from the input file. Nothing is looked up or guessed.

## One comercio-mes (suscripción)

| line | per comercio-mes (suscripción) |
| --- | ---: |
| Price | $35,000.00 |
| IA por comercio por mes (ESTIMACIÓN: ~USD 10 a 1 USD = ARS 1.450) | -$14,500.00 |
| Comisión de cobro de la suscripción (ESTIMACIÓN 7,6%: 6,29% + IVA al instante, comparador de terceros, sin confirmar en MP; ops.md) | -$2,664.00 |
| Soporte e implementación prorrateados (ESTIMACIÓN: 1 h/mes a ARS 0, la hacen los socios) | -$0.00 |
| **Contribution** (what each comercio-mes (suscripción) leaves to pay the fixed costs) | **$17,836.00** (51%) |

## The margin that matters

Fixed costs: $133,400 a month (Base de datos Supabase Pro (USD 25, precio público supabase.com/pricing 05/11/2026) $36,250, Hosting de API, worker y web (ESTIMACIÓN USD 25) $36,250, Mail Resend Pro USD 20 (precio público, resend.com/pricing 05/11/2026) + dominio ESTIMACIÓN USD 2 $31,900, IA: Ollama Cloud Pro USD 20 (precio público, ollama.com/pricing 05/11/2026; incluye USD 60 de uso) $29,000, Sueldos de los socios (NO INFORMADO: 0 en este escenario) $0).

- **Break-even: 8 comercio-mes (suscripción)s a day.** Below that you lose money every month.
- **Profit margin at your plan** (40 a day): **41%** of every sale, after every cost.
- Capacity: 100000 a day.

## Year 1, month by month

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

## What if

| scenario | margin at plan | break-even a day | year 1 profit |
| --- | ---: | ---: | ---: |
| Base plan | 41% | 8 | $2,644,168 |
| Price -10% | 35% | 10 | $1,811,168 |
| Volume -20% | 39% | 8 | $1,795,174 |
| Unit costs +15% | 34% | 9 | $2,031,413 |

No red flags in these numbers. They are only as good as the inputs: check every cost against a real quote.
