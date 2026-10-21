import { useState } from "react";
import { HandHelping, Check, X, Clock, AlertTriangle, ArrowRight } from "lucide-react";
import {
  useListMyOffers, useAcceptOffer, useDeclineOffer, getListMyOffersQueryKey, type MyOffer,
} from "@workspace/api-client-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { useToast } from "@/hooks/use-toast";
import { PageHeader, Panel, Pill, SkeletonRows, Empty, ErrorState } from "@/components/kit";
import { fmtYmd, fmtHm, relative } from "@/lib/time";
import { errMsg } from "@/lib/api-error";
import { useInvalidateOps } from "@/lib/invalidate";
import { cn } from "@/lib/utils";

function pastLabel(o: MyOffer) {
  if (o.status === "expired") return o.caseStatus === "filled" ? "Someone else took it" : "No longer eligible";
  if (o.status === "accepted") return "You took it";
  return undefined;
}

function OfferCard({ o, index, onDecline }: { o: MyOffer; index: number; onDecline: (o: MyOffer) => void }) {
  const accept = useAcceptOffer();
  const invalidate = useInvalidateOps();
  const { toast } = useToast();
  const [err, setErr] = useState<string | null>(null);
  const pct = Math.min(100, (o.hoursAfter / o.maxHoursPerWeek) * 100);
  const pctBefore = Math.min(100, (o.hoursThisWeek / o.maxHoursPerWeek) * 100);
  const over = o.hoursAfter > o.maxHoursPerWeek;
  const go = () => accept.mutate({ offerId: o.id }, {
    onSuccess: () => { invalidate(); toast({ title: "Shift is yours", description: `${fmtYmd(o.shift.date)}, ${fmtHm(o.shift.startTime)}. Your manager has been told.` }); },
    onError: (e) => { setErr(errMsg(e, "This offer is no longer available.")); invalidate(); },
  });
  return (
    <div className="rounded-lg border bg-card overflow-hidden rise" style={{ animationDelay: `${index * 50}ms` }} data-testid={`card-offer-${o.id}`}>
      <div className="flex">
        <div className="w-1.5 bg-accent shrink-0" />
        <div className="flex-1 p-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <div className="font-mono text-[10.5px] uppercase tracking-[0.18em] text-[hsl(32_80%_32%)] flex items-center gap-2"><span className="h-1.5 w-1.5 rounded-full bg-accent pulse-dot" />Cover request · sent {relative(o.createdAt)}</div>
              <div className="font-display text-3xl font-extrabold mt-1.5 leading-none">{fmtYmd(o.shift.date)}</div>
              <div className="font-mono text-sm mt-1.5">{fmtHm(o.shift.startTime)} to {fmtHm(o.shift.endTime)} <span className="text-muted-foreground">· {o.shift.hours.toFixed(1)}h · {o.shift.roleName}</span></div>
            </div>
            <div className="text-sm text-right">
              <div className="text-muted-foreground text-xs">Covering for</div>
              <div className="font-medium">{o.coveringFor}</div>
            </div>
          </div>
          {o.message && <p className="mt-4 text-sm bg-secondary/70 rounded-md px-3 py-2 border-l-2 border-primary">"{o.message}"</p>}
          <div className="mt-4">
            <div className="flex justify-between font-mono text-[11px] text-muted-foreground mb-1">
              <span>Your week</span>
              <span className="tnum">{o.hoursThisWeek.toFixed(1)}h <ArrowRight className="inline h-3 w-3" /> <span className={over ? "text-destructive font-semibold" : "text-foreground"}>{o.hoursAfter.toFixed(1)}h</span> of {o.maxHoursPerWeek}h</span>
            </div>
            <div className="relative h-2 rounded-full bg-secondary overflow-hidden">
              <div className={cn("absolute inset-y-0 left-0", over ? "bg-destructive/60" : "bg-primary/35")} style={{ width: `${pct}%` }} />
              <div className="absolute inset-y-0 left-0 bg-primary" style={{ width: `${pctBefore}%` }} />
            </div>
          </div>
          {(!o.canAccept || err) && (
            <div className="mt-3 text-sm flex gap-2 items-start rounded-md bg-destructive/10 text-destructive px-3 py-2" data-testid={`text-offer-blocked-${o.id}`}>
              <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />{err ?? o.blockedReason ?? "You cannot take this shift."}
            </div>
          )}
          <div className="mt-4 flex gap-2 justify-end">
            <Button variant="outline" onClick={() => onDecline(o)} data-testid={`button-decline-${o.id}`}><X className="h-4 w-4 mr-1.5" />Decline</Button>
            <Button size="lg" disabled={!o.canAccept || accept.isPending || !!err} onClick={go} data-testid={`button-accept-${o.id}`} className="font-semibold">
              <Check className="h-4 w-4 mr-1.5" />{accept.isPending ? "Taking it..." : "Accept shift"}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function StaffOffers() {
  const q = useListMyOffers(undefined, { query: { refetchInterval: 15_000, queryKey: getListMyOffersQueryKey() } });
  const decline = useDeclineOffer();
  const invalidate = useInvalidateOps();
  const { toast } = useToast();
  const [declining, setDeclining] = useState<MyOffer | null>(null);
  const [note, setNote] = useState("");
  const pending = (q.data ?? []).filter((o) => o.status === "pending");
  const past = (q.data ?? []).filter((o) => o.status !== "pending");

  const doDecline = () => {
    if (!declining) return;
    decline.mutate({ offerId: declining.id, data: { note: note.trim() || null } }, {
      onSuccess: () => { invalidate(); setDeclining(null); setNote(""); toast({ title: "Declined", description: "Thanks for letting your manager know." }); },
      onError: (e) => { toast({ title: "Could not decline", description: errMsg(e), variant: "destructive" }); invalidate(); setDeclining(null); },
    });
  };

  return (
    <div className="max-w-3xl">
      <PageHeader eyebrow="Cover requests" title={pending.length ? `${pending.length} shift${pending.length > 1 ? "s" : ""} need you` : "Nothing waiting"}
        sub="When a colleague is on leave, your manager may ask you to cover. The first person to accept gets the shift." />
      {q.isLoading ? <Panel><SkeletonRows n={3} h={90} /></Panel> : q.isError ? <Panel><ErrorState what="your requests" onRetry={() => q.refetch()} /></Panel> : (
        <>
          <div className="space-y-4">
            {pending.length ? pending.map((o, i) => <OfferCard key={o.id} o={o} index={i} onDecline={setDeclining} />) : (
              <Panel><Empty icon={<HandHelping className="h-5 w-5" />} title="No cover requests right now" body="This page checks for new requests every few seconds. You will also see them in your inbox." /></Panel>
            )}
          </div>
          {past.length > 0 && (
            <Panel title="Earlier requests" className="mt-8" delay={80}>
              <div className="divide-y">
                {past.map((o) => (
                  <div key={o.id} className="flex items-center gap-4 px-4 py-3" data-testid={`row-past-offer-${o.id}`}>
                    <Clock className="h-4 w-4 text-muted-foreground shrink-0" />
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium">{fmtYmd(o.shift.date)}, {fmtHm(o.shift.startTime)} to {fmtHm(o.shift.endTime)}</div>
                      <div className="text-xs text-muted-foreground truncate">{o.shift.roleName} · covering for {o.coveringFor}</div>
                    </div>
                    <Pill status={o.status} label={pastLabel(o)} />
                  </div>
                ))}
              </div>
            </Panel>
          )}
        </>
      )}
      <Dialog open={!!declining} onOpenChange={(v) => { if (!v) setDeclining(null); }}>
        <DialogContent className="max-w-md">
          <DialogHeader><DialogTitle className="font-display text-xl">Decline this shift?</DialogTitle>
            <DialogDescription>{declining && `${fmtYmd(declining.shift.date)}, ${fmtHm(declining.shift.startTime)} to ${fmtHm(declining.shift.endTime)}`}</DialogDescription></DialogHeader>
          <Textarea value={note} onChange={(e) => setNote(e.target.value)} placeholder="Optional note for your manager, e.g. I have class that day" data-testid="input-decline-note" />
          <DialogFooter><Button variant="ghost" onClick={() => setDeclining(null)}>Keep it</Button><Button variant="destructive" disabled={decline.isPending} onClick={doDecline} data-testid="button-confirm-decline">Decline</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
