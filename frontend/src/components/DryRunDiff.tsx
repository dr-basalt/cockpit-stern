"use client";

interface DiffLine {
  type: "added" | "removed" | "context";
  content: string;
}

interface DryRunDiffProps {
  title: string;
  agent: string;
  lines: DiffLine[];
  onApprove?: () => void;
  onReject?: () => void;
  onEdit?: () => void;
}

export default function DryRunDiff({ title, agent, lines, onApprove, onReject, onEdit }: DryRunDiffProps) {
  return (
    <div
      style={{
        background: "#0F0F1A",
        border: "1px solid rgba(201,133,26,0.3)",
        borderRadius: 16,
        overflow: "hidden",
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: "13px 18px",
          background: "rgba(201,133,26,0.07)",
          borderBottom: "1px solid rgba(201,133,26,0.2)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <span style={{ fontSize: 13, fontWeight: 600 }}>{title}</span>
        <span
          style={{
            fontSize: 9,
            fontWeight: 700,
            letterSpacing: "0.1em",
            textTransform: "uppercase",
            color: "#C9851A",
            background: "rgba(201,133,26,0.15)",
            padding: "2px 7px",
            borderRadius: 4,
          }}
        >
          DRY RUN · {agent.toUpperCase()}
        </span>
      </div>

      {/* Diff body */}
      <div style={{ padding: 18, fontFamily: "'JetBrains Mono', monospace", fontSize: 12 }}>
        {lines.map((line, i) => (
          <div
            key={i}
            style={{
              padding: "4px 12px",
              borderRadius: 4,
              margin: "2px 0",
              lineHeight: 1.6,
              ...(line.type === "added"
                ? { background: "rgba(27,182,138,0.07)", color: "#80E0B8" }
                : line.type === "removed"
                  ? { background: "rgba(224,90,43,0.07)", color: "#F09080" }
                  : { color: "#5A5A7A" }),
            }}
          >
            {line.type === "added" && <span style={{ opacity: 0.5 }}>{"+ "}</span>}
            {line.type === "removed" && <span style={{ opacity: 0.5 }}>{"− "}</span>}
            {line.type === "context" && <span style={{ opacity: 0.5 }}>{"  "}</span>}
            {line.content}
          </div>
        ))}
      </div>

      {/* Actions */}
      <div
        style={{
          padding: "14px 18px",
          borderTop: "1px solid rgba(255,255,255,0.06)",
          display: "flex",
          gap: 8,
          alignItems: "center",
        }}
      >
        <button
          onClick={onApprove}
          style={{
            padding: "8px 16px",
            borderRadius: 7,
            fontSize: 12,
            fontWeight: 600,
            fontFamily: "'Syne', system-ui",
            background: "rgba(27,182,138,0.14)",
            border: "1px solid rgba(27,182,138,0.3)",
            color: "#1BB68A",
            cursor: "pointer",
          }}
        >
          Approuver
        </button>
        <button
          onClick={onReject}
          style={{
            padding: "8px 16px",
            borderRadius: 7,
            fontSize: 12,
            fontWeight: 600,
            fontFamily: "'Syne', system-ui",
            background: "rgba(224,90,43,0.1)",
            border: "1px solid rgba(224,90,43,0.2)",
            color: "#E05A2B",
            cursor: "pointer",
          }}
        >
          Rejeter
        </button>
        <button
          onClick={onEdit}
          style={{
            padding: "8px 16px",
            borderRadius: 7,
            fontSize: 12,
            fontWeight: 600,
            fontFamily: "'Syne', system-ui",
            background: "transparent",
            border: "1px solid rgba(255,255,255,0.06)",
            color: "#9090B0",
            cursor: "pointer",
          }}
        >
          Modifier
        </button>
      </div>
    </div>
  );
}
