import { CalendarClock } from "lucide-react";
import { useListMyShifts } from "@workspace/api-client-react";
import { PageHeader, Panel, Pill, SkeletonRows, Empty, ErrorState, Tag } from "@/components/kit";
import { fmtYmd, fmtHm, todayKey, addDays } from "@/lib/time";
import { cn } from "@/lib/utils";

export default function StaffShifts() {
  const today = todayKey();
  const q = useListMyShifts({ from: today, to: addDays(today, 14) });
  const groups: Record<string, NonNullable<typeof q.data>> = {};
  for (const s of q.data ?? []) (groups[s.date] ??= []).push(s);
  const days = Object.keys(groups).sort();
  const total = (q.data ?? []).filter((s) => s.status !== "cancelled").reduce((a, s) => a + s.hours, 0);
  return (
    <div className="max-w-3xl">
      <PageHeader eyebrow="My shifts" title="Next two weeks" sub={q.data ? `${q.data.length} shifts · ${total.toFixed(1)} hours` : undefined} />
      <Panel>
        {q.isLoading ? <SkeletonRows n={5} /> : q.isError ? <ErrorState what="your shifts" onRetry={() => q.refetch()} /> : !days.length ? (
          <Empty icon={<CalendarClock className="h-5 w-5" />} title="No shifts in the next 14 days" body="When your manager rosters you, shifts appear here." />
        ) : (
          <div className="divide-y">
            {days.map((d, i) => (
              <div key={d} className="grid grid-cols-[88px_1fr] gap-4 px-4 py-3 rise" style={{ animationDelay: `${i * 30}ms` }}>
                <div>
                  <div className={cn("font-mono text-[10.5px] uppercase", d === today ? "text-primary font-semibold" : "text-muted-foreground")}>{d === today ? "Today" : fmtYmd(d).split(",")[0]}</div>
                  <div className="font-display font-bold">{fmtYmd(d).split(", ")[1] ?? fmtYmd(d)}</div>
                </div>
                <div className="space-y-2">
                  {groups[d].map((s) => (
                    <div key={s.id} className={cn("flex items-center gap-3 rounded-md border px-3 py-2", s.source === "cover" && "border-primary/40 bg-primary/[0.05]")} data-testid={`row-my-shift-${s.id}`}>
                      <div className="font-mono text-sm tnum">{fmtHm(s.startTime)} to {fmtHm(s.endTime)}</div>
                      <div className="text-sm text-muted-foreground flex-1 truncate">{s.roleName}{s.patternName ? ` · ${s.patternName}` : ""}</div>
                      {s.source === "cover" && <Tag className="bg-primary/10 text-primary">cover</Tag>}
                      {s.status !== "scheduled" && <Pill status={s.status} />}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}
