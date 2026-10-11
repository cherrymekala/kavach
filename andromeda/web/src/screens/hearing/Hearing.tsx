import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ChevronDownIcon, MicIcon, SparklesIcon } from 'lucide-react'
import { AppHeader, Button, ChatBubble, FooterCTA } from '@/components'
import { cn } from '@/lib/cn'

const SAMPLE_QA = [
  {
    q: 'Why was your claim rejected, in your own words?',
    a: 'Start with the reason on your letter, then say why you disagree with one plain sentence.',
  },
  {
    q: 'When did you first notice this condition?',
    a: 'Give the exact date on your discharge summary. Do not guess or fill in blanks.',
  },
  {
    q: 'Have you made this claim before?',
    a: 'Answer only yes or no, then stop. Offer details only if asked.',
  },
] as const

export function Hearing() {
  const { caseId } = useParams()
  const navigate = useNavigate()
  const { t } = useTranslation()
  const [open, setOpen] = useState<number | null>(null)

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-6">
      <AppHeader title={t('hearing.title')} />

      <section className="flex flex-col gap-3 rounded-2xl border border-border bg-card p-5">
        <div className="flex items-center gap-3">
          <span className="grid size-10 place-items-center rounded-full bg-accent text-accent-foreground">
            <MicIcon className="size-5" aria-hidden />
          </span>
          <div>
            <h3 className="font-display font-bold">{t('hearing.intro')}</h3>
            <p className="text-sm text-muted-foreground">{t('hearing.introSub')}</p>
          </div>
        </div>
        <Button variant="outline" disabled className="w-full">
          <SparklesIcon className="size-4" aria-hidden />
          {t('hearing.voiceComingSoon')}
        </Button>
      </section>

      <section className="flex flex-col gap-3">
        <h3 className="font-display text-base font-bold">{t('hearing.tips')}</h3>
        <div className="flex flex-col gap-2">
          {[t('hearing.tip1'), t('hearing.tip2'), t('hearing.tip3')].map((tip, i) => (
            <div key={tip} className="flex items-start gap-3 rounded-xl border border-border bg-card p-4">
              <span className="font-display text-lg font-extrabold text-brand">{i + 1}</span>
              <p className="text-sm">{tip}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="flex flex-col gap-3">
        <h3 className="font-display text-base font-bold">{t('hearing.practice')}</h3>
        <div className="flex flex-col gap-2">
          {SAMPLE_QA.map((item, i) => (
            <div key={item.q} className="overflow-hidden rounded-xl border border-border bg-card">
              <button
                type="button"
                onClick={() => setOpen(open === i ? null : i)}
                className="flex w-full items-center justify-between gap-3 p-4 text-left"
              >
                <span className="text-sm font-semibold">{item.q}</span>
                <ChevronDownIcon
                  className={cn('size-4 shrink-0 text-muted-foreground transition-transform', open === i && 'rotate-180')}
                  aria-hidden
                />
              </button>
              {open === i ? (
                <div className="border-t border-border p-4">
                  <ChatBubble role="coach">{item.a}</ChatBubble>
                </div>
              ) : null}
            </div>
          ))}
        </div>
      </section>

      <FooterCTA
        primary={{ label: t('hearing.cta'), onClick: () => navigate(`/case/${caseId}/tracker`) }}
      />
    </div>
  )
}