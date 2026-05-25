"use client";

type Message = {
  role: "user" | "assistant";
  content: string;
  agent?: string;
};

const AGENT_COLORS: Record<string, string> = {
  sp: "#1BB68A",
  clone: "#7B6EE8",
  anti: "#E05A2B",
  real: "#C9851A",
};

export default function ChatStream({ messages }: { messages: Message[] }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      {messages.map((msg, i) => {
        const color = AGENT_COLORS[msg.agent || "sp"];
        return (
          <div
            key={i}
            style={{
              maxWidth: "84%",
              alignSelf: msg.role === "user" ? "flex-end" : "flex-start",
              padding: "11px 14px",
              borderRadius: 12,
              fontSize: 13,
              lineHeight: 1.5,
              ...(msg.role === "user"
                ? { background: "#1D1D30", border: "1px solid rgba(255,255,255,0.1)" }
                : { background: `${color}12`, border: `1px solid ${color}33` }),
            }}
          >
            {msg.role === "assistant" && msg.agent && (
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
                {msg.agent.toUpperCase()}
              </div>
            )}
            {msg.content}
          </div>
        );
      })}
    </div>
  );
}
