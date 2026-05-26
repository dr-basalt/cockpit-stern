"use client";

import { useEffect, useRef, useCallback } from "react";
import { useCockpitStore, type AgentType } from "@/lib/store";
import { sendChat, getProfile, getWsUrl, hitlConfirm } from "@/lib/api";

const AGENTS: { key: AgentType; label: string; color: string }[] = [
  { key: "sp", label: "SP", color: "var(--agent-sp)" },
  { key: "clone", label: "CLONE", color: "var(--agent-clone)" },
  { key: "anti", label: "ANTI", color: "var(--agent-anti)" },
  { key: "real", label: "RÉEL", color: "var(--agent-real)" },
];

export default function CockpitPage() {
  const s = useCockpitStore();
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const p = params.get("profile");
    if (p && !s.profileId) {
      s.setProfileId(p);
      getProfile(p).then((data) => s.setProfile(data)).catch(() => {});
    }
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [s.messages]);

  const send = useCallback(async (text: string) => {
    if (!text.trim() || !s.profileId || s.loading) return;
    s.addMessage({ role: "user", content: text });
    s.setLoading(true);

    try {
      const data = await sendChat(s.sessionId, s.profileId, text, s.energy);
      s.setActiveAgent(data.active_agent as AgentType);
      s.addMessage({ role: "assistant", content: data.message, agent: data.active_agent });
    } catch {
      s.addMessage({ role: "assistant", content: "Erreur de connexion au backend.", agent: "sp" });
    }
    s.setLoading(false);
    inputRef.current?.focus();
  }, [s]);

  const pro = s.profile as Record<string, unknown> | null;

  return (
    <div className="flex h-screen">
      {/* Sidebar */}
      <aside className="w-56 border-r border-white/6 bg-[var(--bg-surface)] flex flex-col p-4 gap-4 overflow-y-auto shrink-0">
        <div className="text-[10px] font-bold tracking-widest uppercase text-[var(--text-tertiary)]">Profil</div>
        {pro ? (
          <div className="space-y-2 text-xs">
            <div className="text-base font-bold">{pro.name as string}</div>
            <div className="text-[var(--text-secondary)]">{pro.hd_type as string} · {pro.hd_authority as string}</div>
            <div className="text-[var(--text-secondary)]">Profil {pro.hd_profile as string}</div>
            <div className="mt-3 text-[10px] font-bold tracking-widest uppercase text-[var(--text-tertiary)]">Forces</div>
            <div className="flex flex-wrap gap-1">
              {(pro.clifton_top5 as string[] || []).map((s) => (
                <span key={s} className="px-1.5 py-0.5 rounded text-[10px] font-semibold"
                  style={{ background: "var(--agent-clone-glow)", color: "var(--agent-clone)" }}>{s}</span>
              ))}
            </div>
            <div className="mt-2 text-[10px] font-bold tracking-widest uppercase text-[var(--text-tertiary)]">Blind spots</div>
            <div className="flex flex-wrap gap-1">
              {(pro.clifton_bottom5 as string[] || []).map((s) => (
                <span key={s} className="px-1.5 py-0.5 rounded text-[10px] font-semibold"
                  style={{ background: "var(--agent-anti-glow)", color: "var(--agent-anti)" }}>{s}</span>
              ))}
            </div>
            {pro.mantra && (
              <div className="mt-3 text-[11px] italic text-[var(--text-secondary)]">"{pro.mantra as string}"</div>
            )}
          </div>
        ) : (
          <div className="text-xs text-[var(--text-tertiary)]">Aucun profil chargé</div>
        )}

        <div className="mt-auto space-y-3">
          <div className="text-[10px] font-bold tracking-widest uppercase text-[var(--text-tertiary)]">Énergie</div>
          <div className="flex items-center gap-2">
            <input type="range" min={1} max={10} value={s.energy} onChange={(e) => s.setEnergy(Number(e.target.value))} className="flex-1" />
            <span className="text-sm font-bold font-mono min-w-[20px] text-right"
              style={{ color: s.energy >= 7 ? "var(--agent-sp)" : s.energy >= 4 ? "var(--agent-real)" : "var(--agent-anti)" }}>
              {s.energy}
            </span>
          </div>
          <div className="text-[10px] text-[var(--text-tertiary)]">
            {s.energy >= 7 ? "Mode brake — Clone produit, Anti freine" : s.energy >= 4 ? "Mode balance" : "Mode accelerate — Anti pousse, Clone en veille"}
          </div>
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* TopBar */}
        <div className="flex items-center gap-2 px-4 h-12 border-b border-white/6 bg-[var(--bg-void)]/95 shrink-0">
          <span className="text-xs font-extrabold tracking-[0.14em] uppercase mr-4">
            COCKPIT <span style={{ color: "var(--agent-clone)" }}>STERN</span>
          </span>
          {AGENTS.map((a) => {
            const active = s.activeAgent === a.key;
            return (
              <div key={a.key} className="flex items-center gap-1.5 px-2 py-1 rounded-md text-[11px] font-semibold transition-all"
                style={{
                  color: active ? a.color : "var(--text-tertiary)",
                  background: active ? `color-mix(in srgb, ${a.color} 10%, transparent)` : "transparent",
                  border: active ? `1px solid color-mix(in srgb, ${a.color} 25%, transparent)` : "1px solid transparent",
                }}>
                <span className="w-2 h-2 rounded-full" style={{ background: a.color, opacity: active ? 1 : 0.3 }} />
                {a.label}
              </div>
            );
          })}
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {s.messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full gap-3 text-[var(--text-tertiary)]">
              <div className="text-4xl">🎯</div>
              <div className="text-sm">Parle à tes agents. Ils s'adaptent à toi.</div>
              <div className="text-xs opacity-60">Demande un pitch, un plan, un challenge, ou dis simplement ce que tu ressens.</div>
            </div>
          )}
          {s.messages.map((msg, i) => {
            const agentColor = msg.agent ? AGENTS.find((a) => a.key === msg.agent)?.color : undefined;
            return (
              <div key={i} className="max-w-[80%] rounded-xl px-3.5 py-2.5 text-[13px] leading-relaxed"
                style={{
                  alignSelf: msg.role === "user" ? "flex-end" : "flex-start",
                  marginLeft: msg.role === "user" ? "auto" : undefined,
                  background: msg.role === "user" ? "var(--bg-overlay)" : agentColor ? `color-mix(in srgb, ${agentColor} 8%, transparent)` : "var(--bg-surface)",
                  border: msg.role === "user" ? "1px solid var(--border-default)" : agentColor ? `1px solid color-mix(in srgb, ${agentColor} 20%, transparent)` : "1px solid var(--border-subtle)",
                  animation: "msgIn 180ms cubic-bezier(0.34,1.56,0.64,1) both",
                }}>
                {msg.role === "assistant" && msg.agent && (
                  <div className="text-[9px] font-bold tracking-widest uppercase mb-1" style={{ color: agentColor }}>
                    {AGENTS.find((a) => a.key === msg.agent)?.label || msg.agent}
                  </div>
                )}
                <div className="whitespace-pre-wrap">{msg.content}</div>
              </div>
            );
          })}
          {s.loading && (
            <div className="flex gap-1 py-2">
              {[0, 1, 2].map((i) => (
                <span key={i} className="w-1.5 h-1.5 rounded-full bg-[var(--text-tertiary)]"
                  style={{ animation: `pulse-dot 1.4s infinite ease-in-out ${i * 0.16}s` }} />
              ))}
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div className="p-3 border-t border-white/6">
          <textarea ref={inputRef} rows={2} placeholder={s.profileId ? "Parle à tes agents..." : "Charge un profil d'abord"}
            disabled={!s.profileId || s.loading}
            className="w-full px-3.5 py-2.5 rounded-xl border border-white/10 bg-[var(--bg-overlay)] text-[var(--text-primary)] text-[13px] outline-none resize-none transition-colors focus:border-[var(--border-focus)] disabled:opacity-40 font-[var(--font-display)]"
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                const val = (e.target as HTMLTextAreaElement).value.trim();
                if (val) {
                  send(val);
                  (e.target as HTMLTextAreaElement).value = "";
                }
              }
            }}
          />
        </div>
      </div>
    </div>
  );
}
