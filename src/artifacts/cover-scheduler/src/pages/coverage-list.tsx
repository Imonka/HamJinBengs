import { useState } from "react";
import { LifeBuoy } from "lucide-react";
import { useListCoverage, type CoverageStatus } from "@workspace/api-client-react";
import { PageHeader, Panel, SkeletonRows, Empty, ErrorState, Segmented } from "@/components/kit";
import { CaseRow } from "@/components/case-row";

const OPTS: { value: CoverageStatus; label: string }[] = [
  { value: "open", label: "Open" }, { value: "offered", label: "Offered" }, { value: "filled", label: "Filled" }, { value: "cancelled", label: "Cancelled" },
];

export default function CoverageList() {
  const [status, setStatus] = useState<CoverageStatus>("open");
  const q = useListCoverage({ status });
  const list = [...(q.data ?? [])].sort((a, b) => {
    const ka = `${a.shift.date}${a.shift.startTime}`, kb = `${b.shift.date}${b.shift.startTime}`;
    return status === "open" || status === "offered" ? ka.localeCompare(kb) : kb.localeCompare(ka);
  });
  return (
    <div>
      <PageHeader eyebrow="Cover queue" title="Shifts left behind by leave" sub="Open means nobody has been asked. Offered means you are waiting on replies. Amber edge: starts within 48 hours."
        actions={<Segmented value={status} onChange={(v) => setStatus(v)} options={OPTS} />} />
      <Panel>
        <div className="hidden md:grid grid-cols-[110px_1fr_200px_110px_20px] gap-4 px-4 h-9 items-center border-b font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
          <span>Starts</span><span>Shift</span><span>{status === "filled" ? "Covered by" : "Window"}</span><span>Status</span><span />
        </div>
        {q.isLoading ? <SkeletonRows n={6} /> : q.isError ? <ErrorState what="cover cases" onRetry={() => q.refetch()} /> : list.length ? (
          <div className="divide-y">{list.map((c, i) => <CaseRow key={c.id} c={c} index={i} />)}</div>
        ) : (
          <Empty icon={<LifeBuoy className="h-5 w-5" />} title={status === "open" ? "Nothing to cover" : `No ${status} cases`}
            body={status === "open" ? "Approve leave and any affected shifts appear here." : "They will collect here over time."} />
        )}
      </Panel>
    </div>
  );
}
