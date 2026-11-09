import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useRouteError } from 'react-router-dom'
import { RotateCwIcon } from 'lucide-react'
import { Button, KavachMark } from '@/components'

/**
 * Shown instead of React Router's raw "Unexpected Application Error" when a screen crashes.
 * The case itself is safe on the server, so a reload or going back to the cases list is enough.
 */
export function RouteError() {
  const { t } = useTranslation()
  const error = useRouteError()

  useEffect(() => {
    console.error('[kavach] screen crashed', error)
  }, [error])

  const detail = error instanceof Error ? error.message : String(error ?? '')

  return (
    <main className="flex min-h-dvh items-center justify-center bg-background px-4 py-10 text-foreground">
      <div className="flex w-full max-w-sm flex-col items-center gap-5 text-center">
        <KavachMark className="h-14 text-brand" />
        <div>
          <h1 className="font-display text-2xl leading-tight font-bold tracking-[-0.03em]">{t('crash.title')}</h1>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{t('crash.sub')}</p>
        </div>
        <div className="flex w-full flex-col gap-2 sm:flex-row sm:justify-center">
          <Button className="h-11" onClick={() => window.location.reload()}>
            <RotateCwIcon aria-hidden />
            {t('crash.reload')}
          </Button>
          <Button variant="outline" className="h-11" onClick={() => window.location.assign('/app')}>
            {t('crash.home')}
          </Button>
        </div>
        {detail ? (
          <details className="w-full text-left text-xs text-muted-foreground">
            <summary className="cursor-pointer text-center">{t('crash.details')}</summary>
            <p className="mt-2 rounded-xl bg-muted/60 p-3 font-mono break-words">{detail}</p>
          </details>
        ) : null}
      </div>
    </main>
  )
}
