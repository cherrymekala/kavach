import { initializeApp, getApp, getApps, type FirebaseApp } from 'firebase/app'
import {
  getAuth,
  RecaptchaVerifier,
  signInWithPhoneNumber,
  type Auth,
  type ConfirmationResult,
} from 'firebase/auth'
import { getFirestore, type Firestore } from 'firebase/firestore'

const config = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
}

export function isConfigured(): boolean {
  return Boolean(import.meta.env.VITE_FIREBASE_API_KEY)
}

export function app(): FirebaseApp {
  if (getApps().length) return getApp()
  if (!isConfigured()) {
    throw new Error('Firebase is not configured. Copy .env.example to .env and set VITE_FIREBASE_* values.')
  }
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

/** Invisible reCAPTCHA verifier — `containerId` must exist in the DOM. */
export function createRecaptchaVerifier(containerId: string): RecaptchaVerifier {
  return new RecaptchaVerifier(auth(), containerId, { size: 'invisible' })
}

/** Send the OTP; resolves with a ConfirmationResult to call `.confirm(code)` on. */
export async function sendOtp(phone: string, verifier: RecaptchaVerifier): Promise<ConfirmationResult> {
  return signInWithPhoneNumber(auth(), phone, verifier)
}

/** Map Firebase auth error codes to user-friendly copy. */
export function mapAuthError(error: unknown): string {
  const code = (error as { code?: string })?.code ?? ''
  switch (code) {
    case 'auth/invalid-phone-number':
      return "That phone number doesn't look right."
    case 'auth/invalid-verification-code':
      return "That code isn't right. Check it and try again."
    case 'auth/code-expired':
      return 'That code expired. Send a new one.'
    case 'auth/too-many-requests':
      return 'Too many attempts. Wait a minute and try again.'
    case 'auth/captcha-check-failed':
      return 'The safety check failed. Please try again.'
    default:
      return 'Could not sign you in. Please try again.'
  }
}