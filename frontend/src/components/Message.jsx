import { useState } from "react";
import { Globe, ChevronDown, ChevronUp, AlertCircle, Copy, ThumbsUp, ThumbsDown } from "lucide-react";

export default function Message({ message }) {
  const [sourcesOpen, setSourcesOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const [hovered, setHovered] = useState(false);
  const isUser = message.role === "user";
  const isError = message.role === "error";

  function copyText() {
    navigator.clipboard.writeText(message.text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  if (isUser) {
    return (
      <div className="animate-fade-slide" style={{
        padding: "6px 28px",
        display: "flex",
        justifyContent: "flex-end",
        maxWidth: 760,
        margin: "0 auto",
        width: "100%",
      }}>
        <div style={{
          background: "var(--surface-2)",
          border: "1px solid var(--border)",
          borderRadius: "18px 18px 4px 18px",
          padding: "11px 18px",
          maxWidth: "72%",
          fontSize: "0.9rem",
          lineHeight: 1.65,
          fontFamily: "var(--sans)",
          color: "var(--text)",
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
        }}>
          {message.text}
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="animate-fade-slide" style={{
        padding: "6px 28px",
        maxWidth: 760,
        margin: "0 auto",
        width: "100%",
      }}>
        <div style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          background: "var(--red-dim)",
          border: "1px solid rgba(248,113,113,0.2)",
          borderRadius: "var(--radius-lg)",
          padding: "10px 14px",
          color: "var(--red)",
          fontSize: "0.8rem",
          fontFamily: "var(--mono)",
        }}>
          <AlertCircle size={13} />
          {message.text}
        </div>
      </div>
    );
  }

  return (
    <div
      className="animate-fade-slide"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        padding: "6px 28px",
        display: "flex",
        gap: 14,
        alignItems: "flex-start",
        maxWidth: 760,
        margin: "0 auto",
        width: "100%",
      }}
    >
      {/* Avatar orb */}
      <div style={{
        width: 34,
        height: 34,
        borderRadius: "50%",
        background: "radial-gradient(circle, rgba(74,222,128,0.12) 0%, transparent 70%)",
        border: "1px solid rgba(74,222,128,0.2)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        flexShrink: 0,
        marginTop: 2,
        boxShadow: "0 0 10px rgba(74,222,128,0.08)",
      }}>
        <div style={{
          width: 10,
          height: 10,
          borderRadius: "50%",
          background: "var(--accent)",
          boxShadow: "0 0 6px var(--accent)",
        }} />
      </div>

      <div style={{
        flex: 1,
        display: "flex",
        flexDirection: "column",
        gap: 8,
        paddingTop: 4,
      }}>
        {/* Answer */}
        <div style={{
          fontSize: "0.9rem",
          lineHeight: 1.75,
          color: "var(--text)",
          fontFamily: "var(--sans)",
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
        }}>
          {message.text}
        </div>

        {/* Action buttons */}
        <div style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          opacity: hovered ? 1 : 0,
          transition: "opacity var(--transition)",
        }}>
          <div style={{ display: "flex", gap: 4 }}>
            <ActionButton icon={<Copy size={11} />} label={copied ? "Copied!" : "Copy"} onClick={copyText} active={copied} />
            <ActionButton icon={<ThumbsUp size={11} />} label="Good" />
            <ActionButton icon={<ThumbsDown size={11} />} label="Bad" />
          </div>

          <div style={{ display: "flex", gap: 6 }}>
            {message.webSearchUsed && (
              <Badge icon={<Globe size={9} />} label="Web search" color="var(--accent)" bg="var(--accent-dim)" border="rgba(74,222,128,0.15)" />
            )}
            {message.retries > 0 && (
              <Badge label={`${message.retries} retr${message.retries === 1 ? "y" : "ies"}`} color="var(--text-muted)" bg="var(--surface-2)" border="var(--border)" />
            )}
          </div>
        </div>

        {/* Sources */}
        {message.sources?.length > 0 && (
          <div style={{
            border: "1px solid var(--border)",
            borderRadius: "var(--radius-lg)",
            overflow: "hidden",
          }}>
            <button
              onClick={() => setSourcesOpen((o) => !o)}
              style={{
                width: "100%",
                background: "var(--surface)",
                border: "none",
                padding: "8px 14px",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                cursor: "pointer",
                color: "var(--text-muted)",
                fontFamily: "var(--mono)",
                fontSize: "0.62rem",
                letterSpacing: "0.06em",
                textTransform: "uppercase",
                transition: "background var(--transition)",
              }}
              onMouseEnter={(e) => e.currentTarget.style.background = "var(--surface-2)"}
              onMouseLeave={(e) => e.currentTarget.style.background = "var(--surface)"}
            >
              <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <div style={{
                  width: 5,
                  height: 5,
                  borderRadius: "50%",
                  background: "var(--accent)",
                  boxShadow: "0 0 4px var(--accent)",
                }} />
                {message.sources.length} Source{message.sources.length !== 1 ? "s" : ""}
              </span>
              {sourcesOpen ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
            </button>

            {sourcesOpen && (
              <div className="animate-fade" style={{
                display: "flex",
                flexDirection: "column",
                gap: 1,
                background: "var(--border-subtle)",
              }}>
                {message.sources.map((src, i) => (
                  <div key={i} style={{
                    background: "var(--surface)",
                    padding: "10px 14px",
                    fontSize: "0.75rem",
                    color: "var(--text-secondary)",
                    fontFamily: "var(--mono)",
                    lineHeight: 1.65,
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-word",
                  }}>
                    <span style={{ color: "var(--accent)", marginRight: 8, fontSize: "0.62rem" }}>
                      [{i + 1}]
                    </span>
                    {src.content.slice(0, 300)}
                    {src.content.length > 300 && <span style={{ color: "var(--text-muted)" }}>…</span>}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function ActionButton({ icon, label, onClick, active }) {
  return (
    <button
      onClick={onClick}
      style={{
        background: active ? "var(--accent-dim)" : "transparent",
        border: `1px solid ${active ? "rgba(74,222,128,0.3)" : "transparent"}`,
        borderRadius: "var(--radius)",
        padding: "3px 8px",
        color: active ? "var(--accent)" : "var(--text-muted)",
        fontFamily: "var(--mono)",
        fontSize: "0.62rem",
        cursor: "pointer",
        display: "flex",
        alignItems: "center",
        gap: 4,
        transition: "all var(--transition)",
      }}
      onMouseEnter={(e) => {
        if (!active) {
          e.currentTarget.style.color = "var(--accent)";
          e.currentTarget.style.borderColor = "var(--border)";
        }
      }}
      onMouseLeave={(e) => {
        if (!active) {
          e.currentTarget.style.color = "var(--text-muted)";
          e.currentTarget.style.borderColor = "transparent";
        }
      }}
    >
      {icon}
      {label}
    </button>
  );
}

function Badge({ icon, label, color, bg, border }) {
  return (
    <div style={{
      display: "inline-flex",
      alignItems: "center",
      gap: 4,
      padding: "2px 8px",
      borderRadius: 999,
      background: bg,
      color: color,
      border: `1px solid ${border}`,
      fontFamily: "var(--mono)",
      fontSize: "0.62rem",
      letterSpacing: "0.04em",
    }}>
      {icon}
      {label}
    </div>
  );
}