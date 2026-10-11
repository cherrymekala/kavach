import { UploadIcon } from 'lucide-react'
import { useRef, useState } from 'react'
import { cn } from '@/lib/cn'

export interface FileDropProps {
  onFiles: (files: File[]) => void
  accept?: string
  maxBytes?: number
}

export function FileDrop({ onFiles, accept = 'image/*,application/pdf,.txt', maxBytes = 20 * 1_000_000 }: FileDropProps) {
  const [over, setOver] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault()
        setOver(true)
      }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => {
        e.preventDefault()
        setOver(false)
        onFiles(Array.from(e.dataTransfer.files))
      }}
      className={cn(
        'flex flex-col items-center gap-2 rounded-lg border-2 border-dashed border-border p-6 text-center transition-colors',
        over && 'border-brand bg-accent/50',
      )}
    >
      <UploadIcon className="size-6 text-muted-foreground" aria-hidden />
      <p className="text-sm text-muted-foreground">Drop files here, or</p>
      <label className="cursor-pointer font-bold text-brand focus-within:outline-2 focus-within:outline-ring">
        choose from your phone
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={accept}
          className="sr-only"
          onChange={(e) => onFiles(Array.from(e.target.files ?? []))}
        />
      </label>
      <p className="font-mono text-xs text-muted-foreground">
        PDF / JPG / PNG / WEBP / TXT · up to {Math.round(maxBytes / 1_000_000)} MB
      </p>
    </div>
  )
}