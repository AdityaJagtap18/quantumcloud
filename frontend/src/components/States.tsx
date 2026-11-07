import { Loader2, AlertCircle, Inbox } from "lucide-react";

export function LoadingState({ label = "Loading" }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 py-12 text-sm text-[var(--text-secondary)]">
      <Loader2 size={14} className="animate-spin" />
      {label}
    </div>
  );
}

export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-[var(--radius-lg)] border border-dashed border-[var(--border)] py-12 text-center">
      <Inbox size={18} className="text-[var(--text-muted)]" />
      <p className="text-sm font-medium text-[var(--text)]">{title}</p>
      {hint && <p className="max-w-sm text-xs text-[var(--text-secondary)]">{hint}</p>}
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2 rounded-[var(--radius-md)] border border-[var(--error)]/30 bg-[var(--error-bg)] px-3 py-2.5 text-sm text-[var(--error)]">
      <AlertCircle size={14} className="mt-0.5 shrink-0" />
      {message}
    </div>
  );
}
