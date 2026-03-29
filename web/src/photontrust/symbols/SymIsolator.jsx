export default function SymIsolator({ width = 80, height = 50 }) {
  return (
    <svg viewBox="0 0 80 50" width={width} height={height}>
      {/* Waveguide left */}
      <line x1="5" y1="25" x2="28" y2="25" stroke="#2196F3" strokeWidth="1.5" strokeLinecap="round" />
      {/* Waveguide right */}
      <line x1="52" y1="25" x2="75" y2="25" stroke="#2196F3" strokeWidth="1.5" strokeLinecap="round" />
      {/* Triangle (diode arrow) pointing right */}
      <polygon points="28,14 52,25 28,36" fill="#f0f4f8" stroke="#455a64" strokeWidth="1.5" strokeLinejoin="round" />
      {/* Vertical bar at tip of triangle */}
      <line x1="52" y1="14" x2="52" y2="36" stroke="#455a64" strokeWidth="1.5" />
      {/* Arrow inside triangle indicating forward direction */}
      <path d="M34 25 L44 25" stroke="#2196F3" strokeWidth="1" fill="none" />
      <polygon points="43,23 47,25 43,27" fill="#2196F3" />
      {/* Label */}
      <text x="40" y="46" fontSize="7" fill="#37474f" fontFamily="monospace" textAnchor="middle">ISO</text>
    </svg>
  );
}
