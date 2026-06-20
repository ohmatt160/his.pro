import { lazy, Suspense, type ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AuthProvider } from "@/context/AuthContext";
import AppShell from "@/components/AppShell";
import ProtectedRoute from "@/components/ProtectedRoute";
import ModuleRoute from "@/components/ModuleRoute";
import { routeRoles } from "@/lib/role-access";

const Alerts = lazy(() => import("./pages/Alerts.tsx"));
const AuditLogs = lazy(() => import("./pages/AuditLogs.tsx"));
const Billing = lazy(() => import("./pages/Billing.tsx"));
const Chat = lazy(() => import("./pages/Chat.tsx"));
const Dashboard = lazy(() => import("./pages/Dashboard.tsx"));
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
const Queue = lazy(() => import("./pages/Queue.tsx"));
const PublicProfile = lazy(() => import("./pages/PublicProfile.tsx"));
const PublicHospital = lazy(() => import("./pages/PublicHospital.tsx"));
const Radiology = lazy(() => import("./pages/Radiology.tsx"));
const Reports = lazy(() => import("./pages/Reports.tsx"));
const SettingUp = lazy(() => import("./pages/SettingUp.tsx"));
const Settings = lazy(() => import("./pages/Settings.tsx"));
const StaffAccess = lazy(() => import("./pages/StaffAccess.tsx"));
const StaffPortal = lazy(() => import("./pages/StaffPortal.tsx"));
const Suppliers = lazy(() => import("./pages/Suppliers.tsx"));
const Consultations = lazy(() => import("./pages/Consultations.tsx"));
const Wards = lazy(() => import("./pages/Wards.tsx"));
const WorkspaceReady = lazy(() => import("./pages/WorkspaceReady.tsx"));

