import { useState, useRef } from "react";
import { Upload, CheckCircle, AlertCircle, Loader } from "lucide-react";
import { incrementDocsIngested } from "../firebase";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
const MAX_FILE_SIZE_MB = 25;
const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;

export default function FileUpload({ user }) {
  const [state, setState] = useState("idle");
  const [message, setMessage] = useState("");
  const inputRef = useRef();

  async function handleFile(file) {
    if (!file) return;

    const isValid = file.name.endsWith(".txt") || file.name.endsWith(".pdf");
    if (!isValid) {
      setState("error");
      setMessage("Only .txt and .pdf files are supported.");
      return;
    }

    if (file.size > MAX_FILE_SIZE_BYTES) {
      setState("error");
      setMessage(`File too large. Maximum size is ${MAX_FILE_SIZE_MB}MB.`);
      return;
    }

    setState("uploading");
    setMessage("");

    const formData = new FormData();
    formData.append("file", file);
    if (user?.uid) {
      formData.append("user_id", user.uid);
    }

    try {
      const token = user ? await user.getIdToken() : null;
      const res = await fetch(`${API_URL}/api/ingest`, {
        method: "POST",
        headers: {
          ...(token && { Authorization: `Bearer ${token}` }),
        },
        body: formData,
      });

      const data = await res.json();

      if (res.ok) {
        setState("success");
        setMessage(`✓ Added ${data.chunks_added} chunks from "${data.filename}"`);

        if (user?.uid) {
          await incrementDocsIngested(user.uid);
        }

        setTimeout(() => setState("idle"), 4000);
      } else {
        setState("error");
        setMessage(data.detail || "Upload failed.");
      }
    } catch (err) {
      setState("error");
      setMessage("Could not reach the backend.");
    }
  }

  function handleDrop(e) {
    e.preventDefault();
    handleFile(e.dataTransfer.files[0]);
  }

  const colors = {
    idle:      { border: "var(--border)",  bg: "transparent" },
    uploading: { border: "var(--accent)",  bg: "var(--accent-dim)" },
    success:   { border: "var(--accent)",  bg: "var(--accent-dim)" },
    error:     { border: "var(--red)",     bg: "var(--red-dim)" },
  };

  const icons = {
    idle:      <Upload size={14} color="var(--text-muted)" />,
    uploading: <Loader size={14} color="var(--accent)"
                 style={{ animation: "spin 1s linear infinite" }} />,
    success:   <CheckCircle size={14} color="var(--accent)" />,
    error:     <AlertCircle size={14} color="var(--red)" />,
  };

  return (
    <>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      <div
        onClick={() => state === "idle" && inputRef.current.click()}
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
        style={{
          border: `1px dashed ${colors[state].border}`,
          background: colors[state].bg,
          borderRadius: "var(--radius)",
          padding: "14px 12px",
          cursor: state === "idle" ? "pointer" : "default",
          transition: "all 0.2s ease",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 8,
          textAlign: "center",
        }}
      >
        {icons[state]}
        <div style={{
          fontFamily: "var(--mono)",
          fontSize: 11,
          color: "var(--text-muted)",
          lineHeight: 1.5,
          whiteSpace: "pre-line",
        }}>
          {state === "idle" && `Click or drop a file\n.txt or .pdf · max ${MAX_FILE_SIZE_MB}MB`}
          {state === "uploading" && "Uploading..."}
          {state === "success" && message}
          {state === "error" && message}
        </div>
      </div>
      <input
        ref={inputRef}
        type="file"
        accept=".txt,.pdf"
        style={{ display: "none" }}
        onChange={(e) => handleFile(e.target.files[0])}
      />
    </>
  );
}