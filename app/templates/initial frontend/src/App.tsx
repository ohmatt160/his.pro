import { lazy, Suspense, type ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
  useLocation,
} from "react-router-dom";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AuthProvider } from "@/context/AuthContext";
import {
  TenantRoutingProvider,
  useTenantRouting,
} from "@/context/TenantRoutingContext";
import AppShell from "@/components/AppShell";
import ProtectedRoute from "@/components/ProtectedRoute";
import ModuleRoute from "@/components/ModuleRoute";
import RealtimeBridge from "@/components/RealtimeBridge";
import { getCanonicalPathForLegacyPath } from "@/lib/tenant-routing";
import { routeRoles } from "@/lib/role-access";

const Alerts = lazy(() => import("./pages/Alerts.tsx"));
const AuditLogs = lazy(() => import("./pages/AuditLogs.tsx"));
const Billing = lazy(() => import("./pages/Billing.tsx"));
const Chat = lazy(() => import("./pages/Chat.tsx"));
const Dashboard = lazy(() => import("./pages/Dashboard.tsx"));
const DataProcessingAgreement = lazy(() => import("./pages/DataProcessingAgreement.tsx"));
const Appointments = lazy(() => import("./pages/Appointments.tsx"));
const GetStarted = lazy(() => import("./pages/GetStarted.tsx"));
const Index = lazy(() => import("./pages/Index.tsx"));
const Inventory = lazy(() => import("./pages/Inventory.tsx"));
const Laboratory = lazy(() => import("./pages/Laboratory.tsx"));
const Login = lazy(() => import("./pages/Login.tsx"));
const MedicalRecords = lazy(() => import("./pages/MedicalRecords.tsx"));
const NotFound = lazy(() => import("./pages/NotFound.tsx"));
const Patients = lazy(() => import("./pages/Patients.tsx"));
const PatientTimeline = lazy(() => import("./pages/PatientTimeline.tsx"));
const Pharmacy = lazy(() => import("./pages/Pharmacy.tsx"));
const PrivacyPolicy = lazy(() => import("./pages/PrivacyPolicy.tsx"));
const Queue = lazy(() => import("./pages/Queue.tsx"));
const PublicProfile = lazy(() => import("./pages/PublicProfile.tsx"));
const PublicHospital = lazy(() => import("./pages/PublicHospital.tsx"));
const Radiology = lazy(() => import("./pages/Radiology.tsx"));
const Reports = lazy(() => import("./pages/Reports.tsx"));
const RecoverAccount = lazy(() => import("./pages/RecoverAccount.tsx"));
const SettingUp = lazy(() => import("./pages/SettingUp.tsx"));
const Settings = lazy(() => import("./pages/Settings.tsx"));
const StaffAccess = lazy(() => import("./pages/StaffAccess.tsx"));
const StaffPortal = lazy(() => import("./pages/StaffPortal.tsx"));
const TermsOfService = lazy(() => import("./pages/TermsOfService.tsx"));
const Suppliers = lazy(() => import("./pages/Suppliers.tsx"));
const Consultations = lazy(() => import("./pages/Consultations.tsx"));
const Wards = lazy(() => import("./pages/Wards.tsx"));
const WorkspaceReady = lazy(() => import("./pages/WorkspaceReady.tsx"));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 2 * 60_000,
      gcTime: 20 * 60_000,
      retry: 1,
      refetchOnWindowFocus: false,
      refetchOnReconnect: true,
    },
    mutations: { retry: 0 },
  },
});

const RouteFallback = () => (
  <div className="flex min-h-screen items-center justify-center bg-background px-4">
    <div className="text-center">
      <div className="mx-auto mb-4 h-8 w-8 animate-spin rounded-full border-2 border-primary/20 border-t-primary" />
      <p className="text-sm font-medium text-muted-foreground">Loading workspace...</p>
    </div>
  </div>
);

const WithAppShell = ({ children }: { children: ReactNode }) => (
  <AppShell>{children}</AppShell>
);

const TenantOnly = ({ children }: { children: ReactNode }) => {
  const { facilitySlug } = useTenantRouting();
  return facilitySlug ? <>{children}</> : <Navigate to="/login" replace />;
};

