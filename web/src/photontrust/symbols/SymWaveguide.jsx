export default function SymWaveguide({ width = 80, height = 50 }) {
  return (
    <svg viewBox="0 0 80 50" width={width} height={height}>
      <line x1="5" y1="25" x2="75" y2="25" stroke="#2196F3" strokeWidth="3" strokeLinecap="round" />
      <ellipse cx="40" cy="25" rx="8" ry="4" fill="#2196F3" opacity="0.15" />
    </svg>
  );
}
