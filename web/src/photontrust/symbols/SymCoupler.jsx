export default function SymCoupler({ width = 80, height = 50 }) {
  return (
    <svg viewBox="0 0 80 50" width={width} height={height}>
      {/* Top waveguide: starts at top-left, curves down to center, then curves back up to top-right */}
      <path
        d="M5 15 C20 15, 25 23, 40 23 C55 23, 60 15, 75 15"
        stroke="#2196F3"
        strokeWidth="1.5"
        fill="none"
        strokeLinecap="round"
      />
      {/* Bottom waveguide: starts at bottom-left, curves up to center, then curves back down to bottom-right */}
      <path
        d="M5 35 C20 35, 25 27, 40 27 C55 27, 60 35, 75 35"
        stroke="#2196F3"
        strokeWidth="1.5"
        fill="none"
        strokeLinecap="round"
      />
      {/* Coupling region indicator */}
      <rect x="30" y="21" width="20" height="8" rx="2" fill="#2196F3" opacity="0.08" stroke="none" />
      {/* Label */}
      <text x="40" y="48" fontSize="7" fill="#37474f" fontFamily="monospace" textAnchor="middle">DC</text>
    </svg>
  );
}
