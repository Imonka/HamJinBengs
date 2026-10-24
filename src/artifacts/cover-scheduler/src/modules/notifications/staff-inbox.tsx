import { Inbox, CheckCheck } from "lucide-react";
import { useListMyNotifications, useMarkAllMyNotificationsRead } from "@workspace/api-client-react";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import { PageHeader, Panel, SkeletonRows, Empty, ErrorState } from "@/components/kit";
import { relative } from "@/lib/time";
import { errMsg } from "@/lib/api-error";
import { useInvalidateOps } from "@/lib/invalidate";
import { cn } from "@/lib/utils";

export default function StaffInbox() {
  const q = useListMyNotifications();
  const mark = useMarkAllMyNotificationsRead();
  const invalidate = useInvalidateOps();
  const { toast } = useToast();
  const unread = (q.data ?? []).filter((n) => !n.readAt).length;
  return (
    <div className="max-w-3xl">
      <PageHeader eyebrow="Inbox" title={unread ? `${unread} unread` : "All caught up"}
        actions={<Button variant="outline" disabled={!unread || mark.isPending} data-testid="button-mark-all-read"
          onClick={() => mark.mutate(undefined, { onSuccess: invalidate, onError: (e) => toast({ title: "Could not update", description: errMsg(e), variant: "destructive" }) })}>
          <CheckCheck className="h-4 w-4 mr-1.5" />Mark all read</Button>} />
      <Panel>
        {q.isLoading ? <SkeletonRows n={5} /> : q.isError ? <ErrorState what="your inbox" onRetry={() => q.refetch()} /> : !q.data?.length ? (
          <Empty icon={<Inbox className="h-5 w-5" />} title="No messages yet" body="Cover requests and roster changes will show up here." />
        ) : (
          <div className="divide-y">
            {q.data.map((n, i) => (
              <details key={n.id} className="group px-4 py-3 rise" style={{ animationDelay: `${Math.min(i, 12) * 30}ms` }} data-testid={`notification-${n.id}`}>
                <summary className="flex items-center gap-3 cursor-pointer list-none">
                  <span className={cn("h-2 w-2 rounded-full shrink-0", n.readAt ? "bg-transparent" : "bg-accent")} />
                  <div className="flex-1 min-w-0">
                    <div className={cn("text-sm truncate", !n.readAt && "font-semibold")}>{n.subject}</div>
                    <div className="font-mono text-[10.5px] text-muted-foreground">{relative(n.createdAt)}</div>
                  </div>
                </summary>
                <pre className="mt-3 ml-5 whitespace-pre-wrap font-sans text-[13px] bg-secondary/60 rounded-md p-3">{n.body}</pre>
              </details>
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}
