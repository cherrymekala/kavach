import type { DischargeCheck } from '@/api/types'
import { DischargePanel } from '@/screens/workspace/Panels/DischargePanel'
import demo from './demo-discharge.json'

/** Dev-only: the pre-discharge panel with a real pipeline result (whirlpool/discharge/in_d01). */
export function DischargePreview() {
  return (
    <div className="mx-auto w-full max-w-[760px] px-5 py-8">
      <DischargePanel check={demo as DischargeCheck} />
    </div>
  )
}
