export default function SymHeater({ width = 80, height = 50 }) {
  return (
    <svg viewBox="0 0 80 50" width={width} height={height}>
      {/* Horizontal waveguide */}
      <line x1="5" y1="32" x2="75" y2="32" stroke="#2196F3" strokeWidth="1.5" strokeLinecap="round" />
      {/* Zigzag resistor pattern (orange, above waveguide) */}
      <path
        d="M18 26 L24 14 L32 26 L40 14 L48 26 L56 14 L62 26"
        stroke="#FF9800"
        strokeWidth="1.5"
        fill="none"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* Electrical contact lines on ends */}
      <line x1="14" y1="26" x2="18" y2="26" stroke="#FF9800" strokeWidth="1.5" strokeLinecap="round" />
      <line x1="62" y1="26" x2="66" y2="26" stroke="#FF9800" strokeWidth="1.5" strokeLinecap="round" />
      {/* Contact pads */}
      <circle cx="14" cy="26" r="2" fill="#FF9800" />
      <circle cx="66" cy="26" r="2" fill="#FF9800" />
      {/* Label */}
      <text x="40" y="44" fontSize="7" fill="#37474f" fontFamily="monospace" textAnchor="middle">HTR</text>
    </svg>
  );
}
