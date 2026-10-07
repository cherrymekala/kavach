export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  // iOS Safari can kill the download if we revoke immediately after click.
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}