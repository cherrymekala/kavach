/* Kavach push: shows tracker reminders when the app is closed.
 * The Firebase web config comes in the registration URL (src/lib/push.ts), so this file
 * stays static. Notification messages are shown by the SDK; a tap opens fcm_options.link. */
importScripts('https://www.gstatic.com/firebasejs/12.19.0/firebase-app-compat.js')
importScripts('https://www.gstatic.com/firebasejs/12.19.0/firebase-messaging-compat.js')

const params = new URL(self.location.href).searchParams
firebase.initializeApp({
  apiKey: params.get('apiKey'),
  projectId: params.get('projectId'),
  messagingSenderId: params.get('messagingSenderId'),
  appId: params.get('appId'),
})
firebase.messaging()
