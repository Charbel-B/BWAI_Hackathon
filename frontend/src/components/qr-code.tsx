import { encode } from 'uqr'

/** QR code dessiné en SVG aux couleurs de la charte ; les modules sont arrondis. */
export function QrCode({
  value,
  label,
  className = '',
}: {
  value: string
  label: string
  className?: string
}) {
  const { data, size } = encode(value, { ecc: 'M', border: 1 })
  return (
    <svg
      viewBox={`0 0 ${size} ${size}`}
      role="img"
      aria-label={label}
      className={className}
      shapeRendering="geometricPrecision"
    >
      <rect width={size} height={size} rx={1.2} fill="white" />
      {data.flatMap((row, y) =>
        row.map((on, x) =>
          on ? (
            <rect
              key={`${x}-${y}`}
              x={x + 0.06}
              y={y + 0.06}
              width={0.88}
              height={0.88}
              rx={0.28}
              fill="var(--color-sky-deep)"
            />
          ) : null,
        ),
      )}
    </svg>
  )
}
