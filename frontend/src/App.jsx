import { useState, useEffect } from "react";
import Sidebar from "./components/Sidebar";
import ChatWindow from "./components/ChatWindow";
import "./index.css";

function generateId() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2);
}

function createChat() {
  return { id: generateId(), title: "New Chat", messages: [] };
}

export default function App() {
  const [chats, setChats] = useState([createChat()]);
  const [activeChatId, setActiveChatId] = useState(chats[0].id);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setMounted(true), 50);
    return () => clearTimeout(t);
  }, []);

  const activeChat = chats.find((c) => c.id === activeChatId) || chats[0];

  function setMessages(updater) {
    setChats((prev) =>
      prev.map((c) => {
        if (c.id !== activeChatId) return c;
        const newMessages =
          typeof updater === "function" ? updater(c.messages) : updater;

        // Auto-title from first user message
        const firstUser = newMessages.find((m) => m.role === "user");
        const title =
          firstUser && c.title === "New Chat"
            ? firstUser.text.slice(0, 36) + (firstUser.text.length > 36 ? "…" : "")
            : c.title;

        return { ...c, messages: newMessages, title };
      })
    );
  }

  function newChat() {
    const chat = createChat();
    setChats((prev) => [chat, ...prev]);
    setActiveChatId(chat.id);
  }

  function deleteChat(id) {
    setChats((prev) => {
      const next = prev.filter((c) => c.id !== id);
      if (next.length === 0) {
        const fresh = createChat();
        setActiveChatId(fresh.id);
        return [fresh];
      }
      if (id === activeChatId) {
        setActiveChatId(next[0].id);
      }
      return next;
    });
  }

  return (
    <div style={{
      display: "flex",
      height: "100vh",
      background: "var(--bg)",
      overflow: "hidden",
      opacity: mounted ? 1 : 0,
      transform: mounted ? "translateY(0)" : "translateY(6px)",
      transition: "opacity 0.4s ease, transform 0.4s ease",
    }}>
      <Sidebar
        status={status}
        setStatus={setStatus}
        chats={chats}
        activeChatId={activeChatId}
        onSelectChat={setActiveChatId}
        onNewChat={newChat}
        onDeleteChat={deleteChat}
      />
      <ChatWindow
        key={activeChatId}
        messages={activeChat.messages}
        setMessages={setMessages}
        loading={loading}
        setLoading={setLoading}
      />
    </div>
  );
}