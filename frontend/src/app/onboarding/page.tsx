"use client";

import { useState } from "react";
import { createProfile } from "@/lib/api";

const HD_TYPES = ["Generator", "Manifesting Generator", "Projector", "Manifestor", "Reflector"];
const HD_AUTHORITIES = ["Sacral", "Emotional", "Splenic", "Ego", "Self-Projected", "Mental", "Lunar", "None"];
const HD_DEFINITIONS = ["Simple", "Split", "Triple Split", "Quadruple Split"];

const HD_SIGNATURES: Record<string, string> = {
  Generator: "Satisfaction", "Manifesting Generator": "Satisfaction",
  Projector: "Succès", Manifestor: "Paix", Reflector: "Surprise",
};
const HD_NOT_SELF: Record<string, string> = {
  Generator: "Frustration", "Manifesting Generator": "Frustration",
  Projector: "Amertume", Manifestor: "Colère", Reflector: "Déception",
};

export default function OnboardingPage() {
  const [step, setStep] = useState(0);
  const [status, setStatus] = useState("");
  const [form, setForm] = useState({
    name: "", hd_type: "Generator", hd_authority: "Sacral", hd_profile: "4/1",
    hd_definition: "Simple", hd_signature: "Satisfaction", hd_not_self: "Frustration",
    clifton_top5: "", clifton_bottom5: "", mantra: "", invariants: "", energy_level: 5,
  });

  const u = (k: string, v: string | number) => {
    const updated = { ...form, [k]: v };
    if (k === "hd_type") {
      updated.hd_signature = HD_SIGNATURES[v as string] || "Satisfaction";
      updated.hd_not_self = HD_NOT_SELF[v as string] || "Frustration";
    }
    setForm(updated);
  };

  const submit = async () => {
    setStatus("Création du profil...");
    try {
      const data = await createProfile({
        ...form,
        clifton_top5: form.clifton_top5.split(",").map((s) => s.trim()).filter(Boolean),
        clifton_bottom5: form.clifton_bottom5.split(",").map((s) => s.trim()).filter(Boolean),
        invariants: form.invariants.split(",").map((s) => s.trim()).filter(Boolean),
      });
      setStatus("Profil créé ! Redirection...");
      setTimeout(() => { window.location.href = `/cockpit?profile=${data.id}`; }, 800);
    } catch (err) {
      setStatus(`Erreur: ${err}`);
    }
  };

  const inp = "w-full px-3 py-2.5 rounded-lg border border-white/10 bg-[var(--bg-surface)] text-[var(--text-primary)] text-sm outline-none focus:border-[var(--border-focus)] transition-colors font-[var(--font-display)]";
  const lbl = "text-xs text-[var(--text-secondary)] mb-1 block";

  const steps = [
    // Step 0: Human Design
    <div key="hd" className="space-y-5">
      <h2 className="text-xl font-bold">Étape 1 — Human Design</h2>
      <p className="text-sm text-[var(--text-secondary)]">Ton type et ton autorité déterminent comment les agents te parlent.</p>
      <div>
        <label className={lbl}>Nom</label>
        <input className={inp} value={form.name} onChange={(e) => u("name", e.target.value)} placeholder="Ton prénom" required />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className={lbl}>Type HD</label>
          <select className={inp} value={form.hd_type} onChange={(e) => u("hd_type", e.target.value)}>
            {HD_TYPES.map((t) => <option key={t}>{t}</option>)}
          </select>
        </div>
        <div>
          <label className={lbl}>Autorité</label>
          <select className={inp} value={form.hd_authority} onChange={(e) => u("hd_authority", e.target.value)}>
            {HD_AUTHORITIES.map((a) => <option key={a}>{a}</option>)}
          </select>
        </div>
      </div>
      <div className="grid grid-cols-3 gap-3">
        <div>
          <label className={lbl}>Profil</label>
          <input className={inp} value={form.hd_profile} onChange={(e) => u("hd_profile", e.target.value)} placeholder="4/1" />
        </div>
        <div>
          <label className={lbl}>Définition</label>
          <select className={inp} value={form.hd_definition} onChange={(e) => u("hd_definition", e.target.value)}>
            {HD_DEFINITIONS.map((d) => <option key={d}>{d}</option>)}
          </select>
        </div>
        <div>
          <label className={lbl}>Signature</label>
          <input className={inp} value={form.hd_signature} onChange={(e) => u("hd_signature", e.target.value)} />
        </div>
      </div>
    </div>,

    // Step 1: Clifton
    <div key="clifton" className="space-y-5">
      <h2 className="text-xl font-bold">Étape 2 — Clifton StrengthsFinder</h2>
      <p className="text-sm text-[var(--text-secondary)]">Tes 5 forces top = le Clone produit dans ce style. Tes 5 bottom = l'Anti challenge là-dessus.</p>
      <div>
        <label className={lbl}>Top 5 (séparés par virgule)</label>
        <input className={inp} value={form.clifton_top5} onChange={(e) => u("clifton_top5", e.target.value)}
          placeholder="Idéation, Futuriste, Stratégique, Individualisation, Contexte" />
      </div>
      <div>
        <label className={lbl}>Bottom 5 (séparés par virgule)</label>
        <input className={inp} value={form.clifton_bottom5} onChange={(e) => u("clifton_bottom5", e.target.value)}
          placeholder="Discipline, Harmonie, Prudent, Équitable, Adaptabilité" />
      </div>
    </div>,

    // Step 2: Mantra + Invariants
    <div key="mantra" className="space-y-5">
      <h2 className="text-xl font-bold">Étape 3 — Mantra & Invariants</h2>
      <p className="text-sm text-[var(--text-secondary)]">Tes règles non-négociables. Les agents les respectent toujours.</p>
      <div>
        <label className={lbl}>Mantra (une phrase)</label>
        <input className={inp} value={form.mantra} onChange={(e) => u("mantra", e.target.value)}
          placeholder="Revenue before infra" />
      </div>
      <div>
        <label className={lbl}>Invariants (séparés par virgule)</label>
        <input className={inp} value={form.invariants} onChange={(e) => u("invariants", e.target.value)}
          placeholder="Revenue before infra, Ship fast, No vanity metrics" />
      </div>
    </div>,

    // Step 3: Energy + Confirmation
    <div key="confirm" className="space-y-5">
      <h2 className="text-xl font-bold">Étape 4 — Énergie & Confirmation</h2>
      <div>
        <label className={lbl}>Niveau d'énergie actuel (1-10)</label>
        <div className="flex items-center gap-3">
          <input type="range" min={1} max={10} value={form.energy_level}
            onChange={(e) => u("energy_level", Number(e.target.value))} className="flex-1" />
          <span className="text-lg font-bold font-mono" style={{ color: form.energy_level >= 7 ? "var(--agent-sp)" : form.energy_level >= 4 ? "var(--agent-real)" : "var(--agent-anti)" }}>
            {form.energy_level}
          </span>
        </div>
      </div>
      <div className="rounded-xl border border-white/6 bg-[var(--bg-surface)] p-4 space-y-2 text-sm">
        <div className="flex justify-between"><span className="text-[var(--text-tertiary)]">Nom</span><span>{form.name || "—"}</span></div>
        <div className="flex justify-between"><span className="text-[var(--text-tertiary)]">Type HD</span><span>{form.hd_type}</span></div>
        <div className="flex justify-between"><span className="text-[var(--text-tertiary)]">Autorité</span><span>{form.hd_authority}</span></div>
        <div className="flex justify-between"><span className="text-[var(--text-tertiary)]">Profil</span><span>{form.hd_profile}</span></div>
        <div className="flex justify-between"><span className="text-[var(--text-tertiary)]">Top 5</span><span className="text-right max-w-[200px] truncate">{form.clifton_top5 || "—"}</span></div>
        <div className="flex justify-between"><span className="text-[var(--text-tertiary)]">Mantra</span><span className="text-right max-w-[200px] truncate">{form.mantra || "—"}</span></div>
      </div>
    </div>,
  ];

  return (
    <div className="max-w-lg mx-auto px-6 py-16">
      <div className="mb-8">
        <span className="text-xs font-bold tracking-widest uppercase text-[var(--text-tertiary)]">
          Cockpit Stern · Onboarding
        </span>
        <div className="flex gap-1.5 mt-3">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="h-1 flex-1 rounded-full transition-all duration-300"
              style={{ background: i <= step ? "var(--agent-clone)" : "var(--bg-raised)" }} />
          ))}
        </div>
      </div>

      {steps[step]}

      <div className="flex gap-3 mt-8">
        {step > 0 && (
          <button onClick={() => setStep(step - 1)}
            className="px-5 py-2.5 rounded-lg border border-white/10 text-sm font-semibold text-[var(--text-secondary)] hover:bg-[var(--bg-raised)] transition-colors">
            Retour
          </button>
        )}
        {step < 3 ? (
          <button onClick={() => setStep(step + 1)}
            className="flex-1 px-5 py-2.5 rounded-lg text-sm font-bold transition-colors"
            style={{ background: "var(--agent-clone-glow)", border: "1px solid rgba(123,110,232,0.3)", color: "var(--agent-clone)" }}>
            Suivant
          </button>
        ) : (
          <button onClick={submit}
            className="flex-1 px-5 py-2.5 rounded-lg text-sm font-bold transition-colors"
            style={{ background: "var(--agent-sp-glow)", border: "1px solid rgba(27,182,138,0.3)", color: "var(--agent-sp)" }}>
            Créer mon profil
          </button>
        )}
      </div>

      {status && <p className="mt-4 text-sm text-[var(--text-secondary)]">{status}</p>}
    </div>
  );
}
