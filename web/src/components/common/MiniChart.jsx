/**
 * Lightweight SVG line chart — no external dependencies.
 * Props:
 *   data: array of { x: number, y: number, label?: string }[]
 *         (array of series, each series is an array of points)
 *   width: number (default 280)
 *   height: number (default 160)
 *   xLabel: string (default "")
 *   yLabel: string (default "")
 *   colors: string[] (default palette)
 */
export default function MiniChart({ data = [], width = 280, height = 160, xLabel = "", yLabel = "", colors }) {
  const palette = colors || ["#2196F3", "#FF9800", "#4CAF50", "#E91E63", "#9C27B0", "#00BCD4", "#FF5722", "#795548"];

  const margin = { top: 10, right: 10, bottom: 28, left: 45 };
  const plotW = width - margin.left - margin.right;
  const plotH = height - margin.top - margin.bottom;

  // Return null if no data
  if (!data.length || !data.some((s) => s.length > 0)) return null;

  // Flatten all points to get global x/y range
  const allPoints = data.flat();
  if (!allPoints.length) return null;

  let xMin = Infinity;
  let xMax = -Infinity;
  let yMin = Infinity;
  let yMax = -Infinity;
  for (const p of allPoints) {
    if (p.x < xMin) xMin = p.x;
    if (p.x > xMax) xMax = p.x;
    if (p.y < yMin) yMin = p.y;
    if (p.y > yMax) yMax = p.y;
  }

  // Handle edge cases: single point or all-same values
  if (xMin === xMax) {
    xMin -= 1;
    xMax += 1;
  }
  if (yMin === yMax) {
    yMin -= 1;
    yMax += 1;
  }

  const xRange = xMax - xMin;
  const yRange = yMax - yMin;

  function scaleX(x) {
    return margin.left + ((x - xMin) / xRange) * plotW;
  }
  function scaleY(y) {
    return margin.top + plotH - ((y - yMin) / yRange) * plotH;
  }

  // Generate tick values (3-5 ticks)
  function makeTicks(min, max, count) {
    if (count < 2) return [min];
    const step = (max - min) / (count - 1);
    const ticks = [];
    for (let i = 0; i < count; i++) {
      ticks.push(min + step * i);
    }
    return ticks;
  }

  function formatTick(v) {
    const abs = Math.abs(v);
    if (abs === 0) return "0";
    if (abs >= 1000) return v.toFixed(0);
    if (abs >= 100) return v.toFixed(0);
    if (abs >= 10) return v.toFixed(1);
    if (abs >= 1) return v.toFixed(2);
    return v.toPrecision(3);
  }

  const xTicks = makeTicks(xMin, xMax, 5);
  const yTicks = makeTicks(yMin, yMax, 5);

  const gridColor = "#e0e0e0";
  const axisColor = "#999";
  const fontStyle = { fontFamily: '"IBM Plex Mono", monospace', fontSize: "9px", fill: "#666" };
  const labelStyle = { fontFamily: '"IBM Plex Mono", monospace', fontSize: "10px", fill: "#444" };

  return (
    <svg width={width} height={height} style={{ fontFamily: '"IBM Plex Mono", monospace', display: "block" }}>
      {/* Grid lines (horizontal) */}
      {yTicks.map((t, i) => (
        <line
          key={`hg-${i}`}
          x1={margin.left}
          y1={scaleY(t)}
          x2={margin.left + plotW}
          y2={scaleY(t)}
          stroke={gridColor}
          strokeDasharray="3,3"
          strokeWidth={0.5}
        />
      ))}
      {/* Grid lines (vertical) */}
      {xTicks.map((t, i) => (
        <line
          key={`vg-${i}`}
          x1={scaleX(t)}
          y1={margin.top}
          x2={scaleX(t)}
          y2={margin.top + plotH}
          stroke={gridColor}
          strokeDasharray="3,3"
          strokeWidth={0.5}
        />
      ))}

      {/* Axis lines */}
      {/* X axis */}
      <line x1={margin.left} y1={margin.top + plotH} x2={margin.left + plotW} y2={margin.top + plotH} stroke={axisColor} strokeWidth={1} />
      {/* Y axis */}
      <line x1={margin.left} y1={margin.top} x2={margin.left} y2={margin.top + plotH} stroke={axisColor} strokeWidth={1} />

      {/* X tick labels */}
      {xTicks.map((t, i) => (
        <text key={`xt-${i}`} x={scaleX(t)} y={margin.top + plotH + 12} textAnchor="middle" style={fontStyle}>
          {formatTick(t)}
        </text>
      ))}

      {/* Y tick labels */}
      {yTicks.map((t, i) => (
        <text key={`yt-${i}`} x={margin.left - 4} y={scaleY(t) + 3} textAnchor="end" style={fontStyle}>
          {formatTick(t)}
        </text>
      ))}

      {/* Axis labels */}
      {xLabel ? (
        <text x={margin.left + plotW / 2} y={height - 2} textAnchor="middle" style={labelStyle}>
          {xLabel}
        </text>
      ) : null}
      {yLabel ? (
        <text
          x={10}
          y={margin.top + plotH / 2}
          textAnchor="middle"
          style={labelStyle}
          transform={`rotate(-90, 10, ${margin.top + plotH / 2})`}
        >
          {yLabel}
        </text>
      ) : null}

      {/* Polylines for each series */}
      {data.map((series, si) => {
        if (!series.length) return null;
        // Sort by x for clean line drawing
        const sorted = [...series].sort((a, b) => a.x - b.x);
        const pointsStr = sorted.map((p) => `${scaleX(p.x)},${scaleY(p.y)}`).join(" ");
        return (
          <polyline
            key={`s-${si}`}
            points={pointsStr}
            fill="none"
            stroke={palette[si % palette.length]}
            strokeWidth={1.5}
            strokeLinejoin="round"
            strokeLinecap="round"
          />
        );
      })}
    </svg>
  );
}
