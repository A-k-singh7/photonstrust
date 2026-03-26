export default function SymRing({ width = 80, height = 50 }) {
  return (
    <svg viewBox="0 0 80 50" width={width} height={height}>
      {/* Bus waveguide (horizontal, bottom) */}
      <line x1="5" y1="38" x2="75" y2="38" stroke="#2196F3" strokeWidth="1.5" strokeLinecap="round" />
      {/* Ring resonator (circle, coupled above bus with gap) */}
      <circle cx="40" cy="22" r="13" fill="none" stroke="#2196F3" strokeWidth="1.5" />
      {/* Coupling gap indication — dashed region */}
      <line x1="30" y1="35" x2="50" y2="35" stroke="#2196F3" strokeWidth="0.5" strokeDasharray="2,2" opacity="0.5" />
      {/* Label */}
      <text x="40" y="48" fontSize="7" fill="#37474f" fontFamily="monospace" textAnchor="middle">Ring</text>
    </svg>
  );
}
