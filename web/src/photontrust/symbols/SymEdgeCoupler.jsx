export default function SymEdgeCoupler({ width = 80, height = 50 }) {
  return (
    <svg viewBox="0 0 80 50" width={width} height={height}>
      {/* Waveguide tapering wider toward chip facet */}
      <path
        d="M5 25 L50 25 L65 22 L65 28 L50 25"
        stroke="#2196F3"
        strokeWidth="1.5"
        fill="#2196F3"
        opacity="0.25"
      />
      <line x1="5" y1="25" x2="50" y2="25" stroke="#2196F3" strokeWidth="1.5" strokeLinecap="round" />
      {/* Taper outline */}
      <path
        d="M50 25 L65 21"
        stroke="#2196F3"
        strokeWidth="1.5"
        fill="none"
      />
      <path
        d="M50 25 L65 29"
        stroke="#2196F3"
        strokeWidth="1.5"
        fill="none"
      />
      {/* Chip facet — vertical line at right edge */}
      <line x1="65" y1="10" x2="65" y2="40" stroke="#455a64" strokeWidth="2" strokeLinecap="round" />
      {/* Facet hatching */}
      <line x1="65" y1="12" x2="69" y2="14" stroke="#455a64" strokeWidth="0.8" />
      <line x1="65" y1="18" x2="69" y2="20" stroke="#455a64" strokeWidth="0.8" />
      <line x1="65" y1="24" x2="69" y2="26" stroke="#455a64" strokeWidth="0.8" />
      <line x1="65" y1="30" x2="69" y2="32" stroke="#455a64" strokeWidth="0.8" />
      <line x1="65" y1="36" x2="69" y2="38" stroke="#455a64" strokeWidth="0.8" />
      {/* Label */}
      <text x="30" y="45" fontSize="7" fill="#37474f" fontFamily="monospace" textAnchor="middle">EC</text>
    </svg>
  );
}
