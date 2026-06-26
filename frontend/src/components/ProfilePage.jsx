import { useEffect, useState } from "react";
import { X, FileText, Mail, Calendar, Zap } from "lucide-react";
import { loadUserProfile } from "../firebase";

function formatDate(ts) {
  if (!ts) return "—";
  const date = ts.toDate ? ts.toDate() : new Date(ts);
  return date.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
}

function formatNumber(n) {
  if (!n) return "0";
  if (n >= 1000000) return (n / 1000000).toFixed(1) + "M";
  if (n >= 1000) return (n / 1000).toFixed(1) + "K";
  return n.toString();
}

export default function ProfilePage({ user, chats, onClose }) {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (user?.uid) {
      loadUserProfile(user.uid)
        .then(setProfile)
        .catch(console.error)
        .finally(() => setLoading(false));
    }
  }, [user?.uid]);

  const promptTokens = profile?.promptTokens || 0;
  const completionTokens = profile?.completionTokens || 0;
  const totalTokens = profile?.totalTokens || 0;
  const promptPct = totalTokens ? Math.round((promptTokens / totalTokens) * 100) : 0;
  const completionPct = totalTokens ? Math.round((completionTokens / totalTokens) * 100) : 0;

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        style={{
          position: "fixed",
          inset: 0,
          background: "rgba(0,0,0,0.6)",
          backdropFilter: "blur(4px)",
          zIndex: 40,
          animation: "fadeIn 0.2s ease",
        }}
      />

      {/* Panel */}
      <div style={{
        position: "fixed",
        top: 0,
        left: 0,
        width: 380,
        height: "100vh",
        background: "var(--surface)",
        borderRight: "1px solid var(--border)",
        zIndex: 50,
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
        animation: "slideInLeft 0.25s cubic-bezier(0.16, 1, 0.3, 1)",
      }}>

        {/* Header */}
        <div style={{
          padding: "20px 20px 16px",
          borderBottom: "1px solid var(--border)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexShrink: 0,
        }}>
          <div style={{
            fontSize: "0.95rem",
            fontWeight: 600,
            color: "var(--text)",
            letterSpacing: "-0.01em",
          }}>
            Profile
          </div>
          <button
            onClick={onClose}
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
            onMouseEnter={(e) => e.currentTarget.style.color = "var(--text)"}
            onMouseLeave={(e) => e.currentTarget.style.color = "var(--text-muted)"}
          >
            <X size={16} />
          </button>
        </div>

        {/* Content */}
        <div style={{ flex: 1, overflowY: "auto", padding: "24px 20px" }}>
          {loading ? (
            <div style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              height: 200,
            }}>
              <div style={{
                width: 24,
                height: 24,
                border: "2px solid var(--border)",
                borderTopColor: "var(--accent)",
                borderRadius: "50%",
                animation: "spin 0.8s linear infinite",
              }} />
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>

              {/* Avatar + info */}
              <div style={{
                display: "flex",
                alignItems: "center",
                gap: 16,
                padding: "20px",
                background: "var(--surface-2)",
                border: "1px solid var(--border)",
                borderRadius: "var(--radius-lg)",
              }}>
                {user?.photoURL ? (
                  <img
                    src={user.photoURL}
                    alt={user.displayName}
                    style={{
                      width: 64,
                      height: 64,
                      borderRadius: "50%",
                      border: "2px solid rgba(74,222,128,0.3)",
                      flexShrink: 0,
                    }}
                  />
                ) : (
                  <div style={{
                    width: 64,
                    height: 64,
                    borderRadius: "50%",
                    background: "rgba(74,222,128,0.08)",
                    border: "2px solid rgba(74,222,128,0.3)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flexShrink: 0,
                    fontSize: "1.5rem",
                    fontWeight: 600,
                    color: "var(--accent)",
                  }}>
                    {user?.displayName?.[0] || "U"}
                  </div>
                )}
                <div style={{ overflow: "hidden" }}>
                  <div style={{
                    fontSize: "1.05rem",
                    fontWeight: 600,
                    color: "var(--text)",
                    letterSpacing: "-0.01em",
                    marginBottom: 4,
                    whiteSpace: "nowrap",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                  }}>
                    {user?.displayName || "User"}
                  </div>
                  <div style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 6,
                    marginBottom: 4,
                  }}>
                    <Mail size={11} color="var(--text-muted)" />
                    <span style={{
                      fontSize: "0.78rem",
                      color: "var(--text-muted)",
                      fontFamily: "var(--mono)",
                      whiteSpace: "nowrap",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                    }}>
                      {user?.email}
                    </span>
                  </div>
                  <div style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 6,
                  }}>
                    <Calendar size={11} color="var(--text-muted)" />
                    <span style={{
                      fontSize: "0.72rem",
                      color: "var(--text-muted)",
                      fontFamily: "var(--mono)",
                    }}>
                      Joined {formatDate(profile?.createdAt)}
                    </span>
                  </div>
                </div>
              </div>

              {/* Account info */}
              <div>
                <div style={{
                  fontFamily: "var(--mono)",
                  fontSize: "0.6rem",
                  color: "var(--text-muted)",
                  letterSpacing: "0.08em",
                  textTransform: "uppercase",
                  marginBottom: 12,
                }}>
                  Account
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {[
                    { label: "Last active", value: formatDate(profile?.lastActiveAt || profile?.lastLoginAt) },
                    { label: "Model", value: "openai/gpt-oss-20b" },
                  ].map(({ label, value }) => (
                    <div key={label} style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      padding: "10px 14px",
                      background: "var(--surface-2)",
                      border: "1px solid var(--border)",
                      borderRadius: "var(--radius)",
                    }}>
                      <span style={{
                        fontSize: "0.78rem",
                        color: "var(--text-muted)",
                        fontFamily: "var(--mono)",
                      }}>
                        {label}
                      </span>
                      <span style={{
                        fontSize: "0.78rem",
                        color: "var(--text)",
                        fontFamily: "var(--mono)",
                        fontWeight: 500,
                      }}>
                        {value}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Token usage bar */}
              <div>
                <div style={{
                  fontFamily: "var(--mono)",
                  fontSize: "0.6rem",
                  color: "var(--text-muted)",
                  letterSpacing: "0.08em",
                  textTransform: "uppercase",
                  marginBottom: 12,
                }}>
                  Token Usage
                </div>
                <div style={{
                  background: "var(--surface-2)",
                  border: "1px solid var(--border)",
                  borderRadius: "var(--radius-lg)",
                  padding: "16px",
                  display: "flex",
                  flexDirection: "column",
                  gap: 14,
                }}>
                  {/* Total count */}
                  <div style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "baseline",
                  }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                      <Zap size={13} color="var(--accent)" />
                      <span style={{
                        fontSize: "0.75rem",
                        color: "var(--text-muted)",
                        fontFamily: "var(--mono)",
                      }}>
                        Total tokens used
                      </span>
                    </div>
                    <span style={{
                      fontSize: "1.1rem",
                      fontWeight: 600,
                      color: "var(--accent)",
                      fontFamily: "var(--mono)",
                      letterSpacing: "-0.02em",
                    }}>
                      {formatNumber(totalTokens)}
                    </span>
                  </div>

                  {/* Stacked bar */}
                  <div style={{
                    height: 8,
                    background: "var(--border)",
                    borderRadius: 4,
                    overflow: "hidden",
                    display: "flex",
                  }}>
                    <div style={{
                      height: "100%",
                      width: `${promptPct}%`,
                      background: "rgba(74,222,128,0.5)",
                      transition: "width 0.6s ease",
                    }} />
                    <div style={{
                      height: "100%",
                      width: `${completionPct}%`,
                      background: "var(--accent)",
                      transition: "width 0.6s ease",
                    }} />
                  </div>

                  {/* Legend */}
                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    {[
                      { label: "Input Tokens", value: promptTokens, pct: promptPct, color: "rgba(74,222,128,0.5)" },
                      { label: "Output Tokens", value: completionTokens, pct: completionPct, color: "var(--accent)" },
                    ].map(({ label, value, pct, color }) => (
                      <div key={label} style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                      }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                          <div style={{
                            width: 8,
                            height: 8,
                            borderRadius: 2,
                            background: color,
                            flexShrink: 0,
                          }} />
                          <span style={{
                            fontSize: "0.72rem",
                            color: "var(--text-muted)",
                            fontFamily: "var(--mono)",
                          }}>
                            {label}
                          </span>
                        </div>
                        <span style={{
                          fontSize: "0.72rem",
                          color: "var(--text-secondary)",
                          fontFamily: "var(--mono)",
                        }}>
                          {formatNumber(value)} ({pct}%)
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Docs ingested */}
              <div>
                <div style={{
                  fontFamily: "var(--mono)",
                  fontSize: "0.6rem",
                  color: "var(--text-muted)",
                  letterSpacing: "0.08em",
                  textTransform: "uppercase",
                  marginBottom: 12,
                }}>
                  Documents
                </div>
                <div style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "16px",
                  background: "var(--surface-2)",
                  border: "1px solid var(--border)",
                  borderRadius: "var(--radius-lg)",
                  transition: "border-color var(--transition)",
                }}
                  onMouseEnter={(e) => e.currentTarget.style.borderColor = "rgba(74,222,128,0.25)"}
                  onMouseLeave={(e) => e.currentTarget.style.borderColor = "var(--border)"}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <div style={{
                      width: 32,
                      height: 32,
                      borderRadius: "var(--radius)",
                      background: "rgba(74,222,128,0.08)",
                      border: "1px solid rgba(74,222,128,0.15)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                    }}>
                      <FileText size={14} color="var(--accent)" />
                    </div>
                    <div>
                      <div style={{
                        fontSize: "0.78rem",
                        color: "var(--text)",
                        fontFamily: "var(--mono)",
                        fontWeight: 500,
                      }}>
                        Docs ingested
                      </div>
                      <div style={{
                        fontSize: "0.65rem",
                        color: "var(--text-muted)",
                        fontFamily: "var(--mono)",
                      }}>
                        into vector store
                      </div>
                    </div>
                  </div>
                  <div style={{
                    fontSize: "1.6rem",
                    fontWeight: 600,
                    color: "var(--text)",
                    letterSpacing: "-0.02em",
                    fontFamily: "var(--mono)",
                  }}>
                    {formatNumber(profile?.docsIngested)}
                  </div>
                </div>
              </div>

            </div>
          )}
        </div>
      </div>

      <style>{`
        @keyframes slideInLeft {
          from { transform: translateX(-100%); opacity: 0; }
          to { transform: translateX(0); opacity: 1; }
        }
      `}</style>
    </>
  );
}