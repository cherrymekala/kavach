import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Navigate, useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { KavachPlates } from '@/components'
import { apiFetch } from '@/api/client'
import { startCaseFromLetter, takeLetter } from '@/lib/pendingLetter'

/** After sign-in from /check: the checked letter becomes the patient's first case, analysed. */
export function CheckContinue() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const started = useRef(false)
  const [letter] = useState(takeLetter)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!letter || started.current) return
    started.current = true
    ;(async () => {
      try {
        const id = await startCaseFromLetter(letter, i18n.language, apiFetch)
        qc.invalidateQueries({ queryKey: ['cases'] })
        navigate(`/case/${id}`, { replace: true })
      } catch (e) {
        setError(e instanceof Error ? e.message : t('check.error'))
      }
    })()
  }, [letter, i18n.language, navigate, qc, t])

  if (!letter) return <Navigate to="/app" replace />
  return (
    <div className="flex min-h-dvh flex-col items-center justify-center gap-5 px-4 text-center" aria-live="polite">
      <KavachPlates size={160} formed={2} />
      <p className="font-display text-xl font-bold tracking-[-0.03em]">{error ? t('check.error') : t('check.saving')}</p>
      {error ? (
        <p className="max-w-[40ch] text-sm text-muted-foreground">
          {error}{' '}
          <a href="/app" className="font-semibold text-brand underline">{t('check.myCases')}</a>
        </p>
      ) : null}
    </div>
  )
}
