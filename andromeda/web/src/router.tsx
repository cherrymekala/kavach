// oxlint-disable react/only-export-components -- a router file exports config, not components
import { lazy } from 'react'
import { createBrowserRouter } from 'react-router-dom'
import { App } from './App'
import { RequireAuth } from './auth'

// Each route is a self-contained lazy chunk. Screens live in src/screens/<name>/.
const SignIn = lazy(() => import('./screens/auth/SignIn').then((m) => ({ default: m.SignIn })))
const Start = lazy(() => import('./screens/start/Start').then((m) => ({ default: m.Start })))
const Upload = lazy(() => import('./screens/upload/Upload').then((m) => ({ default: m.Upload })))
const Summary = lazy(() => import('./screens/summary/Summary').then((m) => ({ default: m.Summary })))
const Chances = lazy(() => import('./screens/chances/Chances').then((m) => ({ default: m.Chances })))
const Letter = lazy(() => import('./screens/letter/Letter').then((m) => ({ default: m.Letter })))
const Filing = lazy(() => import('./screens/filing/Filing').then((m) => ({ default: m.Filing })))
const Hearing = lazy(() => import('./screens/hearing/Hearing').then((m) => ({ default: m.Hearing })))
const Tracker = lazy(() => import('./screens/tracker/Tracker').then((m) => ({ default: m.Tracker })))
const Outcome = lazy(() => import('./screens/outcome/Outcome').then((m) => ({ default: m.Outcome })))
const Foundation = lazy(() => import('./screens/dev/Foundation').then((m) => ({ default: m.Foundation })))

// Dev-only foundation page — never shipped to production hosting.
const devRoutes = import.meta.env.DEV ? [{ path: 'dev', element: <Foundation /> }] : []

export const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      { index: true, element: <SignIn /> },
      {
        element: <RequireAuth />,
        children: [
          { path: 'start', element: <Start /> },
          { path: 'case/:caseId/upload', element: <Upload /> },
          { path: 'case/:caseId/summary', element: <Summary /> },
          { path: 'case/:caseId/chances', element: <Chances /> },
          { path: 'case/:caseId/letter', element: <Letter /> },
          { path: 'case/:caseId/filing', element: <Filing /> },
          { path: 'case/:caseId/hearing', element: <Hearing /> },
          { path: 'case/:caseId/tracker', element: <Tracker /> },
          { path: 'case/:caseId/outcome', element: <Outcome /> },
        ],
      },
      ...devRoutes,
    ],
  },
])