import { cn } from '@/lib/cn'

export function LiveIndicator({ className, label = 'Live' }: { className?: string; label?: string }) {
  return (
    <span className={cn('inline-flex items-center gap-2 text-xs font-bold text-amber', className)}>
      <span className="size-2 rounded-full bg-amber animate-pulse-dot" aria-hidden />
      {label}
    </span>
  )
}