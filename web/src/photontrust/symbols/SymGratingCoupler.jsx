export default function SymGratingCoupler({ width = 80, height = 50 }) {
  return (
    <svg viewBox="0 0 80 50" width={width} height={height}>
      {/* Horizontal waveguide stub */}
      <line x1="5" y1="35" x2="35" y2="35" stroke="#2196F3" strokeWidth="1.5" fill="none" strokeLinecap="round" />
      {/* Grating teeth — 5 parallel diagonal lines */}
      <line x1="38" y1="10" x2="44" y2="38" stroke="#2196F3" strokeWidth="1.5" />
      <line x1="44" y1="10" x2="50" y2="38" stroke="#2196F3" strokeWidth="1.5" />
      <line x1="50" y1="10" x2="56" y2="38" stroke="#2196F3" strokeWidth="1.5" />
      <line x1="56" y1="10" x2="62" y2="38" stroke="#2196F3" strokeWidth="1.5" />
      <line x1="62" y1="10" x2="68" y2="38" stroke="#2196F3" strokeWidth="1.5" />
      {/* Grating bounding outline */}
      <rect x="36" y="8" width="34" height="32" rx="2" fill="#f0f4f8" stroke="#455a64" strokeWidth="1.5" opacity="0.3" />
      {/* Downward arrow indicating fiber coupling */}
      <path d="M53 2 L53 8" stroke="#455a64" strokeWidth="1" markerEnd="none" />
      <polygon points="50,6 53,2 56,6" fill="#455a64" />
      {/* Label */}
      <text x="53" y="47" fontSize="7" fill="#37474f" fontFamily="monospace" textAnchor="middle">GC</text>
    </svg>
  );
}
