export default function PrivacyPage() {
  return (
    <div className="max-w-2xl mx-auto px-6 py-16 text-sm leading-relaxed">
      <h1 className="text-2xl font-bold mb-8">Privacy Policy — Cockpit Stern</h1>
      <p className="text-[var(--text-secondary)] mb-4">Last updated: May 26, 2026</p>

      <h2 className="text-lg font-bold mt-8 mb-3">1. Data We Collect</h2>
      <p className="text-[var(--text-secondary)] mb-4">
        Cockpit Stern collects the following data when you use our service:
        your name, Human Design profile (type, authority, profile), Clifton StrengthsFinder results,
        and conversation history with AI agents. We also collect OAuth tokens when you connect third-party
        services (via Nango).
      </p>

      <h2 className="text-lg font-bold mt-8 mb-3">2. How We Use Your Data</h2>
      <p className="text-[var(--text-secondary)] mb-4">
        Your data is used exclusively to personalize the AI sparring partner experience:
        routing messages to the right agent, adapting responses to your HD type, and
        maintaining conversation context. We do not sell your data to third parties.
      </p>

      <h2 className="text-lg font-bold mt-8 mb-3">3. Third-Party Services</h2>
      <p className="text-[var(--text-secondary)] mb-4">
        When you connect external services (Notion, Google, GitHub, etc.), OAuth tokens are
        stored securely via Nango with AES-256 encryption. We only access the data you explicitly
        authorize through OAuth scopes.
      </p>

      <h2 className="text-lg font-bold mt-8 mb-3">4. Data Retention</h2>
      <p className="text-[var(--text-secondary)] mb-4">
        Your profile and conversation data are retained as long as your account is active.
        You can request deletion at any time via the data deletion endpoint.
      </p>

      <h2 className="text-lg font-bold mt-8 mb-3">5. Data Deletion</h2>
      <p className="text-[var(--text-secondary)] mb-4">
        To request deletion of your data, visit{" "}
        <a href="/data-deletion" className="underline" style={{ color: "var(--agent-clone)" }}>
          our data deletion page
        </a>{" "}
        or send a request to contact@ori3com.cloud.
      </p>

      <h2 className="text-lg font-bold mt-8 mb-3">6. Contact</h2>
      <p className="text-[var(--text-secondary)]">
        For privacy-related questions: contact@ori3com.cloud
      </p>
    </div>
  );
}
