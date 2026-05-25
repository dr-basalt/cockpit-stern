export default function EnergySlider({
  value,
  onChange,
  label = "Énergie",
}: {
  value: number;
  onChange: (v: number) => void;
  label?: string;
}) {
  const color = value >= 7 ? "#1BB68A" : value >= 4 ? "#C9851A" : "#E05A2B";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
      <span style={{ fontSize: 12, color: "#9090B0", minWidth: 60 }}>{label}</span>
      <input
        type="range"
        min={1}
        max={10}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        style={{ flex: 1, accentColor: color }}
      />
      <span
        style={{
          fontSize: 14,
          fontWeight: 700,
          fontFamily: "'JetBrains Mono', monospace",
          color,
          minWidth: 24,
          textAlign: "right",
        }}
      >
        {value}
      </span>
    </div>
  );
}
