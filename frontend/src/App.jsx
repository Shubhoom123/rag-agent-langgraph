import { useState, useEffect } from "react";
import { onAuthStateChanged } from "firebase/auth";
import { auth } from "./firebase";
import Sidebar from "./components/Sidebar";
import ChatWindow from "./components/ChatWindow";
import LoginPage from "./components/LoginPage";
import "./index.css";
import { saveChat, loadChats, deleteChat as deleteChatFromFirestore } from "./firebase";

function generateId() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2);
}
function createChat() {
  return { id: generateId(), title: "New Chat", messages: [] };
}

export default function App() {
  const [user, setUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [chats, setChats] = useState([createChat()]);
  const [activeChatId, setActiveChatId] = useState(chats[0].id);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState(null);
  const [mounted, setMounted] = useState(false);

  // Listen to Firebase auth state and load chats on login
  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (firebaseUser) => {
      setUser(firebaseUser);
      if (firebaseUser) {
        try {
          const saved = await loadChats(firebaseUser.uid);
          if (saved.length > 0) {
            setChats(saved);
            setActiveChatId(saved[0].id);
          }
        } catch (err) {
          console.error("Failed to load chats:", err);
        }
      } else {
        // Reset on logout
        const fresh = createChat();
        setChats([fresh]);
        setActiveChatId(fresh.id);
      }
      setAuthLoading(false);
    });
    return () => unsubscribe();
  }, []);

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
        const firstUser = newMessages.find((m) => m.role === "user");
        const title =
          firstUser && c.title === "New Chat"
            ? firstUser.text.slice(0, 36) + (firstUser.text.length > 36 ? "…" : "")
            : c.title;
        const updatedChat = { ...c, messages: newMessages, title };
  
        // Save to Firestore
        if (user?.uid) {
          saveChat(user.uid, updatedChat).catch(console.error);
        }
  
        return updatedChat;
      })
    );
  }

  function newChat() {
    const chat = createChat();
    setChats((prev) => [chat, ...prev]);
    setActiveChatId(chat.id);
  }

  function deleteChat(id) {
    // Delete from Firestore
    if (user?.uid) {
      deleteChatFromFirestore(user.uid, id).catch(console.error);
    }
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

  // Show nothing while checking auth state
  if (authLoading) {
    return (
      <div style={{
        height: "100vh",
        background: "#000000",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}>
        <div style={{
          width: 32,
          height: 32,
          border: "2px solid #1f1f1f",
          borderTopColor: "#4ade80",
          borderRadius: "50%",
          animation: "spin 0.8s linear infinite",
        }} />
      </div>
    );
  }

  // Show login page if not authenticated
  if (!user) {
    return <LoginPage />;
  }

  // Show main app if authenticated
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
        user={user}
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
        user={user}
        messages={activeChat.messages}
        setMessages={setMessages}
        loading={loading}
        setLoading={setLoading}
      />
    </div>
  );
}