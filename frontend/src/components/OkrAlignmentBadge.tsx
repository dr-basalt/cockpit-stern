type AlignmentLevel = "aligned" | "partial" | "misaligned";

interface OkrAlignmentBadgeProps {
  label: string;
  level: AlignmentLevel;
  score?: number; // 0-100
  visible?: boolean;
}

const LEVEL_CONFIG: Record<AlignmentLevel, { color: string; bg: string; icon: string }> = {
  aligned: { color: "#1BB68A", bg: "rgba(27,182,138,0.12)", icon: "●" },
  partial: { color: "#C9851A", bg: "rgba(201,133,26,0.12)", icon: "◐" },
  misaligned: { color: "#E05A2B", bg: "rgba(224,90,43,0.12)", icon: "○" },
};

export default function OkrAlignmentBadge({ label, level, score, visible = true }: OkrAlignmentBadgeProps) {
  if (!visible) return null;

  const { color, bg, icon } = LEVEL_CONFIG[level];

  return (
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        padding: "4px 10px",
        borderRadius: 6,
        fontSize: 11,
        fontWeight: 600,
        color,
        background: bg,
      }}
    >
      <span>{icon}</span>
      <span>{label}</span>
      {score !== undefined && (
        <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10, opacity: 0.8 }}>
          {score}%
        </span>
      )}
    </div>
  );
}
