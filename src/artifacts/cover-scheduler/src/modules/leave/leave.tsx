import { useRef, useState } from "react";
import { Link } from "wouter";
import { CalendarOff, Check, X, Plus, Upload, Download, FileText, ArrowRight, Users } from "lucide-react";
import {
  useListLeave, useApproveLeave, useRejectLeave, useCreateLeave, useImportLeave, useListEmployees,
  type Leave, type LeaveStatus, type LeaveInputStatus, type LeaveImportRow, type LeaveImportResult, type LeaveResult,
} from "@workspace/api-client-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { PageHeader, Panel, Pill, Initials, SkeletonRows, Empty, ErrorState, Segmented, Tag } from "@/components/kit";
import { fmtDate, fmtYmd } from "@/lib/time";
import { useInvalidateOps } from "@/lib/invalidate";
import { errMsg } from "@/lib/api-error";
import { LeaveCoverPreviewDialog } from "./leave-cover-preview";

type Filter = LeaveStatus | "all";
const COLS = ["employeeEmail", "orbyteId", "leaveType", "startDate", "endDate", "status", "externalRef", "reason"] as const;
const TEMPLATE = COLS.join(",") + "\naisyah@mamarich.my,ORB-0142,Annual,2025-07-14,2025-07-16,approved,ELV-88213,Family trip to Ipoh\n,ORB-0087,Medical,2025-07-15,2025-07-15,pending,ELV-88220,\n";

function parseCsv(text: string): string[][] {
  const rows: string[][] = []; let row: string[] = []; let cell = ""; let q = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (q) {
      if (ch === '"') { if (text[i + 1] === '"') { cell += '"'; i++; } else q = false; } else cell += ch;
    } else if (ch === '"') q = true;
    else if (ch === ",") { row.push(cell); cell = ""; }
    else if (ch === "\n" || ch === "\r") { if (ch === "\r" && text[i + 1] === "\n") i++; row.push(cell); rows.push(row); row = []; cell = ""; }
    else cell += ch;
  }
  if (cell || row.length) { row.push(cell); rows.push(row); }
  return rows.filter((r) => r.some((c) => c.trim()));
}

function toRows(text: string): { rows: LeaveImportRow[]; error?: string } {
  const all = parseCsv(text.replace(/^\uFEFF/, ""));
  if (!all.length) return { rows: [], error: "The file is empty." };
  const head = all[0].map((h) => h.trim());
  const idx = (k: string) => head.findIndex((h) => h.toLowerCase() === k.toLowerCase());
  if (idx("leaveType") < 0 || idx("startDate") < 0 || idx("endDate") < 0) return { rows: [], error: "Missing required columns: leaveType, startDate, endDate." };
  const get = (r: string[], k: string) => { const i = idx(k); const v = i >= 0 ? (r[i] ?? "").trim() : ""; return v || null; };
  return {
    rows: all.slice(1).map((r) => {
      const st = get(r, "status")?.toLowerCase();
      return {
        employeeEmail: get(r, "employeeEmail"), orbyteId: get(r, "orbyteId"),
        leaveType: get(r, "leaveType") ?? "", startDate: get(r, "startDate") ?? "", endDate: get(r, "endDate") ?? "",
        status: st || null,
        externalRef: get(r, "externalRef"), reason: get(r, "reason"),
      };
    }),
  };
}

