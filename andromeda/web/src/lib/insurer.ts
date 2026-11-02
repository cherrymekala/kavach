/** "STAR HEALTH AND ALLIED INSURANCE CO. LTD." → "Star Health": the name a patient would say. */
// Insurer acronyms that contain vowels, so the no-vowel rule below can't spot them.
const ACRONYMS = new Set(['ICICI', 'IFFCO', 'ERGO', 'NTUC', 'FWD'])

export function shortInsurer(name: string): string {
  const cut = name.split(/\s+(?:and|&)\s+|\s+(?:insurance|general|health insurance)\b/i)[0] || name
  const words = cut.trim().split(/\s+/).slice(0, 3).join(' ')
  if (words !== words.toUpperCase()) return words
  // Title-case shouted names but keep acronyms (HDFC, ICICI-style words with no vowels or ≤3 letters).
  return words.replace(/\S+/g, (w) => (w.length <= 3 || ACRONYMS.has(w) || !/[AEIOU]/.test(w.slice(1)) ? w : w[0] + w.slice(1).toLowerCase()))
}
