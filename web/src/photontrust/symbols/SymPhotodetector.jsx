export default function SymPhotodetector({ width = 80, height = 50 }) {
  return (
    <svg viewBox="0 0 80 50" width={width} height={height}>
      {/* Input waveguide */}
      <line x1="5" y1="28" x2="28" y2="28" stroke="#2196F3" strokeWidth="1.5" strokeLinecap="round" />
      {/* Absorber body (filled rectangle) */}
      <rect x="28" y="18" width="24" height="20" rx="2" fill="#455a64" stroke="#455a64" strokeWidth="1.5" />
      {/* Active region highlight */}
      <rect x="30" y="20" width="20" height="16" rx="1" fill="#37474f" stroke="none" />
      {/* Photon absorption arrows */}
      <path d="M35 14 L35 19" stroke="#2196F3" strokeWidth="1" />
      <polygon points="33,18 35,21 37,18" fill="#2196F3" />
      <path d="M43 14 L43 19" stroke="#2196F3" strokeWidth="1" />
      <polygon points="41,18 43,21 45,18" fill="#2196F3" />
      {/* Electrical contacts */}
      <line x1="34" y1="10" x2="34" y2="14" stroke="#FF9800" strokeWidth="1.5" />
      <text x="34" y="9" fontSize="7" fill="#FF9800" fontFamily="monospace" textAnchor="middle">+</text>
      <line x1="46" y1="10" x2="46" y2="14" stroke="#FF9800" strokeWidth="1.5" />
      <text x="46" y="9" fontSize="7" fill="#FF9800" fontFamily="monospace" textAnchor="middle">{"\u2013"}</text>
      {/* Label */}
      <text x="40" y="46" fontSize="7" fill="#37474f" fontFamily="monospace" textAnchor="middle">PD</text>
    </svg>
  );
}
