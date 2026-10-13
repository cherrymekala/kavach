import { useTranslation } from 'react-i18next'
import { Stepper } from '@/components'
import type { Case } from '@/api/types'

/** The analysis progress, in order (sombrero/src/kavach/agents/orchestrator.py). */
const STEPS = [
  'Reading your documents',
  'Decoding the rejection',
  'Finding the rules that apply',
  'Looking up similar past cases',
  'Building your case',
  'Checking every source',
  'Writing your appeal',
] as const

export function AnalysingPanel({ kase }: { kase: Case }) {
  const { t } = useTranslation()
  const progress = kase.progress ?? STEPS[0]
  const at = STEPS.indexOf(progress as (typeof STEPS)[number])
  const current = at >= 0 ? at : 0

  return (
    <section className="flex flex-col gap-4">
      <div>
        <h2 className="font-display text-xl font-bold">{t('upload.analysingHeading')}</h2>
        <p className="mt-1 max-w-[60ch] text-sm text-muted-foreground">{t('upload.analysingSub')}</p>
      </div>
      <Stepper
        steps={STEPS.map((_s, i) => ({
          label: t(`upload.steps.${i}.label`),
          detail: i === current ? t(`upload.steps.${i}.detail`) : undefined,
        }))}
        current={current}
      />
    </section>
  )
}