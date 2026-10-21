import { useEffect, useState } from "react";
import { Plus, Trash2, Minus, Pencil, Plug, Clock } from "lucide-react";
import {
  useGetSettings, useUpdateSettings, getGetSettingsQueryKey,
  useListRoles, useCreateRole, useUpdateRole, useDeleteRole,
  useListShiftPatterns, useCreateShiftPattern, useUpdateShiftPattern, useDeleteShiftPattern,
  type Role, type ShiftPattern, type SettingsInput,
} from "@workspace/api-client-react";
import { useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from "@/components/ui/dialog";
import { useToast } from "@/hooks/use-toast";
import { PageHeader, Panel, SkeletonRows, ErrorState, Empty } from "@/components/kit";
import { WEEKDAYS, fmtHm, hmHours } from "@/lib/time";
import { errMsg } from "@/lib/api-error";
import { useInvalidateOps } from "@/lib/invalidate";
import { cn } from "@/lib/utils";

const PALETTE = ["#1f6f78", "#e8a317", "#c4473a", "#4f7b52", "#5b5f97", "#a0522d", "#2f8f9d", "#8a6d3b"];

function DayChips({ value, onChange, testPrefix }: { value: number[]; onChange: (v: number[]) => void; testPrefix: string }) {
  return (
    <div className="flex flex-wrap gap-1">
      {WEEKDAYS.map((d, i) => {
        const on = value.includes(i);
        return (
          <button key={d} type="button" onClick={() => onChange(on ? value.filter((x) => x !== i) : [...value, i].sort())} data-testid={`${testPrefix}-${i}`}
            className={cn("h-8 w-11 rounded-md text-xs font-medium border transition-colors", on ? "bg-primary text-primary-foreground border-primary" : "bg-card text-muted-foreground hover:border-foreground/40")}>{d}</button>
        );
      })}
    </div>
  );
}

/* ---------------- Rules ---------------- */
function RulesTab() {
  const q = useGetSettings();
  const upd = useUpdateSettings();
  const qc = useQueryClient();
  const invalidate = useInvalidateOps();
  const { toast } = useToast();
  const [f, setF] = useState<SettingsInput | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    if (q.data) setF({ branchName: q.data.branchName, openTime: q.data.openTime, closeTime: q.data.closeTime, maxHoursPerDay: q.data.maxHoursPerDay, maxHoursPerWeek: q.data.maxHoursPerWeek, maxDaysPerWeek: q.data.maxDaysPerWeek, minRestHours: q.data.minRestHours, operatingDays: q.data.operatingDays, weekStartsOn: q.data.weekStartsOn });
  }, [q.data]);
  if (q.isLoading || !f) return q.isError ? <Panel><ErrorState what="settings" onRetry={() => q.refetch()} /></Panel> : <Panel><SkeletonRows n={5} /></Panel>;
  const s = q.data!;
  const dirty = JSON.stringify(f) !== JSON.stringify({ branchName: s.branchName, openTime: s.openTime, closeTime: s.closeTime, maxHoursPerDay: s.maxHoursPerDay, maxHoursPerWeek: s.maxHoursPerWeek, maxDaysPerWeek: s.maxDaysPerWeek, minRestHours: s.minRestHours, operatingDays: s.operatingDays, weekStartsOn: s.weekStartsOn });
  const save = () => { setErr(null); upd.mutate({ data: f }, {
    onSuccess: (r) => { qc.setQueryData(getGetSettingsQueryKey(), r); invalidate(); toast({ title: "Rules saved", description: "New rosters and cover suggestions use them from now." }); },
    onError: (e) => setErr(errMsg(e, "Could not save.")),
  }); };
  const num = (k: "maxHoursPerDay" | "maxHoursPerWeek" | "maxDaysPerWeek" | "minRestHours", label: string, hint: string, unit: string) => (
    <div className="grid grid-cols-[1fr_120px] gap-4 items-center px-4 py-3">
      <div><div className="text-sm font-medium">{label}</div><div className="text-xs text-muted-foreground">{hint}</div></div>
      <div className="relative"><Input type="number" min={0} step={k === "minRestHours" ? 0.5 : 1} value={f[k]} onChange={(e) => setF({ ...f, [k]: Number(e.target.value) })} className="pr-10 font-mono tnum" data-testid={`input-${k}`} />
        <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">{unit}</span></div>
    </div>
  );
  return (
    <div className="space-y-6 max-w-3xl">
      <Panel title="Branch">
        <div className="p-4 grid md:grid-cols-3 gap-4">
          <div className="md:col-span-3 space-y-1.5"><Label>Branch name</Label><Input value={f.branchName} onChange={(e) => setF({ ...f, branchName: e.target.value })} data-testid="input-branch" /></div>
          <div className="space-y-1.5"><Label>Opens</Label><Input type="time" value={f.openTime} onChange={(e) => setF({ ...f, openTime: e.target.value })} data-testid="input-open-time" /></div>
          <div className="space-y-1.5"><Label>Closes</Label><Input type="time" value={f.closeTime} onChange={(e) => setF({ ...f, closeTime: e.target.value })} data-testid="input-close-time" /></div>
          <div className="space-y-1.5"><Label>Week starts on</Label>
            <select value={f.weekStartsOn} onChange={(e) => setF({ ...f, weekStartsOn: Number(e.target.value) })} className="h-9 w-full rounded-md border bg-background px-3 text-sm" data-testid="select-week-start">
              {WEEKDAYS.map((d, i) => <option key={d} value={i}>{d}</option>)}
            </select></div>
          <p className="md:col-span-3 text-xs text-muted-foreground -mt-2">Every shift must start and end inside opening hours. Timezone: {s.timezone}.</p>
          <div className="md:col-span-3 space-y-1.5"><Label>Operating days</Label><DayChips value={f.operatingDays} onChange={(v) => setF({ ...f, operatingDays: v })} testPrefix="toggle-operating-day" />
            <p className="text-xs text-muted-foreground">Closed days get no shifts and show greyed on the roster.</p></div>
        </div>
      </Panel>
      <Panel title="Working-time rules" delay={50}>
        <div className="divide-y">
          {num("maxHoursPerDay", "Max hours per day", "Nobody is rostered or offered more than this in one day.", "h")}
          {num("maxHoursPerWeek", "Max hours per week", "Default weekly cap. A personal limit on a team member overrides it.", "h")}
          {num("maxDaysPerWeek", "Max days per week", "Most days one person may work in a week.", "d")}
          {num("minRestHours", "Minimum rest between shifts", "A shorter gap than this is flagged as back-to-back.", "h")}
        </div>
      </Panel>
      <Panel title="Orbyte connection" delay={100}>
        <div className="p-4 flex gap-4 text-sm">
          <div className={cn("h-10 w-10 rounded-md grid place-items-center shrink-0", s.orbyteConnected ? "bg-primary/15 text-primary" : "bg-accent/20 text-[hsl(32_80%_30%)]")}><Plug className="h-5 w-5" /></div>
          {s.orbyteConnected ? <div><div className="font-medium">Connected to Orbyte eLeave</div><div className="text-muted-foreground">Leave source: {s.leaveSource}</div></div> : (
            <div className="space-y-1.5" data-testid="text-orbyte-status">
              <div className="font-medium">Not connected</div>
              <p className="text-muted-foreground">Leave comes from manual entry or a CSV exported from Orbyte eLeave and uploaded on the Leave page. A live connection (Orbyte API or a read-only database link) can be plugged in later.</p>
            </div>
          )}
        </div>
      </Panel>
      {err && <p className="text-sm text-destructive rounded-md bg-destructive/10 px-3 py-2" data-testid="text-settings-error">{err}</p>}
      <div className="flex justify-end sticky bottom-4">
        <Button size="lg" disabled={!dirty || upd.isPending} onClick={save} data-testid="button-save-settings">{upd.isPending ? "Saving..." : dirty ? "Save rules" : "Saved"}</Button>
      </div>
    </div>
  );
}

