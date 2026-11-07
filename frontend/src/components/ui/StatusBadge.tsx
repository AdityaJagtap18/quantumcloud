import type { JobStatus } from "../../types";

// Restrained text + dot indicators, not large colorful pills.
const STATUS_STYLE: Record<JobStatus, { dot: string; text: string }> = {
  QUEUED: { dot: "bg-[var(--text-muted)]", text: "text-[var(--text-secondary)]" },
  VALIDATING: { dot: "bg-[var(--warning)]", text: "text-[var(--warning)]" },
  RUNNING: { dot: "bg-[var(--accent)]", text: "text-[var(--accent)]" },
  COMPLETED: { dot: "bg-[var(--success)]", text: "text-[var(--success)]" },
  FAILED: { dot: "bg-[var(--error)]", text: "text-[var(--error)]" },
  CANCELLED: { dot: "bg-[var(--text-muted)]", text: "text-[var(--text-muted)]" },
};

export function StatusBadge({ status }: { status: JobStatus }) {
  const style = STATUS_STYLE[status];
  return (
    <span className={`inline-flex items-center gap-1.5 text-xs font-medium ${style.text}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${style.dot} ${status === "RUNNING" ? "animate-pulse" : ""}`} />
      {status.charAt(0) + status.slice(1).toLowerCase()}
    </span>
  );
}
