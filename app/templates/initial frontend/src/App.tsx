import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AuthProvider } from "@/context/AuthContext";
import ProtectedRoute from "@/components/ProtectedRoute";
import Alerts from "./pages/Alerts.tsx";
import AuditLogs from "./pages/AuditLogs.tsx";
import Billing from "./pages/Billing.tsx";
import Dashboard from "./pages/Dashboard.tsx";
import Appointments from "./pages/Appointments.tsx";
import GetStarted from "./pages/GetStarted.tsx";
import Index from "./pages/Index.tsx";
import Inventory from "./pages/Inventory.tsx";
import Laboratory from "./pages/Laboratory.tsx";
import Login from "./pages/Login.tsx";
import MedicalRecords from "./pages/MedicalRecords.tsx";
import NotFound from "./pages/NotFound.tsx";
import Patients from "./pages/Patients.tsx";
import Pharmacy from "./pages/Pharmacy.tsx";
import Radiology from "./pages/Radiology.tsx";
import SettingUp from "./pages/SettingUp.tsx";
import Settings from "./pages/Settings.tsx";
import StaffAccess from "./pages/StaffAccess.tsx";
import StaffPortal from "./pages/StaffPortal.tsx";
import Suppliers from "./pages/Suppliers.tsx";
import WorkspaceReady from "./pages/WorkspaceReady.tsx";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter
        future={{ v7_relativeSplatPath: true, v7_startTransition: true }}
      >
        <AuthProvider>
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
                <ProtectedRoute requireAdmin>
                  <Patients />
                </ProtectedRoute>
              }
            />
            <Route
              path="/dashboard/:facilitySlug/appointments"
              element={
                <ProtectedRoute requireAdmin>
                  <Appointments />
                </ProtectedRoute>
              }
            />
            <Route
              path="/dashboard/:facilitySlug/billing"
              element={
                <ProtectedRoute requireAdmin>
                  <Billing />
                </ProtectedRoute>
              }
            />
            <Route
              path="/dashboard/:facilitySlug/laboratory"
              element={
                <ProtectedRoute requireAdmin>
                  <Laboratory />
                </ProtectedRoute>
              }
            />
            <Route
              path="/dashboard/:facilitySlug/pharmacy"
              element={
                <ProtectedRoute requireAdmin>
                  <Pharmacy />
                </ProtectedRoute>
              }
            />
            <Route
              path="/dashboard/:facilitySlug/radiology"
              element={
                <ProtectedRoute requireAdmin>
                  <Radiology />
                </ProtectedRoute>
              }
            />
            <Route
              path="/dashboard/:facilitySlug/inventory"
              element={
                <ProtectedRoute requireAdmin>
                  <Inventory />
                </ProtectedRoute>
              }
            />
            <Route
              path="/dashboard/:facilitySlug/records"
              element={
                <ProtectedRoute requireAdmin>
                  <MedicalRecords />
                </ProtectedRoute>
              }
            />
            <Route
              path="/dashboard/:facilitySlug/alerts"
              element={
                <ProtectedRoute requireAdmin>
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
                <ProtectedRoute requireAdmin>
                  <Suppliers />
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
        </AuthProvider>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
