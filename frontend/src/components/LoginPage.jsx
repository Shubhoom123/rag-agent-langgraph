import { useState } from "react";
import { signInWithGoogle } from "../firebase";

export default function LoginPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleGoogleSignIn() {
    setLoading(true);
    setError("");
    try {
      await signInWithGoogle();
    } catch (err) {
      setError("Sign in failed. Please try again.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{
      height: "100vh",
      background: "#000000",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      fontFamily: "var(--sans)",
    }}>
      {/* Background glow */}
      <div style={{
        position: "absolute",
        width: 600,
        height: 600,
        borderRadius: "50%",
        background: "radial-gradient(circle, rgba(74,222,128,0.06) 0%, transparent 70%)",
        pointerEvents: "none",
      }} />

      <div style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 32,
        zIndex: 1,
        width: "100%",
        maxWidth: 400,
        padding: "0 24px",
      }}>
        {/* Logo */}
        <div style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 16,
          marginTop: -20,
        }}>
          <img
            src="/dragon-favicon.svg"
            alt="d-RAG-on logo"
            style={{
              width: 300,
              height: 300,
              objectFit: "contain",
              filter: "drop-shadow(0 0 12px rgba(74,222,128,0.8)) drop-shadow(0 0 30px rgba(74,222,128,0.4)) drop-shadow(0 0 60px rgba(74,222,128,0.2))",
              animation: "glowPulse 3s ease-in-out infinite",
            }}
          />
          <div style={{ textAlign: "center" }}>
            <div style={{
              fontSize: "1.6rem",
              fontWeight: 600,
              color: "#f0f0f0",
              letterSpacing: "-0.02em",
              marginBottom: 6,
            }}>
              d-RAG-on
            </div>
          </div>
        </div>

        {/* Card */}
        <div style={{
          width: "100%",
          background: "#0a0a0a",
          border: "1px solid #1f1f1f",
          borderRadius: 16,
          padding: "28px 24px",
          display: "flex",
          flexDirection: "column",
          gap: 16,
        }}>
          <div style={{
            fontSize: "0.95rem",
            fontWeight: 500,
            color: "#f0f0f0",
            textAlign: "center",
            marginBottom: 4,
          }}>
            Sign in to continue
          </div>

          {/* Google Sign In Button */}
          <button
            onClick={handleGoogleSignIn}
            disabled={loading}
            style={{
              width: "100%",
              padding: "12px 16px",
              background: loading ? "#111111" : "#ffffff",
              border: "1px solid #1f1f1f",
              borderRadius: 10,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 12,
              cursor: loading ? "not-allowed" : "pointer",
              transition: "all 180ms ease",
              fontSize: "0.9rem",
              fontWeight: 500,
              color: loading ? "#555" : "#000000",
              fontFamily: "var(--sans)",
            }}
            onMouseEnter={(e) => {
              if (!loading) e.currentTarget.style.background = "#f0f0f0";
            }}
            onMouseLeave={(e) => {
              if (!loading) e.currentTarget.style.background = "#ffffff";
            }}
          >
            {loading ? (
              <div style={{
                width: 18,
                height: 18,
                border: "2px solid #333",
                borderTopColor: "#4ade80",
                borderRadius: "50%",
                animation: "spin 0.8s linear infinite",
              }} />
            ) : (
              <svg width="18" height="18" viewBox="0 0 18 18">
                <path fill="#4285F4" d="M16.51 8H8.98v3h4.3c-.18 1-.74 1.48-1.6 2.04v2.01h2.6a7.8 7.8 0 0 0 2.38-5.88c0-.57-.05-.66-.15-1.18z"/>
                <path fill="#34A853" d="M8.98 17c2.16 0 3.97-.72 5.3-1.94l-2.6-2a4.8 4.8 0 0 1-7.18-2.54H1.83v2.07A8 8 0 0 0 8.98 17z"/>
                <path fill="#FBBC05" d="M4.5 10.52a4.8 4.8 0 0 1 0-3.04V5.41H1.83a8 8 0 0 0 0 7.18z"/>
                <path fill="#EA4335" d="M8.98 4.18c1.17 0 2.23.4 3.06 1.2l2.3-2.3A8 8 0 0 0 1.83 5.4L4.5 7.49a4.77 4.77 0 0 1 4.48-3.3z"/>
              </svg>
            )}
            {loading ? "Signing in..." : "Continue with Google"}
          </button>

          {error && (
            <div style={{
              padding: "8px 12px",
              background: "rgba(248,113,113,0.08)",
              border: "1px solid rgba(248,113,113,0.2)",
              borderRadius: 8,
              color: "#f87171",
              fontSize: "0.8rem",
              textAlign: "center",
              fontFamily: "var(--mono)",
            }}>
              {error}
            </div>
          )}
        </div>

        <div style={{
          fontSize: "0.72rem",
          color: "#555",
          textAlign: "center",
          fontFamily: "var(--mono)",
          lineHeight: 1.6,
        }}>
          Self-correcting RAG · Wikipedia aware · Web fallback
        </div>
      </div>
    </div>
  );
}