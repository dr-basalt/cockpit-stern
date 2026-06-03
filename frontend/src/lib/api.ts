const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function createProfile(data: Record<string, unknown>) {
  const res = await fetch(`${API}/api/profile`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Profile creation failed: ${res.status}`);
  return res.json();
}

export async function getProfile(id: string) {
  const res = await fetch(`${API}/api/profile/${id}`);
  if (!res.ok) throw new Error(`Profile fetch failed: ${res.status}`);
  return res.json();
}

export async function sendChat(sessionId: string, profileId: string, message: string, energy: number) {
  const res = await fetch(`${API}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, profile_id: profileId, message, energy_level: energy }),
  });
  if (!res.ok) throw new Error(`Chat failed: ${res.status}`);
  return res.json();
}

export async function hitlConfirm(token: string, decision: "yes" | "no") {
  const res = await fetch(`${API}/api/chat/hitl/${token}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ decision }),
  });
  return res.json();
}

export async function getConformance() {
  const res = await fetch(`${API}/ada/conformance`);
  return res.json();
}

export async function getDesignTokens() {
  const res = await fetch(`${API}/design/tokens`);
  return res.json();
}

export function getWsUrl() {
  return API.replace(/^http/, "ws") + "/api/chat/stream";
}

export async function getIntegrations(profileId: string) {
  const res = await fetch(`${API}/api/session/${profileId}/integrations`);
  return res.json();
}

export async function connectIntegration(profileId: string, providerKey: string) {
  // Use the new MCP OAuth flow via remote *.obot.ai servers (shared OAuth apps)
  const res = await fetch(`${API}/api/obot/connect/${providerKey}`);
  const data = await res.json();
  // Remap connect_url → oauth_url for backwards compat with the UI
  if (data.connect_url) data.oauth_url = data.connect_url;
  return data;
}
