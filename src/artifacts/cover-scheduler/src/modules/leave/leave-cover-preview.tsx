import { Check, X, Users, AlertTriangle } from "lucide-react";
import { useGetLeaveCoverPreview, getGetLeaveCoverPreviewQueryKey, type Leave } from "@workspace/api-client-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { Initials, SkeletonRows, ErrorState } from "@/components/kit";
import { fmtDate, fmtYmd, fmtHm } from "@/lib/time";
import { cn } from "@/lib/utils";

/** Before deciding on pending leave: the shifts it would leave empty, and the best people to cover each.
 *  Read-only. Nothing is opened or sent until the manager approves. */
export function LeaveCoverPreviewDialog({ leave, onOpenChange, onApprove, onReject, busy }: {
  leave: Leave | null; onOpenChange: (v: boolean) => void; onApprove: (l: Leave) => void; onReject: (l: Leave) => void; busy: boolean;
}) {
  const id = leave?.id ?? 0;
  const q = useGetLeaveCoverPreview(id, { query: { enabled: !!leave, queryKey: getGetLeaveCoverPreviewQueryKey(id), staleTime: 0 } });
  const shifts = q.data?.shifts ?? [];
  const uncoverable = shifts.filter((s) => s.eligibleCount === 0).length;

  return (
    <Dialog open={!!leave} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90dvh] overflow-y-auto">
        {leave && (
          <>
            <DialogHeader>
              <DialogTitle className="font-display text-xl">Cover check: {leave.employeeName}</DialogTitle>
              <DialogDescription>
                {leave.leaveType} leave, {fmtDate(leave.startDate)}{leave.endDate !== leave.startDate && ` to ${fmtDate(leave.endDate)}`}.
                {" "}Who could take each shift if you approve. Nothing is sent until you approve and send offers.
              </DialogDescription>
            </DialogHeader>

            {q.isLoading ? <SkeletonRows n={3} h={72} /> : q.isError ? <ErrorState what="the cover check" onRetry={() => q.refetch()} /> : !shifts.length ? (
              <div className="rounded-md border px-4 py-6 text-sm text-muted-foreground" data-testid="text-preview-none">
                No upcoming rostered shifts fall in this leave, so approving it opens no cover cases.
              </div>
            ) : (
              <div className="space-y-3" data-testid="list-cover-preview">
                <div className={cn("rounded-md px-3 py-2 text-sm flex items-center gap-2", uncoverable ? "bg-destructive/10 text-destructive" : "bg-primary/[0.07] text-foreground")} data-testid="text-preview-summary">
                  {uncoverable ? <AlertTriangle className="h-4 w-4 shrink-0" /> : <Users className="h-4 w-4 shrink-0 text-primary" />}
                  {shifts.length} shift{shifts.length > 1 ? "s" : ""} would need cover.
                  {uncoverable ? ` ${uncoverable} ha${uncoverable > 1 ? "ve" : "s"} nobody available within the rules.` : " Every one has at least one available person."}
                </div>
                {shifts.map((p) => (
                  <div key={p.shift.id} className="rounded-lg border" data-testid={`preview-shift-${p.shift.id}`}>
                    <div className="flex items-center justify-between gap-3 px-3 py-2 border-b bg-secondary/40">
                      <div className="text-sm">
                        <span className="font-medium">{fmtYmd(p.shift.date)}</span>
                        <span className="font-mono text-xs text-muted-foreground ml-2">{fmtHm(p.shift.startTime)}–{fmtHm(p.shift.endTime)} · {p.shift.roleName}</span>
                      </div>
                      <div className="font-mono text-[11px] text-muted-foreground shrink-0">
                        <span className={p.eligibleCount ? "text-primary font-semibold" : "text-destructive font-semibold"}>{p.eligibleCount} available</span>
                        {p.unavailableCount > 0 && ` · ${p.unavailableCount} ruled out`}
                      </div>
                    </div>
                    {p.topCandidates.length ? (
                      <ol className="divide-y">
                        {p.topCandidates.map((c, i) => (
                          <li key={c.employee.id} className="flex items-center gap-3 px-3 py-2" data-testid={`preview-candidate-${p.shift.id}-${c.employee.id}`}>
                            <span className="font-mono text-[10px] text-muted-foreground w-3">{i + 1}</span>
                            <Initials name={c.employee.name} className="h-7 w-7 text-[10px]" />
                            <div className="min-w-0 flex-1">
                              <div className="text-sm font-medium truncate">{c.employee.name}</div>
                              <div className="text-xs text-muted-foreground truncate">
                                {c.hoursAfter.toFixed(1)}h of {c.maxHoursPerWeek}h this week after this shift
                                {c.warnings.length ? ` · ${c.warnings[0]}` : ""}
                              </div>
                            </div>
                            <span className="font-mono text-xs tnum font-semibold">{c.score}</span>
                          </li>
                        ))}
                      </ol>
                    ) : (
                      <div className="px-3 py-3 text-sm text-destructive">Nobody can take this shift without breaking the rules.</div>
                    )}
                  </div>
                ))}
              </div>
            )}

            <DialogFooter className="gap-2">
              <Button variant="ghost" onClick={() => onOpenChange(false)}>Close</Button>
              <Button variant="outline" disabled={busy} onClick={() => onReject(leave)} data-testid="button-preview-reject"><X className="h-4 w-4 mr-1" />Reject</Button>
              <Button disabled={busy} onClick={() => onApprove(leave)} data-testid="button-preview-approve"><Check className="h-4 w-4 mr-1" />Approve</Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
