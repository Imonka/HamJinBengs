import type { ReactNode } from "react";
import { AlertTriangle, RotateCw } from "lucide-react";
import { cn } from "@/lib/utils";
import { initials } from "@/lib/time";

export function PageHeader({ eyebrow, title, sub, actions }: { eyebrow?: string; title: string; sub?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between mb-6 rise">
      <div>
        {eyebrow && <div className="font-mono text-[10.5px] uppercase tracking-[0.18em] text-primary mb-1.5">{eyebrow}</div>}
        <h1 className="font-display text-3xl md:text-[34px] font-bold leading-none" data-testid="text-page-title">{title}</h1>
        {sub && <p className="text-sm text-muted-foreground mt-2 max-w-xl">{sub}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  );
}

const tones: Record<string, string> = {
  open: "bg-accent/20 text-[hsl(32_80%_28%)] ring-accent/50",
  needs_cover: "bg-accent/20 text-[hsl(32_80%_28%)] ring-accent/50",
  pending: "bg-accent/15 text-[hsl(32_80%_30%)] ring-accent/40",
  queued: "bg-accent/15 text-[hsl(32_80%_30%)] ring-accent/40",
  offered: "bg-[hsl(200_60%_92%)] text-[hsl(200_60%_28%)] ring-[hsl(200_50%_70%)]",
  accepted: "bg-primary/12 text-primary ring-primary/30",
  declined: "bg-muted text-muted-foreground ring-border",
  withdrawn: "bg-muted text-muted-foreground ring-border",
  expired: "bg-muted text-muted-foreground ring-border",
  manager: "bg-sidebar text-sidebar-accent-foreground ring-sidebar",
  staff: "bg-secondary text-secondary-foreground ring-border",
  filled: "bg-primary/12 text-primary ring-primary/30",
  covered: "bg-primary/12 text-primary ring-primary/30",
  approved: "bg-primary/12 text-primary ring-primary/30",
  sent: "bg-primary/12 text-primary ring-primary/30",
  scheduled: "bg-secondary text-secondary-foreground ring-border",
  cancelled: "bg-muted text-muted-foreground ring-border line-through decoration-1",
  rejected: "bg-destructive/10 text-destructive ring-destructive/30",
  failed: "bg-destructive/10 text-destructive ring-destructive/30",
};
const labels: Record<string, string> = { needs_cover: "needs cover" };

export function Pill({ status, className, label }: { status: string; className?: string; label?: string }) {
  const live = status === "open" || status === "needs_cover" || status === "offered";
  return (
    <span data-testid={`status-${status}`} className={cn("inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-medium ring-1 ring-inset font-mono uppercase tracking-wide whitespace-nowrap", tones[status] ?? tones.scheduled, className)}>
      {live && <span className={cn("h-1.5 w-1.5 rounded-full pulse-dot", status === "offered" ? "bg-[hsl(200_60%_40%)]" : "bg-accent")} />}
      {label ?? labels[status] ?? status}
    </span>
  );
}

export function Tag({ children, className }: { children: ReactNode; className?: string }) {
  return <span className={cn("inline-flex items-center rounded px-1.5 py-0.5 text-[11px] bg-secondary text-secondary-foreground", className)}>{children}</span>;
}

export function Initials({ name, className }: { name: string; className?: string }) {
  let h = 0;
  for (const c of name) h = (h * 31 + c.charCodeAt(0)) % 360;
  return (
    <span className={cn("inline-grid place-items-center shrink-0 rounded-md h-8 w-8 text-[11px] font-semibold font-mono", className)}
      style={{ background: `hsl(${(h % 60) + 160} 35% 86%)`, color: `hsl(${(h % 60) + 160} 50% 20%)` }}>
      {initials(name)}
    </span>
  );
}

export function Panel({ title, action, children, className, delay = 0 }: { title?: ReactNode; action?: ReactNode; children: ReactNode; className?: string; delay?: number }) {
  return (
    <section className={cn("rounded-lg border bg-card rise", className)} style={{ animationDelay: `${delay}ms` }}>
      {title && (
        <div className="flex items-center justify-between px-4 h-11 border-b">
          <h2 className="font-mono text-[11px] uppercase tracking-[0.14em] text-muted-foreground">{title}</h2>
          {action}
        </div>
      )}
      {children}
    </section>
  );
}

export function SkeletonRows({ n = 5, h = 52 }: { n?: number; h?: number }) {
  return (
    <div className="divide-y">
      {Array.from({ length: n }).map((_, i) => (
        <div key={i} className="flex items-center gap-3 px-4" style={{ height: h }}>
          <div className="h-8 w-8 rounded-md bg-muted animate-pulse" />
          <div className="flex-1 space-y-1.5">
            <div className="h-3 rounded bg-muted animate-pulse" style={{ width: `${40 + ((i * 17) % 35)}%` }} />
            <div className="h-2.5 rounded bg-muted/70 animate-pulse" style={{ width: `${25 + ((i * 11) % 25)}%` }} />
          </div>
        </div>
      ))}
    </div>
  );
}

export function Empty({ icon, title, body, action }: { icon: ReactNode; title: string; body?: ReactNode; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center text-center py-14 px-6 rise" data-testid="state-empty">
      <div className="h-12 w-12 rounded-full grid place-items-center bg-primary/10 text-primary mb-4 ring-8 ring-primary/5">{icon}</div>
      <div className="font-display text-lg font-bold">{title}</div>
      {body && <p className="text-sm text-muted-foreground mt-1 max-w-sm">{body}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function ErrorState({ onRetry, what = "this" }: { onRetry: () => void; what?: string }) {
  return (
    <div className="flex flex-col items-center text-center py-12 px-6" data-testid="state-error">
      <AlertTriangle className="h-6 w-6 text-destructive mb-3" />
      <div className="font-medium">Could not load {what}.</div>
      <p className="text-sm text-muted-foreground mt-1">The server did not answer. Your data is safe.</p>
      <button onClick={onRetry} data-testid="button-retry" className="mt-4 inline-flex items-center gap-1.5 text-sm font-medium text-primary hover:underline">
        <RotateCw className="h-3.5 w-3.5" /> Try again
      </button>
    </div>
  );
}

export function Segmented<T extends string>({ value, onChange, options }: { value: T; onChange: (v: NoInfer<T>) => void; options: { value: NoInfer<T>; label: string; count?: number }[] }) {
  return (
    <div className="inline-flex rounded-md bg-secondary p-0.5 text-sm">
      {options.map((o) => (
        <button key={o.value} onClick={() => onChange(o.value)} data-testid={`filter-${o.value}`}
          className={cn("px-3 py-1.5 rounded-[5px] transition-all duration-200", value === o.value ? "bg-card shadow-sm font-medium text-foreground" : "text-muted-foreground hover:text-foreground")}>
          {o.label}
          {o.count != null && <span className="ml-1.5 font-mono text-[11px] opacity-60">{o.count}</span>}
        </button>
      ))}
    </div>
  );
}
