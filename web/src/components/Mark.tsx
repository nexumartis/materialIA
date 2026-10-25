// Marca de Presupuesto Vivo: una mampara corrediza (marco + dos paños), en el acento.
export function Mark({ size = 24 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      style={{ color: "var(--accent)", flex: "none" }}
      aria-hidden="true"
    >
      <rect x="2.5" y="3.5" width="19" height="17" rx="2" stroke="currentColor" strokeWidth="1.5" />
      <line x1="12" y1="3.5" x2="12" y2="20.5" stroke="currentColor" strokeWidth="1.5" />
      <line x1="7.2" y1="7.2" x2="7.2" y2="16.8" stroke="currentColor" strokeWidth="1.5" />
      <line x1="16.8" y1="7.2" x2="16.8" y2="16.8" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  );
}
