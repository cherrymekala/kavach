import {
  FileIcon,
  FileTextIcon,
  LandmarkIcon,
  ReceiptIcon,
  ScaleIcon,
  StethoscopeIcon,
  type LucideIcon,
} from 'lucide-react'
import { cn } from '@/lib/cn'

const ICONS: Record<string, LucideIcon> = {
  policy: FileTextIcon,
  rejection_letter: FileTextIcon,
  discharge_summary: StethoscopeIcon,
  bill: ReceiptIcon,
  regulation: ScaleIcon,
  ruling: LandmarkIcon,
  other: FileIcon,
}

export function SourceKindIcon({ kind, className }: { kind: string; className?: string }) {
  const Icon = ICONS[kind] ?? FileIcon
  return <Icon className={cn('size-4', className)} aria-hidden />
}