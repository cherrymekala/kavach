# andromeda: web app

Responsive PWA for phones and desktop, hosted on Firebase Hosting.

Owner picks the framework (Next.js or Flutter Web) and scaffolds here. Starting points:

- `prototype/Kavach_Prototype.html`: the clickable flow, 9 screens
- `../sombrero/src/kavach/models.py`: API contract (Case, Document, Assessment)
- Live progress: subscribe to `cases/{id}` in Firestore and show `progress`
- Auth: Firebase phone login; send the ID token as `Authorization: Bearer <token>`
