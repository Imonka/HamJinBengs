import { Link } from "wouter";
import { ArrowRight } from "lucide-react";
import type { CoverageCase } from "@workspace/api-client-react";
import { Pill, Initials, Tag } from "@/components/kit";
import { fmtYmd, fmtHm } from "@/lib/time";
import { cn } from "@/lib/utils";

export function startsIn(h: number) {
  if (h < 0) return "started";
  if (h < 1) return `in ${Math.round(h * 60)}m`;
  if (h < 48) return `in ${Math.round(h)}h`;
  return `in ${Math.round(h / 24)}d`;
}

export function CaseRow({ c, index = 0, next = false }: { c: CoverageCase; index?: number; next?: boolean }) {
  const pending = c.offers.filter((o) => o.status === "pending").length;
  return (
    <Link href={`/coverage/${c.id}`} data-testid={`row-case-${c.id}`}
      className="group grid grid-cols-[auto_1fr_auto] md:grid-cols-[110px_1fr_200px_110px_20px] items-center gap-3 md:gap-4 px-4 py-3 hover:bg-secondary/60 transition-colors rise relative"
      style={{ animationDelay: `${Math.min(index, 12) * 35}ms` }}>
      {c.urgent && <span className="absolute left-0 top-0 bottom-0 w-[3px] bg-accent" />}
      <div className="hidden md:block">
        <div className="font-mono text-[11px] uppercase text-muted-foreground">{fmtYmd(c.shift.date)}</div>
        <div className="font-display font-bold text-[15px] tnum">{fmtHm(c.shift.startTime)}</div>
      </div>
      <Initials name={c.originalEmployee.name} className="md:hidden" />
      <div className="min-w-0">
        <div className="font-medium truncate">{next && <span data-testid="tag-next-up"><Tag className="mr-1.5 bg-primary text-primary-foreground font-mono uppercase text-[9.5px] tracking-wider">Next up</Tag></span>}{c.shift.roleName} <span className="font-mono text-xs text-muted-foreground">{fmtHm(c.shift.startTime)}–{fmtHm(c.shift.endTime)}</span></div>
        <div className="text-xs text-muted-foreground truncate">
          <span className="md:hidden">{fmtYmd(c.shift.date)} · </span>
          {c.originalEmployee.name} on {c.leave.leaveType.toLowerCase()} leave
        </div>
      </div>
      <div className="hidden md:block text-sm truncate">
        {c.replacementEmployee ? (
          <span className="inline-flex items-center gap-2"><Initials name={c.replacementEmployee.name} className="h-6 w-6 text-[9px]" />{c.replacementEmployee.name}</span>
        ) : c.status === "offered" ? (
          <span className="font-mono text-xs text-[hsl(200_60%_30%)]">{pending} asked · waiting</span>
        ) : c.status === "open" ? (
          <span className={cn("font-mono text-xs", c.urgent ? "text-[hsl(32_80%_32%)] font-semibold" : "text-muted-foreground")}>starts {startsIn(c.startsInHours)}</span>
        ) : <span className="text-muted-foreground text-xs">no replacement</span>}
      </div>
      <div className="justify-self-end md:justify-self-start"><Pill status={c.status} /></div>
      <ArrowRight className="hidden md:block h-4 w-4 text-muted-foreground opacity-0 -translate-x-1 group-hover:opacity-100 group-hover:translate-x-0 transition-all" />
    </Link>
  );
}
