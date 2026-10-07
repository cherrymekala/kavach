import { cn } from '@/lib/cn'

export function Spinner({ className }: { className?: string }) {
  return (
    <span
      className={cn('size-4 animate-spin rounded-full border-2 border-current border-t-transparent', className)}
    />
  )
}