function CreateLeaveDialog({ open, onOpenChange, onCreated }: { open: boolean; onOpenChange: (v: boolean) => void; onCreated: (r: LeaveResult) => void }) {
  const emps = useListEmployees();
  const create = useCreateLeave();
  const invalidate = useInvalidateOps();
  const { toast } = useToast();
  const [f, setF] = useState({ employeeId: "", leaveType: "Annual", startDate: "", endDate: "", status: "approved" as LeaveInputStatus, reason: "", externalRef: "" });
  const valid = f.employeeId && f.leaveType && f.startDate && f.endDate && f.endDate >= f.startDate;
  const submit = () => create.mutate({
    data: { employeeId: Number(f.employeeId), leaveType: f.leaveType, startDate: f.startDate, endDate: f.endDate, status: f.status, reason: f.reason || null, externalRef: f.externalRef || null },
  }, {
    onSuccess: (r) => {
      invalidate(); onOpenChange(false); onCreated(r);
      toast({ title: "Leave recorded", description: r.coverageCases.length ? `${r.coverageCases.length} shift(s) now need cover.` : `${r.leave.employeeName}, ${r.leave.leaveType}.` });
      setF((x) => ({ ...x, employeeId: "", startDate: "", endDate: "", reason: "", externalRef: "" }));
    },
    onError: (e) => toast({ title: "Could not save leave", description: errMsg(e), variant: "destructive" }),
  });
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader><DialogTitle className="font-display text-xl">Add leave</DialogTitle><DialogDescription>For leave agreed outside Orbyte, or while the connection is not live.</DialogDescription></DialogHeader>
        <div className="grid grid-cols-2 gap-3">
          <div className="col-span-2 space-y-1.5"><Label>Employee</Label>
            <Select value={f.employeeId} onValueChange={(v) => setF({ ...f, employeeId: v })}>
              <SelectTrigger data-testid="select-employee"><SelectValue placeholder="Choose a person" /></SelectTrigger>
              <SelectContent>{(emps.data ?? []).filter((e) => e.active).map((e) => <SelectItem key={e.id} value={String(e.id)}>{e.name}{e.roleName ? ` · ${e.roleName}` : ""}</SelectItem>)}</SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5"><Label>Leave type</Label>
            <Select value={f.leaveType} onValueChange={(v) => setF({ ...f, leaveType: v })}>
              <SelectTrigger data-testid="select-leave-type"><SelectValue /></SelectTrigger>
              <SelectContent>{["Annual", "Medical", "Emergency", "Hospitalisation", "Maternity", "Paternity", "Compassionate", "Unpaid"].map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}</SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5"><Label>Status</Label>
            <Select value={f.status} onValueChange={(v) => setF({ ...f, status: v as LeaveInputStatus })}>
              <SelectTrigger data-testid="select-status"><SelectValue /></SelectTrigger>
              <SelectContent><SelectItem value="approved">Approved (open cover now)</SelectItem><SelectItem value="pending">Pending</SelectItem></SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5"><Label>From</Label><Input type="date" value={f.startDate} onChange={(e) => setF({ ...f, startDate: e.target.value })} data-testid="input-start" /></div>
          <div className="space-y-1.5"><Label>To</Label><Input type="date" value={f.endDate} min={f.startDate} onChange={(e) => setF({ ...f, endDate: e.target.value })} data-testid="input-end" /></div>
          <div className="col-span-2 space-y-1.5"><Label>Orbyte reference <span className="text-muted-foreground font-normal">(optional)</span></Label><Input value={f.externalRef} onChange={(e) => setF({ ...f, externalRef: e.target.value })} placeholder="ELV-..." data-testid="input-ref" /></div>
          <div className="col-span-2 space-y-1.5"><Label>Reason <span className="text-muted-foreground font-normal">(optional)</span></Label><Textarea value={f.reason} onChange={(e) => setF({ ...f, reason: e.target.value })} className="min-h-[64px]" data-testid="input-reason" /></div>
        </div>
        <DialogFooter><Button variant="ghost" onClick={() => onOpenChange(false)}>Cancel</Button><Button disabled={!valid || create.isPending} onClick={submit} data-testid="button-save-leave">{create.isPending ? "Saving..." : "Save leave"}</Button></DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function ImportDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (v: boolean) => void }) {
  const imp = useImportLeave();
  const invalidate = useInvalidateOps();
  const { toast } = useToast();
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<string | null>(null);
  const [rows, setRows] = useState<LeaveImportRow[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [result, setResult] = useState<LeaveImportResult | null>(null);

  const reset = () => { setFile(null); setRows([]); setErr(null); setResult(null); if (inputRef.current) inputRef.current.value = ""; };
  const onFile = async (fl?: File) => {
    if (!fl) return;
    setResult(null); setFile(fl.name);
    const r = toRows(await fl.text());
    setRows(r.rows); setErr(r.error ?? (r.rows.length ? null : "No data rows found."));
  };
  const download = () => {
    const url = URL.createObjectURL(new Blob([TEMPLATE], { type: "text/csv" }));
    const a = document.createElement("a"); a.href = url; a.download = "orbyte-leave-template.csv"; a.click(); URL.revokeObjectURL(url);
  };
  const run = () => imp.mutate({ data: { rows } }, {
    onSuccess: (r) => { setResult(r); invalidate(); toast({ title: "Import finished", description: `${r.created} created, ${r.skipped} skipped.` }); },
    onError: (e) => toast({ title: "Import failed", description: errMsg(e, "Nothing was imported."), variant: "destructive" }),
  });

  return (
    <Dialog open={open} onOpenChange={(v) => { onOpenChange(v); if (!v) reset(); }}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle className="font-display text-xl">Import leave from Orbyte</DialogTitle>
          <DialogDescription>Export from Orbyte eLeave as CSV. Employees are matched by email or Orbyte ID. Rows with an externalRef already imported are skipped.</DialogDescription>
        </DialogHeader>
        {!result ? (
          <>
            <label onDragOver={(e) => e.preventDefault()} onDrop={(e) => { e.preventDefault(); onFile(e.dataTransfer.files[0]); }}
              className="flex flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-8 text-center cursor-pointer hover:bg-secondary/50 hover:border-primary/40 transition-colors">
              <Upload className="h-6 w-6 text-primary" />
              <span className="text-sm font-medium">{file ?? "Drop a CSV here or click to choose"}</span>
              {rows.length > 0 && <span className="font-mono text-xs text-muted-foreground">{rows.length} rows ready</span>}
              <input ref={inputRef} type="file" accept=".csv,text/csv" className="hidden" onChange={(e) => onFile(e.target.files?.[0])} data-testid="input-csv" />
            </label>
            {err && <p className="text-sm text-destructive">{err}</p>}
            {rows.length > 0 && (
              <div className="rounded-md border max-h-44 overflow-auto text-xs">
                <table className="w-full">
                  <thead className="bg-secondary sticky top-0"><tr className="text-left font-mono text-[10px] uppercase">{["#", "Who", "Type", "Dates", "Status"].map((h) => <th key={h} className="px-2 py-1.5">{h}</th>)}</tr></thead>
                  <tbody className="divide-y">{rows.slice(0, 50).map((r, i) => (
                    <tr key={i}><td className="px-2 py-1 font-mono text-muted-foreground">{i + 1}</td><td className="px-2 py-1">{r.employeeEmail ?? r.orbyteId}</td><td className="px-2 py-1">{r.leaveType}</td><td className="px-2 py-1 font-mono">{r.startDate} – {r.endDate}</td><td className="px-2 py-1">{r.status ?? "pending"}</td></tr>
                  ))}</tbody>
                </table>
              </div>
            )}
            <div className="text-xs text-muted-foreground">Columns: <span className="font-mono">{COLS.join(", ")}</span></div>
            <DialogFooter className="sm:justify-between">
              <Button variant="ghost" onClick={download} data-testid="button-template"><Download className="h-4 w-4 mr-1.5" />CSV template</Button>
              <Button disabled={!rows.length || !!err || imp.isPending} onClick={run} data-testid="button-run-import">{imp.isPending ? "Importing..." : `Import ${rows.length || ""} rows`}</Button>
            </DialogFooter>
          </>
        ) : (
          <div className="space-y-4" data-testid="import-result">
            <div className="grid grid-cols-3 border rounded-lg divide-x">
              {[["Created", result.created], ["Skipped", result.skipped], ["Cover cases opened", result.coverageCasesOpened]].map(([k, v]) => (
                <div key={k} className="p-3"><div className="font-mono text-[10px] uppercase text-muted-foreground">{k}</div><div className="font-display text-2xl font-bold tnum">{v}</div></div>
              ))}
            </div>
            {result.errors.length > 0 && (
              <div className="rounded-md border border-destructive/30 bg-destructive/5 max-h-40 overflow-auto">
                <div className="px-3 py-2 text-xs font-medium text-destructive border-b border-destructive/20">{result.errors.length} row(s) need attention</div>
                {result.errors.map((e) => <div key={e.row} className="px-3 py-1.5 text-xs flex gap-2"><span className="font-mono text-muted-foreground w-12">row {e.row}</span>{e.message}</div>)}
              </div>
            )}
            <DialogFooter>
              <Button variant="ghost" onClick={reset}>Import another</Button>
              {result.coverageCasesOpened > 0 ? <Button asChild><Link href="/coverage" onClick={() => onOpenChange(false)}>Go to cover queue</Link></Button> : <Button onClick={() => onOpenChange(false)}>Done</Button>}
            </DialogFooter>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

export default function LeavePage() {
  const [filter, setFilter] = useState<Filter>("pending");
  const q = useListLeave(filter === "all" ? undefined : { status: filter });
  const approve = useApproveLeave();
  const reject = useRejectLeave();
  const invalidate = useInvalidateOps();
  const { toast } = useToast();
  const [createOpen, setCreateOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [approval, setApproval] = useState<LeaveResult | null>(null);
  const [preview, setPreview] = useState<Leave | null>(null);
  const busy = approve.isPending || reject.isPending;
  const doReject = (l: Leave) => reject.mutate({ leaveId: l.id }, {
    onSuccess: () => { setPreview(null); invalidate(); toast({ title: "Leave rejected", description: l.employeeName }); },
    onError: (e) => toast({ title: "Could not reject", description: errMsg(e), variant: "destructive" }),
  });
  const doApprove = (l: Leave) => approve.mutate({ leaveId: l.id }, {
    onSuccess: (r) => { setPreview(null); setApproval(r); invalidate(); },
    onError: (e) => toast({ title: "Could not approve", description: errMsg(e), variant: "destructive" }),
  });

  return (
    <div>
      <PageHeader eyebrow="Leave" title="Who is away" sub="From Orbyte eLeave via CSV, or entered by hand. Use Check cover to see who could fill the shifts before you decide. Approving leave opens a cover case for every shift it touches."
        actions={<>
          <Button variant="outline" onClick={() => setImportOpen(true)} data-testid="button-import"><Upload className="h-4 w-4 mr-1.5" />Import CSV</Button>
          <Button onClick={() => setCreateOpen(true)} data-testid="button-add-leave"><Plus className="h-4 w-4 mr-1.5" />Add leave</Button>
        </>} />

      {approval && (
        <div className="mb-4 rounded-lg border border-primary/30 bg-primary/[0.06] p-4 flex flex-col md:flex-row md:items-center gap-3 rise" data-testid="banner-approval">
          <Check className="h-5 w-5 text-primary shrink-0" />
          <div className="flex-1 text-sm">
            <span className="font-medium">{approval.leave.employeeName}'s {approval.leave.leaveType.toLowerCase()} leave is approved.</span>{" "}
            {approval.coverageCases.length ? `${approval.coverageCases.length} shift${approval.coverageCases.length > 1 ? "s" : ""} now need cover.` : "No rostered shifts are affected."}
            {approval.coverageCases.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mt-2">{approval.coverageCases.map((c) => (
                <Link key={c.id} href={`/coverage/${c.id}`} className="inline-flex items-center gap-1 rounded bg-card border px-2 py-0.5 text-xs hover:border-primary" data-testid={`link-opened-case-${c.id}`}>
                  {fmtYmd(c.shift.date)} <ArrowRight className="h-3 w-3" />
                </Link>
              ))}</div>
            )}
          </div>
          <div className="flex gap-2">
            {approval.coverageCases[0] && <Button size="sm" asChild><Link href={`/coverage/${approval.coverageCases[0].id}`}>Fill first gap</Link></Button>}
            <Button size="sm" variant="ghost" onClick={() => setApproval(null)}>Dismiss</Button>
          </div>
        </div>
      )}

      <Panel title="Requests" action={<Segmented value={filter} onChange={setFilter} options={[{ value: "pending", label: "Pending" }, { value: "approved", label: "Approved" }, { value: "rejected", label: "Rejected" }, { value: "all", label: "All" }]} />}>
        {q.isLoading ? <SkeletonRows n={6} /> : q.isError ? <ErrorState what="leave" onRetry={() => q.refetch()} /> : !q.data?.length ? (
          <Empty icon={<CalendarOff className="h-5 w-5" />} title={filter === "pending" ? "No leave waiting on you" : "Nothing here"} body="Import an Orbyte export or add leave manually."
            action={<Button variant="outline" size="sm" onClick={() => setImportOpen(true)}><FileText className="h-4 w-4 mr-1.5" />Import CSV</Button>} />
        ) : (
          <div className="divide-y">
            {q.data.map((l, i) => (
              <div key={l.id} className="grid grid-cols-[auto_1fr_auto] md:grid-cols-[auto_1.3fr_1fr_100px_90px_auto] items-center gap-3 md:gap-4 px-4 py-3 rise" style={{ animationDelay: `${Math.min(i, 12) * 30}ms` }} data-testid={`row-leave-${l.id}`}>
                <Initials name={l.employeeName} />
                <div className="min-w-0">
                  <Link href={`/team/${l.employeeId}`} className="font-medium hover:underline">{l.employeeName}</Link>
                  <div className="text-xs text-muted-foreground truncate">{l.roleName ?? ""}{l.reason ? ` · ${l.reason}` : ""}</div>
                </div>
                <div className="hidden md:block text-sm">
                  <div><span className="font-medium">{l.leaveType}</span></div>
                  <div className="font-mono text-xs text-muted-foreground">{fmtDate(l.startDate)}{l.endDate !== l.startDate && ` – ${fmtDate(l.endDate)}`}</div>
                </div>
                <div className="hidden md:block font-mono text-xs">
                  <span className={l.affectedShiftCount ? "text-[hsl(32_80%_30%)] font-semibold" : "text-muted-foreground"}>{l.affectedShiftCount} shift{l.affectedShiftCount === 1 ? "" : "s"}</span>
                </div>
                <div className="hidden md:flex flex-col gap-1 items-start">
                  <Tag className="font-mono uppercase text-[10px]">{l.source}</Tag>
                  {l.externalRef && <span className="font-mono text-[10px] text-muted-foreground">{l.externalRef}</span>}
                </div>
                <div className="flex items-center gap-1.5 justify-end">
                  {l.status === "pending" ? (
                    <>
                      <Button size="sm" variant="outline" onClick={() => setPreview(l)} data-testid={`button-preview-${l.id}`}><Users className="h-4 w-4 mr-1" />Check cover</Button>
                      <Button size="sm" variant="ghost" disabled={busy} aria-label="Reject" data-testid={`button-reject-${l.id}`} onClick={() => doReject(l)}><X className="h-4 w-4" /></Button>
                      <Button size="sm" disabled={busy} data-testid={`button-approve-${l.id}`} onClick={() => doApprove(l)}><Check className="h-4 w-4 mr-1" />Approve</Button>
                    </>
                  ) : <Pill status={l.status} />}
                </div>
              </div>
            ))}
          </div>
        )}
      </Panel>
      <CreateLeaveDialog open={createOpen} onOpenChange={setCreateOpen} onCreated={(r) => { if (r.leave.status === "approved") setApproval(r); }} />
      <ImportDialog open={importOpen} onOpenChange={setImportOpen} />
      <LeaveCoverPreviewDialog leave={preview} onOpenChange={(v) => { if (!v) setPreview(null); }} onApprove={doApprove} onReject={doReject} busy={busy} />
    </div>
  );
}
