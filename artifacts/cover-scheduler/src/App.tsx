import { type ReactNode } from 'react';
import { QueryCache, MutationCache, QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Route, Switch, useLocation, Router as WouterRouter } from 'wouter';
import { useGetCurrentUser, getGetCurrentUserQueryKey, type CurrentUser } from '@workspace/api-client-react';
import { ErrorBoundary } from '@/components/error-boundary';
import { Toaster } from '@/components/ui/toaster';
import { TooltipProvider } from '@/components/ui/tooltip';
import { ManagerLayout, StaffLayout } from '@/components/layout';
import { setToken, useToken } from '@/lib/auth';
import { errStatus } from '@/lib/api-error';
import NotFound from '@/pages/not-found';
import Login from '@/pages/login';
import Dashboard from '@/pages/dashboard';
import CoverageList from '@/pages/coverage-list';
import CoverageDetail from '@/pages/coverage-detail';
import LeavePage from '@/pages/leave';
import Schedule from '@/pages/schedule';
import Team from '@/pages/team';
import EmployeePage from '@/pages/employee';
import Outbox from '@/pages/outbox';
import Setup from '@/pages/setup';
import StaffOffers from '@/pages/staff-offers';
import StaffShifts from '@/pages/staff-shifts';
import StaffInbox from '@/pages/staff-inbox';

const on401 = (e: unknown) => { if (errStatus(e) === 401) setToken(null); };
const queryClient = new QueryClient({
  queryCache: new QueryCache({ onError: on401 }),
  mutationCache: new MutationCache({ onError: on401 }),
  defaultOptions: { queries: { staleTime: 10_000, retry: (n, e) => errStatus(e) !== 401 && errStatus(e) !== 403 && errStatus(e) !== 404 && n < 2 } },
});

function ManagerRoutes({ user }: { user: CurrentUser }) {
  return (
    <ManagerLayout user={user}>
      <RoutedErrorBoundary>
        <Switch>
          <Route path="/" component={Dashboard} />
          <Route path="/coverage" component={CoverageList} />
          <Route path="/coverage/:id" component={CoverageDetail} />
          <Route path="/leave" component={LeavePage} />
          <Route path="/schedule" component={Schedule} />
          <Route path="/team" component={Team} />
          <Route path="/team/:id" component={EmployeePage} />
          <Route path="/outbox" component={Outbox} />
          <Route path="/setup" component={Setup} />
          <Route path="/settings" component={Setup} />
          <Route component={NotFound} />
        </Switch>
      </RoutedErrorBoundary>
    </ManagerLayout>
  );
}

function StaffRoutes({ user }: { user: CurrentUser }) {
  return (
    <StaffLayout user={user}>
      <RoutedErrorBoundary>
        <Switch>
          <Route path="/" component={StaffOffers} />
          <Route path="/my-shifts" component={StaffShifts} />
          <Route path="/inbox" component={StaffInbox} />
          <Route component={NotFound} />
        </Switch>
      </RoutedErrorBoundary>
    </StaffLayout>
  );
}

function Gate() {
  const token = useToken();
  const me = useGetCurrentUser({ query: { enabled: !!token, queryKey: getGetCurrentUserQueryKey() } });
  if (!token) return <Login />;
  if (me.isLoading) return (
    <div className="min-h-[100dvh] grid place-items-center">
      <div className="font-mono text-xs uppercase tracking-[0.2em] text-muted-foreground flex items-center gap-2"><span className="h-1.5 w-1.5 rounded-full bg-accent pulse-dot" />Opening the desk</div>
    </div>
  );
  if (!me.data) return <Login />;
  return me.data.access === 'manager' ? <ManagerRoutes user={me.data} /> : <StaffRoutes user={me.data} />;
}

function RoutedErrorBoundary({ children }: { children: ReactNode }) {
  const [location] = useLocation();
  return <ErrorBoundary resetKey={location}>{children}</ErrorBoundary>;
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <WouterRouter base={import.meta.env.BASE_URL.replace(/\/$/, '')}>
          <Gate />
        </WouterRouter>
        <Toaster />
      </TooltipProvider>
    </QueryClientProvider>
  );
}

export default App;
