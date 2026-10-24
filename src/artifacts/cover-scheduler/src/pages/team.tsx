import { useEffect, useRef, useState } from "react";
import { Link } from "wouter";
import { Plus, Search, Users, Pencil, Upload, Download } from "lucide-react";
import {
  useListEmployees, useListRoles, useCreateEmployee, useUpdateEmployee, useImportEmployees,
  type Employee, type Access, type EmployeeImportRow, type EmployeeImportResult,
} from "@workspace/api-client-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { PageHeader, Panel, Initials, SkeletonRows, Empty, ErrorState, Tag, Pill } from "@/components/kit";
import { PinInput } from "@/components/account";
import { useInvalidateOps } from "@/lib/invalidate";
import { errMsg } from "@/lib/api-error";
import { csvObjects, downloadText } from "@/lib/csv";
import { cn } from "@/lib/utils";

type F = { name: string; email: string; phone: string; access: Access; roleId: string; maxHoursPerWeek: string; orbyteId: string; pin: string; active: boolean };
const blank: F = { name: "", email: "", phone: "", access: "staff", roleId: "none", maxHoursPerWeek: "", orbyteId: "", pin: "", active: true };

export function EmployeeDialog({ open, onOpenChange, employee }: { open: boolean; onOpenChange: (v: boolean) => void; employee?: Employee | null }) {
  const create = useCreateEmployee();
  const update = useUpdateEmployee();
  const roles = useListRoles();
  const invalidate = useInvalidateOps();
  const { toast } = useToast();
  const [f, setF] = useState<F>(blank);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    if (!open) return;
    setErr(null);
    setF(employee ? {
      name: employee.name, email: employee.email, phone: employee.phone ?? "", access: employee.access, roleId: employee.roleId ? String(employee.roleId) : "none",
      maxHoursPerWeek: employee.maxHoursPerWeek != null ? String(employee.maxHoursPerWeek) : "", orbyteId: employee.orbyteId ?? "", pin: "", active: employee.active,
    } : blank);
  }, [open, employee]);
  const lim = f.maxHoursPerWeek ? Number(f.maxHoursPerWeek) : null;
  const valid = f.name.trim() && f.email.includes("@") && (lim == null || (lim > 0 && lim <= 80)) && (employee || /^\d{4,8}$/.test(f.pin));
  const save = () => {
    const base = { name: f.name.trim(), email: f.email.trim(), phone: f.phone || null, access: f.access, roleId: f.roleId === "none" ? null : Number(f.roleId), maxHoursPerWeek: lim, orbyteId: f.orbyteId || null };
    const opts = { onSuccess: () => { invalidate(); onOpenChange(false); toast({ title: employee ? "Saved" : "Added to team", description: f.name }); }, onError: (e: unknown) => setErr(errMsg(e, "Could not save.")) };
    if (employee) update.mutate({ employeeId: employee.id, data: { ...base, active: f.active } }, opts);
    else create.mutate({ data: { ...base, pin: f.pin } }, opts);
  };
  const field = (k: "name" | "email" | "phone" | "maxHoursPerWeek" | "orbyteId", label: string, props: Record<string, unknown> = {}) => (
    <div className="space-y-1.5"><Label>{label}</Label><Input value={f[k]} onChange={(e) => setF({ ...f, [k]: e.target.value })} data-testid={`input-${k}`} {...props} /></div>
  );
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader><DialogTitle className="font-display text-xl">{employee ? `Edit ${employee.name}` : "Add a colleague"}</DialogTitle></DialogHeader>
        <div className="grid grid-cols-2 gap-3">
          <div className="col-span-2">{field("name", "Full name", { placeholder: "Nurul Aisyah binti Rahman" })}</div>
          {field("email", "Email", { type: "email" })}
          {field("phone", "Phone", { placeholder: "+60 12-345 6789" })}
          <div className="space-y-1.5"><Label>Role</Label>
            <Select value={f.roleId} onValueChange={(v) => setF({ ...f, roleId: v })}>
              <SelectTrigger data-testid="select-role"><SelectValue /></SelectTrigger>
              <SelectContent><SelectItem value="none">No role</SelectItem>{(roles.data ?? []).map((r) => <SelectItem key={r.id} value={String(r.id)}>{r.name}</SelectItem>)}</SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5"><Label>Access</Label>
            <Select value={f.access} onValueChange={(v) => setF({ ...f, access: v as Access })}>
              <SelectTrigger data-testid="select-access"><SelectValue /></SelectTrigger>
              <SelectContent><SelectItem value="staff">Staff (cover requests only)</SelectItem><SelectItem value="manager">Manager (full desk)</SelectItem></SelectContent>
            </Select>
          </div>
          {field("maxHoursPerWeek", "Personal weekly limit", { type: "number", min: 1, max: 80, placeholder: "Branch rule" })}
          {field("orbyteId", "Orbyte ID", { placeholder: "Matches imported leave" })}
          {!employee && <div className="col-span-2 space-y-1.5"><Label>Initial PIN (4 to 8 digits)</Label><PinInput value={f.pin} onChange={(v) => setF({ ...f, pin: v })} testId="input-initial-pin" /></div>}
          {employee && (
            <label className="col-span-2 flex items-center justify-between rounded-md border px-3 h-10 text-sm">Active<Switch checked={f.active} onCheckedChange={(v) => setF({ ...f, active: v })} data-testid="switch-active" /></label>
          )}
        </div>
        {err && <p className="text-sm text-destructive" data-testid="text-employee-error">{err}</p>}
        <DialogFooter><Button variant="ghost" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button disabled={!valid || create.isPending || update.isPending} onClick={save} data-testid="button-save-employee">Save</Button></DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

