"use client";

type AgentType = "sp" | "clone" | "anti" | "real";

interface ChatMessageProps {
  role: "user" | "assistant";
  content: string;
  agent?: AgentType;
  timestamp?: string;
  options?: string[];
  onOptionClick?: (option: string) => void;
}

const COLORS: Record<AgentType, string> = {
  sp: "#1BB68A",
  clone: "#7B6EE8",
  anti: "#E05A2B",
  real: "#C9851A",
};

const GLOWS: Record<AgentType, string> = {
  sp: "rgba(27,182,138,0.12)",
  clone: "rgba(123,110,232,0.12)",
  anti: "rgba(224,90,43,0.12)",
  real: "rgba(201,133,26,0.12)",
};

const LABELS: Record<AgentType, string> = {
  sp: "VRAI SP",
  clone: "CLONE",
  anti: "ANTI",
  real: "RÉEL",
};

export default function ChatMessage({ role, content, agent = "sp", timestamp, options, onOptionClick }: ChatMessageProps) {
  const color = COLORS[agent];
  const glow = GLOWS[agent];

  return (
    <div
      style={{
        maxWidth: "84%",
        alignSelf: role === "user" ? "flex-end" : "flex-start",
        padding: "11px 14px",
        borderRadius: 12,
        fontSize: 13,
        lineHeight: 1.6,
        animation: "msgIn 180ms cubic-bezier(0.34,1.56,0.64,1) both",
        ...(role === "user"
          ? { background: "#1D1D30", border: "1px solid rgba(255,255,255,0.10)" }
          : { background: glow, border: `1px solid ${color}33` }),
      }}
    >
      {role === "assistant" && (
        <div
          style={{
            fontSize: 9,
            fontWeight: 700,
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            color,
            marginBottom: 4,
          }}
        >
          {LABELS[agent]}
          {timestamp && (
            <span style={{ marginLeft: 8, color: "#5A5A7A", fontWeight: 400, letterSpacing: 0 }}>
              {timestamp}
            </span>
          )}
        </div>
      )}

      <div style={{ whiteSpace: "pre-wrap" }}>{content}</div>

      {options && options.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 5, marginTop: 9 }}>
          {options.map((opt, i) => (
            <button
              key={i}
              onClick={() => onOptionClick?.(opt)}
              style={{
                padding: "7px 11px",
                borderRadius: 7,
                fontSize: 12,
                background: "rgba(255,255,255,0.04)",
                border: "1px solid rgba(255,255,255,0.06)",
                color: "#9090B0",
                cursor: "pointer",
                textAlign: "left",
                fontFamily: "'Syne', system-ui",
                transition: "all 100ms",
              }}
            >
              {opt}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
