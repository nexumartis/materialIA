import { useState } from "react";

/** Mini barras de puntos (una columna por día). El número y el detalle por día van en texto: el
 *  color nunca es la única señal. */
export function DotBars({ values, labels, color, rows = 8, label }: {
  values: number[]; labels: string[]; color: string; rows?: number; label: string;
}) {
  const max = Math.max(...values, 1);
  const gap = 7, r = 2.2;
  const w = values.length * gap, h = rows * gap;
  return (
    <svg className="dotbars" viewBox={`0 0 ${w} ${h}`} role="img" aria-label={label} preserveAspectRatio="xMaxYMax meet">
      {values.map((v, i) => {
        const filled = v > 0 ? Math.max(1, Math.round((v / max) * rows)) : 0;
        return (
          <g key={i}>
            <title>{`${labels[i]}: ${v}`}</title>
            {Array.from({ length: rows }, (_, j) => (
              <circle key={j} cx={i * gap + gap / 2} cy={h - j * gap - gap / 2} r={r}
                fill={j < filled ? color : "var(--dot-off)"} />
            ))}
          </g>
        );
      })}
    </svg>
  );
}

const TIERS = ["#f2c94c", "#f08a24", "#3ccf6a"];   // abajo → arriba: amarillo, naranja, verde

/** Matriz de puntos por día (ventas cobradas). Las columnas futuras quedan vacías: no se proyecta
 *  nada que no pasó. Hover o foco muestra el día; hay tabla con los mismos datos. */
export function DotMatrix({ days, todayIndex, rows = 9, money }: {
  days: { label: string; value: number; conversations: number }[]; todayIndex: number; rows?: number;
  money: (n: number) => string;
}) {
  const [hover, setHover] = useState<number | null>(null);
  const max = Math.max(...days.map((d) => d.value), 1);
  const gap = 11, r = 2.9, top = 4;
  const w = days.length * gap, h = rows * gap + top;
  const active = hover == null ? null : days[hover];
  return (
    <div className="dotmatrix">
      <div className="dotmatrix-readout" aria-live="polite">
        {active ? <><b>{active.label}</b> · {active.value ? money(active.value) : "sin ventas"} · {active.conversations} conversaciones</>
          : <span className="muted">Pasá el mouse o el foco por un día.</span>}
      </div>
      <svg viewBox={`0 0 ${w} ${h + 2}`} role="img" aria-label="Ventas cobradas por día" onMouseLeave={() => setHover(null)}>
        {days.map((d, i) => {
          const future = i > todayIndex;
          const filled = future || !d.value ? 0 : Math.max(1, Math.round((d.value / max) * rows));
          return (
            <g key={i} tabIndex={future ? -1 : 0} onMouseEnter={() => !future && setHover(i)}
              onFocus={() => setHover(i)} onBlur={() => setHover(null)}
              aria-label={future ? undefined : `${d.label}: ${d.value ? money(d.value) : "sin ventas"}`}>
              <rect x={i * gap} y={0} width={gap} height={h} className="hit" />
              {Array.from({ length: rows }, (_, j) => (
                <circle key={j} cx={i * gap + gap / 2} cy={h - j * gap - gap / 2} r={r}
                  fill={j < filled ? TIERS[Math.min(2, Math.floor((j / rows) * 3))] : "var(--dot-off)"}
                  opacity={hover === i || hover == null ? 1 : 0.55} />
              ))}
            </g>
          );
        })}
        <line x1={todayIndex * gap + gap} x2={todayIndex * gap + gap} y1={top - 2} y2={h + 2} className="today" />
        <circle cx={todayIndex * gap + gap} cy={top - 2} r={2.5} className="today-dot" />
      </svg>
      {/* Ejes en HTML: no escalan con el gráfico. */}
      <div className="dotmatrix-ticks" aria-hidden>
        <span>{days[0]?.label}</span>
        <b style={{ left: `${((todayIndex + 1) / days.length) * 100}%` }}>Hoy</b>
        <span>{days[days.length - 1]?.label}</span>
      </div>
    </div>
  );
}
