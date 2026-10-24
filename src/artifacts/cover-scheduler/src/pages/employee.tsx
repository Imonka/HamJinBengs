import { useState } from "react";
import { Link, useParams } from "wouter";
import { ArrowLeft, Pencil, Power, Mail, Phone, KeyRound } from "lucide-react";
import { useGetEmployee, useUpdateEmployee, useDeactivateEmployee, useResetEmployeePin, getGetEmployeeQueryKey } from "@workspace/api-client-react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { useToast } from "@/hooks/use-toast";
import { Panel, Pill, Initials, SkeletonRows, ErrorState, Tag } from "@/components/kit";
import { PinInput } from "@/components/account";
import { EmployeeDialog } from "@/pages/team";
import { fmtYmd, fmtHm, fmtDate } from "@/lib/time";
import { errMsg } from "@/lib/api-error";
import { useInvalidateOps } from "@/lib/invalidate";

export default function EmployeePage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const { toast } = useToast();
  const invalidate = useInvalidateOps();
  const [editing, setEditing] = useState(false);
  const [pinOpen, setPinOpen] = useState(false);
  const [pin, setPin] = useState("");
  const q = useGetEmployee(id, { query: { enabled: !!id, queryKey: getGetEmployeeQueryKey(id) } });
  const update = useUpdateEmployee();
  const deactivate = useDeactivateEmployee();
  const reset = useResetEmployeePin();

  if (q.isLoading) return <Panel><SkeletonRows n={4} h={64} /></Panel>;
  if (q.isError || !q.data) return <Panel><ErrorState what="this person" onRetry={() => q.refetch()} /></Panel>;
  const { employee: e, upcomingShifts, leave } = q.data;
  const fail = (t: string) => (err: unknown) => toast({ title: t, description: errMsg(err), variant: "destructive" });

  return (
    <div>
      <Link href="/team" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground mb-4" data-testid="link-back-team"><ArrowLeft className="h-4 w-4" /> Team</Link>
      <div className="rounded-lg border bg-card p-5 md:p-6 flex flex-col md:flex-row gap-5 md:items-center mb-6 rise">
        <Initials name={e.name} className="h-16 w-16 text-lg rounded-lg" />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h1 className="font-display text-3xl font-bold" data-testid="text-employee-name">{e.name}</h1>
            <Pill status={e.access} />
            {e.onLeaveToday && <Tag className="bg-accent/25 text-[hsl(32_80%_26%)]">on leave today</Tag>}
            {!e.active && <Tag>inactive</Tag>}
          </div>
          <div className="text-sm text-muted-foreground mt-1">{e.roleName ?? "No role"}</div>
          <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2 text-sm">
            <span className="inline-flex items-center gap-1.5"><Mail className="h-3.5 w-3.5 text-muted-foreground" />{e.email}</span>
            {e.phone && <span className="inline-flex items-center gap-1.5"><Phone className="h-3.5 w-3.5 text-muted-foreground" />{e.phone}</span>}
            <span className="font-mono text-xs self-center">{e.hoursThisWeek.toFixed(1)}h this week · limit {e.maxHoursPerWeek != null ? `${e.maxHoursPerWeek}h (personal)` : "branch rule"} · Orbyte {e.orbyteId ?? "unlinked"}</span>
          </div>
        </div>
        <div className="flex gap-2 flex-wrap">
          <Button variant="outline" onClick={() => setEditing(true)} data-testid="button-edit-employee"><Pencil className="h-4 w-4 mr-1.5" />Edit</Button>
          <Button variant="outline" onClick={() => setPinOpen(true)} data-testid="button-reset-pin"><KeyRound className="h-4 w-4 mr-1.5" />Reset PIN</Button>
          {e.active ? (
            <AlertDialog>
              <AlertDialogTrigger asChild><Button variant="outline" className="text-destructive hover:text-destructive" data-testid="button-deactivate"><Power className="h-4 w-4 mr-1.5" />Deactivate</Button></AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader><AlertDialogTitle>Deactivate {e.name}?</AlertDialogTitle>
                  <AlertDialogDescription>They can no longer sign in, will not be rostered, and will not be asked to cover. Their history stays.</AlertDialogDescription></AlertDialogHeader>
                <AlertDialogFooter><AlertDialogCancel>Keep active</AlertDialogCancel>
                  <AlertDialogAction data-testid="button-confirm-deactivate" onClick={() => deactivate.mutate({ employeeId: id }, {
                    onSuccess: () => { invalidate(); toast({ title: "Deactivated", description: e.name }); }, onError: fail("Could not deactivate"),
                  })}>Deactivate</AlertDialogAction></AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          ) : (
            <Button variant="outline" disabled={update.isPending} data-testid="button-reactivate" onClick={() => update.mutate({
              employeeId: id, data: { name: e.name, email: e.email, phone: e.phone, access: e.access, roleId: e.roleId, maxHoursPerWeek: e.maxHoursPerWeek, orbyteId: e.orbyteId, active: true },
            }, { onSuccess: () => { invalidate(); toast({ title: "Reactivated" }); }, onError: fail("Could not reactivate") })}><Power className="h-4 w-4 mr-1.5" />Reactivate</Button>
          )}
        </div>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        <Panel title="Upcoming shifts" delay={60}>
          {!upcomingShifts.length ? <div className="px-4 py-6 text-sm text-muted-foreground">Nothing on the roster ahead.</div> : (
            <div className="divide-y">{upcomingShifts.slice(0, 20).map((s) => (
              <div key={s.id} className="flex items-center gap-4 px-4 py-2.5" data-testid={`row-shift-${s.id}`}>
                <div className="w-28"><div className="font-mono text-[10.5px] uppercase text-muted-foreground">{fmtYmd(s.date)}</div><div className="font-display font-bold tnum">{fmtHm(s.startTime)}</div></div>
                <div className="flex-1 text-sm min-w-0 truncate">{s.roleName}{s.patternName ? ` · ${s.patternName}` : ""}<div className="text-xs text-muted-foreground">until {fmtHm(s.endTime)} · {s.source}</div></div>
                <Pill status={s.status} />
              </div>
            ))}</div>
          )}
        </Panel>
        <Panel title="Leave" delay={100}>
          {!leave.length ? <div className="px-4 py-6 text-sm text-muted-foreground">No leave on record.</div> : (
            <div className="divide-y">{leave.map((l) => (
              <div key={l.id} className="flex items-center gap-4 px-4 py-2.5" data-testid={`row-leave-${l.id}`}>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium">{l.leaveType}</div>
                  <div className="font-mono text-xs text-muted-foreground">{fmtDate(l.startDate)}{l.endDate !== l.startDate && ` – ${fmtDate(l.endDate)}`} · {l.affectedShiftCount} shifts</div>
                </div>
                <Pill status={l.status} />
              </div>
            ))}</div>
          )}
        </Panel>
      </div>
      <EmployeeDialog open={editing} onOpenChange={setEditing} employee={e} />
      <Dialog open={pinOpen} onOpenChange={(v) => { setPinOpen(v); if (!v) setPin(""); }}>
        <DialogContent className="max-w-sm">
          <DialogHeader><DialogTitle className="font-display text-xl">Reset PIN for {e.name}</DialogTitle><DialogDescription>Tell them the new PIN in person. They can change it after signing in.</DialogDescription></DialogHeader>
          <div className="space-y-1.5"><Label>New PIN (4 to 8 digits)</Label><PinInput value={pin} onChange={setPin} testId="input-reset-pin" autoFocus /></div>
          <DialogFooter><Button variant="ghost" onClick={() => setPinOpen(false)}>Cancel</Button>
            <Button disabled={!/^\d{4,8}$/.test(pin) || reset.isPending} data-testid="button-confirm-reset-pin" onClick={() => reset.mutate({ employeeId: id, data: { pin } }, {
              onSuccess: () => { setPinOpen(false); setPin(""); toast({ title: "PIN reset", description: e.name }); }, onError: fail("Could not reset PIN"),
            })}>Set PIN</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
