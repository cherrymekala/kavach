// Barrel — import primitives and feature components from '@/components'.
// Individual imports from '@/components/ui/<name>' also work (shadcn convention).

// ── shadcn/ui primitives ────────────────────────────────────────────────
export { Button, buttonVariants } from './ui/button'
export { Badge, badgeVariants } from './ui/badge'
export {
  Card,
  CardHeader,
  CardFooter,
  CardTitle,
  CardAction,
  CardDescription,
  CardContent,
} from './ui/card'
export {
  Sheet,
  SheetTrigger,
  SheetClose,
  SheetContent,
  SheetHeader,
  SheetFooter,
  SheetTitle,
  SheetDescription,
} from './ui/sheet'
export {
  Dialog,
  DialogTrigger,
  DialogPortal,
  DialogClose,
  DialogOverlay,
  DialogContent,
  DialogHeader,
  DialogFooter,
  DialogTitle,
  DialogDescription,
} from './ui/dialog'
export {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from './ui/alert-dialog'
export {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectSeparator,
  SelectTrigger,
  SelectValue,
} from './ui/select'
export {
  Popover,
  PopoverTrigger,
  PopoverContent,
  PopoverAnchor,
  PopoverHeader,
  PopoverTitle,
  PopoverDescription,
} from './ui/popover'
export { Input } from './ui/input'
export { Textarea } from './ui/textarea'
export { Label } from './ui/label'
export { Checkbox } from './ui/checkbox'
export { Switch } from './ui/switch'
export { RadioGroup, RadioGroupItem } from './ui/radio-group'
export { Progress } from './ui/progress'
export { Separator } from './ui/separator'
export { Skeleton } from './ui/skeleton'
export { Toggle, toggleVariants } from './ui/toggle'
export { ToggleGroup, ToggleGroupItem } from './ui/toggle-group'
export { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider } from './ui/tooltip'
export { Accordion, AccordionItem, AccordionTrigger, AccordionContent } from './ui/accordion'
export { InputOTP, InputOTPGroup, InputOTPSlot, InputOTPSeparator } from './ui/input-otp'
export { Calendar, CalendarDayButton } from './ui/calendar'
export {
  Command,
  CommandDialog,
  CommandInput,
  CommandList,
  CommandEmpty,
  CommandGroup,
  CommandItem,
  CommandShortcut,
  CommandSeparator,
} from './ui/command'
export {
  Form,
  FormItem,
  FormLabel,
  FormControl,
  FormDescription,
  FormMessage,
  FormField,
  useFormField,
} from './ui/form'
export { Toaster } from './ui/sonner'

// ── Kavach primitives ────────────────────────────────────────────────────
export { Spinner } from './ui/spinner'
export { Pill, pillVariants } from './ui/pill'
export { Meter } from './ui/meter'
export { LiveIndicator } from './ui/live-indicator'

// ── Feature components ───────────────────────────────────────────────────
export { AppHeader, type AppHeaderProps } from './app-header'
export { FooterCTA, type FooterCTAProps } from './footer-cta'
export { Stepper, type StepperProps } from './stepper'
export { Timeline, type TimelineProps } from './timeline'
export { SourceChip, type SourceChipProps } from './source-chip'
export { Argument, type ArgumentProps, type ArgumentSource } from './argument'
export { SourceKindIcon } from './source-kind-icon'
export { Countdown } from './countdown'
export { ChatBubble, type ChatBubbleProps } from './chat-bubble'
export { FileDrop, type FileDropProps } from './file-drop'
export { FileTile, type FileTileProps } from './file-tile'
export { EmptyState, ErrorState, type EmptyStateProps } from './empty-state'
export { LanguagePicker, type LanguagePickerProps } from './language-picker'
export { PhoneOTPForm, DEFAULT_DIALS, type PhoneOTPFormProps, type CountryDial } from './phone-otp-form'