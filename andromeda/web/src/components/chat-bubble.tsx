import type { ReactNode } from 'react'
import { cn } from '@/lib/cn'

export interface ChatBubbleProps {
  role: 'ai' | 'me' | 'coach'
  children: ReactNode
}

export function ChatBubble({ role, children }: ChatBubbleProps) {
  return (
    <div
      className={cn(
        'max-w-[85%] rounded-lg px-3 py-2 text-sm leading-snug',
        role === 'ai' && 'self-start rounded-bl-sm bg-muted text-foreground',
        role === 'me' && 'self-end rounded-br-sm bg-primary text-primary-foreground',
        role === 'coach' && 'w-full max-w-full rounded-lg border border-mint/40 bg-mint/10 text-foreground',
      )}
    >
      {role === 'coach' ? <span className="font-bold text-mint">Coach · </span> : null}
      {children}
    </div>
  )
}