const queryClient = new QueryClient();

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

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter
        future={{ v7_relativeSplatPath: true, v7_startTransition: true }}
      >
        <AuthProvider>
          <Suspense fallback={<RouteFallback />}>
            <Routes>
              <Route path="/" element={<Index />} />
              <Route path="/get-started" element={<GetStarted />} />
              <Route path="/login" element={<Login />} />
              <Route path="/login/:facilitySlug" element={<Login />} />
              <Route path="/:facilitySlug/login" element={<Login />} />
              <Route path="/:facilitySlug/branches/:branchSlug/login" element={<Login />} />
              <Route path="/:facilitySlug" element={<Login />} />
              <Route path="/setting-up" element={<SettingUp />} />
              <Route
                path="/dashboard/:facilitySlug"
                element={
                  <ProtectedRoute requireAdmin>
                    <WithAppShell>
                      <Dashboard />
                    </WithAppShell>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/dashboard/:facilitySlug/staff"
                element={
                  <ProtectedRoute requireAdmin>
                    <WithAppShell>
                      <StaffAccess />
                    </WithAppShell>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/dashboard/:facilitySlug/patients"
                element={
                  <ProtectedRoute allowedRoles={routeRoles.patients}>
                    <ModuleRoute module="reception">
                      <WithAppShell>
                        <Patients />
                      </WithAppShell>
                    </ModuleRoute>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/dashboard/:facilitySlug/patients/:patientId/timeline"
                element={
                  <ProtectedRoute allowedRoles={routeRoles.patients}>
                    <ModuleRoute module="reception">
                      <WithAppShell>
                        <PatientTimeline />
                      </WithAppShell>
                    </ModuleRoute>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/dashboard/:facilitySlug/appointments"
                element={
                  <ProtectedRoute allowedRoles={routeRoles.appointments}>
                    <ModuleRoute module="reception">
                      <WithAppShell>
                        <Appointments />
                      </WithAppShell>
                    </ModuleRoute>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/dashboard/:facilitySlug/billing"
                element={
                  <ProtectedRoute allowedRoles={routeRoles.billing}>
                    <ModuleRoute module="billing">
                      <WithAppShell>
                        <Billing />
                      </WithAppShell>
                    </ModuleRoute>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/dashboard/:facilitySlug/laboratory"
                element={
                  <ProtectedRoute allowedRoles={routeRoles.laboratory}>
                    <ModuleRoute module="lab">
                      <WithAppShell>
                        <Laboratory />
                      </WithAppShell>
                    </ModuleRoute>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/dashboard/:facilitySlug/pharmacy"
                element={
                  <ProtectedRoute allowedRoles={routeRoles.pharmacy}>
                    <ModuleRoute module="pharmacy">
                      <WithAppShell>
                        <Pharmacy />
                      </WithAppShell>
                    </ModuleRoute>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/dashboard/:facilitySlug/radiology"
                element={
                  <ProtectedRoute allowedRoles={routeRoles.radiology}>
                    <ModuleRoute module="radiology">
                      <WithAppShell>
                        <Radiology />
                      </WithAppShell>
                    </ModuleRoute>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/dashboard/:facilitySlug/inventory"
                element={
                  <ProtectedRoute allowedRoles={routeRoles.inventory}>
                    <ModuleRoute module="inventory">
                      <WithAppShell>
                        <Inventory />
                      </WithAppShell>
                    </ModuleRoute>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/dashboard/:facilitySlug/records"
                element={
                  <ProtectedRoute allowedRoles={routeRoles.records}>
                    <ModuleRoute module="records">
                      <WithAppShell>
                        <MedicalRecords />
                      </WithAppShell>
                    </ModuleRoute>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/dashboard/:facilitySlug/alerts"
                element={
                  <ProtectedRoute allowedRoles={routeRoles.alerts}>
                    <WithAppShell>
                      <Alerts />
                    </WithAppShell>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/dashboard/:facilitySlug/chat"
                element={
                  <ProtectedRoute allowedRoles={routeRoles.chat}>
                    <WithAppShell>
                      <Chat />
                    </WithAppShell>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/dashboard/:facilitySlug/audit-logs"
                element={
                  <ProtectedRoute requireAdmin>
                    <WithAppShell>
                      <AuditLogs />
                    </WithAppShell>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/dashboard/:facilitySlug/settings"
                element={
                  <ProtectedRoute requireAdmin>
                    <WithAppShell>
                      <Settings />
                    </WithAppShell>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/dashboard/:facilitySlug/suppliers"
                element={
                  <ProtectedRoute allowedRoles={routeRoles.inventory}>
                    <ModuleRoute module="inventory">
                      <WithAppShell>
                        <Suppliers />
                      </WithAppShell>
                    </ModuleRoute>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/dashboard/:facilitySlug/queue"
                element={
                  <ProtectedRoute allowedRoles={routeRoles.queue}>
                    <ModuleRoute module="reception">
                      <WithAppShell>
                        <Queue />
                      </WithAppShell>
                    </ModuleRoute>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/dashboard/:facilitySlug/consultations"
                element={
                  <ProtectedRoute allowedRoles={routeRoles.consultations}>
                    <ModuleRoute module="consultations">
                      <WithAppShell>
                        <Consultations />
                      </WithAppShell>
                    </ModuleRoute>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/dashboard/:facilitySlug/wards"
                element={
                  <ProtectedRoute allowedRoles={routeRoles.wards}>
                    <ModuleRoute module="nursing">
                      <WithAppShell>
                        <Wards />
                      </WithAppShell>
                    </ModuleRoute>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/dashboard/:facilitySlug/reports"
                element={
                  <ProtectedRoute allowedRoles={routeRoles.reports}>
                    <ModuleRoute module="reports">
                      <WithAppShell>
                        <Reports />
                      </WithAppShell>
                    </ModuleRoute>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/portal/:facilitySlug"
                element={
                  <ProtectedRoute>
                    <WithAppShell>
                      <StaffPortal />
                    </WithAppShell>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/dashboard/:facilitySlug/public-profile"
                element={
                  <ProtectedRoute requireAdmin>
                    <WithAppShell>
                      <PublicProfile />
                    </WithAppShell>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/dashboard/:facilitySlug/public-profile/:section"
                element={
                  <ProtectedRoute requireAdmin>
                    <WithAppShell>
                      <PublicProfile />
                    </WithAppShell>
                  </ProtectedRoute>
                }
              />
              <Route path="/workspace-ready/:facilitySlug" element={<WorkspaceReady />} />
              <Route path="/hospital/:facilitySlug" element={<PublicHospital />} />
              {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
              <Route path="*" element={<NotFound />} />
            </Routes>
          </Suspense>
        </AuthProvider>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;




