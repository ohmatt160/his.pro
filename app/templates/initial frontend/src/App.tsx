import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
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
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Index />} />
          <Route path="/get-started" element={<GetStarted />} />
          <Route path="/login" element={<Login />} />
          <Route path="/login/:facilitySlug" element={<Login />} />
          <Route path="/setting-up" element={<SettingUp />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/dashboard/:facilitySlug" element={<Dashboard />} />
          <Route path="/dashboard/:facilitySlug/staff" element={<StaffAccess />} />
          <Route path="/portal/:facilitySlug" element={<StaffPortal />} />
          <Route path="/workspace-ready/:facilitySlug" element={<WorkspaceReady />} />
          {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
