import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useLocation } from "wouter";
import { useChangeMyPin, useLogout, useUpdateMyProfile, getGetCurrentUserQueryKey, type CurrentUser } from "@workspace/api-client-react";
import { KeyRound, LogOut, UserRound } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { useToast } from "@/hooks/use-toast";
import { setToken } from "@/lib/auth";
import { errMsg } from "@/lib/api-error";

const pinOk = (p: string) => /^\d{4,8}$/.test(p);

export function PinInput(props: { value: string; onChange: (v: string) => void; id?: string; testId?: string; autoFocus?: boolean }) {
  return (
    <Input id={props.id} type="password" inputMode="numeric" autoComplete="off" maxLength={8} autoFocus={props.autoFocus}
      value={props.value} onChange={(e) => props.onChange(e.target.value.replace(/\D/g, "").slice(0, 8))}
      className="font-mono tracking-[0.4em]" data-testid={props.testId} />
  );
}

export function ChangePinDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (v: boolean) => void }) {
  const change = useChangeMyPin();
  const { toast } = useToast();
  const [cur, setCur] = useState("");
  const [next, setNext] = useState("");
  const [again, setAgain] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const close = (v: boolean) => { onOpenChange(v); if (!v) { setCur(""); setNext(""); setAgain(""); setErr(null); } };
  const valid = pinOk(cur) && pinOk(next) && next === again;
  const submit = () => change.mutate({ data: { currentPin: cur, newPin: next } }, {
    onSuccess: () => { close(false); toast({ title: "PIN changed", description: "Use the new PIN next time you sign in." }); },
    onError: (e) => setErr(errMsg(e, "Could not change PIN.")),
  });
  return (
    <Dialog open={open} onOpenChange={close}>
      <DialogContent className="max-w-sm">
        <DialogHeader><DialogTitle className="font-display text-xl">Change PIN</DialogTitle><DialogDescription>4 to 8 digits.</DialogDescription></DialogHeader>
        <div className="space-y-3">
          <div className="space-y-1.5"><Label>Current PIN</Label><PinInput value={cur} onChange={setCur} testId="input-current-pin" autoFocus /></div>
          <div className="space-y-1.5"><Label>New PIN</Label><PinInput value={next} onChange={setNext} testId="input-new-pin" /></div>
          <div className="space-y-1.5"><Label>New PIN again</Label><PinInput value={again} onChange={setAgain} testId="input-new-pin-again" />
            {again && next !== again && <p className="text-xs text-destructive">PINs do not match.</p>}</div>
          {err && <p className="text-sm text-destructive" data-testid="text-pin-error">{err}</p>}
        </div>
        <DialogFooter><Button variant="ghost" onClick={() => close(false)}>Cancel</Button><Button disabled={!valid || change.isPending} onClick={submit} data-testid="button-save-pin">Save PIN</Button></DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/** Your own name, email and phone. Only you can change these; managers can't. */
export function ProfileDialog({ user, open, onOpenChange }: { user: CurrentUser; open: boolean; onOpenChange: (v: boolean) => void }) {
  const update = useUpdateMyProfile();
  const qc = useQueryClient();
  const { toast } = useToast();
  const [f, setF] = useState({ name: "", email: "", phone: "", pin: "" });
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    if (open) { setF({ name: user.name, email: user.email, phone: user.phone ?? "", pin: "" }); setErr(null); }
  }, [open, user]);
  const emailChanged = f.email.trim().toLowerCase() !== user.email;
  const valid = f.name.trim() && f.email.includes("@") && (!emailChanged || pinOk(f.pin));
  const submit = () => update.mutate({ data: { name: f.name.trim(), email: f.email.trim(), phone: f.phone.trim() || null, currentPin: emailChanged ? f.pin : null } }, {
    onSuccess: (u) => { qc.setQueryData(getGetCurrentUserQueryKey(), u); qc.invalidateQueries(); onOpenChange(false); toast({ title: "Details saved" }); },
    onError: (e) => setErr(errMsg(e, "Could not save your details.")),
  });
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-sm">
        <DialogHeader><DialogTitle className="font-display text-xl">My details</DialogTitle><DialogDescription>Only you can change these.</DialogDescription></DialogHeader>
        <div className="space-y-3">
          <div className="space-y-1.5"><Label htmlFor="profile-name">Full name</Label><Input id="profile-name" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} data-testid="input-profile-name" /></div>
          <div className="space-y-1.5"><Label htmlFor="profile-email">Email (used to sign in)</Label><Input id="profile-email" type="email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} data-testid="input-profile-email" /></div>
          <div className="space-y-1.5"><Label htmlFor="profile-phone">Phone</Label><Input id="profile-phone" value={f.phone} onChange={(e) => setF({ ...f, phone: e.target.value })} placeholder="+60 12-345 6789" data-testid="input-profile-phone" /></div>
          {emailChanged && <div className="space-y-1.5"><Label htmlFor="profile-pin">Current PIN, to confirm the new email</Label><PinInput id="profile-pin" value={f.pin} onChange={(v) => setF({ ...f, pin: v })} testId="input-profile-pin" /></div>}
          {err && <p className="text-sm text-destructive" data-testid="text-profile-error">{err}</p>}
        </div>
        <DialogFooter><Button variant="ghost" onClick={() => onOpenChange(false)}>Cancel</Button><Button disabled={!valid || update.isPending} onClick={submit} data-testid="button-save-profile">{update.isPending ? "Saving..." : "Save"}</Button></DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function AccountFooter({ user, sub }: { user: CurrentUser; sub: string }) {
  const [pinOpen, setPinOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const logout = useLogout();
  const qc = useQueryClient();
  const [, setLocation] = useLocation();
  const signOut = () => {
    // Back to the home page, so the next person to sign in doesn't land on the previous user's page.
    const done = () => { setLocation("/"); setToken(null); qc.clear(); };
    logout.mutate(undefined, { onSettled: done });
  };
  return (
    <div className="m-3 rounded-md border border-sidebar-border p-3 text-[11.5px]">
      <div className="font-medium text-sidebar-accent-foreground truncate" data-testid="text-current-user">{user.name}</div>
      <div className="text-sidebar-foreground/55 truncate">{sub}</div>
      <div className="mt-2.5 flex gap-1">
        <button onClick={() => setProfileOpen(true)} data-testid="button-my-details" className="flex-1 inline-flex items-center justify-center gap-1.5 h-7 rounded bg-sidebar-accent/60 hover:bg-sidebar-accent text-sidebar-accent-foreground"><UserRound className="h-3 w-3" />Me</button>
        <button onClick={() => setPinOpen(true)} data-testid="button-change-pin" className="flex-1 inline-flex items-center justify-center gap-1.5 h-7 rounded bg-sidebar-accent/60 hover:bg-sidebar-accent text-sidebar-accent-foreground"><KeyRound className="h-3 w-3" />PIN</button>
        <button onClick={signOut} data-testid="button-sign-out" className="flex-1 inline-flex items-center justify-center gap-1.5 h-7 rounded bg-sidebar-accent/60 hover:bg-sidebar-accent text-sidebar-accent-foreground"><LogOut className="h-3 w-3" />Sign out</button>
      </div>
      <ChangePinDialog open={pinOpen} onOpenChange={setPinOpen} />
      <ProfileDialog user={user} open={profileOpen} onOpenChange={setProfileOpen} />
    </div>
  );
}