const CanonicalPathNormalizer = ({ children }: { children: ReactNode }) => {
  const location = useLocation();
  const { facilitySlug } = useTenantRouting();
  const canonicalPath = getCanonicalPathForLegacyPath(location.pathname, facilitySlug);

  if (facilitySlug && canonicalPath !== location.pathname) {
    return <Navigate to={`${canonicalPath}${location.search}${location.hash}`} replace />;
  }
  return <>{children}</>;
};

const RootRoute = () => {
  const { facilitySlug } = useTenantRouting();
  return facilitySlug ? <Login /> : <Index />;
};

const tenantOnly = (node: ReactNode) => <TenantOnly>{node}</TenantOnly>;

const workspaceRoutes = (basePath: string, canonical = false) => {
  const wrap = (node: ReactNode) => (canonical ? tenantOnly(node) : node);
  return (
    <>
      <Route path={basePath} element={wrap(<ProtectedRoute requireAdmin><WithAppShell><Dashboard /></WithAppShell></ProtectedRoute>)} />
      <Route path={`${basePath}/staff`} element={wrap(<ProtectedRoute requireAdmin><WithAppShell><StaffAccess /></WithAppShell></ProtectedRoute>)} />
      <Route path={`${basePath}/patients`} element={wrap(<ProtectedRoute allowedRoles={routeRoles.patients}><ModuleRoute module={["reception", "records"]}><WithAppShell><Patients /></WithAppShell></ModuleRoute></ProtectedRoute>)} />
      <Route path={`${basePath}/patients/:patientId/timeline`} element={wrap(<ProtectedRoute allowedRoles={routeRoles.patients}><ModuleRoute module={["reception", "records"]}><WithAppShell><PatientTimeline /></WithAppShell></ModuleRoute></ProtectedRoute>)} />
      <Route path={`${basePath}/appointments`} element={wrap(<ProtectedRoute allowedRoles={routeRoles.appointments}><ModuleRoute module="reception"><WithAppShell><Appointments /></WithAppShell></ModuleRoute></ProtectedRoute>)} />
      <Route path={`${basePath}/billing`} element={wrap(<ProtectedRoute allowedRoles={routeRoles.billing}><ModuleRoute module="billing"><WithAppShell><Billing /></WithAppShell></ModuleRoute></ProtectedRoute>)} />
      <Route path={`${basePath}/laboratory`} element={wrap(<ProtectedRoute allowedRoles={routeRoles.laboratory}><ModuleRoute module="lab"><WithAppShell><Laboratory /></WithAppShell></ModuleRoute></ProtectedRoute>)} />
      <Route path={`${basePath}/pharmacy`} element={wrap(<ProtectedRoute allowedRoles={routeRoles.pharmacy}><ModuleRoute module="pharmacy"><WithAppShell><Pharmacy /></WithAppShell></ModuleRoute></ProtectedRoute>)} />
      <Route path={`${basePath}/radiology`} element={wrap(<ProtectedRoute allowedRoles={routeRoles.radiology}><ModuleRoute module="radiology"><WithAppShell><Radiology /></WithAppShell></ModuleRoute></ProtectedRoute>)} />
      <Route path={`${basePath}/inventory`} element={wrap(<ProtectedRoute allowedRoles={routeRoles.inventory}><ModuleRoute module="inventory"><WithAppShell><Inventory /></WithAppShell></ModuleRoute></ProtectedRoute>)} />
      <Route path={`${basePath}/records`} element={wrap(<ProtectedRoute allowedRoles={routeRoles.records}><ModuleRoute module="records"><WithAppShell><MedicalRecords /></WithAppShell></ModuleRoute></ProtectedRoute>)} />
      <Route path={`${basePath}/alerts`} element={wrap(<ProtectedRoute allowedRoles={routeRoles.alerts}><WithAppShell><Alerts /></WithAppShell></ProtectedRoute>)} />
      <Route path={`${basePath}/chat`} element={wrap(<ProtectedRoute allowedRoles={routeRoles.chat}><WithAppShell><Chat /></WithAppShell></ProtectedRoute>)} />
      <Route path={`${basePath}/audit-logs`} element={wrap(<ProtectedRoute requireFacilityAdmin><WithAppShell><AuditLogs /></WithAppShell></ProtectedRoute>)} />
      <Route path={`${basePath}/settings`} element={wrap(<ProtectedRoute requireAdmin><WithAppShell><Settings /></WithAppShell></ProtectedRoute>)} />
      <Route path={`${basePath}/suppliers`} element={wrap(<ProtectedRoute allowedRoles={routeRoles.inventory}><ModuleRoute module="inventory"><WithAppShell><Suppliers /></WithAppShell></ModuleRoute></ProtectedRoute>)} />
      <Route path={`${basePath}/queue`} element={wrap(<ProtectedRoute allowedRoles={routeRoles.queue}><ModuleRoute module="reception"><WithAppShell><Queue /></WithAppShell></ModuleRoute></ProtectedRoute>)} />
      <Route path={`${basePath}/consultations`} element={wrap(<ProtectedRoute allowedRoles={routeRoles.consultations}><ModuleRoute module="consultations"><WithAppShell><Consultations /></WithAppShell></ModuleRoute></ProtectedRoute>)} />
      <Route path={`${basePath}/wards`} element={wrap(<ProtectedRoute allowedRoles={routeRoles.wards}><ModuleRoute module="nursing"><WithAppShell><Wards /></WithAppShell></ModuleRoute></ProtectedRoute>)} />
      <Route path={`${basePath}/reports`} element={wrap(<ProtectedRoute allowedRoles={routeRoles.reports}><ModuleRoute module="reports"><WithAppShell><Reports /></WithAppShell></ModuleRoute></ProtectedRoute>)} />
      <Route path={`${basePath}/public-profile`} element={wrap(<ProtectedRoute requireFacilityAdmin><WithAppShell><PublicProfile /></WithAppShell></ProtectedRoute>)} />
      <Route path={`${basePath}/public-profile/:section`} element={wrap(<ProtectedRoute requireFacilityAdmin><WithAppShell><PublicProfile /></WithAppShell></ProtectedRoute>)} />
    </>
  );
};

