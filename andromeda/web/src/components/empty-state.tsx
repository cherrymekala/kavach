import type { ReactNode } from 'react'

export interface EmptyStateProps {
  title: string
  description?: string
  action?: ReactNode
  icon?: ReactNode
}

export function EmptyState({ title, description, action, icon }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed border-border p-8 text-center">
      {icon ? <div className="text-muted-foreground">{icon}</div> : null}
      <p className="font-display text-lg font-bold">{title}</p>
      {description ? <p className="max-w-xs text-sm text-muted-foreground">{description}</p> : null}
      {action ? <div className="mt-2">{action}</div> : null}
    </div>
  )
}

export interface ErrorStateProps {
  /** Backend `detail` message — shown verbatim. */
  message?: string
  title?: string
}

export function ErrorState({ message, title = 'Something went wrong' }: ErrorStateProps) {
  return <EmptyState title={title} description={message ?? 'Please try again.'} />
}