import { useTranslation } from 'react-i18next'
import { KavachPlates, Stepper } from '@/components'
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

/** Pre-discharge checks run a shorter pipeline (agents/discharge.py). */
const DISCHARGE_STEPS = [
  'Reading your documents',
  'Finding the rules that apply',
  'Checking your bill against the policy',
  'Checking every source',
] as const

export function AnalysingPanel({ kase }: { kase: Case }) {
  const { t } = useTranslation()
  const discharge = kase.kind === 'pre_discharge'
  const steps: readonly string[] = discharge ? DISCHARGE_STEPS : STEPS
  const prefix = discharge ? 'discharge.steps' : 'upload.steps'
  const at = steps.indexOf(kase.progress ?? steps[0])
  const current = at >= 0 ? at : 0

  // The shield is the progress bar: plates count finished thirds of the pipeline, and the
  // last plate waits until the analysis is done (the panel is replaced then).
  const formed = Math.min(2, Math.round((current * 3) / steps.length))

  return (
    <section className="flex flex-col gap-8">
      <div className="flex flex-col items-center gap-4 text-center">
        <KavachPlates size={190} formed={formed} />
        <p className="text-sm font-semibold text-muted-foreground" aria-live="polite">
          {t('upload.stepOf', { current: current + 1, total: steps.length })}
        </p>
        <h2 className="max-w-[22ch] font-display text-2xl leading-tight font-bold tracking-[-0.03em]">
          {t(`${prefix}.${current}.label`)}
        </h2>
        <p className="max-w-[44ch] text-sm leading-relaxed text-muted-foreground">{t('upload.analysingSub')}</p>
      </div>
      <Stepper
        steps={steps.map((_s, i) => ({
          label: t(`${prefix}.${i}.label`),
          detail: i === current ? t(`${prefix}.${i}.detail`) : undefined,
        }))}
        current={current}
      />
    </section>
  )
}