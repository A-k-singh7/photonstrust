export default function SymAWG({ width = 80, height = 50 }) {
  return (
    <svg viewBox="0 0 80 50" width={width} height={height}>
      {/* Left slab region (trapezoidal) */}
      <path
        d="M18 12 L28 8 L28 42 L18 38 Z"
        fill="#f0f4f8"
        stroke="#455a64"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      {/* Right slab region (trapezoidal) */}
      <path
        d="M52 8 L62 12 L62 38 L52 42 Z"
        fill="#f0f4f8"
        stroke="#455a64"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      {/* Array waveguides (fanning lines connecting slab regions) */}
      <path d="M28 12 C36 8, 44 8, 52 12" stroke="#2196F3" strokeWidth="1" fill="none" />
      <path d="M28 18 C36 15, 44 15, 52 18" stroke="#2196F3" strokeWidth="1" fill="none" />
      <path d="M28 25 C36 25, 44 25, 52 25" stroke="#2196F3" strokeWidth="1" fill="none" />
      <path d="M28 32 C36 35, 44 35, 52 32" stroke="#2196F3" strokeWidth="1" fill="none" />
      <path d="M28 38 C36 42, 44 42, 52 38" stroke="#2196F3" strokeWidth="1" fill="none" />
      {/* Input waveguide */}
      <line x1="5" y1="25" x2="18" y2="25" stroke="#2196F3" strokeWidth="1.5" strokeLinecap="round" />
      {/* Output waveguides */}
      <line x1="62" y1="15" x2="75" y2="13" stroke="#2196F3" strokeWidth="1.5" strokeLinecap="round" />
      <line x1="62" y1="22" x2="75" y2="21" stroke="#2196F3" strokeWidth="1.5" strokeLinecap="round" />
      <line x1="62" y1="29" x2="75" y2="30" stroke="#2196F3" strokeWidth="1.5" strokeLinecap="round" />
      <line x1="62" y1="36" x2="75" y2="38" stroke="#2196F3" strokeWidth="1.5" strokeLinecap="round" />
      {/* Label */}
      <text x="40" y="48" fontSize="7" fill="#37474f" fontFamily="monospace" textAnchor="middle">AWG</text>
    </svg>
  );
}
