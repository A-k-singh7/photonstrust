export default function SymYBranch({ width = 80, height = 50 }) {
  return (
    <svg viewBox="0 0 80 50" width={width} height={height}>
      {/* Input waveguide */}
      <line x1="5" y1="25" x2="25" y2="25" stroke="#2196F3" strokeWidth="1.5" strokeLinecap="round" />
      {/* Upper branch — smooth curve from center to top-right */}
      <path
        d="M25 25 C35 25, 45 13, 75 13"
        stroke="#2196F3"
        strokeWidth="1.5"
        fill="none"
        strokeLinecap="round"
      />
      {/* Lower branch — smooth curve from center to bottom-right */}
      <path
        d="M25 25 C35 25, 45 37, 75 37"
        stroke="#2196F3"
        strokeWidth="1.5"
        fill="none"
        strokeLinecap="round"
      />
      {/* Junction point */}
      <circle cx="25" cy="25" r="2" fill="#2196F3" opacity="0.3" />
      {/* Label */}
      <text x="40" y="48" fontSize="7" fill="#37474f" fontFamily="monospace" textAnchor="middle">Y</text>
    </svg>
  );
}
