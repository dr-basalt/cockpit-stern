interface ConformanceRow {
  label: string;
  score: number; // 0-100
}

interface ConformanceIndicatorProps {
  rows: ConformanceRow[];
  visible?: boolean;
}

function barColor(score: number): string {
  if (score >= 90) return "#1BB68A";
  if (score >= 70) return "#C9851A";
  return "#E05A2B";
}

export default function ConformanceIndicator({ rows, visible = true }: ConformanceIndicatorProps) {
  if (!visible) return null;

  return (
    <div
      style={{
        background: "#0F0F1A",
        border: "1px solid rgba(255,255,255,0.06)",
        borderRadius: 16,
        padding: 22,
      }}
    >
      {rows.map((row, i) => (
        <div key={i} style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: i < rows.length - 1 ? 12 : 0 }}>
          <span style={{ width: 76, fontSize: 12, color: "#9090B0" }}>{row.label}</span>
          <div
            style={{
              flex: 1,
              height: 5,
              background: "#1D1D30",
              borderRadius: 3,
              overflow: "hidden",
            }}
          >
            <div
              style={{
                height: "100%",
                width: `${row.score}%`,
                background: barColor(row.score),
                borderRadius: 3,
                transition: "width 800ms cubic-bezier(0.4,0,0.2,1)",
              }}
            />
          </div>
          <span
            style={{
              width: 34,
              textAlign: "right",
              fontSize: 12,
              fontFamily: "'JetBrains Mono', monospace",
              fontWeight: 500,
              color: barColor(row.score),
            }}
          >
            {row.score}
          </span>
        </div>
      ))}
    </div>
  );
}
