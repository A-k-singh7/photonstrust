export default function SymMZM({ width = 80, height = 50 }) {
  return (
    <svg viewBox="0 0 80 50" width={width} height={height}>
      {/* Input waveguide */}
      <line x1="5" y1="25" x2="15" y2="25" stroke="#2196F3" strokeWidth="1.5" strokeLinecap="round" />
      {/* Splitter — Y-branch to two arms */}
      <path d="M15 25 C20 25, 22 14, 28 14" stroke="#2196F3" strokeWidth="1.5" fill="none" />
      <path d="M15 25 C20 25, 22 36, 28 36" stroke="#2196F3" strokeWidth="1.5" fill="none" />
      {/* Top arm */}
      <line x1="28" y1="14" x2="52" y2="14" stroke="#2196F3" strokeWidth="1.5" />
      {/* Bottom arm */}
      <line x1="28" y1="36" x2="52" y2="36" stroke="#2196F3" strokeWidth="1.5" />
      {/* Combiner — Y-branch merging */}
      <path d="M52 14 C58 14, 60 25, 65 25" stroke="#2196F3" strokeWidth="1.5" fill="none" />
      <path d="M52 36 C58 36, 60 25, 65 25" stroke="#2196F3" strokeWidth="1.5" fill="none" />
      {/* Output waveguide */}
      <line x1="65" y1="25" x2="75" y2="25" stroke="#2196F3" strokeWidth="1.5" strokeLinecap="round" />
      {/* Electrode on top arm (orange) */}
      <rect x="33" y="9" width="14" height="5" rx="1" fill="#f0f4f8" stroke="#FF9800" strokeWidth="1.2" />
      {/* Electrode on bottom arm (orange) */}
      <rect x="33" y="33" width="14" height="5" rx="1" fill="#f0f4f8" stroke="#FF9800" strokeWidth="1.2" />
      {/* Voltage labels */}
      <text x="40" y="7" fontSize="6" fill="#FF9800" fontFamily="monospace" textAnchor="middle">V</text>
      <text x="40" y="45" fontSize="6" fill="#FF9800" fontFamily="monospace" textAnchor="middle">V</text>
    </svg>
  );
}
