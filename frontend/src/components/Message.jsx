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
        padding: "8px 24px",
        display: "flex",
        justifyContent: "flex-end",
        maxWidth: 760,
        margin: "0 auto",
        width: "100%",
      }}>
        <div style={{
          background: "rgba(107,165,132,0.08)",
          border: "1px solid rgba(107,165,132,0.25)",
          borderRadius: "12px 12px 4px 12px",
          padding: "10px 16px",
          maxWidth: "72%",
          fontSize: "0.9375rem",
          lineHeight: 1.6,
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
        padding: "8px 24px",
        maxWidth: 760,
        margin: "0 auto",
        width: "100%",
      }}>
        <div style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          background: "var(--red-dim)",
          border: "1px solid var(--red)",
          borderRadius: "var(--radius)",
          padding: "10px 14px",
          color: "var(--red)",
          fontSize: "0.75rem",
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
        padding: "8px 24px",
        display: "flex",
        gap: 12,
        alignItems: "flex-start",
        maxWidth: 760,
        margin: "0 auto",
        width: "100%",
      }}
    >
      {/* Avatar */}
      <div style={{
        width: 32,
        height: 32,
        borderRadius: "var(--radius)",
        background: "var(--surface-2)",
        border: "1px solid var(--border)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        flexShrink: 0,
        marginTop: 3,
      }}>
        <img
          src="/favicon_32.png"
          alt="agent"
          style={{
            width: 16,
            height: 16,
            objectFit: "contain",
            filter: "invert(1) brightness(0.7) sepia(1) saturate(5) hue-rotate(95deg)",          }}
        />
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
          fontSize: "0.9375rem",
          lineHeight: 1.7,
          color: "var(--text)",
          fontFamily: "var(--sans)",
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: "4px 12px 12px 12px",
          padding: "12px 16px",
        }}>
          {message.text}
        </div>

        {/* Action buttons — visible on hover */}
        <div style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          opacity: hovered ? 1 : 0,
          transition: `opacity var(--transition)`,
        }}>
          <div style={{ display: "flex", gap: 4 }}>
            <ActionButton
              icon={<Copy size={12} />}
              label={copied ? "Copied!" : "Copy"}
              onClick={copyText}
              active={copied}
            />
            <ActionButton
              icon={<ThumbsUp size={12} />}
              label="Good"
            />
            <ActionButton
              icon={<ThumbsDown size={12} />}
              label="Bad"
            />
          </div>

          {/* Badges */}
          <div style={{ display: "flex", gap: 6 }}>
            {message.webSearchUsed && (
              <Badge
                icon={<Globe size={10} />}
                label="Web search"
                color="var(--accent)"
                bg="var(--accent-dim)"
                border="rgba(107,165,132,0.2)"
              />
            )}
            {message.retries > 0 && (
              <Badge
                label={`${message.retries} retr${message.retries === 1 ? "y" : "ies"}`}
                color="var(--text-muted)"
                bg="var(--surface-2)"
                border="var(--border)"
              />
            )}
          </div>
        </div>

        {/* Sources */}
        {message.sources?.length > 0 && (
          <div style={{
            border: "1px solid var(--border)",
            borderRadius: "var(--radius)",
            overflow: "hidden",
          }}>
            <button
              onClick={() => setSourcesOpen((o) => !o)}
              style={{
                width: "100%",
                background: "var(--surface-2)",
                border: "none",
                padding: "7px 12px",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                cursor: "pointer",
                color: "var(--text-muted)",
                fontFamily: "var(--mono)",
                fontSize: "0.65rem",
                letterSpacing: "0.06em",
                textTransform: "uppercase",
                transition: `background var(--transition)`,
              }}
              onMouseEnter={(e) =>
                e.currentTarget.style.background = "var(--surface-3)"
              }
              onMouseLeave={(e) =>
                e.currentTarget.style.background = "var(--surface-2)"
              }
            >
              <span style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
              }}>
                <div style={{
                  width: 5,
                  height: 5,
                  borderRadius: "50%",
                  background: "var(--accent)",
                }} />
                {message.sources.length} Source{message.sources.length !== 1 ? "s" : ""}
              </span>
              {sourcesOpen
                ? <ChevronUp size={11} />
                : <ChevronDown size={11} />
              }
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
                    <span style={{
                      color: "var(--accent)",
                      marginRight: 8,
                      fontSize: "0.65rem",
                      opacity: 0.8,
                    }}>
                      [{i + 1}]
                    </span>
                    {src.content.slice(0, 300)}
                    {src.content.length > 300 && (
                      <span style={{ color: "var(--text-muted)" }}>…</span>
                    )}
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
        border: `1px solid ${active ? "var(--accent)" : "transparent"}`,
        borderRadius: "var(--radius)",
        padding: "3px 8px",
        color: active ? "var(--accent)" : "var(--text-muted)",
        fontFamily: "var(--mono)",
        fontSize: "0.65rem",
        cursor: "pointer",
        display: "flex",
        alignItems: "center",
        gap: 4,
        transition: `all var(--transition)`,
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
      fontSize: "0.65rem",
      letterSpacing: "0.04em",
    }}>
      {icon}
      {label}
    </div>
  );
}