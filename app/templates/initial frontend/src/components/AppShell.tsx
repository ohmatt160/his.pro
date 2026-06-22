import { useEffect, useState, type ElementType, type ReactNode } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import {
  Activity,
  BedDouble,
  Bell,
  CalendarDays,
  ClipboardList,
  FileHeart,
  Globe,
  FlaskConical,
  LayoutDashboard,
  LogOut,
  MessageSquare,
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
import { getBranchLoginPath, getBranchStaffAccessPath, getBranchStaffPortalPath, getFacilityLoginPath, getStaffAccessPath, getStaffPortalPath } from "@/lib/facility-staff";
import {
  getFacilityWorkspace,
  getWorkspaceRoutePath,
  WORKSPACE_UPDATED_EVENT,
  type SavedFacilityWorkspace,
} from "@/lib/facility-workspace";
import { isModuleEnabled, normalizeModules } from "@/lib/modules";
import { roleAllows, routeRoles, type WorkspaceRole } from "@/lib/role-access";
import { apiClient } from "@/api/client";

type DashboardStats = {
  active_alerts: number;
};

type FacilityBranch = {
  id: string;
  name: string;
  slug?: string;
  modules?: string[];
};

type AppShellProps = {
  children: ReactNode;
};

const navItems: Array<{
  id: string;
  label: string;
  icon: ElementType;
  module?: Parameters<typeof isModuleEnabled>[1];
  path: (slug: string, branchSlug?: string) => string;
  adminOnly?: boolean;
  roles?: WorkspaceRole[];
}> = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard, path: (slug, branchSlug) => getWorkspaceRoutePath(slug, "", branchSlug), roles: routeRoles.admin },
  { id: "portal", label: "My Portal", icon: LayoutDashboard, path: (slug, branchSlug) => branchSlug ? getBranchStaffPortalPath(slug, branchSlug) : getStaffPortalPath(slug), roles: ["doctor", "nurse", "reception", "pharmacist", "lab"] },
  { id: "staff", label: "Staff & Access", icon: ShieldCheck, path: (slug, branchSlug) => branchSlug ? getBranchStaffAccessPath(slug, branchSlug) : getStaffAccessPath(slug), roles: routeRoles.admin },
  { id: "chat", label: "Messages", icon: MessageSquare, path: (slug, branchSlug) => getWorkspaceRoutePath(slug, "chat", branchSlug), roles: routeRoles.chat },
  { id: "alerts", label: "Alerts", icon: Bell, path: (slug, branchSlug) => getWorkspaceRoutePath(slug, "alerts", branchSlug), roles: routeRoles.alerts },
  { id: "audit", label: "Audit Logs", icon: ClipboardList, path: (slug, branchSlug) => getWorkspaceRoutePath(slug, "audit-logs", branchSlug), adminOnly: true },
  { id: "reports", label: "Reports", icon: Activity, module: "reports", path: (slug, branchSlug) => getWorkspaceRoutePath(slug, "reports", branchSlug), roles: routeRoles.reports },
  { id: "public-profile", label: "Public Profile", icon: Globe, path: (slug, branchSlug) => getWorkspaceRoutePath(slug, "public-profile", branchSlug), roles: routeRoles.admin },
  { id: "patients", label: "Patients", icon: Users, module: "reception", path: (slug, branchSlug) => getWorkspaceRoutePath(slug, "patients", branchSlug), roles: routeRoles.patients },
  { id: "queue", label: "Reception Queue", icon: ClipboardList, module: "reception", path: (slug, branchSlug) => getWorkspaceRoutePath(slug, "queue", branchSlug), roles: routeRoles.queue },
  { id: "appointments", label: "Appointments", icon: CalendarDays, module: "reception", path: (slug, branchSlug) => getWorkspaceRoutePath(slug, "appointments", branchSlug), roles: routeRoles.appointments },
  { id: "consultations", label: "Consultations", icon: Stethoscope, module: "consultations", path: (slug, branchSlug) => getWorkspaceRoutePath(slug, "consultations", branchSlug), roles: routeRoles.consultations },
  { id: "wards", label: "Wards", icon: BedDouble, module: "nursing", path: (slug, branchSlug) => getWorkspaceRoutePath(slug, "wards", branchSlug), roles: routeRoles.wards },
  { id: "records", label: "Medical Records", icon: FileHeart, module: "records", path: (slug, branchSlug) => getWorkspaceRoutePath(slug, "records", branchSlug), roles: routeRoles.records },
  { id: "billing", label: "Billing", icon: Receipt, module: "billing", path: (slug, branchSlug) => getWorkspaceRoutePath(slug, "billing", branchSlug), roles: routeRoles.billing },
  { id: "lab", label: "Laboratory", icon: FlaskConical, module: "lab", path: (slug, branchSlug) => getWorkspaceRoutePath(slug, "laboratory", branchSlug), roles: routeRoles.laboratory },
  { id: "pharmacy", label: "Pharmacy", icon: Pill, module: "pharmacy", path: (slug, branchSlug) => getWorkspaceRoutePath(slug, "pharmacy", branchSlug), roles: routeRoles.pharmacy },
  { id: "radiology", label: "Radiology", icon: ScanLine, module: "radiology", path: (slug, branchSlug) => getWorkspaceRoutePath(slug, "radiology", branchSlug), roles: routeRoles.radiology },
  { id: "inventory", label: "Inventory", icon: Package, module: "inventory", path: (slug, branchSlug) => getWorkspaceRoutePath(slug, "inventory", branchSlug), roles: routeRoles.inventory },
  { id: "suppliers", label: "Suppliers", icon: Truck, module: "inventory", path: (slug, branchSlug) => getWorkspaceRoutePath(slug, "suppliers", branchSlug), roles: routeRoles.inventory },
  { id: "settings", label: "Settings", icon: Settings, path: (slug, branchSlug) => getWorkspaceRoutePath(slug, "settings", branchSlug), adminOnly: true },
];

