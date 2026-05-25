"use client";

type AgentType = "sp" | "clone" | "anti" | "real";

interface TopBarProps {
  activeAgent: AgentType;
  conformanceScore?: number;
  onAgentClick?: (agent: AgentType) => void;
}

const AGENTS: { key: AgentType; label: string; color: string }[] = [
  { key: "sp", label: "SP", color: "#1BB68A" },
  { key: "clone", label: "CLONE", color: "#7B6EE8" },
  { key: "anti", label: "ANTI", color: "#E05A2B" },
  { key: "real", label: "RÉEL", color: "#C9851A" },
];

export default function TopBar({ activeAgent, conformanceScore, onAgentClick }: TopBarProps) {
  return (
    <div
      style={{
        background: "rgba(7,7,13,0.95)",
        border: "1px solid rgba(255,255,255,0.06)",
        borderRadius: 12,
        padding: "0 18px",
        height: 50,
        display: "flex",
        alignItems: "center",
        gap: 10,
      }}
    >
      {/* Brand */}
      <span
        style={{
          fontSize: 12,
          fontWeight: 800,
          letterSpacing: "0.14em",
          textTransform: "uppercase",
          marginRight: 16,
        }}
      >
        COCKPIT <span style={{ color: "#7B6EE8" }}>STERN</span>
      </span>

      {/* Agent tabs */}
      {AGENTS.map((a) => {
        const isActive = activeAgent === a.key;
        return (
          <button
            key={a.key}
            onClick={() => onAgentClick?.(a.key)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 5,
              padding: "4px 9px",
              borderRadius: 6,
              fontSize: 11,
              fontWeight: 600,
              fontFamily: "'Syne', system-ui",
              cursor: "pointer",
              border: isActive ? `1px solid ${a.color}40` : "1px solid transparent",
              background: isActive ? `${a.color}14` : "transparent",
              color: isActive ? a.color : "#5A5A7A",
              transition: "all 100ms",
            }}
          >
            <span
              style={{
                width: 8,
                height: 8,
                borderRadius: "50%",
                background: a.color,
                opacity: isActive ? 1 : 0.3,
                ...(isActive && a.key === "sp"
                  ? { animation: "pulseSp 2s ease-out infinite" }
                  : {}),
              }}
            />
            {a.label}
          </button>
        );
      })}

      {/* Separator */}
      <div style={{ width: 1, height: 18, background: "rgba(255,255,255,0.06)" }} />

      {/* Conformance */}
      {conformanceScore !== undefined && (
        <span
          style={{
            marginLeft: "auto",
            fontSize: 11,
            fontFamily: "'JetBrains Mono', monospace",
            color: conformanceScore >= 90 ? "#1BB68A" : conformanceScore >= 70 ? "#C9851A" : "#E05A2B",
          }}
        >
          conformance {conformanceScore}%
        </span>
      )}
    </div>
  );
}
