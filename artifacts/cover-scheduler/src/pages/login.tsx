import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useLocation } from "wouter";
import { useLogin, getGetCurrentUserQueryKey } from "@workspace/api-client-react";
import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { PinInput } from "@/components/account";
import { setToken } from "@/lib/auth";
import { errMsg } from "@/lib/api-error";

export default function Login() {
  const login = useLogin();
  const qc = useQueryClient();
  const [, setLocation] = useLocation();
  const [email, setEmail] = useState("");
  const [pin, setPin] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const valid = email.includes("@") && /^\d{4,8}$/.test(pin);
  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!valid) return;
    setErr(null);
    login.mutate({ data: { email: email.trim(), pin } }, {
      onSuccess: (r) => { setLocation("/"); qc.clear(); qc.setQueryData(getGetCurrentUserQueryKey(), r.user); setToken(r.token); },
      onError: (e) => { setErr(errMsg(e, "Email or PIN is not right.")); setPin(""); },
    });
  };
  return (
    <div className="min-h-[100dvh] grid md:grid-cols-[1fr_480px]">
      <div className="hidden md:flex relative bg-sidebar text-sidebar-accent-foreground p-12 flex-col justify-between overflow-hidden">
        <div className="absolute inset-0 stripes opacity-25" />
        <div className="relative flex items-center gap-2.5">
          <div className="h-9 w-9 rounded-md bg-sidebar-primary grid place-items-center"><div className="h-4 w-4 rounded-sm border-2 border-sidebar-primary-foreground border-r-transparent rotate-45" /></div>
          <span className="font-display font-extrabold text-xl">Gantian</span>
        </div>
        <div className="relative">
          <div className="font-mono text-[11px] uppercase tracking-[0.22em] text-sidebar-primary mb-4">Leave cover desk</div>
          <h1 className="font-display text-5xl lg:text-6xl font-extrabold leading-[0.95] max-w-lg">Someone is on leave.<br />The shift still opens.</h1>
          <p className="mt-5 text-sidebar-foreground/70 max-w-md">Managers send cover offers to the colleagues who fit. The first to accept gets the shift and everyone is told.</p>
        </div>
        <div className="relative font-mono text-[10.5px] uppercase tracking-wider text-sidebar-foreground/40">Times in Malaysia (MYT)</div>
      </div>
      <div className="flex items-center justify-center p-6 md:p-12">
        <form onSubmit={submit} className="w-full max-w-sm rise">
          <div className="md:hidden font-display font-extrabold text-2xl mb-8">Gantian</div>
          <h2 className="font-display text-3xl font-bold">Sign in</h2>
          <p className="text-sm text-muted-foreground mt-1.5">Use your work email and PIN.</p>
          <div className="mt-7 space-y-4">
            <div className="space-y-1.5"><Label htmlFor="email">Email</Label>
              <Input id="email" type="email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@company.my" data-testid="input-email" autoFocus /></div>
            <div className="space-y-1.5"><Label htmlFor="pin">PIN</Label>
              <PinInput id="pin" value={pin} onChange={setPin} testId="input-pin" /></div>
            {err && <p className="text-sm text-destructive rounded-md bg-destructive/10 px-3 py-2" data-testid="text-login-error">{err}</p>}
            <Button type="submit" size="lg" className="w-full font-semibold" disabled={!valid || login.isPending} data-testid="button-sign-in">
              {login.isPending ? "Signing in..." : <>Sign in <ArrowRight className="h-4 w-4 ml-1.5" /></>}
            </Button>
          </div>
          {import.meta.env.DEV && (
            <div className="mt-8 rounded-md border border-dashed p-3 text-xs text-muted-foreground" data-testid="text-demo-accounts">
              <div className="font-mono uppercase tracking-wider text-[10px] mb-1.5">Demo accounts</div>
              <div>Manager: <button type="button" className="font-mono text-foreground hover:underline" onClick={() => { setEmail("farah@kopilane.my"); setPin("1234"); }}>farah@kopilane.my</button> / PIN 1234</div>
              <div>Staff: <button type="button" className="font-mono text-foreground hover:underline" onClick={() => { setEmail("aisyah@kopilane.my"); setPin("1111"); }}>aisyah@kopilane.my</button> / PIN 1111</div>
            </div>
          )}
        </form>
      </div>
    </div>
  );
}
