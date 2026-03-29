export default function SymTouchstone({ width = 80, height = 50 }) {
  return (
    <svg viewBox="0 0 80 50" width={width} height={height}>
      {/* Input waveguide */}
      <line x1="5" y1="25" x2="18" y2="25" stroke="#2196F3" strokeWidth="1.5" strokeLinecap="round" />
      {/* Black box rectangle */}
      <rect x="18" y="10" width="44" height="30" rx="3" fill="#f0f4f8" stroke="#455a64" strokeWidth="1.5" />
      {/* [S] label */}
      <text x="40" y="29" fontSize="12" fill="#37474f" fontFamily="monospace" textAnchor="middle" fontWeight="bold">[S]</text>
      {/* Output waveguide */}
      <line x1="62" y1="25" x2="75" y2="25" stroke="#2196F3" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}
