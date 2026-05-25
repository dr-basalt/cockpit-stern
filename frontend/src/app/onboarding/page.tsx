"use client";

import { useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const HD_TYPES = ["Generator", "Manifesting Generator", "Projector", "Manifestor", "Reflector"];
const HD_AUTHORITIES = ["Sacral", "Emotional", "Splenic", "Ego", "Self-Projected", "Mental", "Lunar", "None"];
const HD_DEFINITIONS = ["Simple", "Split", "Triple Split", "Quadruple Split"];

export default function OnboardingPage() {
  const [form, setForm] = useState({
    name: "",
    hd_type: "Generator",
    hd_authority: "Sacral",
    hd_profile: "4/1",
    hd_definition: "Simple",
    hd_signature: "Satisfaction",
    hd_not_self: "Frustration",
    clifton_top5: "",
    clifton_bottom5: "",
    mantra: "",
    invariants: "",
  });
  const [status, setStatus] = useState<string>("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus("Création...");
    try {
      const res = await fetch(`${API}/api/profile`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...form,
          clifton_top5: form.clifton_top5.split(",").map((s) => s.trim()),
          clifton_bottom5: form.clifton_bottom5.split(",").map((s) => s.trim()),
          invariants: form.invariants.split(",").map((s) => s.trim()),
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setStatus(`Profil créé: ${data.id}`);
      } else {
        setStatus(`Erreur: ${res.status}`);
      }
    } catch (err) {
      setStatus(`Erreur réseau: ${err}`);
    }
  };

  const inputStyle = {
    width: "100%",
    padding: "10px 14px",
    borderRadius: 8,
    border: "1px solid rgba(255,255,255,0.1)",
    background: "#0F0F1A",
    color: "#F2F2FA",
    fontSize: 14,
    fontFamily: "'Syne', system-ui",
    outline: "none",
  };

  const labelStyle = { fontSize: 12, color: "#9090B0", marginBottom: 4, display: "block" };

  return (
    <div style={{ maxWidth: 600, margin: "0 auto", padding: "64px 24px" }}>
      <h1 style={{ fontSize: 28, fontWeight: 800, marginBottom: 8 }}>Onboarding</h1>
      <p style={{ color: "#9090B0", marginBottom: 40 }}>Configure ton profil Human Design + Clifton</p>

      <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 20 }}>
        <div>
          <label style={labelStyle}>Nom</label>
          <input style={inputStyle} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
          <div>
            <label style={labelStyle}>Type HD</label>
            <select style={inputStyle} value={form.hd_type} onChange={(e) => setForm({ ...form, hd_type: e.target.value })}>
              {HD_TYPES.map((t) => <option key={t}>{t}</option>)}
            </select>
          </div>
          <div>
            <label style={labelStyle}>Autorité</label>
            <select style={inputStyle} value={form.hd_authority} onChange={(e) => setForm({ ...form, hd_authority: e.target.value })}>
              {HD_AUTHORITIES.map((a) => <option key={a}>{a}</option>)}
            </select>
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 14 }}>
          <div>
            <label style={labelStyle}>Profil HD</label>
            <input style={inputStyle} value={form.hd_profile} onChange={(e) => setForm({ ...form, hd_profile: e.target.value })} />
          </div>
          <div>
            <label style={labelStyle}>Définition</label>
            <select style={inputStyle} value={form.hd_definition} onChange={(e) => setForm({ ...form, hd_definition: e.target.value })}>
              {HD_DEFINITIONS.map((d) => <option key={d}>{d}</option>)}
            </select>
          </div>
          <div>
            <label style={labelStyle}>Signature</label>
            <input style={inputStyle} value={form.hd_signature} onChange={(e) => setForm({ ...form, hd_signature: e.target.value })} />
          </div>
        </div>

        <div>
          <label style={labelStyle}>Signal Not-Self</label>
          <input style={inputStyle} value={form.hd_not_self} onChange={(e) => setForm({ ...form, hd_not_self: e.target.value })} />
        </div>

        <div>
          <label style={labelStyle}>Clifton Top 5 (séparés par virgule)</label>
          <input style={inputStyle} value={form.clifton_top5} onChange={(e) => setForm({ ...form, clifton_top5: e.target.value })} placeholder="Idéation, Futuriste, Stratégique, Individualisation, Contexte" />
        </div>

        <div>
          <label style={labelStyle}>Clifton Bottom 5 (séparés par virgule)</label>
          <input style={inputStyle} value={form.clifton_bottom5} onChange={(e) => setForm({ ...form, clifton_bottom5: e.target.value })} placeholder="Discipline, Harmonie, Prudent, Équitable" />
        </div>

        <div>
          <label style={labelStyle}>Mantra</label>
          <input style={inputStyle} value={form.mantra} onChange={(e) => setForm({ ...form, mantra: e.target.value })} />
        </div>

        <div>
          <label style={labelStyle}>Invariants (séparés par virgule)</label>
          <input style={inputStyle} value={form.invariants} onChange={(e) => setForm({ ...form, invariants: e.target.value })} placeholder="Revenue before infra, Ship fast" />
        </div>

        <button
          type="submit"
          style={{
            padding: "14px 28px",
            borderRadius: 10,
            background: "rgba(27,182,138,0.14)",
            border: "1px solid rgba(27,182,138,0.3)",
            color: "#1BB68A",
            fontWeight: 700,
            fontSize: 15,
            cursor: "pointer",
            fontFamily: "'Syne', system-ui",
          }}
        >
          Créer le profil
        </button>

        {status && <p style={{ color: "#9090B0", fontSize: 13 }}>{status}</p>}
      </form>
    </div>
  );
}
