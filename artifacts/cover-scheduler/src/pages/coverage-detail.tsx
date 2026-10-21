import { useState } from "react";
import { Link, useParams } from "wouter";
import { ArrowLeft, ArrowRight, Check, Clock, AlertTriangle, Users, Mail, Ban, Moon, Send, ChevronDown, Undo2 } from "lucide-react";
import {
  useGetCoverage, useGetCoverageCandidates, useSendCoverOffers, useWithdrawCoverOffer, useCancelCoverage, useListNotifications,
  getGetCoverageQueryKey, getGetCoverageCandidatesQueryKey, getListNotificationsQueryKey,
  type Candidate, type Notification, type CoverOffer,
} from "@workspace/api-client-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { useToast } from "@/hooks/use-toast";
import { PageHeader, Panel, Pill, Initials, SkeletonRows, Empty, ErrorState, Tag } from "@/components/kit";
import { startsIn } from "@/components/case-row";
import { fmtYmd, fmtHm, fmtDate, fmtDateTime, relative } from "@/lib/time";
import { errMsg } from "@/lib/api-error";
import { useInvalidateOps } from "@/lib/invalidate";
import { cn } from "@/lib/utils";

const audienceLabel: Record<string, string> = { offered: "Offered", replacement: "Replacement", original: "Person on leave", team: "Teammate", manager: "Manager" };

export function NotificationList({ items }: { items: Notification[] }) {
  return (
    <div className="divide-y">
      {items.map((n, i) => (
        <details key={n.id} className="group px-4 py-3 rise" style={{ animationDelay: `${Math.min(i, 12) * 30}ms` }} data-testid={`notification-${n.id}`}>
          <summary className="flex items-center gap-3 cursor-pointer list-none">
            <Mail className="h-4 w-4 text-muted-foreground shrink-0" />
            <div className="min-w-0 flex-1">
              <div className="text-sm font-medium truncate">{n.recipientName} <span className="text-muted-foreground font-normal">· {n.recipientEmail}</span></div>
              <div className="text-xs text-muted-foreground truncate">{n.subject}</div>
            </div>
            <div className="hidden sm:flex items-center gap-1.5">
              <Tag>{audienceLabel[n.audience] ?? n.audience}</Tag>
              <Tag className="font-mono text-[10px]">{n.kind.replace(/_/g, " ")}</Tag>
              <span className="font-mono text-[10px] text-muted-foreground w-16 text-right">{n.readAt ? "read" : "unread"}</span>
            </div>
            <Pill status={n.emailStatus} label={n.emailStatus === "queued" ? "email queued" : undefined} />
          </summary>
          <div className="mt-3 ml-7 text-[11px] font-mono text-muted-foreground">{fmtDateTime(n.createdAt)}{n.readAt ? ` · read ${relative(n.readAt)}` : ""}</div>
          <pre className="mt-1.5 ml-7 whitespace-pre-wrap font-sans text-[13px] bg-secondary/60 rounded-md p-3 text-secondary-foreground">{n.body}</pre>
        </details>
      ))}
    </div>
  );
}

function Meter({ label, value, after, max, unit = "h" }: { label: string; value: number; after?: number; max: number; unit?: string }) {
  const a = after ?? value;
  const over = a > max;
  return (
    <div className="min-w-0">
      <div className="flex justify-between font-mono text-[10px] text-muted-foreground mb-0.5"><span className="uppercase">{label}</span>
        <span className="tnum">{after != null && <>{value.toFixed(unit === "h" ? 1 : 0)}<ArrowRight className="inline h-2.5 w-2.5 mx-0.5" /></>}<span className={over ? "text-destructive font-semibold" : "text-foreground"}>{a.toFixed(unit === "h" ? 1 : 0)}</span>/{max}{unit}</span></div>
      <div className="relative h-1.5 rounded-full bg-secondary overflow-hidden">
        <div className={cn("absolute inset-y-0 left-0", over ? "bg-destructive/70" : "bg-primary/35")} style={{ width: `${Math.min(100, (a / max) * 100)}%` }} />
        <div className="absolute inset-y-0 left-0 bg-primary" style={{ width: `${Math.min(100, (value / max) * 100)}%` }} />
      </div>
    </div>
  );
}

