import { Badge, Button, Card, CardContent, CardTitle, Meter, Pill, Separator, Spinner } from '@/components'

const SWATCHES: { name: string; className: string; dark?: boolean }[] = [
  { name: 'background', className: 'bg-background border border-border' },
  { name: 'card', className: 'bg-card border border-border' },
  { name: 'foreground', className: 'bg-foreground', dark: true },
  { name: 'muted-foreground', className: 'bg-muted-foreground', dark: true },
  { name: 'primary (brand)', className: 'bg-primary' },
  { name: 'accent (brand-soft)', className: 'bg-accent' },
  { name: 'mint', className: 'bg-mint' },
  { name: 'amber', className: 'bg-amber' },
  { name: 'destructive (red)', className: 'bg-destructive' },
]

/** Dev-only smoke screen: verifies the design system and primitives render. */
export function Foundation() {
  return (
    <div className="flex flex-col gap-6">
      <section>
        <h1 className="font-display text-2xl font-extrabold text-balance">Foundation ready</h1>
        <p className="mt-1 text-muted-foreground">
          Vite + React 19 + Tailwind v4 + shadcn/ui primitives. Dev check, not a screen.
        </p>
      </section>

      <section className="flex flex-col gap-2">
        <h2 className="font-display text-lg font-bold">Colour tokens</h2>
        <div className="grid grid-cols-3 gap-2">
          {SWATCHES.map((s) => (
            <div
              key={s.name}
              className={`flex h-12 items-center justify-center rounded-md px-1 text-center font-mono text-[10px] leading-tight ${s.className} ${
                s.dark ? 'text-background' : ''
              }`}
            >
              {s.name}
            </div>
          ))}
        </div>
      </section>

      <section className="flex flex-col gap-2">
        <h2 className="font-display text-lg font-bold">Buttons</h2>
        <div className="flex flex-wrap gap-2">
          <Button>Primary</Button>
          <Button variant="secondary">Secondary</Button>
          <Button variant="outline">Outline</Button>
          <Button variant="ghost">Ghost</Button>
          <Button variant="destructive">Destructive</Button>
          <Button disabled>Disabled</Button>
        </div>
      </section>

      <section className="flex flex-col gap-2">
        <h2 className="font-display text-lg font-bold">Badges & pills</h2>
        <div className="flex flex-wrap items-center gap-2">
          <Badge>Default</Badge>
          <Badge variant="secondary">Secondary</Badge>
          <Badge variant="outline">Outline</Badge>
          <Pill tone="ok">Strong</Pill>
          <Pill tone="warn">Waiting</Pill>
          <Pill tone="bad">Rejected</Pill>
          <Pill tone="neutral">Neutral</Pill>
        </div>
      </section>

      <section className="flex flex-col gap-2">
        <h2 className="font-display text-lg font-bold">Meter</h2>
        <Meter value={0.78} tone="mint" />
        <Meter value={0.45} tone="amber" />
        <Meter value={0.3} tone="brand" />
      </section>

      <Card>
        <CardContent>
          <div className="flex items-center gap-3">
            <Spinner />
            <CardTitle className="text-base">Card + spinner</CardTitle>
          </div>
        </CardContent>
      </Card>

      <Separator />

      <section className="flex flex-col gap-2">
        <h2 className="font-display text-lg font-bold">Typography</h2>
        <p className="font-display text-xl">Display — Bricolage Grotesque</p>
        <p>Body — Figtree</p>
        <p className="font-mono text-sm">Mono — JetBrains Mono 012345</p>
      </section>
    </div>
  )
}