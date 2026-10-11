import {
  Argument,
  Badge,
  Button,
  Card,
  CardContent,
  CardTitle,
  ChatBubble,
  Countdown,
  FileTile,
  LanguagePicker,
  Meter,
  PhoneOTPForm,
  Pill,
  Separator,
  SourceChip,
  Spinner,
  Stepper,
  Timeline,
  ThemeToggle,
} from '@/components'

const SWATCHES: { name: string; className: string; dark?: boolean }[] = [
  { name: 'background', className: 'bg-background border border-border' },
  { name: 'card', className: 'bg-card border border-border' },
  { name: 'foreground', className: 'bg-foreground', dark: true },
  { name: 'primary (brand)', className: 'bg-primary' },
  { name: 'accent (brand-soft)', className: 'bg-accent' },
  { name: 'mint', className: 'bg-mint' },
  { name: 'amber', className: 'bg-amber' },
  { name: 'destructive (red)', className: 'bg-destructive' },
]

const DEMO_DEADLINE = new Date(Date.now() + 9 * 86_400_000).toISOString()

/** Dev-only smoke screen: verifies the design system and primitives render. */
export function Foundation() {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-start justify-between">
        <section>
          <h1 className="font-display text-2xl font-extrabold text-balance">Foundation ready</h1>
          <p className="mt-1 text-muted-foreground">
            Vite + React 19 + Tailwind v4 + shadcn/ui. Dev check, not a screen.
          </p>
        </section>
        <ThemeToggle />
      </div>

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
          <Button loading>Loading</Button>
        </div>
      </section>

      <section className="flex flex-col gap-2">
        <h2 className="font-display text-lg font-bold">Badges & pills</h2>
        <div className="flex flex-wrap items-center gap-2">
          <Badge>Default</Badge>
          <Badge variant="secondary">Secondary</Badge>
          <Pill tone="ok">Strong</Pill>
          <Pill tone="warn">Waiting</Pill>
          <Pill tone="bad">Rejected</Pill>
        </div>
      </section>

      <section className="flex flex-col gap-2">
        <h2 className="font-display text-lg font-bold">Meter</h2>
        <Meter value={0.78} tone="mint" />
        <Meter value={0.45} tone="amber" />
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="font-display text-lg font-bold">Stepper</h2>
        <Stepper
          current={1}
          steps={[
            { label: 'Appeal to insurer grievance cell', detail: 'Sent 02 Sep 2026' },
            { label: 'Insurer reply (15 days)', detail: 'Reminder set' },
            { label: 'Complaint on Bima Bharosa' },
            { label: 'Insurance Ombudsman hearing' },
          ]}
        />
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="font-display text-lg font-bold">Timeline</h2>
        <Timeline
          items={[
            { label: 'Mar 2022', detail: 'Policy started' },
            { label: 'Mar 2025', detail: 'Waiting period ends', hot: true },
            { label: '12 Jul 2026', detail: 'Admitted for surgery' },
          ]}
        />
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="font-display text-lg font-bold">Argument & sources</h2>
        <Argument
          claim="The waiting period was already over."
          explanation="Policy began Mar 2022; the 36-month period ended Mar 2025, before admission."
          sources={[
            { ref: 'Policy Clause 4.2, p.11' },
            { ref: 'IRDAI Master Circular 2024' },
          ]}
        />
        <SourceChip label="Discharge summary, line 14" />
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="font-display text-lg font-bold">FileTile & chat</h2>
        <FileTile filename="rejection_letter.pdf" docType="rejection_letter" pages={1} />
        <FileTile filename="hospital_bill.jpg" docType="bill" warning="Looks like a bill, not the final summary" />
        <div className="flex flex-col gap-2">
          <ChatBubble role="ai">Why do you say this wasn't pre-existing?</ChatBubble>
          <ChatBubble role="me">My policy started in Mar 2022 and I was diagnosed in June 2026.</ChatBubble>
          <ChatBubble role="coach">Name the document: “The discharge summary, line 14.”</ChatBubble>
        </div>
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="font-display text-lg font-bold">Countdown & language</h2>
        <Countdown deadline={DEMO_DEADLINE} />
        <LanguagePicker
          value="en"
          onChange={() => {}}
          languages={[
            { code: 'en', label: 'English' },
            { code: 'hi', label: 'हिंदी' },
            { code: 'ta', label: 'தமிழ்' },
          ]}
        />
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="font-display text-lg font-bold">Phone OTP</h2>
        <PhoneOTPForm
          onSend={async () => {}}
          onVerify={async () => {}}
        />
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
    </div>
  )
}