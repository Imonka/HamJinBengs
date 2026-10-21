import { useState, type ReactNode } from "react";
import { Link, useLocation } from "wouter";
import { LayoutGrid, LifeBuoy, CalendarOff, CalendarDays, Users, Inbox, SlidersHorizontal, Menu, X, HandHelping, CalendarClock } from "lucide-react";
import { useGetDashboardSummary, useListMyNotifications, useListMyOffers, getGetDashboardSummaryQueryKey, getListMyOffersQueryKey, getListMyNotificationsQueryKey, type CurrentUser } from "@workspace/api-client-react";
import { AccountFooter } from "@/modules/accounts";
import { cn } from "@/lib/utils";

type NavItem = { href: string; label: string; icon: typeof LayoutGrid; count?: number; hot?: boolean };

function Shell({ nav, user, children }: { nav: NavItem[]; user: CurrentUser; children: ReactNode }) {
  const [loc] = useLocation();
  const [open, setOpen] = useState(false);
  const active = (h: string) => (h === "/" ? loc === "/" : loc.startsWith(h));
  const sidebar = (
    <aside className="flex h-full w-60 flex-col bg-sidebar text-sidebar-foreground">
      <div className="px-5 pt-6 pb-5">
        <div className="flex items-center gap-2.5">
          <div className="h-8 w-8 rounded-md bg-sidebar-primary grid place-items-center">
            <div className="h-3.5 w-3.5 rounded-sm border-2 border-sidebar-primary-foreground border-r-transparent rotate-45" />
          </div>
          <div>
            <div className="font-display font-extrabold text-[17px] leading-none text-sidebar-accent-foreground">Gantian</div>
            <div className="font-mono text-[9.5px] uppercase tracking-[0.2em] text-sidebar-foreground/50 mt-1">{user.access === "manager" ? "leave cover desk" : "staff portal"}</div>
          </div>
        </div>
      </div>
      <nav className="flex-1 px-3 space-y-0.5">
        {nav.map((n) => (
          <Link key={n.href} href={n.href} onClick={() => setOpen(false)} data-testid={`link-nav-${n.label.toLowerCase().replace(/\s/g, "-")}`}
            className={cn("group flex items-center gap-3 rounded-md px-3 h-9 text-[13.5px] transition-colors relative",
              active(n.href) ? "bg-sidebar-accent text-sidebar-accent-foreground" : "text-sidebar-foreground/70 hover:text-sidebar-accent-foreground hover:bg-sidebar-accent/50")}>
            {active(n.href) && <span className="absolute left-0 top-2 bottom-2 w-[3px] rounded-r bg-sidebar-primary" />}
            <n.icon className="h-4 w-4" />
            <span className="flex-1">{n.label}</span>
            {!!n.count && <span className={cn("font-mono text-[10.5px] px-1.5 rounded tnum", n.hot ? "bg-sidebar-primary text-sidebar-primary-foreground" : "bg-sidebar-foreground/10")}>{n.count}</span>}
          </Link>
        ))}
      </nav>
      <AccountFooter user={user} sub={user.access === "manager" ? "Manager" : user.roleName ?? "Staff"} />
    </aside>
  );
  return (
    <div className="min-h-[100dvh] flex">
      <div className="hidden md:block fixed inset-y-0 left-0 z-30">{sidebar}</div>
      {open && (
        <div className="md:hidden fixed inset-0 z-40 flex">
          {sidebar}
          <button aria-label="Close menu" className="flex-1 bg-foreground/30" onClick={() => setOpen(false)} />
        </div>
      )}
      <div className="flex-1 md:pl-60 min-w-0">
        <div className="md:hidden sticky top-0 z-20 flex items-center gap-3 h-12 px-4 bg-sidebar text-sidebar-accent-foreground">
          <button onClick={() => setOpen(!open)} data-testid="button-menu">{open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}</button>
          <span className="font-display font-bold">Gantian</span>
        </div>
        <main className="px-4 md:px-8 py-6 md:py-8 max-w-[1400px] mx-auto">{children}</main>
      </div>
    </div>
  );
}

export function ManagerLayout({ user, children }: { user: CurrentUser; children: ReactNode }) {
  const { data: s } = useGetDashboardSummary({ query: { refetchInterval: 30_000, queryKey: getGetDashboardSummaryQueryKey() } });
  const nav: NavItem[] = [
    { href: "/", label: "Desk", icon: LayoutGrid },
    { href: "/coverage", label: "Cover queue", icon: LifeBuoy, count: s ? s.openCases + s.offeredCases : undefined, hot: true },
    { href: "/leave", label: "Leave", icon: CalendarOff, count: s?.pendingLeave },
    { href: "/schedule", label: "Roster", icon: CalendarDays, count: s?.rosterGapsThisWeek },
    { href: "/team", label: "Team", icon: Users },
    { href: "/outbox", label: "Outbox", icon: Inbox },
    { href: "/setup", label: "Setup", icon: SlidersHorizontal },
  ];
  return <Shell nav={nav} user={user}>{children}</Shell>;
}

export function StaffLayout({ user, children }: { user: CurrentUser; children: ReactNode }) {
  const offers = useListMyOffers(undefined, { query: { refetchInterval: 15_000, queryKey: getListMyOffersQueryKey() } });
  const notes = useListMyNotifications({ query: { refetchInterval: 30_000, queryKey: getListMyNotificationsQueryKey() } });
  const nav: NavItem[] = [
    { href: "/", label: "Cover requests", icon: HandHelping, count: offers.data?.filter((o) => o.status === "pending").length, hot: true },
    { href: "/my-shifts", label: "My shifts", icon: CalendarClock },
    { href: "/inbox", label: "Inbox", icon: Inbox, count: notes.data?.filter((n) => !n.readAt).length },
  ];
  return <Shell nav={nav} user={user}>{children}</Shell>;
}
