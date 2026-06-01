import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AuthProvider } from "@/context/AuthContext";
import ProtectedRoute from "@/components/ProtectedRoute";
import Dashboard from "./pages/Dashboard.tsx";
import GetStarted from "./pages/GetStarted.tsx";
import Index from "./pages/Index.tsx";
import Login from "./pages/Login.tsx";
import NotFound from "./pages/NotFound.tsx";
import SettingUp from "./pages/SettingUp.tsx";
import StaffAccess from "./pages/StaffAccess.tsx";
import StaffPortal from "./pages/StaffPortal.tsx";
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
