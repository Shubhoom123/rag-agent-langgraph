import { useState, useRef, useEffect } from "react";
import { Send, MoreHorizontal } from "lucide-react";
import Message from "./Message";
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function ChatWindow({ messages, setMessages, loading, setLoading }) {
  const [input, setInput] = useState("");
  const bottomRef = useRef();
  const textareaRef = useRef();

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 160) + "px";
  }, [input]);

  async function handleSubmit(e) {
    e.preventDefault();
    const question = input.trim();
    if (!question || loading) return;

    setInput("");
    const newMessages = [...messages, { role: "user", text: question }];
    setMessages(newMessages);
    setLoading(true);

    const history = messages
      .filter((m) => m.role === "user" || m.role === "assistant")
      .map((m) => ({ role: m.role, text: m.text }));

    try {
      const res = await fetch(`${API_URL}/api/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, history }),
      });

      const data = await res.json();

      if (res.ok) {
        setMessages([
          ...newMessages,
          {
            role: "assistant",
            text: data.answer,
            sources: data.sources,
            webSearchUsed: data.web_search_used,
            retries: data.retries,
          },
        ]);
      } else {
        setMessages([
          ...newMessages,
          { role: "error", text: data.detail || "Something went wrong." },
        ]);
      }
    } catch {
      setMessages([
        ...newMessages,
        { role: "error", text: "Could not reach the backend." },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  }

  const chatTitle = messages.find((m) => m.role === "user")?.text?.slice(0, 40)
    || "New Conversation";

  return (
    <main style={{
      flex: 1,
      display: "flex",
      flexDirection: "column",
      height: "100vh",
      overflow: "hidden",
      background: "var(--bg)",
    }}>

      {/* Header */}
      <div style={{
        borderBottom: "1px solid var(--border)",
        padding: "0 24px",
        height: 56,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        background: "var(--surface)",
        flexShrink: 0,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{
            fontSize: "0.95rem",
            fontWeight: 600,
            color: "var(--text)",
            letterSpacing: "-0.01em",
            maxWidth: 400,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}>
            {chatTitle}
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          {/* Model badge */}
          <div style={{
            display: "flex",
            alignItems: "center",
            gap: 6,
            padding: "4px 10px",
            borderRadius: "var(--radius)",
            border: "1px solid var(--border)",
            background: "var(--surface-2)",
            cursor: "default",
          }}>
            <div style={{
              width: 6,
              height: 6,
              borderRadius: "50%",
              background: "var(--accent)",
            }} />
            <span style={{
              fontFamily: "var(--mono)",
              fontSize: "0.65rem",
              color: "var(--text-secondary)",
              letterSpacing: "0.05em",
            }}>
              llama-3.1-8b
            </span>
          </div>

          <button
            style={{
              background: "transparent",
              border: "none",
              cursor: "pointer",
              color: "var(--text-muted)",
              padding: 6,
              borderRadius: "var(--radius)",
              display: "flex",
              alignItems: "center",
              transition: "color var(--transition)",
            }}
            onMouseEnter={(e) => e.currentTarget.style.color = "var(--accent)"}
            onMouseLeave={(e) => e.currentTarget.style.color = "var(--text-muted)"}
          >
            <MoreHorizontal size={16} />
          </button>
        </div>
      </div>

      {/* Messages */}
      <div style={{
        flex: 1,
        overflowY: "auto",
        padding: "32px 0 16px",
        display: "flex",
        flexDirection: "column",
      }}>
        {messages.length === 0 && <EmptyState />}
        {messages.map((msg, i) => (
          <Message key={i} message={msg} />
        ))}
        {loading && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div style={{
        borderTop: "1px solid var(--border)",
        padding: "12px 24px 16px",
        background: "var(--surface)",
        flexShrink: 0,
      }}>
        <div style={{
          maxWidth: 760,
          margin: "0 auto",
        }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              background: "var(--surface-2)",
              border: "1px solid var(--border)",
              borderRadius: "var(--radius-lg)",
              padding: "0 8px 0 14px",
              minHeight: 44,
              transition: `border-color var(--transition)`,
            }}
            onFocusCapture={(e) => {
              e.currentTarget.style.borderColor = "var(--accent)";
            }}
            onBlurCapture={(e) => {
              e.currentTarget.style.borderColor = "var(--border)";
            }}
          >
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Message LangGraph..."
              rows={1}
              style={{
                flex: 1,
                background: "transparent",
                border: "none",
                outline: "none",
                color: "var(--text)",
                fontFamily: "var(--sans)",
                fontSize: "0.9rem",
                resize: "none",
                lineHeight: 1.5,
                padding: "11px 0",
                maxHeight: 160,
              }}
            />
            <button
              onClick={handleSubmit}
              disabled={!input.trim() || loading}
              style={{
                width: 32,
                height: 32,
                background: input.trim() && !loading
                  ? "var(--accent)" : "var(--disabled)",
                border: "none",
                borderRadius: "var(--radius)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                cursor: input.trim() && !loading ? "pointer" : "not-allowed",
                transition: `all var(--transition)`,
                flexShrink: 0,
              }}
              onMouseEnter={(e) => {
                if (input.trim() && !loading) {
                  e.currentTarget.style.background = "var(--accent-dark)";
                  e.currentTarget.style.transform = "scale(0.97)";
                }
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = input.trim() && !loading
                  ? "var(--accent)" : "var(--disabled)";
                e.currentTarget.style.transform = "scale(1)";
              }}
            >
              <Send
                size={13}
                color={input.trim() && !loading ? "#0d1117" : "var(--text-muted)"}
              />
            </button>
          </div>

          <div style={{
            textAlign: "center",
            marginTop: 8,
            fontFamily: "var(--mono)",
            fontSize: "0.65rem",
            color: "var(--text-muted)",
          }}>
            Enter to send · Shift+Enter for new line
          </div>
        </div>
      </div>
    </main>
  );
}

function EmptyState() {
  const suggestions = [
    "What is machine learning?",
    "Who is Nikola Tesla?",
    "What is LangGraph?",
    "Explain transformers in AI",
  ];

  return (
    <div style={{
      flex: 1,
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      gap: 20,
      padding: 48,
      marginTop: "8vh",
      background: "radial-gradient(ellipse at center, rgba(63,185,80,0.03) 0%, transparent 70%)",
    }}>
      <div style={{
        width: 56,
        height: 56,
        borderRadius: "var(--radius-lg)",
        background: "var(--surface-2)",
        border: "1px solid var(--border)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}>
        <img
          src="/favicon_64.png"
          alt="agent"
          style={{
            width: 28,
            height: 28,
            objectFit: "contain",
            filter: "invert(1) brightness(0.7) sepia(1) saturate(5) hue-rotate(95deg)",
          }}
        />
      </div>

      <div style={{ textAlign: "center" }}>
        <div style={{
          fontSize: "0.95rem",
          fontWeight: 600,
          color: "var(--text)",
          letterSpacing: "-0.01em",
          marginBottom: 6,
        }}>
          LangGraph RAG Agent
        </div>
        <div style={{
          fontFamily: "var(--mono)",
          fontSize: "0.75rem",
          color: "var(--text-muted)",
          lineHeight: 1.8,
        }}>
          Clean, minimal, and powerful.
        </div>
      </div>

      {/* Feature pills */}
      <div style={{
        display: "flex",
        gap: 8,
        flexWrap: "wrap",
        justifyContent: "center",
      }}>
        {["Self-Correcting RAG", "Wikipedia Aware", "Web Fallback"].map((f) => (
          <div key={f} style={{
            padding: "4px 12px",
            borderRadius: 999,
            background: "var(--accent-dim)",
            border: "1px solid var(--border)",
            fontFamily: "var(--mono)",
            fontSize: "0.65rem",
            color: "var(--accent)",
            letterSpacing: "0.04em",
          }}>
            {f}
          </div>
        ))}
      </div>

      {/* Suggestion grid */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "1fr 1fr",
        gap: 8,
        maxWidth: 480,
        width: "100%",
        marginTop: 4,
      }}>
        {suggestions.map((q) => (
          <div
            key={q}
            style={{
              padding: "12px 14px",
              borderRadius: "var(--radius)",
              background: "var(--surface-2)",
              border: "1px solid var(--border)",
              fontFamily: "var(--sans)",
              fontSize: "0.8rem",
              color: "var(--text-secondary)",
              cursor: "default",
              lineHeight: 1.4,
              transition: `border-color var(--transition)`,
            }}
            onMouseEnter={(e) => e.currentTarget.style.borderColor = "var(--accent)"}
            onMouseLeave={(e) => e.currentTarget.style.borderColor = "var(--border)"}
          >
            {q}
          </div>
        ))}
      </div>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div style={{
      padding: "12px 24px",
      display: "flex",
      gap: 12,
      alignItems: "center",
      maxWidth: 760,
      margin: "0 auto",
      width: "100%",
    }}>
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
      }}>
        <img
          src="/favicon_32.png"
          alt="agent"
          style={{
            width: 16,
            height: 16,
            objectFit: "contain",
            filter: "invert(1) brightness(0.7) sepia(1) saturate(5) hue-rotate(95deg)",
          }}
        />
      </div>
      <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
        {[0, 1, 2].map((i) => (
          <div key={i} style={{
            width: 5,
            height: 5,
            borderRadius: "50%",
            background: "var(--accent)",
            animation: `pulse 1.2s ease-in-out ${i * 0.2}s infinite`,
          }} />
        ))}
      </div>
    </div>
  );
}