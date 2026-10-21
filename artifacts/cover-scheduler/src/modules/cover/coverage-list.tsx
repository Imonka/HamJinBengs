import { useState } from "react";
import { LifeBuoy } from "lucide-react";
import { useListCoverage, type ListCoverageParams } from "@workspace/api-client-react";
import { PageHeader, Panel, SkeletonRows, Empty, ErrorState, Segmented } from "@/components/kit";
import { CaseRow } from "./case-row";

type View = "unfilled" | "filled" | "cancelled";
const OPTS: { value: View; label: string }[] = [
  { value: "unfilled", label: "Unfilled" }, { value: "filled", label: "Filled" }, { value: "cancelled", label: "Cancelled" },
];
const PARAMS: Record<View, ListCoverageParams> = { unfilled: { unfilled: true }, filled: { status: "filled" }, cancelled: { status: "cancelled" } };

export default function CoverageList() {
  const [view, setView] = useState<View>("unfilled");
  const q = useListCoverage(PARAMS[view]);
  // Unfilled: one queue, earliest gap first, so the earliest gap is always handled first.
  // History (filled / cancelled): most recent first.
  const list = [...(q.data ?? [])].sort((a, b) => {
    const ka = `${a.shift.date}${a.shift.startTime}`, kb = `${b.shift.date}${b.shift.startTime}`;
    return view === "unfilled" ? ka.localeCompare(kb) : kb.localeCompare(ka);
  });
  return (
    <div>
      <PageHeader eyebrow="Cover queue" title="Shifts left behind by leave"
        sub={view === "unfilled"
          ? "Every unfilled gap in one list, earliest first. Work from the top. Open means nobody has been asked; offered means you are waiting on replies. Amber edge: starts within 48 hours."
          : "Closed cases, most recent first."}
        actions={<Segmented value={view} onChange={(v) => setView(v)} options={OPTS} />} />
      <Panel>
        <div className="hidden md:grid grid-cols-[110px_1fr_200px_110px_20px] gap-4 px-4 h-9 items-center border-b font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
          <span>Starts</span><span>Shift</span><span>{view === "filled" ? "Covered by" : "Window"}</span><span>Status</span><span />
        </div>
        {q.isLoading ? <SkeletonRows n={6} /> : q.isError ? <ErrorState what="cover cases" onRetry={() => q.refetch()} /> : list.length ? (
          <div className="divide-y">{list.map((c, i) => <CaseRow key={c.id} c={c} index={i} next={view === "unfilled" && i === 0} />)}</div>
        ) : (
          <Empty icon={<LifeBuoy className="h-5 w-5" />} title={view === "unfilled" ? "Nothing to cover" : `No ${view} cases`}
            body={view === "unfilled" ? "Approve leave and any affected shifts appear here." : "They will collect here over time."} />
        )}
      </Panel>
    </div>
  );
}