const defaultModules = ["reception", "records", "consultations", "nursing", "pharmacy", "billing"];

const AppShell = ({ children }: AppShellProps) => {
  const { facilitySlug = "", branchSlug = "" } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [workspace, setWorkspace] = useState<SavedFacilityWorkspace | null>(null);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [currentBranch, setCurrentBranch] = useState<FacilityBranch | null>(null);
  const [unreadMessages, setUnreadMessages] = useState(0);
  const canUseChat = roleAllows(user?.role, routeRoles.chat);

  useEffect(() => {
    if (!facilitySlug) {
      return;
    }
    getFacilityWorkspace(facilitySlug).then(setWorkspace).catch(() => setWorkspace(null));
    apiClient
      .get<FacilityBranch[]>(`/facilities/${facilitySlug}/branches`)
      .then((branches) => {
        const branch = user?.branchId ? branches.find((item) => item.id === user.branchId) || null : null;
        setCurrentBranch(branch);
      })
      .catch(() => setCurrentBranch(null));
    const branchQuery = user?.branchId ? `&branch_id=${encodeURIComponent(user.branchId)}` : "";
    apiClient
      .get<DashboardStats>(
        `/dashboard/stats?facility_slug=${encodeURIComponent(facilitySlug)}${branchQuery}`
      )
      .then(setStats)
      .catch(() => setStats(null));
    if (canUseChat) {
      apiClient
        .get<{ unread_count: number }>("/chat/unread-count")
        .then((result) => setUnreadMessages(result.unread_count))
        .catch(() => setUnreadMessages(0));
    } else {
      setUnreadMessages(0);
    }
  }, [facilitySlug, user?.branchId, canUseChat]);

  useEffect(() => {
    if (!canUseChat) {
      setUnreadMessages(0);
      return;
    }

    const timer = window.setInterval(() => {
      apiClient
        .get<{ unread_count: number }>("/chat/unread-count")
        .then((result) => setUnreadMessages(result.unread_count))
        .catch(() => undefined);
    }, 15000);
    return () => window.clearInterval(timer);
  }, [canUseChat]);

  useEffect(() => {
    const handleWorkspaceUpdated = (event: Event) => {
      const workspaceDetail = (event as CustomEvent<SavedFacilityWorkspace>).detail;
      if (workspaceDetail?.facilitySlug === facilitySlug) {
        setWorkspace(workspaceDetail);
      }
    };

    window.addEventListener(WORKSPACE_UPDATED_EVENT, handleWorkspaceUpdated);
    return () => {
      window.removeEventListener(WORKSPACE_UPDATED_EVENT, handleWorkspaceUpdated);
    };
  }, [facilitySlug]);

  const selectedModules = normalizeModules(
    currentBranch
      ? currentBranch.modules || []
      : workspace?.selectedModules?.length
        ? workspace.selectedModules
        : defaultModules
  );
  const facilityType = currentBranch ? currentBranch.name : workspace?.facilityType || "facility";
  const visibleNav = navItems.filter((entry) => {
    if (entry.adminOnly && !["admin", "branch_admin"].includes(user?.role || "")) {
      return false;
    }
    return roleAllows(user?.role, entry.roles) && (!entry.module || isModuleEnabled(selectedModules, entry.module));
  });

  const handleLogout = () => {
    logout();
    navigate(facilitySlug ? (branchSlug ? getBranchLoginPath(facilitySlug, branchSlug) : getFacilityLoginPath(facilitySlug)) : "/login", { replace: true });
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
            const to = entry.path(facilitySlug, branchSlug || currentBranch?.slug || undefined);
            const badge = entry.id === "alerts" ? stats?.active_alerts : entry.id === "chat" ? unreadMessages : undefined;
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

