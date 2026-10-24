import { useEffect, useState } from "react";
import { Plus, Trash2, Minus, Pencil, Clock } from "lucide-react";
import {
  useListRoles, useListShiftPatterns, useCreateShiftPattern, useUpdateShiftPattern, useDeleteShiftPattern, type ShiftPattern,
} from "@workspace/api-client-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from "@/components/ui/dialog";
import { useToast } from "@/hooks/use-toast";
import { Panel, SkeletonRows, ErrorState, Empty } from "@/components/kit";
import { WEEKDAYS, fmtHm, hmHours } from "@/lib/time";
import { errMsg } from "@/lib/api-error";
import { useInvalidateOps } from "@/lib/invalidate";
import { cn } from "@/lib/utils";
import { DayChips } from "./day-chips";

/* ---------------- Patterns ---------------- */
type PF = { name: string; startTime: string; endTime: string; days: number[]; active: boolean; req: Record<number, number> };

function PatternDialog({ pattern, open, onOpenChange }: { pattern: ShiftPattern | null; open: boolean; onOpenChange: (v: boolean) => void }) {
  const roles = useListRoles();
  const create = useCreateShiftPattern();
  const upd = useUpdateShiftPattern();
  const invalidate = useInvalidateOps();
  const { toast } = useToast();
  const [f, setF] = useState<PF>({ name: "", startTime: "07:00", endTime: "15:00", days: [0, 1, 2, 3, 4], active: true, req: {} });
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    if (!open) return;
    setErr(null);
    setF(pattern ? { name: pattern.name, startTime: pattern.startTime, endTime: pattern.endTime, days: pattern.days, active: pattern.active, req: Object.fromEntries(pattern.requirements.map((r) => [r.roleId, r.headcount])) }
      : { name: "", startTime: "07:00", endTime: "15:00", days: [0, 1, 2, 3, 4], active: true, req: {} });
  }, [open, pattern]);
  const total = Object.values(f.req).reduce((a, b) => a + b, 0);
  const valid = f.name.trim() && f.startTime && f.endTime && f.days.length;
  const save = () => {
    const data = { name: f.name.trim(), startTime: f.startTime, endTime: f.endTime, days: f.days, active: f.active, requirements: Object.entries(f.req).filter(([, h]) => h > 0).map(([roleId, headcount]) => ({ roleId: Number(roleId), headcount })) };
    const opts = { onSuccess: () => { invalidate(); onOpenChange(false); toast({ title: pattern ? "Pattern saved" : "Pattern added" }); }, onError: (e: unknown) => setErr(errMsg(e, "Could not save.")) };
    if (pattern) upd.mutate({ patternId: pattern.id, data }, opts); else create.mutate({ data }, opts);
  };
  const step = (rid: number, d: number) => setF((x) => ({ ...x, req: { ...x.req, [rid]: Math.max(0, (x.req[rid] ?? 0) + d) } }));
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader><DialogTitle className="font-display text-xl">{pattern ? `Edit ${pattern.name}` : "New shift pattern"}</DialogTitle>
          <DialogDescription>How many people each role needs, on which days.</DialogDescription></DialogHeader>
        <div className="space-y-4">
          <div className="space-y-1.5"><Label>Name</Label><Input value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} placeholder="Weekday morning" data-testid="input-pattern-name" /></div>
          <div className="grid grid-cols-3 gap-3 items-end">
            <div className="space-y-1.5"><Label>Starts</Label><Input type="time" value={f.startTime} onChange={(e) => setF({ ...f, startTime: e.target.value })} data-testid="input-pattern-start" /></div>
            <div className="space-y-1.5"><Label>Ends</Label><Input type="time" value={f.endTime} onChange={(e) => setF({ ...f, endTime: e.target.value })} data-testid="input-pattern-end" /></div>
            <div className="h-9 flex items-center font-mono text-sm"><Clock className="h-4 w-4 mr-1.5 text-muted-foreground" />{f.startTime && f.endTime ? hmHours(f.startTime, f.endTime).toFixed(1) : "–"}h</div>
          </div>
          <div className="space-y-1.5"><Label>Runs on</Label><DayChips value={f.days} onChange={(v) => setF({ ...f, days: v })} testPrefix="toggle-pattern-day" /></div>
          <div className="space-y-1.5">
            <Label>People needed <span className="font-mono text-xs text-muted-foreground font-normal">· {total} total</span></Label>
            <div className="rounded-md border divide-y">
              {(roles.data ?? []).map((r) => (
                <div key={r.id} className="flex items-center gap-3 px-3 h-11">
                  <span className="h-2.5 w-2.5 rounded-full" style={{ background: r.color }} />
                  <span className="flex-1 text-sm">{r.name}</span>
                  <Button type="button" size="icon" variant="outline" className="h-7 w-7" onClick={() => step(r.id, -1)} data-testid={`button-dec-${r.id}`}><Minus className="h-3 w-3" /></Button>
                  <span className="w-6 text-center font-mono tnum" data-testid={`text-headcount-${r.id}`}>{f.req[r.id] ?? 0}</span>
                  <Button type="button" size="icon" variant="outline" className="h-7 w-7" onClick={() => step(r.id, 1)} data-testid={`button-inc-${r.id}`}><Plus className="h-3 w-3" /></Button>
                </div>
              ))}
              {!roles.data?.length && <div className="px-3 py-3 text-sm text-muted-foreground">Add roles first.</div>}
            </div>
          </div>
          <label className="flex items-center justify-between rounded-md border px-3 h-10 text-sm">Active (used when generating rosters)<Switch checked={f.active} onCheckedChange={(v) => setF({ ...f, active: v })} data-testid="switch-pattern-active" /></label>
          {err && <p className="text-sm text-destructive">{err}</p>}
        </div>
        <DialogFooter><Button variant="ghost" onClick={() => onOpenChange(false)}>Cancel</Button><Button disabled={!valid || create.isPending || upd.isPending} onClick={save} data-testid="button-save-pattern">Save pattern</Button></DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function PatternsTab() {
  const q = useListShiftPatterns();
  const roles = useListRoles();
  const upd = useUpdateShiftPattern();
  const del = useDeleteShiftPattern();
  const invalidate = useInvalidateOps();
  const { toast } = useToast();
  const [dlg, setDlg] = useState<{ open: boolean; p: ShiftPattern | null }>({ open: false, p: null });
  const color = (rid: number) => roles.data?.find((r) => r.id === rid)?.color ?? "#888";
  const toggle = (p: ShiftPattern) => upd.mutate({ patternId: p.id, data: { name: p.name, startTime: p.startTime, endTime: p.endTime, days: p.days, active: !p.active, requirements: p.requirements.map((r) => ({ roleId: r.roleId, headcount: r.headcount })) } }, {
    onSuccess: invalidate, onError: (e) => toast({ title: "Could not update", description: errMsg(e), variant: "destructive" }),
  });
  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <p className="text-sm text-muted-foreground max-w-xl">Patterns describe a normal week. "Generate roster" fills each pattern with people, respecting your rules.</p>
        <Button onClick={() => setDlg({ open: true, p: null })} data-testid="button-add-pattern"><Plus className="h-4 w-4 mr-1.5" />New pattern</Button>
      </div>
      {q.isLoading ? <Panel><SkeletonRows n={4} /></Panel> : q.isError ? <Panel><ErrorState what="patterns" onRetry={() => q.refetch()} /></Panel> : !q.data?.length ? (
        <Panel><Empty icon={<Clock className="h-5 w-5" />} title="No shift patterns" body="Add one per recurring shift, e.g. Weekday morning 07:00 to 15:00." /></Panel>
      ) : (
        <div className="grid md:grid-cols-2 gap-4">
          {q.data.map((p, i) => {
            const total = p.requirements.reduce((a, r) => a + r.headcount, 0);
            return (
              <div key={p.id} className={cn("rounded-lg border bg-card p-4 rise", !p.active && "opacity-60")} style={{ animationDelay: `${i * 40}ms` }} data-testid={`card-pattern-${p.id}`}>
                <div className="flex items-start gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="font-display text-lg font-bold">{p.name}</div>
                    <div className="font-mono text-sm">{fmtHm(p.startTime)} to {fmtHm(p.endTime)} <span className="text-muted-foreground">· {p.hours.toFixed(1)}h · {total} people</span></div>
                  </div>
                  <Switch checked={p.active} onCheckedChange={() => toggle(p)} data-testid={`switch-pattern-${p.id}`} />
                </div>
                <div className="flex gap-1 mt-3">{WEEKDAYS.map((d, di) => <span key={d} className={cn("text-[10.5px] font-mono w-8 text-center rounded py-0.5", p.days.includes(di) ? "bg-primary/15 text-primary font-semibold" : "text-muted-foreground/50")}>{d}</span>)}</div>
                <div className="flex flex-wrap gap-1.5 mt-3">
                  {p.requirements.map((r) => (
                    <span key={r.roleId} className="inline-flex items-center gap-1.5 rounded-md border px-2 py-1 text-xs"><span className="h-2 w-2 rounded-full" style={{ background: color(r.roleId) }} />{r.roleName}<span className="font-mono font-semibold">{r.headcount}</span></span>
                  ))}
                  {!p.requirements.length && <span className="text-xs text-muted-foreground">No people required yet</span>}
                </div>
                <div className="flex justify-end gap-1 mt-3">
                  <Button size="sm" variant="ghost" onClick={() => setDlg({ open: true, p })} data-testid={`button-edit-pattern-${p.id}`}><Pencil className="h-3.5 w-3.5 mr-1" />Edit</Button>
                  <Button size="sm" variant="ghost" className="text-destructive hover:text-destructive" data-testid={`button-delete-pattern-${p.id}`}
                    onClick={() => { if (confirm(`Delete pattern ${p.name}?`)) del.mutate({ patternId: p.id }, { onSuccess: () => { invalidate(); toast({ title: "Pattern deleted" }); }, onError: (e) => toast({ title: "Could not delete", description: errMsg(e), variant: "destructive" }) }); }}>
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>
            );
          })}
        </div>
      )}
      <PatternDialog open={dlg.open} pattern={dlg.p} onOpenChange={(v) => setDlg((d) => ({ ...d, open: v }))} />
    </div>
  );
}

