import { initializeApp, getApp, getApps, type FirebaseApp } from 'firebase/app'
import { getAuth, type Auth } from 'firebase/auth'
import { getFirestore, type Firestore } from 'firebase/firestore'

const config = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
}

export function app(): FirebaseApp {
  if (getApps().length) return getApp()
  return initializeApp(config)
}

export function auth(): Auth {
  return getAuth(app())
}

export function db(): Firestore {
  return getFirestore(app())
}

/** Current user's Firebase ID token, or null when signed out. */
export async function getIdToken(): Promise<string | null> {
  const user = auth().currentUser
  return user ? user.getIdToken() : null
}