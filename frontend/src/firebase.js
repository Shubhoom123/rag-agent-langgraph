import { initializeApp } from "firebase/app";
import { getAuth, GoogleAuthProvider, signInWithPopup, signOut } from "firebase/auth";
import { getFirestore, doc, setDoc, getDoc, collection, getDocs, updateDoc, serverTimestamp, orderBy, query } from "firebase/firestore";

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const db = getFirestore(app);
export const googleProvider = new GoogleAuthProvider();

export async function signInWithGoogle() {
  const result = await signInWithPopup(auth, googleProvider);
  await saveUserProfile(result.user);
  return result.user;
}

export async function logOut() {
  await signOut(auth);
}

// Save or update user profile in Firestore
export async function saveUserProfile(user) {
  const userRef = doc(db, "users", user.uid);
  const existing = await getDoc(userRef);

  if (!existing.exists()) {
    // First time login
    await setDoc(userRef, {
      uid: user.uid,
      email: user.email,
      name: user.displayName,
      photoURL: user.photoURL,
      createdAt: serverTimestamp(),
      lastLoginAt: serverTimestamp(),
    });
  } else {
    // Update last login
    await updateDoc(userRef, {
      lastLoginAt: serverTimestamp(),
    });
  }
}

// Load all chats for a user from Firestore
export async function loadChats(userId) {
  const chatsRef = collection(db, "users", userId, "chats");
  const q = query(chatsRef, orderBy("updatedAt", "desc"));
  const snapshot = await getDocs(q);
  return snapshot.docs.map((doc) => doc.data());
}

// Delete a chat from Firestore
export async function deleteChat(userId, chatId) {
  const { deleteDoc } = await import("firebase/firestore");
  const chatRef = doc(db, "users", userId, "chats", chatId);
  await deleteDoc(chatRef);
}

// Save a chat session to Firestore
export async function saveChat(userId, chat) {
  const chatRef = doc(db, "users", userId, "chats", chat.id);
  await setDoc(chatRef, {
    id: chat.id,
    title: chat.title,
    messages: chat.messages,
    updatedAt: serverTimestamp(),
  });
}

// Save usage stats after each query
export async function saveUsageStats(userId, stats) {
  const userRef = doc(db, "users", userId);
  const existing = await getDoc(userRef);
  const current = existing.data() || {};

  await updateDoc(userRef, {
    totalTokens: (current.totalTokens || 0) + (stats.tokens || 0),
    promptTokens: (current.promptTokens || 0) + (stats.promptTokens || 0),
    completionTokens: (current.completionTokens || 0) + (stats.completionTokens || 0),
    totalQueries: (current.totalQueries || 0) + 1,
    webSearchesUsed: (current.webSearchesUsed || 0) + (stats.webSearchUsed ? 1 : 0),
    lastActiveAt: serverTimestamp(),
  });
}

// Load user profile
export async function loadUserProfile(userId) {
  const userRef = doc(db, "users", userId);
  const snap = await getDoc(userRef);
  return snap.exists() ? snap.data() : null;
}

// Save docs ingested count
export async function incrementDocsIngested(userId) {
  const userRef = doc(db, "users", userId);
  const existing = await getDoc(userRef);
  const current = existing.data() || {};
  await updateDoc(userRef, {
    docsIngested: (current.docsIngested || 0) + 1,
  });
}