"use client";

import { useState, useRef } from "react";

interface ChatInputProps {
  onSend: (message: string) => void;
  placeholder?: string;
  disabled?: boolean;
}

export default function ChatInput({ onSend, placeholder = "Parle à tes agents...", disabled = false }: ChatInputProps) {
  const [value, setValue] = useState("");
  const ref = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
    ref.current?.focus();
  };

  return (
    <div style={{ padding: "14px 18px", borderTop: "1px solid rgba(255,255,255,0.06)" }}>
      <div style={{ position: "relative" }}>
        <textarea
          ref={ref}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSend();
            }
          }}
          placeholder={placeholder}
          disabled={disabled}
          rows={2}
          style={{
            width: "100%",
            padding: "10px 14px",
            paddingRight: 48,
            borderRadius: 10,
            border: "1px solid rgba(255,255,255,0.10)",
            background: "#1D1D30",
            color: "#F2F2FA",
            fontSize: 13,
            fontFamily: "'Syne', system-ui",
            outline: "none",
            resize: "none",
            transition: "border-color 140ms",
            opacity: disabled ? 0.5 : 1,
          }}
          onFocus={(e) => (e.target.style.borderColor = "rgba(123,110,232,0.5)")}
          onBlur={(e) => (e.target.style.borderColor = "rgba(255,255,255,0.10)")}
        />
        <button
          onClick={handleSend}
          disabled={disabled || !value.trim()}
          style={{
            position: "absolute",
            right: 10,
            bottom: 10,
            width: 30,
            height: 30,
            borderRadius: 7,
            border: "none",
            background: value.trim() ? "rgba(123,110,232,0.2)" : "transparent",
            color: value.trim() ? "#7B6EE8" : "#5A5A7A",
            fontSize: 16,
            cursor: value.trim() ? "pointer" : "default",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            transition: "all 100ms",
          }}
        >
          ↑
        </button>
      </div>
    </div>
  );
}
