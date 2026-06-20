import { useState, useRef, useEffect } from "react";
import { Send, MoreHorizontal } from "lucide-react";
import { saveUsageStats } from "../firebase";

import Message from "./Message";
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function ChatWindow({ user, messages, setMessages, loading, setLoading }) {
  const [input, setInput] = useState("");
  const [inputFocused, setInputFocused] = useState(false);
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
        setMessages([...newMessages, {
          role: "assistant",
          text: data.answer,
          sources: data.sources,
          webSearchUsed: data.web_search_used,
          retries: data.retries,
        }]);

        // Track usage in Firestore
        if (user?.uid && data.token_usage) {
          saveUsageStats(user.uid, {
            tokens: data.token_usage.total_tokens,
            promptTokens: data.token_usage.prompt_tokens,
            completionTokens: data.token_usage.completion_tokens,
            webSearchUsed: data.web_search_used,
          }).catch(console.error);
        }
      } else {
        setMessages([...newMessages, { role: "error", text: data.detail || "Something went wrong." }]);
      }
    } catch {
      setMessages([...newMessages, { role: "error", text: "Could not reach the backend." }]);
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

  const chatTitle = messages.find((m) => m.role === "user")?.text?.slice(0, 40) || "New Conversation";
  const canSend = input.trim() && !loading;

  return (
    <main style={{
      flex: 1,
      display: "flex",
      flexDirection: "column",
      height: "100vh",
      overflow: "hidden",
      background: "#000000",
    }}>
      {/* Header */}
      <div style={{
        borderBottom: "1px solid var(--border)",
        padding: "0 28px",
        height: 58,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        background: "rgba(0,0,0,0.9)",
        backdropFilter: "blur(12px)",
        flexShrink: 0,
      }}>
        <div style={{
          fontSize: "0.95rem",
          fontWeight: 500,
          color: "var(--text)",
          letterSpacing: "-0.01em",
          maxWidth: 400,
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
        }}>
          {chatTitle}
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div style={{
            display: "flex",
            alignItems: "center",
            gap: 6,
            padding: "4px 12px",
            borderRadius: 999,
            border: "1px solid var(--border)",
            background: "var(--surface)",
          }}>
            <div style={{
              width: 6,
              height: 6,
              borderRadius: "50%",
              background: "var(--accent)",
              boxShadow: "0 0 6px var(--accent)",
            }} />
            <span style={{
              fontFamily: "var(--mono)",
              fontSize: "0.65rem",
              color: "var(--text-secondary)",
              letterSpacing: "0.04em",
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
        {messages.length === 0 && <EmptyState onSuggest={(q) => setInput(q)} />}
        {messages.map((msg, i) => (
          <Message key={i} message={msg} />
        ))}
        {loading && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div style={{
        padding: "12px 24px 20px",
        background: "rgba(0,0,0,0.95)",
        backdropFilter: "blur(12px)",
        flexShrink: 0,
        borderTop: "1px solid var(--border)",
      }}>
        <div style={{ maxWidth: 760, margin: "0 auto" }}>
          <div style={{
            display: "flex",
            alignItems: "flex-end",
            gap: 10,
            background: "var(--surface)",
            border: `1px solid ${inputFocused ? "rgba(74,222,128,0.4)" : "var(--border)"}`,
            borderRadius: "var(--radius-xl)",
            padding: "8px 10px 8px 18px",
            minHeight: 52,
            transition: "border-color var(--transition), box-shadow var(--transition)",
            boxShadow: inputFocused
              ? "0 0 0 3px rgba(74,222,128,0.06), 0 0 20px rgba(74,222,128,0.08)"
              : "none",
          }}>
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              onFocus={() => setInputFocused(true)}
              onBlur={() => setInputFocused(false)}
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
                lineHeight: 1.6,
                padding: "6px 0",
                maxHeight: 160,
              }}
            />
            <button
              onClick={handleSubmit}
              disabled={!canSend}
              style={{
                width: 36,
                height: 36,
                background: canSend ? "var(--accent)" : "var(--surface-2)",
                border: "none",
                borderRadius: "50%",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                cursor: canSend ? "pointer" : "not-allowed",
                transition: "all var(--transition)",
                flexShrink: 0,
                boxShadow: canSend ? "0 0 12px rgba(74,222,128,0.3)" : "none",
              }}
              onMouseEnter={(e) => {
                if (canSend) {
                  e.currentTarget.style.background = "var(--accent-bright)";
                  e.currentTarget.style.boxShadow = "0 0 20px rgba(74,222,128,0.5)";
                }
              }}
              onMouseLeave={(e) => {
                if (canSend) {
                  e.currentTarget.style.background = "var(--accent)";
                  e.currentTarget.style.boxShadow = "0 0 12px rgba(74,222,128,0.3)";
                }
              }}
            >
              <Send size={14} color={canSend ? "#000000" : "var(--text-dim)"} />
            </button>
          </div>

          <div style={{
            textAlign: "center",
            marginTop: 10,
            fontFamily: "var(--mono)",
            fontSize: "0.62rem",
            color: "var(--text-muted)",
            letterSpacing: "0.03em",
          }}>
            Enter to send · Shift+Enter for new line
          </div>
        </div>
      </div>
    </main>
  );
}

function EmptyState({ onSuggest }) {
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
      gap: 28,
      padding: 48,
    }}>
      {/* Gemini-style central glow orb */}
      <div style={{
        width: 72,
        height: 72,
        borderRadius: "50%",
        background: "radial-gradient(circle at center, rgba(74,222,128,0.3) 0%, rgba(74,222,128,0.08) 50%, transparent 70%)",
        boxShadow: "0 0 60px 20px rgba(74,222,128,0.12), 0 0 120px 50px rgba(74,222,128,0.05)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        animation: "glowPulse 3s ease-in-out infinite",
      }}>
        <div style={{
          width: 14,
          height: 14,
          borderRadius: "50%",
          background: "#4ade80",
          boxShadow: "0 0 10px #4ade80, 0 0 20px rgba(74,222,128,0.6)",
        }} />
      </div>

      <div style={{ textAlign: "center" }}>
        <div style={{
          fontSize: "1.6rem",
          fontWeight: 500,
          color: "var(--text)",
          letterSpacing: "-0.02em",
        }}>
          How can I help you today?
        </div>
      </div>

      <div style={{
        display: "grid",
        gridTemplateColumns: "1fr 1fr",
        gap: 10,
        maxWidth: 520,
        width: "100%",
      }}>
        {suggestions.map((q) => (
          <button
            key={q}
            onClick={() => onSuggest(q)}
            style={{
              padding: "14px 16px",
              borderRadius: "var(--radius-lg)",
              background: "var(--surface)",
              border: "1px solid var(--border)",
              fontFamily: "var(--sans)",
              fontSize: "0.85rem",
              color: "var(--text-secondary)",
              cursor: "pointer",
              lineHeight: 1.4,
              textAlign: "left",
              transition: "all var(--transition)",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = "rgba(74,222,128,0.3)";
              e.currentTarget.style.color = "var(--text)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = "var(--border)";
              e.currentTarget.style.color = "var(--text-secondary)";
            }}
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div style={{
      padding: "12px 28px",
      display: "flex",
      gap: 14,
      alignItems: "center",
      maxWidth: 760,
      margin: "0 auto",
      width: "100%",
    }}>
      <div style={{
        width: 34,
        height: 34,
        borderRadius: "50%",
        background: "radial-gradient(circle, rgba(74,222,128,0.1) 0%, transparent 70%)",
        border: "1px solid rgba(74,222,128,0.2)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        flexShrink: 0,
      }}>
        <div style={{
          width: 10,
          height: 10,
          borderRadius: "50%",
          background: "var(--accent)",
          boxShadow: "0 0 6px var(--accent)",
        }} />
      </div>
      <div style={{ display: "flex", gap: 5, alignItems: "center" }}>
        {[0, 1, 2].map((i) => (
          <div key={i} style={{
            width: 5,
            height: 5,
            borderRadius: "50%",
            background: "var(--accent)",
            animation: `pulse 1.4s ease-in-out ${i * 0.2}s infinite`,
          }} />
        ))}
      </div>
    </div>
  );
}