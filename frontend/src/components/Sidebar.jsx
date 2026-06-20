import { useEffect, useState } from "react";
import { Upload, Plus, Trash2, MessageSquare, Search, LogOut } from "lucide-react";
import FileUpload from "./FileUpload";
import { logOut } from "../firebase";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function Sidebar({ user, status, setStatus, chats, activeChatId, onSelectChat, onNewChat, onDeleteChat, onOpenProfile }) {
  const [showUpload, setShowUpload] = useState(false);
  const [search, setSearch] = useState("");
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    fetch(`${API_URL}/api/health`)
      .then((r) => r.json())
      .then(setStatus)
      .catch(() => setStatus(null));
  }, []);

  const allOk = status?.llm_reachable && status?.vector_store_reachable;
  const filteredChats = chats.filter((c) =>
    c.title.toLowerCase().includes(search.toLowerCase())
  );

  if (collapsed) {
    return (
      <aside style={{
        width: 56,
        minWidth: 56,
        background: "var(--surface)",
        borderRight: "1px solid var(--border)",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        padding: "16px 0",
        gap: 16,
      }}>
        <button
          onClick={() => setCollapsed(false)}
          style={{
            background: "transparent",
            border: "none",
            cursor: "pointer",
            padding: 8,
            borderRadius: "var(--radius)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <img
            src="/dragon-favicon.svg"
            alt="d-RAG-on"
            style={{ width: 22, height: 22, objectFit: "contain" }}
          />
        </button>
        <button
          onClick={onNewChat}
          style={{
            background: "transparent",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius)",
            cursor: "pointer",
            color: "var(--accent)",
            padding: 8,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            transition: "all var(--transition)",
          }}
          onMouseEnter={(e) => e.currentTarget.style.background = "var(--accent-dim)"}
          onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}
        >
          <Plus size={15} />
        </button>
      </aside>
    );
  }

  return (
    <aside style={{
      width: 280,
      minWidth: 280,
      background: "var(--surface)",
      borderRight: "1px solid var(--border)",
      display: "flex",
      flexDirection: "column",
      height: "100vh",
      overflow: "hidden",
    }}>
      {/* Header */}
      <div style={{
        padding: "20px 16px 14px",
        borderBottom: "1px solid var(--border)",
        flexShrink: 0,
      }}>
        <div style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: 16,
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{
              width: 36,
              height: 36,
              borderRadius: "var(--radius)",
              background: "var(--surface-2)",
              border: "1px solid var(--border)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0,
            }}>
              <img
                src="/dragon-favicon.svg"
                alt="d-RAG-on"
                style={{ width: 28, height: 28, objectFit: "contain" }}
              />
            </div>
            <div>
              <div style={{
                fontSize: "0.95rem",
                fontWeight: 600,
                color: "var(--text)",
                letterSpacing: "-0.01em",
                lineHeight: 1.2,
              }}>
                d-RAG-on
              </div>
              <div style={{
                fontFamily: "var(--mono)",
                fontSize: "0.6rem",
                color: "var(--accent)",
                letterSpacing: "0.1em",
                textTransform: "uppercase",
                opacity: 0.7,
              }}>
                RAG Agent
              </div>
            </div>
          </div>

          <button
            onClick={() => setCollapsed(true)}
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
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <rect x="2" y="4" width="12" height="1.5" rx="0.75" fill="currentColor"/>
              <rect x="2" y="7.25" width="8" height="1.5" rx="0.75" fill="currentColor"/>
              <rect x="2" y="10.5" width="10" height="1.5" rx="0.75" fill="currentColor"/>
            </svg>
          </button>
        </div>

        <button
          onClick={onNewChat}
          style={{
            width: "100%",
            background: "transparent",
            border: "1px solid rgba(74,222,128,0.3)",
            borderRadius: "var(--radius-lg)",
            padding: "9px 14px",
            color: "var(--accent)",
            fontFamily: "var(--sans)",
            fontWeight: 500,
            fontSize: "0.82rem",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 8,
            transition: "all var(--transition)",
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = "var(--accent-dim)";
            e.currentTarget.style.borderColor = "rgba(74,222,128,0.5)";
            e.currentTarget.style.boxShadow = "0 0 12px rgba(74,222,128,0.08)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = "transparent";
            e.currentTarget.style.borderColor = "rgba(74,222,128,0.3)";
            e.currentTarget.style.boxShadow = "none";
          }}
        >
          <Plus size={14} />
          New chat
        </button>
      </div>

      {/* Search */}
      <div style={{
        padding: "10px 14px",
        borderBottom: "1px solid var(--border-subtle)",
        flexShrink: 0,
      }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            background: "var(--surface-2)",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius-lg)",
            padding: "7px 12px",
            transition: "border-color var(--transition)",
          }}
          onFocusCapture={(e) => e.currentTarget.style.borderColor = "rgba(74,222,128,0.3)"}
          onBlurCapture={(e) => e.currentTarget.style.borderColor = "var(--border)"}
        >
          <Search size={12} color="var(--text-muted)" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search chats"
            style={{
              flex: 1,
              background: "transparent",
              border: "none",
              outline: "none",
              color: "var(--text)",
              fontFamily: "var(--sans)",
              fontSize: "0.8rem",
            }}
          />
        </div>
      </div>

      {/* Chat list */}
      <div style={{ flex: 1, overflowY: "auto", padding: "6px 8px" }}>
        {filteredChats.length > 0 && (
          <div style={{
            fontFamily: "var(--mono)",
            fontSize: "0.6rem",
            color: "var(--text-muted)",
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            padding: "6px 8px 6px",
          }}>
            Recents
          </div>
        )}
        {filteredChats.length === 0 ? (
          <div style={{
            padding: "20px 8px",
            fontFamily: "var(--mono)",
            fontSize: "0.75rem",
            color: "var(--text-muted)",
            textAlign: "center",
          }}>
            No chats found
          </div>
        ) : (
          filteredChats.map((chat) => (
            <ChatItem
              key={chat.id}
              chat={chat}
              active={chat.id === activeChatId}
              onSelect={() => onSelectChat(chat.id)}
              onDelete={() => onDeleteChat(chat.id)}
            />
          ))
        )}
      </div>

      {/* Footer */}
      <div style={{
        borderTop: "1px solid var(--border)",
        padding: "12px 14px",
        flexShrink: 0,
        display: "flex",
        flexDirection: "column",
        gap: 10,
      }}>
        <button
          onClick={() => setShowUpload((v) => !v)}
          style={{
            background: showUpload ? "var(--accent-dim)" : "transparent",
            border: `1px solid ${showUpload ? "rgba(74,222,128,0.3)" : "var(--border)"}`,
            borderRadius: "var(--radius-lg)",
            padding: "8px 12px",
            color: showUpload ? "var(--accent)" : "var(--text-muted)",
            fontFamily: "var(--sans)",
            fontSize: "0.8rem",
            fontWeight: 500,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: 7,
            transition: "all var(--transition)",
            width: "100%",
          }}
          onMouseEnter={(e) => {
            if (!showUpload) {
              e.currentTarget.style.borderColor = "rgba(74,222,128,0.3)";
              e.currentTarget.style.color = "var(--accent)";
            }
          }}
          onMouseLeave={(e) => {
            if (!showUpload) {
              e.currentTarget.style.borderColor = "var(--border)";
              e.currentTarget.style.color = "var(--text-muted)";
            }
          }}
        >
          <Upload size={12} />
          Ingest Document
        </button>

        {showUpload && (
          <div className="animate-fade">
            <FileUpload />
          </div>
        )}

        {/* User row */}
        <div style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "4px 2px 0",
        }}>
          {/* Clickable user info area */}
          <div
            onClick={onOpenProfile}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              overflow: "hidden",
              flex: 1,
              cursor: "pointer",
              borderRadius: "var(--radius)",
              padding: "4px 6px",
              marginLeft: -6,
              transition: "background var(--transition)",
            }}
            onMouseEnter={(e) => e.currentTarget.style.background = "var(--surface-2)"}
            onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}
          >
            {user?.photoURL ? (
              <img
                src={user.photoURL}
                alt={user.displayName}
                style={{
                  width: 30,
                  height: 30,
                  borderRadius: "50%",
                  border: "1px solid var(--border)",
                  flexShrink: 0,
                }}
              />
            ) : (
              <div style={{
                width: 30,
                height: 30,
                borderRadius: "50%",
                background: "var(--accent-dim)",
                border: "1px solid rgba(74,222,128,0.3)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
                fontSize: "0.75rem",
                fontWeight: 600,
                color: "var(--accent)",
              }}>
                {user?.displayName?.[0] || user?.email?.[0] || "U"}
              </div>
            )}
            <div style={{ overflow: "hidden" }}>
              <div style={{
                fontSize: "0.8rem",
                fontWeight: 500,
                color: "var(--text)",
                lineHeight: 1.2,
                whiteSpace: "nowrap",
                overflow: "hidden",
                textOverflow: "ellipsis",
              }}>
                {user?.displayName || "User"}
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                <div style={{
                  width: 5,
                  height: 5,
                  borderRadius: "50%",
                  background: allOk ? "var(--accent)" : "var(--red)",
                  boxShadow: allOk ? "0 0 4px var(--accent)" : "0 0 4px var(--red)",
                  flexShrink: 0,
                }} />
                <span style={{
                  fontFamily: "var(--mono)",
                  fontSize: "0.62rem",
                  color: "var(--text-muted)",
                  whiteSpace: "nowrap",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                }}>
                  {allOk ? "connected" : "disconnected"}
                </span>
              </div>
            </div>
          </div>

          {/* Sign out button */}
          <button
            onClick={logOut}
            title="Sign out"
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
              flexShrink: 0,
            }}
            onMouseEnter={(e) => e.currentTarget.style.color = "var(--red)"}
            onMouseLeave={(e) => e.currentTarget.style.color = "var(--text-muted)"}
          >
            <LogOut size={14} />
          </button>
        </div>
      </div>
    </aside>
  );
}

