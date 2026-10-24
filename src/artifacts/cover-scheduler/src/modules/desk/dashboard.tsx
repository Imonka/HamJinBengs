import { Link } from "wouter";
import { ArrowRight, CheckCircle2, Clock } from "lucide-react";
import { useGetDashboardSummary, useGetRecentActivity, useListCoverage } from "@workspace/api-client-react";
import { PageHeader, Panel, SkeletonRows, Empty, ErrorState, Initials } from "@/components/kit";
import { CaseRow, startsIn } from "@/modules/cover";
import { fmtYmd, fmtHm, relative } from "@/lib/time";
import { cn } from "@/lib/utils";

const kindDot = (k: string) =>
  k.includes("filled") || k.includes("accepted") || k.includes("approved") ? "bg-primary"
  : k.includes("offer") ? "bg-[hsl(200_60%_45%)]"
  : k.includes("opened") || k.includes("leave") ? "bg-accent"
  : k.includes("reject") || k.includes("cancel") ? "bg-destructive" : "bg-muted-foreground/50";

export default function Dashboard() {
  const sum = useGetDashboardSummary();
  const act = useGetRecentActivity();
  const open = useListCoverage({ status: "open" });
  const offered = useListCoverage({ status: "offered" });
  const sortKey = (c: { shift: { date: string; startTime: string } }) => `${c.shift.date}${c.shift.startTime}`;
  const cases = [...(open.data ?? [])].sort((a, b) => sortKey(a).localeCompare(sortKey(b)));
  const waiting = [...(offered.data ?? [])].sort((a, b) => sortKey(a).localeCompare(sortKey(b)));
  const next = cases[0];
  const s = sum.data;

  const stats = [
    { k: "Urgent, under 48h", v: s?.urgentCases, hot: (s?.urgentCases ?? 0) > 0 },
    { k: "Nobody asked yet", v: s?.openCases },
    { k: "Waiting on replies", v: s?.offeredCases },
    { k: "Filled this week", v: s?.filledThisWeek },
    { k: "Roster gaps this week", v: s?.rosterGapsThisWeek, hot: (s?.rosterGapsThisWeek ?? 0) > 0 },
    { k: "On leave today", v: s?.onLeaveToday },
    { k: "Leave pending", v: s?.pendingLeave },
  ];

  return (
    <div>
      <PageHeader eyebrow="Operations desk" title={cases.length ? `${cases.length} shift${cases.length > 1 ? "s" : ""} need cover` : "Nobody left to ask"}
        sub={s ? `${s.staffCount} staff · ${s.shiftsThisWeek} shifts this week · ${s.pendingOffers} offers awaiting a reply.` : "Loading the floor..."} />

      {sum.isError ? <Panel className="mb-6"><ErrorState what="the summary" onRetry={() => sum.refetch()} /></Panel> : (
        <div className="grid grid-cols-2 md:grid-cols-7 border rounded-lg bg-card divide-x divide-y md:divide-y-0 overflow-hidden mb-6 rise">
          {stats.map((x) => (
            <div key={x.k} className={cn("px-4 py-3", x.hot && "stripes")} data-testid={`stat-${x.k}`}>
              <div className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">{x.k}</div>
              {s ? <div className="font-display text-[28px] font-bold tnum leading-tight">{x.v}</div> : <div className="h-7 w-10 mt-1 rounded bg-muted animate-pulse" />}
            </div>
          ))}
        </div>
      )}

      <div className="grid lg:grid-cols-[1fr_340px] gap-6">
        <div className="space-y-6 min-w-0">
          {open.isLoading ? <Panel><SkeletonRows n={3} h={80} /></Panel> : open.isError ? (
            <Panel><ErrorState what="open cases" onRetry={() => open.refetch()} /></Panel>
          ) : next ? (
            <Link href={`/coverage/${next.id}`} data-testid="card-next-gap"
              className="block rounded-lg bg-sidebar text-sidebar-accent-foreground p-5 md:p-6 relative overflow-hidden group rise">
              <div className="absolute inset-0 opacity-30 stripes" />
              <div className="relative flex flex-col md:flex-row md:items-center gap-5">
                <div className="flex-1 min-w-0">
                  <div className="font-mono text-[10.5px] uppercase tracking-[0.2em] text-sidebar-primary flex items-center gap-2">
                    <span className="h-1.5 w-1.5 rounded-full bg-sidebar-primary pulse-dot" /> Next gap to fill · starts {startsIn(next.startsInHours)}
                  </div>
                  <div className="font-display text-3xl md:text-4xl font-extrabold mt-2 leading-none">{fmtYmd(next.shift.date)}, {fmtHm(next.shift.startTime)}</div>
                  <div className="mt-2 text-sidebar-foreground/80 text-sm flex flex-wrap gap-x-3">
                    <span>{next.shift.roleName}</span>
                    <span className="inline-flex items-center gap-1"><Clock className="h-3.5 w-3.5" />{fmtHm(next.shift.startTime)} to {fmtHm(next.shift.endTime)} · {next.shift.hours.toFixed(1)}h</span>
                  </div>
                  <div className="mt-3 text-sm text-sidebar-foreground/70 flex items-center gap-2">
                    <Initials name={next.originalEmployee.name} className="h-6 w-6 text-[9px]" /> {next.originalEmployee.name}, {next.leave.leaveType} leave
                  </div>
                </div>
                <span className="inline-flex items-center justify-center gap-2 rounded-md bg-sidebar-primary text-sidebar-primary-foreground font-semibold h-11 px-5 group-hover:gap-3 transition-all">
                  Ask for cover <ArrowRight className="h-4 w-4" />
                </span>
              </div>
            </Link>
          ) : (
            <Panel><Empty icon={<CheckCircle2 className="h-5 w-5" />} title="No unasked gaps" body="When leave is approved, any shifts it touches land here, soonest first." /></Panel>
          )}

          {cases.length > 1 && (
            <Panel title="Also open" action={<Link href="/coverage" className="text-xs text-primary font-medium hover:underline" data-testid="link-all-cases">Full queue</Link>} delay={60}>
              <div className="divide-y">{cases.slice(1, 8).map((c, i) => <CaseRow key={c.id} c={c} index={i} />)}</div>
            </Panel>
          )}

          <Panel title="Waiting on replies" delay={100}>
            {offered.isLoading ? <SkeletonRows n={3} /> : waiting.length ? <div className="divide-y">{waiting.slice(0, 8).map((c, i) => <CaseRow key={c.id} c={c} index={i} />)}</div>
              : <div className="px-4 py-6 text-sm text-muted-foreground">No offers out right now.</div>}
          </Panel>
        </div>

        <Panel title="Activity" delay={90} className="self-start">
          {act.isLoading ? <SkeletonRows n={6} h={44} /> : act.isError ? <ErrorState what="activity" onRetry={() => act.refetch()} /> : !act.data?.length ? (
            <div className="px-4 py-6 text-sm text-muted-foreground">Nothing has happened yet.</div>
          ) : (
            <ol className="px-4 py-3 max-h-[620px] overflow-auto">
              {act.data.slice(0, 30).map((a, i) => (
                <li key={a.id} data-testid={`activity-${a.id}`} className="flex gap-3 py-2 rise" style={{ animationDelay: `${i * 25}ms` }}>
                  <span className={cn("mt-1.5 h-2 w-2 rounded-full shrink-0", kindDot(a.kind))} />
                  <div className="min-w-0">
                    <div className="text-[13px] leading-snug">{a.message}</div>
                    <div className="font-mono text-[10.5px] text-muted-foreground mt-0.5">{relative(a.createdAt)}</div>
                  </div>
                </li>
              ))}
            </ol>
          )}
        </Panel>
      </div>
    </div>
  );
}
