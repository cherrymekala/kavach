import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider } from 'react-router-dom'
import './styles/globals.css'
import './i18n'
import { AuthProvider } from './auth'
import { ThemeProvider } from './lib/theme'
import { router } from './router'
import { ApiError } from './api/client'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Don't retry requests we know will fail (404/409/etc.); only retry 5xx/network.
      retry: (failureCount, error) =>
        error instanceof ApiError && error.status < 500 ? false : failureCount < 1,
      staleTime: 30_000,
      refetchOnWindowFocus: false,
    },
  },
})

if (import.meta.env.DEV) {
  // Seed the design-preview case (see router.tsx /preview routes).
  const demo = await import('./dev/demo-case.json')
  const docs = demo.default.documents
  const variants = {
    demo: demo.default,
    'demo-new': { ...demo.default, status: 'collecting', documents: [], facts: null, assessment: null, letter: null, events: [] },
    'demo-docs': { ...demo.default, status: 'collecting', facts: null, assessment: null, letter: null, events: [] },
    'demo-filed': {
      ...demo.default,
      status: 'escalated',
      escalation_step: 1,
      next_deadline: null,
      events: [
        { at: '2026-09-02T09:00:00Z', kind: 'filed', step: 0, text: 'Filed with Insurer grievance cell on 02 Sep 2026. Reply due by 17 Sep 2026.' },
        { at: '2026-09-18T03:30:00Z', kind: 'escalated', step: 1, text: 'No reply from Insurer grievance cell within 15 days. Your Bima Bharosa online complaint for Bima Bharosa complaint is ready to review and file.' },
        { at: '2026-09-20T10:00:00Z', kind: 'rehearsal', step: 1, text: 'Hearing rehearsal: average score 3.4/5.' },
      ],
    },
    'demo-run': { ...demo.default, status: 'analysing', progress: 'Finding the rules that apply', facts: null, assessment: null, letter: null, events: [], documents: docs },
  }
  const packs = { IN: await import('./dev/pack-IN.json'), SG: await import('./dev/pack-SG.json') }
  for (const [code, pack] of Object.entries(packs)) {
    queryClient.setQueryData(['pack', code], pack.default)
  }
  for (const [id, data] of Object.entries(variants)) {
    queryClient.setQueryData(['case', id], data)
    queryClient.setQueryDefaults(['case', id], { staleTime: Infinity })
  }
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ThemeProvider>
      <AuthProvider>
        <QueryClientProvider client={queryClient}>
          <RouterProvider router={router} />
        </QueryClientProvider>
      </AuthProvider>
    </ThemeProvider>
  </StrictMode>,
)