function CandidateRow({ c, rank, checked, disabled, onToggle }: { c: Candidate; rank: number; checked: boolean; disabled: boolean; onToggle: () => void }) {
  return (
    <label data-testid={`card-candidate-${c.employee.id}`}
      className={cn("grid grid-cols-[22px_28px_1fr_auto] gap-3 px-4 py-3.5 transition-colors rise border-l-[3px]",
        checked ? "bg-primary/[0.07] border-l-primary" : "border-l-transparent hover:bg-secondary/60", disabled ? "cursor-default opacity-80" : "cursor-pointer")}
      style={{ animationDelay: `${rank * 40}ms` }}>
      <Checkbox checked={checked} disabled={disabled} onCheckedChange={onToggle} className="mt-2" data-testid={`checkbox-candidate-${c.employee.id}`} />
      <div className="font-mono text-xs text-muted-foreground pt-2 tnum">{String(rank + 1).padStart(2, "0")}</div>
      <div className="min-w-0">
        <div className="flex items-center gap-2.5 flex-wrap">
          <Initials name={c.employee.name} />
          <div className="font-medium leading-tight">{c.employee.name}</div>
          {rank === 0 && <Tag className="bg-accent/25 text-[hsl(32_80%_26%)]">best fit</Tag>}
          {c.backToBack && (
            <Tag className="bg-destructive/10 text-destructive font-medium">
              <Moon className="h-3 w-3 mr-1" />Back-to-back
              {c.restHoursBefore != null && ` · ${c.restHoursBefore.toFixed(0)}h before`}
              {c.restHoursAfter != null && ` · ${c.restHoursAfter.toFixed(0)}h after`}
            </Tag>
          )}
          {c.offerStatus && <Pill status={c.offerStatus} label={c.offerStatus === "pending" ? "asked" : undefined} />}
        </div>
        <div className="mt-2.5 grid grid-cols-1 sm:grid-cols-3 gap-x-5 gap-y-2 max-w-xl">
          <Meter label="Week" value={c.hoursThisWeek} after={c.hoursAfter} max={c.maxHoursPerWeek} />
          <Meter label="That day" value={c.hoursThatDay} max={c.maxHoursPerDay} />
          <Meter label="Days" value={c.daysThisWeek} max={c.maxDaysPerWeek} unit="d" />
        </div>
        <div className="mt-1.5 font-mono text-[10.5px] text-muted-foreground">{c.hoursWorkedSoFar.toFixed(1)}h worked so far this week</div>
        {(c.reasons.length > 0 || c.warnings.length > 0) && (
          <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1">
            {c.reasons.map((r) => <span key={r} className="text-[11.5px] inline-flex items-center gap-1 text-muted-foreground"><Check className="h-3 w-3 text-primary" />{r}</span>)}
            {c.warnings.map((w) => <span key={w} className="text-[11.5px] inline-flex items-center gap-1 rounded bg-accent/20 text-[hsl(32_80%_26%)] px-1.5"><AlertTriangle className="h-3 w-3" />{w}</span>)}
          </div>
        )}
      </div>
      <div className="text-right">
        <div className={cn("font-display text-2xl font-extrabold tnum leading-none", c.score >= 75 ? "text-primary" : c.score >= 50 ? "text-foreground" : "text-[hsl(32_80%_32%)]")}>{Math.round(c.score)}</div>
        <div className="font-mono text-[9.5px] uppercase text-muted-foreground mt-1">score</div>
      </div>
    </label>
  );
}