/* ---------------- Roles ---------------- */
function RoleRow({ r }: { r: Role }) {
  const upd = useUpdateRole();
  const del = useDeleteRole();
  const invalidate = useInvalidateOps();
  const { toast } = useToast();
  const [name, setName] = useState(r.name);
  const [editing, setEditing] = useState(false);
  const save = (data: { name: string; color?: string }) => upd.mutate({ roleId: r.id, data }, {
    onSuccess: () => { invalidate(); setEditing(false); }, onError: (e) => toast({ title: "Could not save role", description: errMsg(e), variant: "destructive" }),
  });
  return (
    <div className="flex items-center gap-3 px-4 py-2.5" data-testid={`row-role-${r.id}`}>
      <div className="flex gap-1">
        {PALETTE.map((c) => (
          <button key={c} onClick={() => save({ name: r.name, color: c })} aria-label={`Colour ${c}`} data-testid={`button-role-color-${r.id}-${c.slice(1)}`}
            className={cn("h-5 w-5 rounded-full transition-transform hover:scale-110", r.color.toLowerCase() === c && "ring-2 ring-offset-2 ring-offset-card ring-foreground/60")} style={{ background: c }} />
        ))}
      </div>
      {editing ? (
        <form className="flex-1 flex gap-2" onSubmit={(e) => { e.preventDefault(); if (name.trim()) save({ name: name.trim(), color: r.color }); }}>
          <Input value={name} onChange={(e) => setName(e.target.value)} autoFocus className="h-8" data-testid={`input-role-name-${r.id}`} />
          <Button size="sm" type="submit" disabled={upd.isPending}>Save</Button>
          <Button size="sm" type="button" variant="ghost" onClick={() => { setEditing(false); setName(r.name); }}>Cancel</Button>
        </form>
      ) : (
        <div className="flex-1 flex items-center gap-2 min-w-0">
          <span className="font-medium truncate">{r.name}</span>
          <span className="font-mono text-xs text-muted-foreground">{r.employeeCount} people</span>
        </div>
      )}
      {!editing && <Button size="icon" variant="ghost" onClick={() => setEditing(true)} data-testid={`button-rename-role-${r.id}`}><Pencil className="h-4 w-4" /></Button>}
      <Button size="icon" variant="ghost" className="text-destructive hover:text-destructive" disabled={del.isPending} data-testid={`button-delete-role-${r.id}`}
        onClick={() => { if (confirm(`Delete role ${r.name}?`)) del.mutate({ roleId: r.id }, { onSuccess: () => { invalidate(); toast({ title: "Role deleted" }); }, onError: (e) => toast({ title: "Cannot delete role", description: errMsg(e), variant: "destructive" }) }); }}>
        <Trash2 className="h-4 w-4" />
      </Button>
    </div>
  );
}

