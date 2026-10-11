/** Group an integer with Indian digit grouping (1,84,000) — not the western 184,000. */
function indianGroup(n: number): string {
  const int = Math.round(n).toString()
  const last3 = int.slice(-3)
  const rest = int.slice(0, -3)
  return rest ? `${rest.replace(/\B(?=(\d{2})+(?!\d))/g, ',')},${last3}` : int
}

export function formatMoney(amount: number, currency: string): string {
  const n = Number(amount) || 0
  if (currency === 'INR') return `₹${indianGroup(n)}`
  if (currency === 'SGD') return `S$${n.toLocaleString('en-SG')}`
  return `${n.toLocaleString('en-SG')} ${currency}`
}