"use client";

import { useState } from "react";

export default function DataDeletionPage() {
  const [profileId, setProfileId] = useState("");
  const [status, setStatus] = useState("");

  const handleDelete = async () => {
    if (!profileId) return;
    setStatus("Suppression en cours...");
    try {
      const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${API}/api/profile/${profileId}`, { method: "DELETE" });
      if (res.ok) {
        setStatus("Données supprimées. Votre profil et toutes les données associées ont été effacés.");
      } else {
        setStatus(`Erreur: ${res.status}. Vérifiez l'ID du profil.`);
      }
    } catch {
      setStatus("Erreur de connexion. Contactez contact@ori3com.cloud.");
    }
  };

  return (
    <div className="max-w-lg mx-auto px-6 py-16">
      <h1 className="text-2xl font-bold mb-4">Data Deletion — Cockpit Stern</h1>
      <p className="text-sm text-[var(--text-secondary)] mb-8">
        Conformément au RGPD et aux exigences Meta Platform, vous pouvez demander la suppression
        complète de vos données (profil, conversations, tokens OAuth, mémoire).
      </p>

      <div className="space-y-4">
        <div>
          <label className="text-xs text-[var(--text-secondary)] mb-1 block">Profile ID</label>
          <input
            value={profileId}
            onChange={(e) => setProfileId(e.target.value)}
            placeholder="Votre UUID de profil"
            className="w-full px-3 py-2.5 rounded-lg border border-white/10 bg-[var(--bg-surface)] text-[var(--text-primary)] text-sm outline-none focus:border-[var(--border-focus)]"
          />
        </div>
        <button
          onClick={handleDelete}
          className="w-full px-5 py-2.5 rounded-lg text-sm font-bold"
          style={{ background: "var(--agent-anti-glow)", border: "1px solid rgba(224,90,43,0.3)", color: "var(--agent-anti)" }}
        >
          Supprimer mes données
        </button>
        {status && <p className="text-sm text-[var(--text-secondary)]">{status}</p>}
      </div>

      <p className="text-xs text-[var(--text-tertiary)] mt-8">
        Vous pouvez aussi envoyer une demande à contact@ori3com.cloud avec votre Profile ID.
        La suppression est irréversible et sera effectuée sous 30 jours.
      </p>
    </div>
  );
}
