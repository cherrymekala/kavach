import { createBrowserRouter } from 'react-router-dom'
import { App } from './App'
import { Foundation } from './screens/dev/Foundation'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [{ index: true, element: <Foundation /> }],
  },
])