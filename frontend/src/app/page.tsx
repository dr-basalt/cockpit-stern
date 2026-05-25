export default function Home() {
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", minHeight: "100vh", gap: 24 }}>
      <h1 style={{ fontSize: 48, fontWeight: 800, letterSpacing: "-0.02em" }}>
        COCKPIT <span style={{ color: "#7B6EE8" }}>STERN</span>
      </h1>
      <p style={{ color: "#9090B0", fontSize: 16 }}>
        AI Sparring Partner · Multi-Agent System
      </p>
      <div style={{ display: "flex", gap: 12, marginTop: 32 }}>
        <a
          href="/onboarding"
          style={{
            padding: "12px 28px",
            borderRadius: 10,
            background: "rgba(123,110,232,0.14)",
            border: "1px solid rgba(123,110,232,0.3)",
            color: "#7B6EE8",
            fontWeight: 700,
            fontSize: 14,
            textDecoration: "none",
          }}
        >
          Créer un profil
        </a>
        <a
          href="/cockpit"
          style={{
            padding: "12px 28px",
            borderRadius: 10,
            background: "rgba(27,182,138,0.14)",
            border: "1px solid rgba(27,182,138,0.3)",
            color: "#1BB68A",
            fontWeight: 700,
            fontSize: 14,
            textDecoration: "none",
          }}
        >
          Ouvrir le cockpit
        </a>
      </div>
    </div>
  );
}
