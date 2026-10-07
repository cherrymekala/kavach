// oxlint-disable react/only-export-components -- a router file exports config, not components
import { lazy } from 'react'
import { createBrowserRouter } from 'react-router-dom'
import { App } from './App'

const SignIn = lazy(() => import('./screens/auth/SignIn').then((m) => ({ default: m.SignIn })))
const Start = lazy(() => import('./screens/start/Start').then((m) => ({ default: m.Start })))
const Foundation = lazy(() => import('./screens/dev/Foundation').then((m) => ({ default: m.Foundation })))

export const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      { index: true, element: <SignIn /> },
      { path: 'start', element: <Start /> },
      { path: 'dev', element: <Foundation /> },
    ],
  },
])