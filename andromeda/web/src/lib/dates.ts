export function formatDate(value: string | null | undefined): string {
  if (!value) return ''
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })
}

/** Whole days from now until `deadline` (can be negative when overdue). */
export function daysUntil(deadline: string | null | undefined): number | null {
  if (!deadline) return null
  const d = new Date(deadline).getTime()
  if (Number.isNaN(d)) return null
  return Math.ceil((d - Date.now()) / 86_400_000)
}