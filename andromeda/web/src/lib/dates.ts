export function formatDate(value: string | null | undefined): string {
  if (!value) return ''
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })
}

/**
 * A deadline is a calendar day the backend stores as 23:59 UTC (agents/escalation.py).
 * Shown in the viewer's zone it becomes the next day east of UTC (India: 05:29 next
 * morning), so it is formatted in UTC to match "Reply due by …" in the history.
 */
export function formatDeadline(value: string | null | undefined): string {
  if (!value) return ''
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' })
}

/** Whole days from now until `deadline` (can be negative when overdue). */
export function daysUntil(deadline: string | null | undefined): number | null {
  if (!deadline) return null
  const d = new Date(deadline).getTime()
  if (Number.isNaN(d)) return null
  return Math.ceil((d - Date.now()) / 86_400_000)
}

/** Compact relative time, e.g. "3m ago", "2h ago", then a plain date after a week. */
export function timeAgo(value: string | null | undefined): string {
  if (!value) return ''
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return ''
  const diff = Date.now() - d.getTime()
  const min = Math.floor(diff / 60_000)
  if (min < 1) return 'now'
  if (min < 60) return `${min}m`
  const h = Math.floor(min / 60)
  if (h < 24) return `${h}h`
  const days = Math.floor(h / 24)
  if (days < 7) return `${days}d`
  return formatDate(value)
}