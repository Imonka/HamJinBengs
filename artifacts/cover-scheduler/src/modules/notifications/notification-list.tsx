import { Mail } from "lucide-react";
import { type Notification } from "@workspace/api-client-react";
import { Pill, Tag } from "@/components/kit";
import { fmtDateTime, relative } from "@/lib/time";

const audienceLabel: Record<string, string> = { offered: "Offered", replacement: "Replacement", original: "Person on leave", team: "Teammate", manager: "Manager" };

export function NotificationList({ items }: { items: Notification[] }) {
  return (
    <div className="divide-y">
      {items.map((n, i) => (
        <details key={n.id} className="group px-4 py-3 rise" style={{ animationDelay: `${Math.min(i, 12) * 30}ms` }} data-testid={`notification-${n.id}`}>
          <summary className="flex items-center gap-3 cursor-pointer list-none">
            <Mail className="h-4 w-4 text-muted-foreground shrink-0" />
            <div className="min-w-0 flex-1">
              <div className="text-sm font-medium truncate">{n.recipientName} <span className="text-muted-foreground font-normal">· {n.recipientEmail}</span></div>
              <div className="text-xs text-muted-foreground truncate">{n.subject}</div>
            </div>
            <div className="hidden sm:flex items-center gap-1.5">
              <Tag>{audienceLabel[n.audience] ?? n.audience}</Tag>
              <Tag className="font-mono text-[10px]">{n.kind.replace(/_/g, " ")}</Tag>
              <span className="font-mono text-[10px] text-muted-foreground w-16 text-right">{n.readAt ? "read" : "unread"}</span>
            </div>
            <Pill status={n.emailStatus} label={n.emailStatus === "queued" ? "email queued" : undefined} />
          </summary>
          <div className="mt-3 ml-7 text-[11px] font-mono text-muted-foreground">{fmtDateTime(n.createdAt)}{n.readAt ? ` · read ${relative(n.readAt)}` : ""}</div>
          <pre className="mt-1.5 ml-7 whitespace-pre-wrap font-sans text-[13px] bg-secondary/60 rounded-md p-3 text-secondary-foreground">{n.body}</pre>
        </details>
      ))}
    </div>
  );
}