function RolesTab() {
  const q = useListRoles();
  const create = useCreateRole();
  const invalidate = useInvalidateOps();
  const { toast } = useToast();
  const [name, setName] = useState("");
  const add = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    create.mutate({ data: { name: name.trim(), color: PALETTE[(q.data?.length ?? 0) % PALETTE.length] } }, {
      onSuccess: () => { invalidate(); setName(""); }, onError: (err) => toast({ title: "Could not add role", description: errMsg(err), variant: "destructive" }),
    });
  };
  return (
    <div className="max-w-3xl">
      <Panel title="Job roles" action={<span className="text-xs text-muted-foreground">Cover is only offered within the same role</span>}>
        {q.isLoading ? <SkeletonRows n={4} /> : q.isError ? <ErrorState what="roles" onRetry={() => q.refetch()} /> : !q.data?.length ? (
          <Empty icon={<Plus className="h-5 w-5" />} title="No roles yet" body="Add roles like Cashier, Server, Chef." />
        ) : <div className="divide-y">{q.data.map((r) => <RoleRow key={r.id} r={r} />)}</div>}
        <form onSubmit={add} className="flex gap-2 p-4 border-t">
          <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="New role, e.g. Barista" data-testid="input-new-role" />
          <Button type="submit" disabled={!name.trim() || create.isPending} data-testid="button-add-role"><Plus className="h-4 w-4 mr-1.5" />Add role</Button>
        </form>
      </Panel>
    </div>
  );
}

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

function PatternsTab() {
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

export default function Setup() {
  return (
    <div>
      <PageHeader eyebrow="Setup" title="The scheduling model" sub="Roles, the shifts you need each week, and the working-time rules the roster and cover suggestions must respect." />
      <Tabs defaultValue="patterns">
        <TabsList className="mb-5">
          <TabsTrigger value="patterns" data-testid="tab-patterns">Shift patterns</TabsTrigger>
          <TabsTrigger value="roles" data-testid="tab-roles">Roles</TabsTrigger>
          <TabsTrigger value="rules" data-testid="tab-rules">Rules & branch</TabsTrigger>
        </TabsList>
        <TabsContent value="patterns"><PatternsTab /></TabsContent>
        <TabsContent value="roles"><RolesTab /></TabsContent>
        <TabsContent value="rules"><RulesTab /></TabsContent>
      </Tabs>
    </div>
  );
}
