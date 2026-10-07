import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/cn'

const pillVariants = cva(
  'inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-bold whitespace-nowrap',
  {
    variants: {
      tone: {
        ok: 'bg-mint/15 text-mint',
        warn: 'bg-amber/15 text-amber',
        bad: 'bg-red/15 text-red',
        neutral: 'bg-muted text-muted-foreground',
      },
    },
    defaultVariants: { tone: 'neutral' },
  },
)

export interface PillProps
  extends React.ComponentProps<'span'>,
    VariantProps<typeof pillVariants> {}

export function Pill({ className, tone, ...props }: PillProps) {
  return <span className={cn(pillVariants({ tone }), className)} {...props} />
}

export { pillVariants }