function ChatItem({ chat, active, onSelect, onDelete }) {
  const [hovered, setHovered] = useState(false);

  return (
    <div
      onClick={onSelect}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        padding: "9px 10px",
        borderRadius: "var(--radius-lg)",
        background: active ? "var(--accent-dim)" : hovered ? "var(--surface-2)" : "transparent",
        border: `1px solid ${active ? "rgba(74,222,128,0.2)" : "transparent"}`,
        cursor: "pointer",
        transition: "all var(--transition)",
        marginBottom: 2,
      }}
    >
      <MessageSquare
        size={12}
        color={active ? "var(--accent)" : "var(--text-muted)"}
        style={{ flexShrink: 0 }}
      />
      <div style={{ flex: 1, overflow: "hidden" }}>
        <div style={{
          fontSize: "0.82rem",
          fontWeight: active ? 500 : 400,
          color: active ? "var(--text)" : "var(--text-secondary)",
          whiteSpace: "nowrap",
          overflow: "hidden",
          textOverflow: "ellipsis",
          lineHeight: 1.3,
        }}>
          {chat.title}
        </div>
        <div style={{
          fontSize: "0.62rem",
          color: "var(--text-muted)",
          fontFamily: "var(--mono)",
          marginTop: 1,
        }}>
          {chat.messages?.length || 0} messages
        </div>
      </div>

      {hovered && (
        <button
          onClick={(e) => { e.stopPropagation(); onDelete(chat.id); }}
          style={{
            background: "transparent",
            border: "none",
            cursor: "pointer",
            padding: 4,
            color: "var(--text-muted)",
            borderRadius: 4,
            display: "flex",
            alignItems: "center",
            transition: "color var(--transition)",
            flexShrink: 0,
          }}
          onMouseEnter={(e) => e.currentTarget.style.color = "var(--red)"}
          onMouseLeave={(e) => e.currentTarget.style.color = "var(--text-muted)"}
        >
          <Trash2 size={11} />
        </button>
      )}
    </div>
  );
}