import { useState } from "react";
import { Link } from "wouter";
import { Inbox, Info } from "lucide-react";
import { useListNotifications } from "@workspace/api-client-react";
import { PageHeader, Panel, SkeletonRows, Empty, ErrorState, Segmented } from "@/components/kit";
import { NotificationList } from "./notification-list";

type F = "all" | "offered" | "replacement" | "original" | "team" | "manager";
const OPTS: { value: F; label: string }[] = [
  { value: "all", label: "All" }, { value: "offered", label: "Offers" }, { value: "replacement", label: "Replacement" },
  { value: "original", label: "On leave" }, { value: "team", label: "Team" }, { value: "manager", label: "Manager" },
];

export default function Outbox() {
  const q = useListNotifications();
  const [f, setF] = useState<F>("all");
  const all = q.data ?? [];
  const list = f === "all" ? all : all.filter((n) => n.audience === f);
  const queued = all.filter((n) => n.emailStatus === "queued").length;
  const unread = all.filter((n) => !n.readAt).length;
  return (
    <div>
      <PageHeader eyebrow="Outbox" title="Every message the desk wrote" sub={`${all.length} messages · ${unread} unread in-app · ${queued} emails queued`}
        actions={<Segmented value={f} onChange={(v) => setF(v)} options={OPTS} />} />
      <div className="mb-4 rounded-lg border border-accent/60 bg-accent/10 p-4 flex gap-3 text-sm rise" data-testid="banner-no-provider">
        <Info className="h-5 w-5 text-[hsl(32_80%_32%)] shrink-0" />
        <div>
          <div className="font-medium">Email is not connected yet, so no email has been delivered.</div>
          <div className="text-muted-foreground mt-0.5">Staff see these messages in their in-app inbox when they sign in. The email copy is held as <span className="font-mono">queued</span> until an email provider is set up.</div>
        </div>
      </div>
      <Panel>
        {q.isLoading ? <SkeletonRows n={6} /> : q.isError ? <ErrorState what="the outbox" onRetry={() => q.refetch()} /> : !list.length ? (
          <Empty icon={<Inbox className="h-5 w-5" />} title="Nothing here" body="Messages are written when you send cover offers and when shifts are filled." action={<Link href="/coverage" className="text-sm text-primary font-medium hover:underline">Open the cover queue</Link>} />
        ) : <NotificationList items={list} />}
      </Panel>
    </div>
  );
}
