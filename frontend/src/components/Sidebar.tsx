"use client";

import { useState } from "react";

interface SidebarSection {
  id: string;
  label: string;
  visible: boolean;
  collapsed?: boolean;
  content?: React.ReactNode;
}

interface SidebarProps {
  sections: SidebarSection[];
  onReorder?: (newOrder: string[]) => void;
}

export default function Sidebar({ sections, onReorder }: SidebarProps) {
  const [collapsedState, setCollapsedState] = useState<Record<string, boolean>>(
    Object.fromEntries(sections.map((s) => [s.id, s.collapsed ?? false]))
  );

  const toggleCollapse = (id: string) => {
    setCollapsedState((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const visibleSections = sections.filter((s) => s.visible);

  return (
    <div
      style={{
        background: "#0F0F1A",
        border: "1px solid rgba(255,255,255,0.06)",
        borderRadius: 14,
        padding: 16,
        display: "flex",
        flexDirection: "column",
        gap: 12,
        overflowY: "auto",
        width: 220,
        minHeight: 0,
      }}
    >
      <div
        style={{
          fontSize: 10,
          color: "#5A5A7A",
          textTransform: "uppercase",
          letterSpacing: "0.07em",
          marginBottom: 6,
        }}
      >
        Navigation
      </div>

      {visibleSections.map((section) => (
        <div key={section.id}>
          <button
            onClick={() => toggleCollapse(section.id)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              width: "100%",
              padding: "5px 7px",
              borderRadius: 6,
              fontSize: 12,
              fontFamily: "'Syne', system-ui",
              color: "#F2F2FA",
              background: "transparent",
              border: "none",
              cursor: "pointer",
              transition: "background 100ms",
              textAlign: "left",
            }}
          >
            <span style={{ color: "#5A5A7A", fontSize: 10, width: 12 }}>
              {collapsedState[section.id] ? "▸" : "▾"}
            </span>
            <span style={{ color: "#5A5A7A", fontSize: 10, cursor: "grab" }}>⠿</span>
            {section.label}
          </button>

          {!collapsedState[section.id] && section.content && (
            <div style={{ paddingLeft: 28, paddingTop: 6 }}>{section.content}</div>
          )}
        </div>
      ))}
    </div>
  );
}
