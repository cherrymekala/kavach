// Barrel — import primitives from '@/components' for convenience.
// Individual imports from '@/components/ui/<name>' also work (shadcn convention).

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
export { Input } from './ui/input'
export { Textarea } from './ui/textarea'
export { Label } from './ui/label'
export { Progress } from './ui/progress'
export { Separator } from './ui/separator'
export { Toggle, toggleVariants } from './ui/toggle'
export { ToggleGroup, ToggleGroupItem } from './ui/toggle-group'
export { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider } from './ui/tooltip'
export { Toaster } from './ui/sonner'

// Kavach primitives (not in shadcn)
export { Spinner } from './ui/spinner'
export { Pill, pillVariants } from './ui/pill'
export { Meter } from './ui/meter'
export { LiveIndicator } from './ui/live-indicator'