const COLS = ["name", "email", "phone", "roleName", "access", "maxHoursPerWeek", "orbyteId", "pin"];
const TEMPLATE = COLS.join(",") + "\nNurul Aisyah,aisyah@kopilane.my,+60123456789,Server,staff,,ORB-0142,1111\nFarah Hassan,farah@kopilane.my,,Cashier,manager,40,ORB-0009,1234\n";

function ImportEmployeesDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (v: boolean) => void }) {
  const imp = useImportEmployees();
  const invalidate = useInvalidateOps();
  const { toast } = useToast();
  const ref = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<string | null>(null);
  const [rows, setRows] = useState<EmployeeImportRow[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [result, setResult] = useState<EmployeeImportResult | null>(null);
  const reset = () => { setFile(null); setRows([]); setErr(null); setResult(null); if (ref.current) ref.current.value = ""; };
  const onFile = async (fl?: File) => {
    if (!fl) return;
    setResult(null); setFile(fl.name);
    const { header, rows: objs } = csvObjects(await fl.text());
    const lower = header.map((h) => h.toLowerCase());
    if (!lower.includes("name") || !lower.includes("email") || !lower.includes("pin")) { setRows([]); setErr("Missing required columns: name, email, pin."); return; }
    const out = objs.map((o) => ({
      name: o.name ?? "", email: o.email ?? "", phone: o.phone || null, roleName: o.rolename || null,
      access: (o.access === "manager" ? "manager" : "staff") as Access,
      maxHoursPerWeek: o.maxhoursperweek ? Number(o.maxhoursperweek) : null, orbyteId: o.orbyteid || null, pin: o.pin ?? "",
    }));
    setRows(out); setErr(out.length ? null : "No data rows found.");
  };
  const run = () => imp.mutate({ data: { rows } }, {
    onSuccess: (r) => { setResult(r); invalidate(); toast({ title: "Import finished", description: `${r.created} added.` }); },
    onError: (e) => toast({ title: "Import failed", description: errMsg(e), variant: "destructive" }),
  });
  return (
    <Dialog open={open} onOpenChange={(v) => { onOpenChange(v); if (!v) reset(); }}>
      <DialogContent className="max-w-xl">
        <DialogHeader><DialogTitle className="font-display text-xl">Bulk add staff</DialogTitle>
          <DialogDescription>Upload a CSV. Role names must match a role in Setup. Each row needs an initial PIN.</DialogDescription></DialogHeader>
        {!result ? (
          <>
            <label onDragOver={(e) => e.preventDefault()} onDrop={(e) => { e.preventDefault(); onFile(e.dataTransfer.files[0]); }}
              className="flex flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-8 text-center cursor-pointer hover:bg-secondary/50 hover:border-primary/40 transition-colors">
              <Upload className="h-6 w-6 text-primary" />
              <span className="text-sm font-medium">{file ?? "Drop a CSV here or click to choose"}</span>
              {rows.length > 0 && <span className="font-mono text-xs text-muted-foreground">{rows.length} rows ready</span>}
              <input ref={ref} type="file" accept=".csv,text/csv" className="hidden" onChange={(e) => onFile(e.target.files?.[0])} data-testid="input-employee-csv" />
            </label>
            {err && <p className="text-sm text-destructive">{err}</p>}
            {rows.length > 0 && (
              <div className="rounded-md border max-h-44 overflow-auto text-xs">
                <table className="w-full">
                  <thead className="bg-secondary sticky top-0"><tr className="text-left font-mono text-[10px] uppercase">{["#", "Name", "Email", "Role", "Access"].map((h) => <th key={h} className="px-2 py-1.5">{h}</th>)}</tr></thead>
                  <tbody className="divide-y">{rows.slice(0, 50).map((r, i) => (
                    <tr key={i}><td className="px-2 py-1 font-mono text-muted-foreground">{i + 1}</td><td className="px-2 py-1">{r.name}</td><td className="px-2 py-1">{r.email}</td><td className="px-2 py-1">{r.roleName}</td><td className="px-2 py-1">{r.access}</td></tr>
                  ))}</tbody>
                </table>
              </div>
            )}
            <div className="text-xs text-muted-foreground">Columns: <span className="font-mono">{COLS.join(", ")}</span></div>
            <DialogFooter className="sm:justify-between">
              <Button variant="ghost" onClick={() => downloadText("gantian-staff-template.csv", TEMPLATE)} data-testid="button-employee-template"><Download className="h-4 w-4 mr-1.5" />CSV template</Button>
              <Button disabled={!rows.length || !!err || imp.isPending} onClick={run} data-testid="button-run-employee-import">{imp.isPending ? "Importing..." : `Import ${rows.length || ""} rows`}</Button>
            </DialogFooter>
          </>
        ) : (
          <div className="space-y-4" data-testid="employee-import-result">
            <div className="grid grid-cols-2 border rounded-lg divide-x">
              <div className="p-3"><div className="font-mono text-[10px] uppercase text-muted-foreground">Added</div><div className="font-display text-2xl font-bold tnum">{result.created}</div></div>
              <div className="p-3"><div className="font-mono text-[10px] uppercase text-muted-foreground">Row errors</div><div className="font-display text-2xl font-bold tnum">{result.errors.length}</div></div>
            </div>
            {result.errors.length > 0 && (
              <div className="rounded-md border border-destructive/30 bg-destructive/5 max-h-40 overflow-auto">
                {result.errors.map((e) => <div key={e.row} className="px-3 py-1.5 text-xs flex gap-2"><span className="font-mono text-muted-foreground w-12">row {e.row}</span>{e.message}</div>)}
              </div>
            )}
            <DialogFooter><Button variant="ghost" onClick={reset}>Import another</Button><Button onClick={() => onOpenChange(false)}>Done</Button></DialogFooter>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

export default function Team() {
  const [search, setSearch] = useState("");
  const [roleId, setRoleId] = useState<number | null>(null);
  const [showInactive, setShowInactive] = useState(false);
  const [dlg, setDlg] = useState<{ open: boolean; emp: Employee | null }>({ open: false, emp: null });
  const [importOpen, setImportOpen] = useState(false);
  const roles = useListRoles();
  const q = useListEmployees({ search: search || undefined, roleId: roleId ?? undefined, active: showInactive ? undefined : true });

  return (
    <div>
      <PageHeader eyebrow="Team" title="The people who cover" sub="Cover candidates come from colleagues with the same role. Personal weekly limits override the branch rule."
        actions={<>
          <Button variant="outline" onClick={() => setImportOpen(true)} data-testid="button-import-employees"><Upload className="h-4 w-4 mr-1.5" />Bulk add</Button>
          <Button onClick={() => setDlg({ open: true, emp: null })} data-testid="button-add-employee"><Plus className="h-4 w-4 mr-1.5" />Add colleague</Button>
        </>} />
      <div className="flex flex-col md:flex-row md:items-center gap-3 mb-4">
        <div className="relative md:w-72">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search name or email" className="pl-9 bg-card" data-testid="input-search" />
        </div>
        <div className="flex flex-wrap gap-1.5 flex-1">
          <button onClick={() => setRoleId(null)} className={cn("rounded-full px-3 h-8 text-sm border transition-colors", roleId == null ? "bg-foreground text-background border-foreground" : "bg-card hover:border-foreground/40")} data-testid="filter-role-all">All</button>
          {(roles.data ?? []).map((r) => (
            <button key={r.id} onClick={() => setRoleId(r.id)} data-testid={`filter-role-${r.id}`}
              className={cn("rounded-full px-3 h-8 text-sm border transition-colors inline-flex items-center gap-1.5", roleId === r.id ? "bg-foreground text-background border-foreground" : "bg-card hover:border-foreground/40")}>
              <span className="h-2 w-2 rounded-full" style={{ background: r.color }} />{r.name}<span className="font-mono text-[10.5px] opacity-60">{r.employeeCount}</span>
            </button>
          ))}
        </div>
        <label className="flex items-center gap-2 text-sm text-muted-foreground"><Switch checked={showInactive} onCheckedChange={setShowInactive} data-testid="switch-show-inactive" />Show inactive</label>
      </div>
      <Panel>
        <div className="hidden md:grid grid-cols-[1.5fr_1fr_90px_120px_110px_40px] gap-4 px-4 h-9 items-center border-b font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
          <span>Name</span><span>Role</span><span>Access</span><span>This week</span><span>Orbyte ID</span><span />
        </div>
        {q.isLoading ? <SkeletonRows n={8} /> : q.isError ? <ErrorState what="the team" onRetry={() => q.refetch()} /> : !q.data?.length ? (
          <Empty icon={<Users className="h-5 w-5" />} title={search || roleId ? "No one matches" : "No colleagues yet"} body={search || roleId ? "Try a different search or role." : "Add the people on your roster so cover can be ranked."} />
        ) : (
          <div className="divide-y">
            {q.data.map((e, i) => (
              <div key={e.id} className={cn("grid grid-cols-[1fr_auto] md:grid-cols-[1.5fr_1fr_90px_120px_110px_40px] gap-4 items-center px-4 py-2.5 hover:bg-secondary/50 rise", !e.active && "opacity-50")} style={{ animationDelay: `${Math.min(i, 15) * 25}ms` }} data-testid={`row-employee-${e.id}`}>
                <Link href={`/team/${e.id}`} className="flex items-center gap-3 min-w-0">
                  <Initials name={e.name} />
                  <div className="min-w-0">
                    <div className="font-medium truncate flex items-center gap-2">{e.name}
                      {e.onLeaveToday && <Tag className="bg-accent/25 text-[hsl(32_80%_26%)]">on leave today</Tag>}
                      {!e.active && <Tag>inactive</Tag>}
                    </div>
                    <div className="text-xs text-muted-foreground truncate">{e.email}</div>
                  </div>
                </Link>
                <div className="hidden md:block text-sm truncate">{e.roleName ?? <span className="text-muted-foreground">No role</span>}</div>
                <div className="hidden md:block"><Pill status={e.access} /></div>
                <div className="hidden md:block font-mono text-sm tnum">{e.hoursThisWeek.toFixed(1)}h{e.maxHoursPerWeek != null && <span className="text-muted-foreground"> / {e.maxHoursPerWeek}h</span>}</div>
                <div className="hidden md:block font-mono text-xs text-muted-foreground">{e.orbyteId ?? "–"}</div>
                <Button variant="ghost" size="icon" onClick={() => setDlg({ open: true, emp: e })} data-testid={`button-edit-${e.id}`}><Pencil className="h-4 w-4" /></Button>
              </div>
            ))}
          </div>
        )}
      </Panel>
      <EmployeeDialog open={dlg.open} employee={dlg.emp} onOpenChange={(v) => setDlg((d) => ({ ...d, open: v }))} />
      <ImportEmployeesDialog open={importOpen} onOpenChange={setImportOpen} />
    </div>
  );
}
