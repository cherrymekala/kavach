import { TooltipProvider } from '@/components/ui/tooltip'
import { DocketRail } from './DocketRail'
import { Dossier } from './Dossier'

/** The workspace shell: docket rail (left) + dossier reading surface (right). */
export function Workspace() {
  return (
    <TooltipProvider>
      <div className="flex h-dvh flex-col overflow-hidden bg-page text-foreground md:flex-row">
        <DocketRail />
        <main className="min-h-0 min-w-0 flex-1 overflow-hidden bg-page">
          <Dossier />
        </main>
      </div>
    </TooltipProvider>
  )
}