export default function SymMMI({ width = 80, height = 50 }) {
  return (
    <svg viewBox="0 0 80 50" width={width} height={height}>
      {/* Central multimode region */}
      <rect x="25" y="12" width="30" height="26" rx="2" fill="#f0f4f8" stroke="#455a64" strokeWidth="1.5" />
      {/* Input waveguide 1 (top-left) */}
      <line x1="5" y1="18" x2="25" y2="18" stroke="#2196F3" strokeWidth="1.5" strokeLinecap="round" />
      {/* Input waveguide 2 (bottom-left) */}
      <line x1="5" y1="32" x2="25" y2="32" stroke="#2196F3" strokeWidth="1.5" strokeLinecap="round" />
      {/* Output waveguide 1 (top-right) */}
      <line x1="55" y1="18" x2="75" y2="18" stroke="#2196F3" strokeWidth="1.5" strokeLinecap="round" />
      {/* Output waveguide 2 (bottom-right) */}
      <line x1="55" y1="32" x2="75" y2="32" stroke="#2196F3" strokeWidth="1.5" strokeLinecap="round" />
      {/* Mode pattern inside MMI */}
      <ellipse cx="33" cy="25" rx="3" ry="8" fill="#2196F3" opacity="0.1" />
      <ellipse cx="40" cy="25" rx="3" ry="8" fill="#2196F3" opacity="0.1" />
      <ellipse cx="47" cy="25" rx="3" ry="8" fill="#2196F3" opacity="0.1" />
      {/* Label */}
      <text x="40" y="28" fontSize="7" fill="#37474f" fontFamily="monospace" textAnchor="middle">MMI</text>
    </svg>
  );
}
