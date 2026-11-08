import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQueryClient } from '@tanstack/react-query'
import { CheckCircle2Icon, KeyboardIcon, MicIcon, MicOffIcon, SendIcon } from 'lucide-react'
import {
  Button,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  Input,
  KavachMark,
} from '@/components'
import { caseKey } from '@/api/hooks'
import { useVoiceIntake } from '@/api/voiceIntake'
import { cn } from '@/lib/cn'

/**
 * "Tell us by voice": a short spoken interview in the patient's language (Gemini Live). The
 * transcript is saved to the case as a document, so the analysis reads it with any uploads.
 */
export function VoiceIntakeDialog({ caseId, open, onClose }: { caseId: string; open: boolean; onClose: () => void }) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const voice = useVoiceIntake(caseId)
  const [typing, setTyping] = useState(false)
  const [draft, setDraft] = useState('')
  const bottom = useRef<HTMLDivElement>(null)
  const { start, cleanup, state, saved } = voice

  // Opening the dialog starts the conversation; closing it ends the connection.
  useEffect(() => {
    if (open) void start()
    return () => cleanup()
  }, [open, start, cleanup])

  useEffect(() => bottom.current?.scrollIntoView({ block: 'end' }), [voice.lines])

  useEffect(() => {
    if (state === 'saved') queryClient.invalidateQueries({ queryKey: caseKey(caseId) })
  }, [state, caseId, queryClient])

  const live = state === 'live'

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="flex max-h-[90dvh] flex-col">
        <DialogHeader>
          <DialogTitle>{t('voice.title')}</DialogTitle>
          <DialogDescription>{t('voice.sub')}</DialogDescription>
        </DialogHeader>

        {state === 'saved' ? (
          <div className="flex flex-col items-center gap-3 py-6 text-center">
            <CheckCircle2Icon className="size-10 text-mint" aria-hidden />
            <p className="font-display text-xl font-bold tracking-[-0.03em]">
              {saved ? t('voice.saved') : t('voice.notSaved')}
            </p>
            <p className="max-w-[36ch] text-sm text-muted-foreground">{saved ? t('voice.savedSub') : t('voice.notSavedSub')}</p>
            <Button className="mt-2" onClick={onClose}>
              {t('voice.close')}
            </Button>
          </div>
        ) : (
          <>
            <div className="flex min-h-48 flex-1 flex-col gap-2 overflow-y-auto rounded-2xl bg-muted/50 p-3" aria-live="polite">
              {voice.lines.length === 0 ? (
                <p className="m-auto flex items-center gap-2 text-sm text-muted-foreground">
                  <KavachMark className="h-5 text-brand" />
                  {state === 'error' ? t('voice.error') : t('voice.connecting')}
                </p>
              ) : (
                voice.lines.map((l) => (
                  <p
                    key={l.id}
                    className={cn(
                      'max-w-[85%] rounded-[18px] px-3.5 py-2.5 text-[15px] leading-relaxed',
                      l.who === 'you'
                        ? 'self-end rounded-br-md bg-primary text-primary-foreground'
                        : 'self-start rounded-bl-md bg-card',
                    )}
                  >
                    {l.text}
                  </p>
                ))
              )}
              <div ref={bottom} />
            </div>

            {voice.error === 'mic' ? <p className="text-sm text-muted-foreground">{t('voice.noMic')}</p> : null}
            {live && voice.yourTurn ? <p className="text-center text-sm font-bold text-brand">{t('hearing.yourTurn')}</p> : null}

            {typing ? (
              <form
                className="flex items-center gap-2"
                onSubmit={(e) => {
                  e.preventDefault()
                  voice.sendText(draft)
                  setDraft('')
                }}
              >
                <Input value={draft} onChange={(e) => setDraft(e.target.value)} placeholder={t('hearing.typePlaceholder')} disabled={!live} />
                <Button type="submit" size="icon" disabled={!live || !draft.trim()} aria-label={t('hearing.send')}>
                  <SendIcon aria-hidden />
                </Button>
              </form>
            ) : null}

            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="icon"
                className="size-12"
                onClick={() => setTyping((v) => !v)}
                aria-pressed={typing}
                aria-label={t('hearing.typeInstead')}
              >
                <KeyboardIcon aria-hidden />
              </Button>
              <Button
                size="lg"
                disabled={!live}
                onClick={voice.toggleMic}
                aria-pressed={voice.micOn}
                className={cn('h-12 flex-1', voice.micOn && 'kv-mic bg-vermilion text-[#1a0b06] hover:bg-vermilion/90')}
              >
                {voice.micOn ? <MicOffIcon aria-hidden /> : <MicIcon aria-hidden />}
                {voice.micOn ? t('hearing.micOff') : t('voice.speak')}
              </Button>
              <Button variant="outline" className="h-12" disabled={!live} loading={state === 'ending'} onClick={voice.end}>
                {t('voice.done')}
              </Button>
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}
