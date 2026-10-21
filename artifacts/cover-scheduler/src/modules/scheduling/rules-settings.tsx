import { useEffect, useState } from "react";
import { Plug } from "lucide-react";
import { useGetSettings, useUpdateSettings, getGetSettingsQueryKey, type SettingsInput } from "@workspace/api-client-react";
import { useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/hooks/use-toast";
import { Panel, SkeletonRows, ErrorState } from "@/components/kit";
import { WEEKDAYS } from "@/lib/time";
import { errMsg } from "@/lib/api-error";
import { useInvalidateOps } from "@/lib/invalidate";
import { cn } from "@/lib/utils";
import { DayChips } from "./day-chips";

/* ---------------- Rules ---------------- */
export function RulesTab() {
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