function OfferRow({ o, caseId, canWithdraw }: { o: CoverOffer; caseId: number; canWithdraw: boolean }) {
  const withdraw = useWithdrawCoverOffer();
  const invalidate = useInvalidateOps();
  const { toast } = useToast();
  return (
    <div className="flex items-start gap-3 px-4 py-3" data-testid={`row-offer-${o.id}`}>
      <Initials name={o.employee.name} className="h-7 w-7 text-[10px]" />
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium">{o.employee.name}</div>
        <div className="font-mono text-[10.5px] text-muted-foreground">asked {relative(o.createdAt)}{o.respondedAt ? ` · replied ${relative(o.respondedAt)}` : ""}</div>
        {o.responseNote && <p className="text-xs mt-1 italic text-muted-foreground">"{o.responseNote}"</p>}
      </div>
      <Pill status={o.status} />
      {o.status === "pending" && canWithdraw && (
        <Button size="sm" variant="ghost" className="h-7 px-2" disabled={withdraw.isPending} data-testid={`button-withdraw-${o.id}`}
          onClick={() => withdraw.mutate({ caseId, offerId: o.id }, {
            onSuccess: () => { invalidate(); toast({ title: "Offer withdrawn", description: o.employee.name }); },
            onError: (e) => toast({ title: "Could not withdraw", description: errMsg(e), variant: "destructive" }),
          })}><Undo2 className="h-3.5 w-3.5 mr-1" />Withdraw</Button>
      )}
    </div>
  );
}

