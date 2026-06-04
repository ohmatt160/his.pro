import { useEffect, useState, type ElementType, type ReactNode } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import {
  Activity,
  BedDouble,
  Bell,
  CalendarDays,
  ClipboardList,
  FileHeart,
  FlaskConical,
  LayoutDashboard,
  LogOut,
  Package,
  Pill,
  Receipt,
  ScanLine,
  Settings,
  ShieldCheck,
  Stethoscope,
  Truck,
  Users,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { getFacilityLoginPath, getStaffAccessPath } from "@/lib/facility-staff";
import { getFacilityWorkspace, type SavedFacilityWorkspace } from "@/lib/facility-workspace";
import { isModuleEnabled, normalizeModules } from "@/lib/modules";
import { apiClient } from "@/api/client";

type DashboardStats = {
  active_alerts: number;
};

type AppShellProps = {
  children: ReactNode;
};

const navItems: Array<{
  id: string;
  label: string;
  icon: ElementType;
  module?: Parameters<typeof isModuleEnabled>[1];
  path: (slug: string) => string;
  adminOnly?: boolean;
}> = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard, path: (slug) => `/dashboard/${slug}` },
  { id: "staff", label: "Staff & Access", icon: ShieldCheck, path: getStaffAccessPath, adminOnly: true },
  { id: "alerts", label: "Alerts", icon: Bell, path: (slug) => `/dashboard/${slug}/alerts` },
  { id: "audit", label: "Audit Logs", icon: ClipboardList, path: (slug) => `/dashboard/${slug}/audit-logs`, adminOnly: true },
  { id: "reports", label: "Reports", icon: Activity, module: "reports", path: (slug) => `/dashboard/${slug}/reports` },
  { id: "patients", label: "Patients", icon: Users, module: "reception", path: (slug) => `/dashboard/${slug}/patients` },
  { id: "queue", label: "Reception Queue", icon: ClipboardList, module: "reception", path: (slug) => `/dashboard/${slug}/queue` },
  { id: "appointments", label: "Appointments", icon: CalendarDays, module: "reception", path: (slug) => `/dashboard/${slug}/appointments` },
  { id: "consultations", label: "Consultations", icon: Stethoscope, module: "consultations", path: (slug) => `/dashboard/${slug}/consultations` },
  { id: "wards", label: "Wards", icon: BedDouble, module: "nursing", path: (slug) => `/dashboard/${slug}/wards` },
  { id: "records", label: "Medical Records", icon: FileHeart, module: "records", path: (slug) => `/dashboard/${slug}/records` },
  { id: "billing", label: "Billing", icon: Receipt, module: "billing", path: (slug) => `/dashboard/${slug}/billing` },
  { id: "lab", label: "Laboratory", icon: FlaskConical, module: "lab", path: (slug) => `/dashboard/${slug}/laboratory` },
  { id: "pharmacy", label: "Pharmacy", icon: Pill, module: "pharmacy", path: (slug) => `/dashboard/${slug}/pharmacy` },
  { id: "radiology", label: "Radiology", icon: ScanLine, module: "radiology", path: (slug) => `/dashboard/${slug}/radiology` },
  { id: "inventory", label: "Inventory", icon: Package, module: "inventory", path: (slug) => `/dashboard/${slug}/inventory` },
  { id: "suppliers", label: "Suppliers", icon: Truck, module: "inventory", path: (slug) => `/dashboard/${slug}/suppliers` },
  { id: "settings", label: "Settings", icon: Settings, path: (slug) => `/dashboard/${slug}/settings`, adminOnly: true },
];

const defaultModules = ["reception", "records", "consultations", "nursing", "pharmacy", "billing"];

const AppShell = ({ children }: AppShellProps) => {
  const { facilitySlug = "" } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [workspace, setWorkspace] = useState<SavedFacilityWorkspace | null>(null);
  const [stats, setStats] = useState<DashboardStats | null>(null);

  useEffect(() => {
    if (!facilitySlug) {
      return;
    }
    getFacilityWorkspace(facilitySlug).then(setWorkspace).catch(() => setWorkspace(null));
    apiClient.get<DashboardStats>("/dashboard/stats").then(setStats).catch(() => setStats(null));
  }, [facilitySlug]);

  const selectedModules = normalizeModules(workspace?.selectedModules?.length ? workspace.selectedModules : defaultModules);
  const facilityType = workspace?.facilityType || "facility";
  const visibleNav = navItems.filter((entry) => {
    if (entry.adminOnly && user?.role !== "admin") {
      return false;
    }
    return !entry.module || isModuleEnabled(selectedModules, entry.module);
  });

  const handleLogout = () => {
    logout();
    navigate(facilitySlug ? getFacilityLoginPath(facilitySlug) : "/login", { replace: true });
  };

  return (
    <div className="min-h-screen bg-background lg:flex">
      <aside className="hidden w-64 shrink-0 flex-col border-r border-border bg-card lg:flex">
        <div className="border-b border-border p-5">
          <Link to="/" className="text-xl font-extrabold tracking-tight">
            <span className="text-gradient">HIS</span>
            <span className="text-foreground">.Pro</span>
          </Link>
          <p className="mt-1 text-xs capitalize text-muted-foreground">{facilityType} Workspace</p>
        </div>

        <nav className="flex-1 space-y-1 overflow-y-auto p-3">
          {visibleNav.map((entry) => {
            const to = entry.path(facilitySlug);
            const badge = entry.id === "alerts" ? stats?.active_alerts : undefined;
            return (
              <SidebarLink
                key={entry.id}
                icon={entry.icon}
                label={entry.label}
                to={to}
                active={location.pathname === to}
                badge={badge}
              />
            );
          })}
        </nav>

        <div className="border-t border-border p-3">
          <button
            type="button"
            onClick={handleLogout}
            className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          >
            <LogOut className="h-4 w-4 shrink-0" />
            Log Out
          </button>
        </div>
      </aside>
      <div className="min-w-0 flex-1">{children}</div>
    </div>
  );
};

const SidebarLink = ({
  icon: Icon,
  label,
  to,
  active,
  badge,
}: {
  icon: ElementType;
  label: string;
  to: string;
  active?: boolean;
  badge?: number;
}) => (
  <Link
    to={to}
    className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors ${
      active
        ? "bg-primary/10 text-primary"
        : "text-muted-foreground hover:bg-muted hover:text-foreground"
    }`}
  >
    <Icon className="h-4 w-4 shrink-0" />
    <span className="min-w-0 flex-1 truncate">{label}</span>
    {Boolean(badge) && (
      <span className="rounded-full bg-primary px-2 py-0.5 text-xs font-semibold text-primary-foreground">
        {badge}
      </span>
    )}
  </Link>
);

export default AppShell;
