import { AppHeader } from '@/components'
import { useAuth } from '@/auth'

export function Start() {
  const { user } = useAuth()
  return (
    <div className="flex flex-col gap-4">
      <AppHeader title="Kavach" />
      <div className="rounded-lg border border-dashed border-border p-8 text-center">
        <p className="font-display text-lg font-bold">You're signed in</p>
        <p className="mt-1 text-sm text-muted-foreground">
          {user?.phoneNumber ?? 'Signed in'} · starting a case comes next.
        </p>
      </div>
    </div>
  )
}