export default function CoverageDetail() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const { toast } = useToast();
  const invalidate = useInvalidateOps();
  const cs = useGetCoverage(id, { query: { enabled: !!id, queryKey: getGetCoverageQueryKey(id), refetchInterval: (q) => (q.state.data?.status === "offered" ? 10_000 : false) } });
  const status = cs.data?.status;
  const active = status === "open" || status === "offered";
  const polling = status === "offered";
  const cand = useGetCoverageCandidates(id, { query: { enabled: !!id && active, queryKey: getGetCoverageCandidatesQueryKey(id), refetchInterval: polling ? 10_000 : false } });
  const notes = useListNotifications({ query: { enabled: status === "filled" || status === "offered", queryKey: getListNotificationsQueryKey() } });
  const send = useSendCoverOffers();
  const cancel = useCancelCoverage();

  const [picked, setPicked] = useState<Set<number> | null>(null);
  const [message, setMessage] = useState("");
  const [showUnavail, setShowUnavail] = useState(false);

  const eligible = cand.data?.eligible ?? [];
  const unavailable = cand.data?.unavailable ?? [];
  const selectable = (c: Candidate) => c.offerStatus !== "pending" && c.offerStatus !== "accepted";
  const firstPick = eligible.find(selectable);
  const sel = picked ?? new Set(firstPick ? [firstPick.employee.id] : []);
  const toggle = (eid: number) => { const n = new Set(sel); if (n.has(eid)) n.delete(eid); else n.add(eid); setPicked(n); };

  const sendOffers = () => {
    const ids = [...sel].filter((x) => eligible.some((c) => c.employee.id === x && selectable(c)));
    if (!ids.length) return;
    send.mutate({ caseId: id, data: { employeeIds: ids, message: message.trim() || null } }, {
      onSuccess: () => { invalidate(); setPicked(new Set()); setMessage(""); toast({ title: `Offer sent to ${ids.length}`, description: "The first person to accept gets the shift." }); },
      onError: (e) => toast({ title: "Could not send offers", description: errMsg(e), variant: "destructive" }),
    });
  };

  if (cs.isLoading) return <Panel><SkeletonRows n={5} h={70} /></Panel>;
  if (cs.isError || !cs.data) return <Panel><ErrorState what="this case" onRetry={() => cs.refetch()} /></Panel>;
  const c = cs.data;
  const caseNotes = (notes.data ?? []).filter((n) => n.caseId === c.id);
  const selCount = [...sel].filter((x) => eligible.some((e) => e.employee.id === x && selectable(e))).length;

  return (
    <div>
      <Link href="/coverage" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground mb-4" data-testid="link-back"><ArrowLeft className="h-4 w-4" /> Cover queue</Link>
      <PageHeader eyebrow={`Case #${c.id} · opened ${relative(c.openedAt)}`} title={`${c.shift.roleName}, ${fmtYmd(c.shift.date)}`}
        actions={<>
          <Pill status={c.status} className="text-xs py-1 px-2.5" />
          {active && (
            <AlertDialog>
              <AlertDialogTrigger asChild><Button variant="outline" size="sm" data-testid="button-cancel-case"><Ban className="h-4 w-4 mr-1.5" />Cancel case</Button></AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Cancel this cover case?</AlertDialogTitle>
                  <AlertDialogDescription>The shift stays uncovered and leaves the queue. Any pending offers are withdrawn.</AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Keep it open</AlertDialogCancel>
                  <AlertDialogAction data-testid="button-confirm-cancel" onClick={() => cancel.mutate({ caseId: id }, {
                    onSuccess: () => { invalidate(); toast({ title: "Case cancelled" }); },
                    onError: (e) => toast({ title: "Could not cancel", description: errMsg(e), variant: "destructive" }),
                  })}>Cancel case</AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          )}
        </>} />

      <div className="grid lg:grid-cols-[320px_1fr] gap-6">
        <div className="space-y-4">
          <Panel title="The gap">
            <div className="p-4">
              <div className="font-display text-4xl font-extrabold tnum leading-none">{fmtHm(c.shift.startTime)}</div>
              <div className="font-mono text-sm text-muted-foreground mt-1">to {fmtHm(c.shift.endTime)} · {c.shift.hours.toFixed(1)}h</div>
              <div className="mt-4 space-y-2 text-sm">
                <div className="flex items-center gap-2"><Clock className="h-4 w-4 text-muted-foreground" />{fmtYmd(c.shift.date)}, starts {startsIn(c.startsInHours)}</div>
                <div className="flex items-center gap-2"><Users className="h-4 w-4 text-muted-foreground" />{c.shift.roleName}{c.shift.patternName ? ` · ${c.shift.patternName}` : ""}</div>
              </div>
              {c.urgent && <div className="mt-3 text-xs font-mono uppercase tracking-wider px-2 py-1 rounded stripes text-[hsl(32_80%_26%)] inline-block">Urgent · under 48h</div>}
              {c.shift.notes && <p className="mt-3 text-sm bg-secondary rounded p-2.5">{c.shift.notes}</p>}
            </div>
          </Panel>
          <Panel title="On leave">
            <Link href={`/team/${c.originalEmployee.id}`} className="block p-4 hover:bg-secondary/50" data-testid="link-original-employee">
              <div className="flex items-center gap-3">
                <Initials name={c.originalEmployee.name} className="h-10 w-10 text-xs" />
                <div className="min-w-0 flex-1">
                  <div className="font-medium">{c.originalEmployee.name}</div>
                  <div className="text-xs text-muted-foreground truncate">{c.originalEmployee.roleName ?? ""}</div>
                </div>
                <Tag className="bg-accent/25 text-[hsl(32_80%_26%)]">{c.leave.leaveType}</Tag>
              </div>
              <div className="mt-2 font-mono text-xs text-muted-foreground">{fmtDate(c.leave.startDate)}{c.leave.endDate !== c.leave.startDate && ` – ${fmtDate(c.leave.endDate)}`}</div>
              {c.leave.reason && <p className="mt-1.5 text-sm">{c.leave.reason}</p>}
            </Link>
          </Panel>
          {c.status === "filled" && c.replacementEmployee && (
            <Panel title="Covered by" className="relative overflow-hidden">
              <div className="flex items-center gap-3 p-4">
                <Initials name={c.replacementEmployee.name} className="h-10 w-10 text-xs" />
                <div>
                  <div className="font-medium" data-testid="text-replacement">{c.replacementEmployee.name}</div>
                  <div className="text-xs text-muted-foreground">{c.filledAt ? `Accepted ${fmtDateTime(c.filledAt)}` : "Accepted"}</div>
                </div>
              </div>
              <div className="stamp absolute right-3 top-12 border-2 border-primary text-primary rounded px-2 py-0.5 font-mono text-xs font-bold uppercase tracking-widest">Filled</div>
            </Panel>
          )}
          {c.offers.length > 0 && (
            <Panel title={`Offers · ${c.offers.filter((o) => o.status === "pending").length} waiting`}>
              <div className="divide-y">{c.offers.map((o) => <OfferRow key={o.id} o={o} caseId={c.id} canWithdraw={active} />)}</div>
              {c.status === "offered" && <div className="px-4 py-2 border-t font-mono text-[10px] uppercase tracking-wider text-muted-foreground flex items-center gap-1.5"><span className="h-1.5 w-1.5 rounded-full bg-[hsl(200_60%_40%)] pulse-dot" />Checking for replies every 10s</div>}
            </Panel>
          )}
        </div>

        <div className="min-w-0 space-y-4">
          {active ? (
            <>
              <Panel title={`Who can cover · ${c.shift.roleName}`} action={cand.data && <span className="font-mono text-[11px] text-muted-foreground">{eligible.length} eligible · {unavailable.length} not available</span>}>
                {cand.isLoading ? <SkeletonRows n={4} h={100} /> : cand.isError ? <ErrorState what="candidates" onRetry={() => cand.refetch()} /> : eligible.length ? (
                  <div className="divide-y">{eligible.map((x, i) => (
                    <CandidateRow key={x.employee.id} c={x} rank={i} checked={sel.has(x.employee.id) || x.offerStatus === "pending"} disabled={!selectable(x)} onToggle={() => toggle(x.employee.id)} />
                  ))}</div>
                ) : (
                  <Empty icon={<Users className="h-5 w-5" />} title="Nobody is eligible" body="Everyone in this role is on leave, already working, or would break a rule. See who is not available below." />
                )}
                {unavailable.length > 0 && (
                  <div className="border-t">
                    <button onClick={() => setShowUnavail(!showUnavail)} className="w-full flex items-center justify-between px-4 h-10 text-sm text-muted-foreground hover:text-foreground" data-testid="button-toggle-unavailable">
                      <span>Not available ({unavailable.length})</span><ChevronDown className={cn("h-4 w-4 transition-transform", showUnavail && "rotate-180")} />
                    </button>
                    {showUnavail && (
                      <div className="divide-y bg-secondary/30">
                        {unavailable.map((u) => (
                          <div key={u.employee.id} className="flex items-start gap-3 px-4 py-2.5 opacity-80" data-testid={`row-unavailable-${u.employee.id}`}>
                            <Initials name={u.employee.name} className="h-7 w-7 text-[10px] grayscale" />
                            <div className="min-w-0">
                              <div className="text-sm">{u.employee.name}</div>
                              <div className="flex flex-wrap gap-1 mt-1">{u.reasons.map((r) => <Tag key={r}>{r}</Tag>)}</div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </Panel>

              {eligible.some(selectable) && (
                <Panel title="Send cover offer" className="sticky bottom-4 shadow-lg shadow-foreground/5">
                  <div className="p-4 grid md:grid-cols-[1fr_auto] gap-4 items-end">
                    <Textarea value={message} onChange={(e) => setMessage(e.target.value)} placeholder="Optional message, e.g. Can you help? Kitchen is short on Saturday" className="min-h-[72px] resize-none" data-testid="input-message" />
                    <div className="flex flex-col gap-1.5 md:items-end">
                      <Button size="lg" onClick={sendOffers} disabled={!selCount || send.isPending} data-testid="button-send-offers" className="font-semibold">
                        <Send className="h-4 w-4 mr-1.5" />{send.isPending ? "Sending..." : `Send offer to ${selCount}`}
                      </Button>
                      <span className="text-xs text-muted-foreground">First to accept gets the shift. Others are told it is taken.</span>
                    </div>
                  </div>
                </Panel>
              )}

              {c.status === "offered" && caseNotes.length > 0 && (
                <Panel title="Messages for this case"><NotificationList items={caseNotes} /></Panel>
              )}
            </>
          ) : (
            <Panel title={c.status === "filled" ? "Messages for this case" : "Case closed"}>
              {c.status === "filled" && (
                <div className="px-4 py-2.5 border-b text-xs bg-accent/10 text-[hsl(32_70%_26%)]">
                  Messages show in each person's in-app inbox. Email is queued: no email provider is connected yet.
                </div>
              )}
              {notes.isLoading && c.status === "filled" ? <SkeletonRows n={3} /> : caseNotes.length ? <NotificationList items={caseNotes} /> : (
                <Empty icon={<Mail className="h-5 w-5" />} title={c.status === "cancelled" ? "Cancelled without cover" : "No messages"} body={c.status === "cancelled" ? "This shift was taken out of the queue." : "Nothing was sent for this case."} />
              )}
            </Panel>
          )}
        </div>
      </div>
    </div>
  );
}
