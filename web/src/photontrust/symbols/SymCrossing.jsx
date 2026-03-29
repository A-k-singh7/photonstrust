export default function SymCrossing({ width = 80, height = 50 }) {
  return (
    <svg viewBox="0 0 80 50" width={width} height={height}>
      {/* Horizontal waveguide */}
      <line x1="5" y1="25" x2="75" y2="25" stroke="#2196F3" strokeWidth="1.5" strokeLinecap="round" />
      {/* Vertical waveguide */}
      <line x1="40" y1="3" x2="40" y2="47" stroke="#2196F3" strokeWidth="1.5" strokeLinecap="round" />
      {/* Optimized crossing region — elliptical blobs */}
      <ellipse cx="40" cy="25" rx="5" ry="5" fill="#f0f4f8" stroke="#455a64" strokeWidth="1" />
      <ellipse cx="40" cy="25" rx="3" ry="3" fill="#2196F3" opacity="0.15" />
      {/* Small taper indications at crossing */}
      <ellipse cx="40" cy="25" rx="6" ry="2.5" fill="#2196F3" opacity="0.08" />
      <ellipse cx="40" cy="25" rx="2.5" ry="6" fill="#2196F3" opacity="0.08" />
    </svg>
  );
}
