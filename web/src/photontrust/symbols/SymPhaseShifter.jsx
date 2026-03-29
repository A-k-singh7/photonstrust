export default function SymPhaseShifter({ width = 80, height = 50 }) {
  return (
    <svg viewBox="0 0 80 50" width={width} height={height}>
      {/* Horizontal waveguide */}
      <line x1="5" y1="30" x2="75" y2="30" stroke="#2196F3" strokeWidth="1.5" strokeLinecap="round" />
      {/* Electrode pad on top of waveguide */}
      <rect x="25" y="18" width="30" height="8" rx="1.5" fill="#f0f4f8" stroke="#FF9800" strokeWidth="1.5" />
      {/* Electrode contact lines */}
      <line x1="40" y1="18" x2="40" y2="10" stroke="#FF9800" strokeWidth="1.5" />
      <circle cx="40" cy="9" r="2" fill="#FF9800" />
      {/* Phi symbol */}
      <text x="40" y="7" fontSize="8" fill="#37474f" fontFamily="monospace" textAnchor="middle" dominantBaseline="auto">{"\u03C6"}</text>
      {/* Label */}
      <text x="40" y="44" fontSize="7" fill="#37474f" fontFamily="monospace" textAnchor="middle">PS</text>
    </svg>
  );
}
