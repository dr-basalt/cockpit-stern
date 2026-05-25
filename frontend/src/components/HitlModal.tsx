"use client";

export default function HitlModal({
  title,
  description,
  context,
  onConfirm,
  onReject,
}: {
  title: string;
  description: string;
  context: Record<string, string>;
  onConfirm: () => void;
  onReject: () => void;
}) {
  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(7,7,13,0.85)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 9999,
      }}
    >
      <div
        style={{
          background: "#161625",
          border: "1px solid rgba(201,133,26,0.4)",
          borderRadius: 18,
          padding: 28,
          maxWidth: 400,
          textAlign: "center",
        }}
      >
        <div style={{ fontSize: 28, marginBottom: 14 }}>&#9888;</div>
        <h2 style={{ fontSize: 20, fontWeight: 800, marginBottom: 7 }}>{title}</h2>
        <p style={{ fontSize: 13, color: "#9090B0", lineHeight: 1.5, marginBottom: 20 }}>
          {description}
        </p>

        <div
          style={{
            background: "#0F0F1A",
            border: "1px solid rgba(255,255,255,0.06)",
            borderRadius: 9,
            padding: 13,
            textAlign: "left",
            marginBottom: 20,
          }}
        >
          {Object.entries(context).map(([k, v]) => (
            <div
              key={k}
              style={{
                display: "flex",
                justifyContent: "space-between",
                fontSize: 11,
                padding: "4px 0",
                borderBottom: "1px solid rgba(255,255,255,0.06)",
              }}
            >
              <span style={{ color: "#5A5A7A" }}>{k}</span>
              <span style={{ fontWeight: 500 }}>{v}</span>
            </div>
          ))}
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 9 }}>
          <button
            onClick={onConfirm}
            style={{
              padding: 13,
              borderRadius: 9,
              fontSize: 14,
              fontWeight: 700,
              background: "rgba(27,182,138,0.14)",
              border: "1px solid rgba(27,182,138,0.35)",
              color: "#1BB68A",
              cursor: "pointer",
              fontFamily: "'Syne', system-ui",
            }}
          >
            Confirmer
          </button>
          <button
            onClick={onReject}
            style={{
              padding: 13,
              borderRadius: 9,
              fontSize: 14,
              fontWeight: 700,
              background: "rgba(224,90,43,0.1)",
              border: "1px solid rgba(224,90,43,0.25)",
              color: "#E05A2B",
              cursor: "pointer",
              fontFamily: "'Syne', system-ui",
            }}
          >
            Annuler
          </button>
        </div>
      </div>
    </div>
  );
}