const portalRoute = (path: string, canonical = false) => (
  <Route
    path={path}
    element={(canonical ? tenantOnly : (node: ReactNode) => node)(
      <ProtectedRoute><WithAppShell><StaffPortal /></WithAppShell></ProtectedRoute>
    )}
  />
);

const AppRoutes = () => (
  <CanonicalPathNormalizer>
    <Suspense fallback={<RouteFallback />}>
      <Routes>
        <Route path="/" element={<RootRoute />} />
        <Route path="/get-started" element={<GetStarted />} />
        <Route path="/privacy" element={<PrivacyPolicy />} />
        <Route path="/terms" element={<TermsOfService />} />
        <Route path="/dpa" element={<DataProcessingAgreement />} />
        <Route path="/login" element={<Login />} />
        <Route path="/recover-account" element={<RecoverAccount />} />
        <Route path="/branches/:branchSlug/login" element={tenantOnly(<Login />)} />
        <Route path="/login/:facilitySlug" element={<Login />} />
        <Route path="/:facilitySlug/login" element={<Login />} />
        <Route path="/:facilitySlug/branches/:branchSlug/login" element={<Login />} />
        <Route path="/:facilitySlug" element={<Login />} />
        <Route path="/setting-up" element={<SettingUp />} />

        {workspaceRoutes("/dashboard", true)}
        {workspaceRoutes("/branches/:branchSlug/dashboard", true)}
        {portalRoute("/portal", true)}
        {portalRoute("/branches/:branchSlug/portal", true)}

        {workspaceRoutes("/dashboard/:facilitySlug")}
        {workspaceRoutes("/:facilitySlug/branches/:branchSlug/dashboard")}
        {portalRoute("/portal/:facilitySlug")}
        {portalRoute("/:facilitySlug/branches/:branchSlug/portal")}

        <Route path="/workspace-ready" element={tenantOnly(<WorkspaceReady />)} />
        <Route path="/hospital" element={tenantOnly(<PublicHospital />)} />
        <Route path="/workspace-ready/:facilitySlug" element={<WorkspaceReady />} />
        <Route path="/hospital/:facilitySlug" element={<PublicHospital />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </Suspense>
  </CanonicalPathNormalizer>
);

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
        <TenantRoutingProvider>
          <AuthProvider>
            <RealtimeBridge />
            <AppRoutes />
          </AuthProvider>
        </TenantRoutingProvider>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
