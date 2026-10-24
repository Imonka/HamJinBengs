import { useEffect, useState } from "react";
import { Link } from "wouter";
import { ChevronLeft, ChevronRight, Plus, Trash2, Wand2, AlertTriangle } from "lucide-react";
import {
  useGetRosterWeek, useGenerateRoster, useListShifts, useCreateShift, useUpdateShift, useDeleteShift, useListEmployees, useListRoles,
  getGetRosterWeekQueryKey,
  type Shift, type ShiftInput, type GenerateRosterResult, type RosterEmployeeHours,
} from "@workspace/api-client-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { PageHeader, Panel, ErrorState, Pill } from "@/components/kit";
import { addDays, todayKey, fmtDate, fmtYmd, fmtHm, WEEKDAYS } from "@/lib/time";
import { errMsg, errStatus, errViolations } from "@/lib/api-error";
import { useInvalidateOps } from "@/lib/invalidate";
import { cn } from "@/lib/utils";

type ShiftTarget = { shiftId: number } | { date: string } | null;
type Form = { employeeId: string; roleId: string; date: string; startTime: string; endTime: string; notes: string };

function ShiftDialog({ target, shift, onClose }: { target: ShiftTarget; shift: Shift | null; onClose: () => void }) {
  const emps = useListEmployees({ active: true });
  const roles = useListRoles();
  const create = useCreateShift();
  const update = useUpdateShift();
  const del = useDeleteShift();
  const invalidate = useInvalidateOps();
  const { toast } = useToast();
  const [f, setF] = useState<Form>({ employeeId: "", roleId: "", date: "", startTime: "07:00", endTime: "15:00", notes: "" });
  const [violations, setViolations] = useState<string[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    if (!target) return;
    setViolations(null); setErr(null);
    if (shift) setF({ employeeId: shift.employeeId ? String(shift.employeeId) : "", roleId: String(shift.roleId), date: shift.date, startTime: shift.startTime, endTime: shift.endTime, notes: shift.notes ?? "" });
    else if ("date" in target) setF({ employeeId: "", roleId: "", date: target.date, startTime: "07:00", endTime: "15:00", notes: "" });
  }, [target, shift]);
  const pickEmp = (v: string) => {
    const e = emps.data?.find((x) => String(x.id) === v);
    setF((x) => ({ ...x, employeeId: v, roleId: x.roleId || (e?.roleId ? String(e.roleId) : "") }));
  };
  const valid = f.employeeId && f.roleId && f.date && f.startTime && f.endTime;
  const done = (msg: string) => { invalidate(); onClose(); toast({ title: msg }); };
  const onErr = (e: unknown) => {
    const v = errViolations(e);
    if (errStatus(e) === 409 && v.length) { setViolations(v); setErr(errMsg(e)); }
    else { setErr(errMsg(e, "Could not save shift.")); setViolations(null); }
  };
  const save = (override: boolean) => {
    const data: ShiftInput = { employeeId: Number(f.employeeId), roleId: Number(f.roleId), date: f.date, startTime: f.startTime, endTime: f.endTime, notes: f.notes || null, override };
    if (shift) update.mutate({ shiftId: shift.id, data }, { onSuccess: () => done("Shift updated"), onError: onErr });
    else create.mutate({ data }, { onSuccess: () => done("Shift added"), onError: onErr });
  };
  const pending = create.isPending || update.isPending || del.isPending;
  return (
    <Dialog open={!!target} onOpenChange={(v) => { if (!v) onClose(); }}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="font-display text-xl">{shift ? "Edit shift" : "New shift"}</DialogTitle>
          <DialogDescription>{shift?.patternName ? `Part of ${shift.patternName}. ` : ""}Branch-local time.</DialogDescription>
        </DialogHeader>
        <div className="grid grid-cols-2 gap-3">
          <div className="col-span-2 space-y-1.5"><Label>Employee</Label>
            <Select value={f.employeeId} onValueChange={pickEmp}>
              <SelectTrigger data-testid="select-shift-employee"><SelectValue placeholder="Choose a person" /></SelectTrigger>
              <SelectContent>{(emps.data ?? []).map((e) => <SelectItem key={e.id} value={String(e.id)}>{e.name}{e.roleName ? ` · ${e.roleName}` : ""}</SelectItem>)}</SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5"><Label>Role</Label>
            <Select value={f.roleId} onValueChange={(v) => setF({ ...f, roleId: v })}>
              <SelectTrigger data-testid="select-shift-role"><SelectValue placeholder="Role" /></SelectTrigger>
              <SelectContent>{(roles.data ?? []).map((r) => <SelectItem key={r.id} value={String(r.id)}>{r.name}</SelectItem>)}</SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5"><Label>Date</Label><Input type="date" value={f.date} onChange={(e) => setF({ ...f, date: e.target.value })} data-testid="input-shift-date" /></div>
          <div className="space-y-1.5"><Label>Starts</Label><Input type="time" value={f.startTime} onChange={(e) => setF({ ...f, startTime: e.target.value })} data-testid="input-shift-start" /></div>
          <div className="space-y-1.5"><Label>Ends</Label><Input type="time" value={f.endTime} onChange={(e) => setF({ ...f, endTime: e.target.value })} data-testid="input-shift-end" /></div>
          <div className="col-span-2 space-y-1.5"><Label>Notes</Label><Textarea value={f.notes} onChange={(e) => setF({ ...f, notes: e.target.value })} className="min-h-[56px]" data-testid="input-shift-notes" /></div>
        </div>
        {violations ? (
          <div className="rounded-md border border-accent bg-accent/10 p-3 text-sm" data-testid="box-violations">
            <div className="font-medium flex items-center gap-1.5"><AlertTriangle className="h-4 w-4 text-[hsl(32_80%_32%)]" />{err ?? "This breaks scheduling rules"}</div>
            <ul className="mt-1.5 space-y-0.5 list-disc pl-5 text-[13px]">{violations.map((v) => <li key={v}>{v}</li>)}</ul>
          </div>
        ) : err && <p className="text-sm text-destructive">{err}</p>}
        <DialogFooter className="sm:justify-between">
          {shift ? (
            <Button variant="ghost" className="text-destructive hover:text-destructive" disabled={pending} data-testid="button-delete-shift"
              onClick={() => { if (confirm("Delete this shift?")) del.mutate({ shiftId: shift.id }, { onSuccess: () => done("Shift deleted"), onError: (e) => setErr(errMsg(e)) }); }}>
              <Trash2 className="h-4 w-4 mr-1.5" />Delete
            </Button>
          ) : <span />}
          <div className="flex gap-2">
            {violations && <Button variant="outline" disabled={pending} onClick={() => save(true)} data-testid="button-save-anyway">Save anyway</Button>}
            <Button disabled={!valid || pending} onClick={() => save(false)} data-testid="button-save-shift">{pending ? "Saving..." : "Save shift"}</Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function HoursTable({ rows }: { rows: RosterEmployeeHours[] }) {
  if (!rows.length) return <div className="px-4 py-6 text-sm text-muted-foreground">Nobody is rostered this week.</div>;
  return (
    <div className="divide-y">
      {[...rows].sort((a, b) => b.hours - a.hours).map((e) => {
        const over = e.hours > e.maxHours;
        return (
          <Link key={e.employeeId} href={`/team/${e.employeeId}`} className="grid grid-cols-[1fr_120px] gap-3 items-center px-4 py-2 hover:bg-secondary/50" data-testid={`row-hours-${e.employeeId}`}>
            <div className="min-w-0"><div className="text-sm truncate">{e.name}</div><div className="text-[11px] text-muted-foreground truncate">{e.roleName ?? ""}</div></div>
            <div>
              <div className="flex justify-between font-mono text-[10.5px] tnum"><span className={over ? "text-destructive font-semibold" : ""}>{e.hours.toFixed(1)}/{e.maxHours}h</span><span className="text-muted-foreground">{e.days}d</span></div>
              <div className="h-1.5 rounded-full bg-secondary overflow-hidden mt-1"><div className={cn("h-full", over ? "bg-destructive" : "bg-primary")} style={{ width: `${Math.min(100, (e.hours / e.maxHours) * 100)}%` }} /></div>
            </div>
          </Link>
        );
      })}
    </div>
  );
}

function GenerateDialog({ open, onOpenChange, weekStart }: { open: boolean; onOpenChange: (v: boolean) => void; weekStart: string }) {
  const gen = useGenerateRoster();
  const invalidate = useInvalidateOps();
  const { toast } = useToast();
  const [replace, setReplace] = useState(false);
  const [result, setResult] = useState<GenerateRosterResult | null>(null);
  const close = (v: boolean) => { onOpenChange(v); if (!v) setResult(null); };
  const run = () => gen.mutate({ data: { weekStart, replaceExisting: replace } }, {
    onSuccess: (r) => { setResult(r); invalidate(); },
    onError: (e) => toast({ title: "Could not generate", description: errMsg(e), variant: "destructive" }),
  });
  return (
    <Dialog open={open} onOpenChange={close}>
      <DialogContent className="max-w-2xl">
        <DialogHeader><DialogTitle className="font-display text-xl">Generate roster · week of {fmtDate(weekStart)}</DialogTitle>
          <DialogDescription>Fills every active shift pattern with people in the right role, keeping to your hour, day and rest rules. Leave is respected.</DialogDescription></DialogHeader>
        {!result ? (
          <>
            <label className="flex items-center justify-between gap-4 rounded-md border px-3 py-3 text-sm">
              <div><div className="font-medium">Replace previously generated shifts</div><div className="text-xs text-muted-foreground">Removes generated future shifts this week first. Manual and cover shifts stay.</div></div>
              <Switch checked={replace} onCheckedChange={setReplace} data-testid="switch-replace-existing" />
            </label>
            <DialogFooter><Button variant="ghost" onClick={() => close(false)}>Cancel</Button><Button onClick={run} disabled={gen.isPending} data-testid="button-run-generate"><Wand2 className="h-4 w-4 mr-1.5" />{gen.isPending ? "Generating..." : "Generate"}</Button></DialogFooter>
          </>
        ) : (
          <div className="space-y-4" data-testid="generate-result">
            <div className="grid grid-cols-3 border rounded-lg divide-x">
              {([["Shifts created", result.created], ["Removed", result.removed], ["Gaps left", result.gaps.reduce((a, g) => a + g.missing, 0)]] as const).map(([k, v]) => (
                <div key={k} className="p-3"><div className="font-mono text-[10px] uppercase text-muted-foreground">{k}</div><div className="font-display text-2xl font-bold tnum">{v}</div></div>
              ))}
            </div>
            {result.gaps.length > 0 && (
              <div className="rounded-md border border-accent/60 max-h-48 overflow-auto">
                <div className="px-3 py-2 text-xs font-medium bg-accent/15 border-b border-accent/40">Could not fill</div>
                {result.gaps.map((g, i) => (
                  <div key={i} className="grid grid-cols-[110px_1fr_40px] gap-2 px-3 py-1.5 text-xs border-b last:border-0">
                    <span className="font-mono">{fmtYmd(g.date)}</span>
                    <span><span className="font-medium">{g.patternName} · {g.roleName}</span> <span className="text-muted-foreground">{g.reason}</span></span>
                    <span className="font-mono text-right text-[hsl(32_80%_32%)] font-semibold">-{g.missing}</span>
                  </div>
                ))}
              </div>
            )}
            <div className="rounded-md border max-h-56 overflow-auto"><HoursTable rows={result.employees} /></div>
            <DialogFooter><Button onClick={() => close(false)}>Done</Button></DialogFooter>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

export default function Schedule() {
  const [anchor, setAnchor] = useState(() => todayKey());
  const [target, setTarget] = useState<ShiftTarget>(null);
  const [genOpen, setGenOpen] = useState(false);
  const roles = useListRoles();
  const params = { start: anchor };
  const q = useGetRosterWeek(params, { query: { queryKey: getGetRosterWeekQueryKey(params) } });
  const w = q.data;
  const today = todayKey();
  const color = (rid: number) => roles.data?.find((r) => r.id === rid)?.color ?? "#888";
  const weekShifts = useListShifts(w ? { from: w.weekStart, to: w.weekEnd } : undefined, { query: { enabled: !!w, queryKey: ["/api/shifts", w?.weekStart, w?.weekEnd] } });
  const allShifts: Shift[] = [...(w ? w.days.flatMap((d) => d.otherShifts) : []), ...(weekShifts.data ?? [])];
  const editing = target && "shiftId" in target ? allShifts.find((s) => s.id === target.shiftId) ?? null : null;
  const openShift = (id: number) => setTarget({ shiftId: id });

  return (
    <div>
      <PageHeader eyebrow="Roster" title={w ? `Week of ${fmtDate(w.weekStart)}` : "Roster"}
        sub={w && <span className="font-mono text-xs">{w.filled}/{w.required} filled · <span className={w.gaps ? "text-[hsl(32_80%_30%)] font-semibold" : ""}>{w.gaps} gaps</span></span>}
        actions={<>
          <div className="inline-flex rounded-md border bg-card">
            <Button variant="ghost" size="icon" onClick={() => setAnchor(addDays(w?.weekStart ?? anchor, -7))} data-testid="button-prev-week"><ChevronLeft className="h-4 w-4" /></Button>
            <Button variant="ghost" onClick={() => setAnchor(today)} data-testid="button-this-week">This week</Button>
            <Button variant="ghost" size="icon" onClick={() => setAnchor(addDays(w?.weekStart ?? anchor, 7))} data-testid="button-next-week"><ChevronRight className="h-4 w-4" /></Button>
          </div>
          <Button variant="outline" onClick={() => setTarget({ date: w?.days.find((d) => d.date === today)?.date ?? w?.weekStart ?? today })} data-testid="button-add-shift"><Plus className="h-4 w-4 mr-1.5" />Add shift</Button>
          <Button onClick={() => setGenOpen(true)} disabled={!w} data-testid="button-generate"><Wand2 className="h-4 w-4 mr-1.5" />Generate roster</Button>
        </>} />

      <div className="grid xl:grid-cols-[1fr_280px] gap-4">
        {q.isError ? <Panel><ErrorState what="the roster" onRetry={() => q.refetch()} /></Panel> : (
          <div className="overflow-x-auto -mx-4 px-4 md:mx-0 md:px-0">
            <div className="grid grid-cols-7 gap-2 min-w-[980px]">
              {(w?.days ?? Array.from({ length: 7 }, (_, i) => ({ date: String(i), weekday: i, open: true, slots: [], otherShifts: [] }))).map((d, di) => {
                const patterns = new Map<number, typeof d.slots>();
                d.slots.forEach((s) => { const l = patterns.get(s.patternId) ?? []; l.push(s); patterns.set(s.patternId, l); });
                return (
                  <div key={d.date} className={cn("rounded-lg border flex flex-col min-h-[460px] rise", d.open ? "bg-card/70" : "bg-muted/50", d.date === today && "ring-2 ring-primary/40")} style={{ animationDelay: `${di * 30}ms` }} data-testid={`col-day-${d.date}`}>
                    <div className="flex items-center justify-between px-2.5 h-10 border-b">
                      <div>
                        <span className="font-mono text-[10px] uppercase text-muted-foreground">{WEEKDAYS[d.weekday]}</span>
                        {w && <span className={cn("ml-1.5 font-display font-bold", d.date === today && "text-primary")}>{Number(d.date.slice(8))}</span>}
                      </div>
                      {d.open && w && <button onClick={() => setTarget({ date: d.date })} className="h-6 w-6 rounded grid place-items-center text-muted-foreground hover:bg-secondary hover:text-foreground" data-testid={`button-add-shift-${d.date}`}><Plus className="h-3.5 w-3.5" /></button>}
                    </div>
                    <div className="p-1.5 space-y-2 flex-1">
                      {q.isLoading ? Array.from({ length: 2 }).map((_, i) => <div key={i} className="h-28 rounded bg-muted animate-pulse" />) : !d.open ? (
                        <div className="text-center pt-10 font-mono text-[10.5px] uppercase tracking-wider text-muted-foreground">Closed</div>
                      ) : (
                        <>
                          {[...patterns.values()].map((slots) => (
                            <div key={slots[0].patternId} className="rounded-md border bg-card">
                              <div className="px-2 py-1 border-b bg-secondary/50 rounded-t-md">
                                <div className="text-[11px] font-semibold truncate">{slots[0].patternName}</div>
                                <div className="font-mono text-[10px] text-muted-foreground">{fmtHm(slots[0].startTime)}–{fmtHm(slots[0].endTime)}</div>
                              </div>
                              <div className="p-1 space-y-1">
                                {slots.map((s) => {
                                  return (
                                    <div key={s.roleId} className="text-[11px]">
                                      <div className="flex items-center justify-between px-1">
                                        <span className="flex items-center gap-1 font-medium"><span className="h-2 w-2 rounded-full" style={{ background: color(s.roleId) }} />{s.roleName}</span>
                                        <span className={cn("font-mono tnum", s.shortBy > 0 ? "text-[hsl(32_80%_30%)] font-semibold" : "text-muted-foreground")}>{Math.max(0, s.required - s.shortBy)}/{s.required}</span>
                                      </div>
                                      <div className="mt-0.5 space-y-0.5">
                                        {s.assigned.map((a) => (
                                          <button key={a.shiftId} onClick={() => openShift(a.shiftId)} data-testid={`shift-${a.shiftId}`}
                                            className={cn("w-full text-left truncate rounded px-1.5 py-0.5 border-l-2 hover:bg-secondary transition-colors",
                                              a.status === "needs_cover" && "bg-accent/20 line-through decoration-1", a.status === "covered" && "opacity-60 line-through", a.status === "cancelled" && "opacity-40 line-through")}
                                            style={{ borderLeftColor: color(s.roleId) }}>
                                            {a.employeeName ?? "Unassigned"}
                                          </button>
                                        ))}
                                        {Array.from({ length: Math.max(0, s.shortBy) }).map((_, gi) => (
                                          <button key={`gap-${gi}`} onClick={() => setTarget({ date: d.date })} className="w-full text-left rounded px-1.5 py-0.5 stripes border border-dashed border-accent text-[hsl(32_80%_28%)] font-mono text-[10px] uppercase" data-testid={`gap-${d.date}-${s.patternId}-${s.roleId}-${gi}`}>gap</button>
                                        ))}
                                      </div>
                                    </div>
                                  );
                                })}
                              </div>
                            </div>
                          ))}
                          {d.otherShifts.length > 0 && (
                            <div className="space-y-1">
                              <div className="font-mono text-[9.5px] uppercase tracking-wider text-muted-foreground px-1 pt-1">Other shifts</div>
                              {d.otherShifts.map((s) => (
                                <button key={s.id} onClick={() => openShift(s.id)} data-testid={`shift-${s.id}`}
                                  className={cn("w-full text-left rounded-md border px-2 py-1 text-[11px] border-l-[3px] hover:bg-secondary/60", s.source === "cover" && "bg-primary/[0.06]")} style={{ borderLeftColor: color(s.roleId) }}>
                                  <div className="font-mono text-[10px] tnum">{fmtHm(s.startTime)}–{fmtHm(s.endTime)}</div>
                                  <div className="font-medium truncate">{s.employeeName ?? "Unassigned"}</div>
                                  <div className="flex items-center justify-between gap-1"><span className="text-muted-foreground truncate">{s.roleName} · {s.source}</span>{s.status !== "scheduled" && <Pill status={s.status} className="text-[9px] px-1" />}</div>
                                </button>
                              ))}
                            </div>
                          )}
                          {!d.slots.length && !d.otherShifts.length && <div className="text-[11px] text-muted-foreground/70 text-center pt-6">No shifts</div>}
                        </>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
        <Panel title="Hours this week" className="self-start xl:sticky xl:top-6">
          {q.isLoading ? <div className="p-4 space-y-2">{Array.from({ length: 6 }).map((_, i) => <div key={i} className="h-8 rounded bg-muted animate-pulse" />)}</div> : <HoursTable rows={w?.employees ?? []} />}
        </Panel>
      </div>
      <p className="mt-4 text-xs text-muted-foreground">Struck-through names are on leave. Fill those from the <Link href="/coverage" className="text-primary hover:underline">cover queue</Link> so the right people are asked and told. Click a shift to edit it.</p>
      <ShiftDialog target={target} shift={editing} onClose={() => setTarget(null)} />
      {w && <GenerateDialog open={genOpen} onOpenChange={setGenOpen} weekStart={w.weekStart} />}
    </div>
  );
}
