import { app } from '@/firebase'
import { apiFetch } from '@/api/client'

/** Web push for tracker reminders (backend: sombrero/src/kavach/tools/push.py). */

const VAPID_KEY = import.meta.env.VITE_FIREBASE_VAPID_KEY ?? ''
const STORAGE_KEY = 'kavach-push-token'

export type PushState = 'unsupported' | 'blocked' | 'off' | 'on'

function stored(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY)
  } catch {
    return null
  }
}

function remember(token: string | null) {
  try {
    if (token) localStorage.setItem(STORAGE_KEY, token)
    else localStorage.removeItem(STORAGE_KEY)
  } catch {
    /* private mode: the switch just shows "off" next time */
  }
}

/** Where this browser stands. iPhones only allow push once the app is on the home screen. */
export async function pushState(): Promise<PushState> {
  if (!VAPID_KEY || !('Notification' in window) || !('serviceWorker' in navigator)) return 'unsupported'
  const { isSupported } = await import('firebase/messaging')
  if (!(await isSupported())) return 'unsupported'
  if (Notification.permission === 'denied') return 'blocked'
  return Notification.permission === 'granted' && stored() ? 'on' : 'off'
}

function workerUrl(): string {
  const o = app().options
  const q = new URLSearchParams({
    apiKey: o.apiKey ?? '',
    projectId: o.projectId ?? '',
    messagingSenderId: o.messagingSenderId ?? '',
    appId: o.appId ?? '',
  })
  return `/firebase-messaging-sw.js?${q}`
}

/** Ask permission (must run from a tap), get this device's token and register it. */
export async function enablePush(): Promise<PushState> {
  const permission = await Notification.requestPermission()
  if (permission !== 'granted') return permission === 'denied' ? 'blocked' : 'off'
  const { getMessaging, getToken } = await import('firebase/messaging')
  const registration = await navigator.serviceWorker.register(workerUrl(), {
    scope: '/firebase-cloud-messaging-push-scope',
  })
  const token = await getToken(getMessaging(app()), {
    vapidKey: VAPID_KEY,
    serviceWorkerRegistration: registration,
  })
  await apiFetch('/push/tokens', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token }),
  })
  remember(token)
  return 'on'
}

export async function disablePush(): Promise<PushState> {
  const token = stored()
  if (token) {
    await apiFetch('/push/tokens/remove', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token }),
    })
    const { deleteToken, getMessaging } = await import('firebase/messaging')
    await deleteToken(getMessaging(app())).catch(() => undefined)
  }
  remember(null)
  return 'off'
}
