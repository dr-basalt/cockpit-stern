import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Cockpit Stern",
  description: "AI Sparring Partner — Multi-Agent Cockpit",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=Syne:wght@400;500;700;800&family=JetBrains+Mono:wght@400;500&display=swap"
          rel="stylesheet"
        />
      </head>
      <body
        style={{
          margin: 0,
          background: "#07070D",
          color: "#F2F2FA",
          fontFamily: "'Syne', system-ui, sans-serif",
        }}
      >
        {children}
      </body>
    </html>
  );
}
