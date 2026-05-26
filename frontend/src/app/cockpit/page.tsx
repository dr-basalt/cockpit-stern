"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import TopBar from "@/components/TopBar";
import ChatMessage from "@/components/ChatMessage";
import ChatInput from "@/components/ChatInput";
import EnergySlider from "@/components/EnergySlider";
import HitlModal from "@/components/HitlModal";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const WS_URL = API.replace(/^http/, "ws");

type AgentType = "sp" | "clone" | "anti" | "real";

type Message = {
  role: "user" | "assistant";
  content: string;
  agent?: string;
};

type StreamMode = "rest" | "ws";

export default function CockpitPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [profileId, setProfileId] = useState("");
  const [sessionId] = useState(() => crypto.randomUUID());
  const [energy, setEnergy] = useState(5);
  const [loading, setLoading] = useState(false);
  const [activeAgent, setActiveAgent] = useState<AgentType>("sp");
  const [streamMode, setStreamMode] = useState<StreamMode>("ws");
  const [hitl, setHitl] = useState<{ token: string; message: string } | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const p = params.get("profile");
    if (p && !profileId) setProfileId(p);
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // WebSocket connection
  const getWs = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      return wsRef.current;
    }
    const ws = new WebSocket(`${WS_URL}/api/chat/stream`);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      switch (data.type) {
        case "agent":
          setActiveAgent(data.agent as AgentType);
          break;

        case "chunk":
          setMessages((prev) => {
            const last = prev[prev.length - 1];
            // If last message is from same agent and assistant, append
            if (last && last.role === "assistant" && last.agent === data.agent) {
              return [...prev.slice(0, -1), { ...last, content: data.content }];
            }
            return [...prev, { role: "assistant", content: data.content, agent: data.agent }];
          });
          break;

        case "meta":
          if (data.requires_hitl && data.hitl_token) {
            setHitl({ token: data.hitl_token, message: "Décision irréversible détectée" });
          }
          break;

        case "done":
          setLoading(false);
          break;

        case "error":
          setMessages((prev) => [...prev, { role: "assistant", content: `Erreur: ${data.detail}`, agent: "sp" }]);
          setLoading(false);
          break;
      }
    };

    ws.onclose = () => {
      wsRef.current = null;
    };

    return ws;
  }, []);

  // REST fallback
  const sendRest = async (message: string) => {
    try {
      const res = await fetch(`${API}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          profile_id: profileId,
          message,
          energy_level: energy,
        }),
      });
      const data = await res.json();
      setActiveAgent(data.active_agent as AgentType);
      setMessages((prev) => [...prev, { role: "assistant", content: data.message, agent: data.active_agent }]);

      if (data.requires_hitl && data.hitl_token) {
        setHitl({ token: data.hitl_token, message: "Décision irréversible détectée" });
      }
    } catch {
      setMessages((prev) => [...prev, { role: "assistant", content: "Erreur de connexion.", agent: "sp" }]);
    }
    setLoading(false);
  };

  // WebSocket send
  const sendWs = (message: string) => {
    const ws = getWs();
    const payload = JSON.stringify({
      session_id: sessionId,
      profile_id: profileId,
      message,
      energy_level: energy,
    });

    if (ws.readyState === WebSocket.OPEN) {
      ws.send(payload);
    } else {
      ws.onopen = () => ws.send(payload);
    }
  };

  const send = (message: string) => {
    if (!message.trim() || !profileId) return;
    setMessages((prev) => [...prev, { role: "user", content: message }]);
    setLoading(true);

    if (streamMode === "ws") {
      sendWs(message);
    } else {
      sendRest(message);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh" }}>
      {/* TopBar */}
      <div style={{ padding: "0 18px", paddingTop: 8 }}>
        <TopBar activeAgent={activeAgent} />
      </div>

      {/* Config bar */}
      <div style={{ display: "flex", gap: 12, padding: "10px 18px", borderBottom: "1px solid rgba(255,255,255,0.06)", alignItems: "center" }}>
        <input
          placeholder="Profile ID (UUID)"
          value={profileId}
          onChange={(e) => setProfileId(e.target.value)}
          style={{
            flex: 1,
            padding: "8px 12px",
            borderRadius: 8,
            border: "1px solid rgba(255,255,255,0.1)",
            background: "#0F0F1A",
            color: "#F2F2FA",
            fontSize: 12,
            fontFamily: "'JetBrains Mono', monospace",
            outline: "none",
          }}
        />
        <div style={{ width: 160 }}>
          <EnergySlider value={energy} onChange={setEnergy} />
        </div>
        <button
          onClick={() => setStreamMode(streamMode === "ws" ? "rest" : "ws")}
          style={{
            padding: "5px 10px",
            borderRadius: 6,
            fontSize: 10,
            fontWeight: 600,
            fontFamily: "'JetBrains Mono', monospace",
            background: streamMode === "ws" ? "rgba(27,182,138,0.12)" : "rgba(123,110,232,0.12)",
            border: "1px solid rgba(255,255,255,0.06)",
            color: streamMode === "ws" ? "#1BB68A" : "#7B6EE8",
            cursor: "pointer",
          }}
        >
          {streamMode === "ws" ? "WS" : "REST"}
        </button>
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflow: "auto", padding: 18, display: "flex", flexDirection: "column", gap: 10 }}>
        {messages.map((msg, i) => (
          <ChatMessage
            key={i}
            role={msg.role}
            content={msg.content}
            agent={(msg.agent as AgentType) || "sp"}
          />
        ))}
        {loading && (
          <div style={{ alignSelf: "flex-start", color: "#5A5A7A", fontSize: 12, animation: "pulse 1.5s infinite" }}>
            <span style={{ display: "inline-flex", gap: 3 }}>
              <span style={{ width: 4, height: 4, borderRadius: "50%", background: "#5A5A7A", animation: "bounce 1s infinite 0ms" }} />
              <span style={{ width: 4, height: 4, borderRadius: "50%", background: "#5A5A7A", animation: "bounce 1s infinite 150ms" }} />
              <span style={{ width: 4, height: 4, borderRadius: "50%", background: "#5A5A7A", animation: "bounce 1s infinite 300ms" }} />
            </span>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <ChatInput onSend={send} disabled={loading || !profileId} />

      {/* HITL Modal */}
      {hitl && (
        <HitlModal
          title="Décision irréversible"
          description={hitl.message}
          context={{ Token: hitl.token, Agent: activeAgent, Énergie: `${energy}/10` }}
          onConfirm={() => setHitl(null)}
          onReject={() => setHitl(null)}
        />
      )}
    </div>
  );
}
