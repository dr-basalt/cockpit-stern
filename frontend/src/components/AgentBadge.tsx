type AgentType = "sp" | "clone" | "anti" | "real";

const COLORS: Record<AgentType, string> = {
  sp: "#1BB68A",
  clone: "#7B6EE8",
  anti: "#E05A2B",
  real: "#C9851A",
};

const LABELS: Record<AgentType, string> = {
  sp: "Vrai SP",
  clone: "Clone IA",
  anti: "Anti SP",
  real: "Réel",
};

export default function AgentBadge({ agent, active = false }: { agent: AgentType; active?: boolean }) {
  const color = COLORS[agent];
  return (
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        padding: "4px 10px",
        borderRadius: 6,
        fontSize: 11,
        fontWeight: 700,
        letterSpacing: "0.06em",
        textTransform: "uppercase",
        color,
        background: active ? `${color}14` : "transparent",
        border: active ? `1px solid ${color}40` : "1px solid transparent",
      }}
    >
      <span
        style={{
          width: 8,
          height: 8,
          borderRadius: "50%",
          background: color,
          opacity: active ? 1 : 0.4,
        }}
      />
      {LABELS[agent]}
    </div>
  );
}
