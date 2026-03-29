export default function SymSSC({ width = 80, height = 50 }) {
  return (
    <svg viewBox="0 0 80 50" width={width} height={height}>
      {/* Narrow input waveguide on left */}
      <line x1="5" y1="25" x2="18" y2="25" stroke="#2196F3" strokeWidth="1.5" strokeLinecap="round" />
      {/* Taper: two converging lines expanding from narrow (left) to wide (right) */}
      <path
        d="M18 24 C30 23, 50 16, 68 12"
        stroke="#2196F3"
        strokeWidth="1.5"
        fill="none"
      />
      <path
        d="M18 26 C30 27, 50 34, 68 38"
        stroke="#2196F3"
        strokeWidth="1.5"
        fill="none"
      />
      {/* Taper fill */}
      <path
        d="M18 24 C30 23, 50 16, 68 12 L68 38 C50 34, 30 27, 18 26 Z"
        fill="#2196F3"
        opacity="0.08"
      />
      {/* Mode field indication at wide end */}
      <ellipse cx="68" cy="25" rx="3" ry="13" fill="#2196F3" opacity="0.12" />
      {/* Output line */}
      <line x1="68" y1="25" x2="75" y2="25" stroke="#2196F3" strokeWidth="3" strokeLinecap="round" />
      {/* Label */}
      <text x="40" y="47" fontSize="7" fill="#37474f" fontFamily="monospace" textAnchor="middle">SSC</text>
    </svg>
  );
}
