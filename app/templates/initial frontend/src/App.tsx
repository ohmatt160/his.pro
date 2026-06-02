import { lazy, Suspense } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AuthProvider } from "@/context/AuthContext";
import ProtectedRoute from "@/components/ProtectedRoute";

const Alerts = lazy(() => import("./pages/Alerts.tsx"));
const AuditLogs = lazy(() => import("./pages/AuditLogs.tsx"));
const Billing = lazy(() => import("./pages/Billing.tsx"));
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
const Pharmacy = lazy(() => import("./pages/Pharmacy.tsx"));
const Queue = lazy(() => import("./pages/Queue.tsx"));
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
              <Route path="/:facilitySlug" element={<Login />} />
              <Route path="/setting-up" element={<SettingUp />} />
              <Route
                path="/dashboard/:facilitySlug"
                element={
                  <ProtectedRoute requireAdmin>
                    <Dashboard />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/dashboard/:facilitySlug/staff"
                element={
                  <ProtectedRoute requireAdmin>
                    <StaffAccess />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/dashboard/:facilitySlug/patients"
                element={
                  <ProtectedRoute>
                    <Patients />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/dashboard/:facilitySlug/appointments"
                element={
                  <ProtectedRoute>
                    <Appointments />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/dashboard/:facilitySlug/billing"
                element={
                  <ProtectedRoute>
                    <Billing />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/dashboard/:facilitySlug/laboratory"
                element={
                  <ProtectedRoute>
                    <Laboratory />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/dashboard/:facilitySlug/pharmacy"
                element={
                  <ProtectedRoute>
                    <Pharmacy />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/dashboard/:facilitySlug/radiology"
                element={
                  <ProtectedRoute>
                    <Radiology />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/dashboard/:facilitySlug/inventory"
                element={
                  <ProtectedRoute>
                    <Inventory />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/dashboard/:facilitySlug/records"
                element={
                  <ProtectedRoute>
                    <MedicalRecords />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/dashboard/:facilitySlug/alerts"
                element={
                  <ProtectedRoute>
                    <Alerts />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/dashboard/:facilitySlug/audit-logs"
                element={
                  <ProtectedRoute requireAdmin>
                    <AuditLogs />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/dashboard/:facilitySlug/settings"
                element={
                  <ProtectedRoute requireAdmin>
                    <Settings />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/dashboard/:facilitySlug/suppliers"
                element={
                  <ProtectedRoute>
                    <Suppliers />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/dashboard/:facilitySlug/queue"
                element={
                  <ProtectedRoute>
                    <Queue />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/dashboard/:facilitySlug/consultations"
                element={
                  <ProtectedRoute>
                    <Consultations />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/dashboard/:facilitySlug/wards"
                element={
                  <ProtectedRoute>
                    <Wards />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/dashboard/:facilitySlug/reports"
                element={
                  <ProtectedRoute>
                    <Reports />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/portal/:facilitySlug"
                element={
                  <ProtectedRoute>
                    <StaffPortal />
                  </ProtectedRoute>
                }
              />
              <Route path="/workspace-ready/:facilitySlug" element={<WorkspaceReady />} />
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
