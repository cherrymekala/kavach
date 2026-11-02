import { useTranslation } from 'react-i18next'
import { Stepper, ShieldHero } from '@/components'
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

  return (
    <section className="flex flex-col gap-8">
      <ShieldHero footer={t('upload.analysingSub')}>{t('upload.analysingHeading')}</ShieldHero>
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