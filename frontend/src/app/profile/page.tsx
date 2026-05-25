"use client";

import { useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function ProfilePage() {
  const [profileId, setProfileId] = useState("");
  const [profile, setProfile] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState("");

  const load = async () => {
    setError("");
    try {
      const res = await fetch(`${API}/api/profile/${profileId}`);
      if (res.ok) {
        setProfile(await res.json());
      } else {
        setError(`Erreur ${res.status}`);
      }
    } catch (err) {
      setError(`Erreur réseau: ${err}`);
    }
  };

  return (
    <div style={{ maxWidth: 700, margin: "0 auto", padding: "64px 24px" }}>
      <h1 style={{ fontSize: 28, fontWeight: 800, marginBottom: 32 }}>Profil</h1>

      <div style={{ display: "flex", gap: 12, marginBottom: 32 }}>
        <input
          placeholder="Profile ID (UUID)"
          value={profileId}
          onChange={(e) => setProfileId(e.target.value)}
          style={{
            flex: 1,
            padding: "10px 14px",
            borderRadius: 8,
            border: "1px solid rgba(255,255,255,0.1)",
            background: "#0F0F1A",
            color: "#F2F2FA",
            fontSize: 13,
            fontFamily: "'JetBrains Mono', monospace",
            outline: "none",
          }}
        />
        <button
          onClick={load}
          style={{
            padding: "10px 20px",
            borderRadius: 8,
            background: "rgba(123,110,232,0.14)",
            border: "1px solid rgba(123,110,232,0.3)",
            color: "#7B6EE8",
            fontWeight: 700,
            cursor: "pointer",
            fontFamily: "'Syne', system-ui",
          }}
        >
          Charger
        </button>
      </div>

      {error && <p style={{ color: "#E05A2B" }}>{error}</p>}

      {profile && (
        <div
          style={{
            background: "#0F0F1A",
            border: "1px solid rgba(255,255,255,0.06)",
            borderRadius: 16,
            padding: 22,
          }}
        >
          <pre style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 12, color: "#9090B0", whiteSpace: "pre-wrap" }}>
            {JSON.stringify(profile, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
