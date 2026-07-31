import {
  useEffect,
  useMemo,
  useState,
  type ElementType,
  type ReactNode,
} from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useQueryClient } from "@tanstack/react-query";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useTenantParams } from "@/context/TenantRoutingContext";
import {
  Activity,
  BedDouble,
  Bell,
  Building2,
  CalendarDays,
  ChevronRight,
  ClipboardList,
  FileHeart,
  FlaskConical,
  Globe,
  LayoutDashboard,
  LogOut,
  Menu,
  MessageSquare,
  Package,
  PanelLeftClose,
  PanelLeftOpen,
  Pill,
  Receipt,
  ScanLine,
  Search,
  Settings,
  ShieldCheck,
  Stethoscope,
  Truck,
  Users,
  X,
} from "lucide-react";
import ClinicalPulse from "@/components/ClinicalPulse";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/context/AuthContext";
import {
  getBranchLoginPath,
  getBranchStaffAccessPath,
  getBranchStaffPortalPath,
  getFacilityLoginPath,
  getStaffAccessPath,
  getStaffPortalPath,
} from "@/lib/facility-staff";
import {
  getWorkspaceRoutePath,
  WORKSPACE_UPDATED_EVENT,
  type SavedFacilityWorkspace,
} from "@/lib/facility-workspace";
import { isModuleEnabled, normalizeModules } from "@/lib/modules";
import { roleAllows, routeRoles, type WorkspaceRole } from "@/lib/role-access";
import logo from "@/lib/assets/logo.png";
import {
  useBranchesQuery,
  useDashboardStatsQuery,
  useUnreadMessagesQuery,
  useWorkspaceQuery,
  workspaceQueryKeys,
} from "@/hooks/useWorkspaceQueries";

type AppShellProps = {
  children: ReactNode;
};

type NavGroup = "Workspace" | "Care delivery" | "Operations" | "Governance";

type NavEntry = {
  id: string;
  label: string;
  icon: ElementType;
  group: NavGroup;
  module?: Parameters<typeof isModuleEnabled>[1];
  path: (slug: string, branchSlug?: string) => string;
  adminOnly?: boolean;
  facilityAdminOnly?: boolean;
  roles?: WorkspaceRole[];
};

const navGroups: NavGroup[] = ["Workspace", "Care delivery", "Operations", "Governance"];

const navItems: NavEntry[] = [
  { id: "dashboard", label: "Command center", icon: LayoutDashboard, group: "Workspace", path: (slug, branchSlug) => getWorkspaceRoutePath(slug, "", branchSlug), roles: routeRoles.admin },
  { id: "portal", label: "My portal", icon: Activity, group: "Workspace", path: (slug, branchSlug) => branchSlug ? getBranchStaffPortalPath(slug, branchSlug) : getStaffPortalPath(slug), roles: ["doctor", "nurse", "reception", "pharmacist", "lab", "billing"] },
  { id: "patients", label: "Patients", icon: Users, group: "Care delivery", module: "reception", path: (slug, branchSlug) => getWorkspaceRoutePath(slug, "patients", branchSlug), roles: routeRoles.patients },
  { id: "queue", label: "Reception queue", icon: ClipboardList, group: "Care delivery", module: "reception", path: (slug, branchSlug) => getWorkspaceRoutePath(slug, "queue", branchSlug), roles: routeRoles.queue },
  { id: "appointments", label: "Appointments", icon: CalendarDays, group: "Care delivery", module: "reception", path: (slug, branchSlug) => getWorkspaceRoutePath(slug, "appointments", branchSlug), roles: routeRoles.appointments },
  { id: "consultations", label: "Consultations", icon: Stethoscope, group: "Care delivery", module: "consultations", path: (slug, branchSlug) => getWorkspaceRoutePath(slug, "consultations", branchSlug), roles: routeRoles.consultations },
  { id: "wards", label: "Wards", icon: BedDouble, group: "Care delivery", module: "nursing", path: (slug, branchSlug) => getWorkspaceRoutePath(slug, "wards", branchSlug), roles: routeRoles.wards },
  { id: "records", label: "Medical records", icon: FileHeart, group: "Care delivery", module: "records", path: (slug, branchSlug) => getWorkspaceRoutePath(slug, "records", branchSlug), roles: routeRoles.records },
  { id: "lab", label: "Laboratory", icon: FlaskConical, group: "Care delivery", module: "lab", path: (slug, branchSlug) => getWorkspaceRoutePath(slug, "laboratory", branchSlug), roles: routeRoles.laboratory },
  { id: "radiology", label: "Radiology", icon: ScanLine, group: "Care delivery", module: "radiology", path: (slug, branchSlug) => getWorkspaceRoutePath(slug, "radiology", branchSlug), roles: routeRoles.radiology },
  { id: "pharmacy", label: "Pharmacy", icon: Pill, group: "Operations", module: "pharmacy", path: (slug, branchSlug) => getWorkspaceRoutePath(slug, "pharmacy", branchSlug), roles: routeRoles.pharmacy },
  { id: "billing", label: "Billing", icon: Receipt, group: "Operations", module: "billing", path: (slug, branchSlug) => getWorkspaceRoutePath(slug, "billing", branchSlug), roles: routeRoles.billing },
  { id: "inventory", label: "Inventory", icon: Package, group: "Operations", module: "inventory", path: (slug, branchSlug) => getWorkspaceRoutePath(slug, "inventory", branchSlug), roles: routeRoles.inventory },
  { id: "suppliers", label: "Suppliers", icon: Truck, group: "Operations", module: "inventory", path: (slug, branchSlug) => getWorkspaceRoutePath(slug, "suppliers", branchSlug), roles: routeRoles.inventory },
  { id: "reports", label: "Reports", icon: Activity, group: "Operations", module: "reports", path: (slug, branchSlug) => getWorkspaceRoutePath(slug, "reports", branchSlug), roles: routeRoles.reports },
  { id: "chat", label: "Messages", icon: MessageSquare, group: "Workspace", path: (slug, branchSlug) => getWorkspaceRoutePath(slug, "chat", branchSlug), roles: routeRoles.chat },
  { id: "alerts", label: "Alerts", icon: Bell, group: "Workspace", path: (slug, branchSlug) => getWorkspaceRoutePath(slug, "alerts", branchSlug), roles: routeRoles.alerts },
  { id: "staff", label: "Staff and access", icon: ShieldCheck, group: "Governance", path: (slug, branchSlug) => branchSlug ? getBranchStaffAccessPath(slug, branchSlug) : getStaffAccessPath(slug), roles: routeRoles.admin },
  { id: "audit", label: "Audit logs", icon: ClipboardList, group: "Governance", path: (slug, branchSlug) => getWorkspaceRoutePath(slug, "audit-logs", branchSlug), adminOnly: true, facilityAdminOnly: true },
  { id: "public-profile", label: "Public profile", icon: Globe, group: "Governance", path: (slug, branchSlug) => getWorkspaceRoutePath(slug, "public-profile", branchSlug), roles: routeRoles.admin, facilityAdminOnly: true },
  { id: "settings", label: "Settings", icon: Settings, group: "Governance", path: (slug, branchSlug) => getWorkspaceRoutePath(slug, "settings", branchSlug), adminOnly: true },
];

const defaultModules = ["reception", "records", "consultations", "nursing", "pharmacy", "billing"];

const initials = (name?: string) =>
  (name || "HIS")
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();

const AppShell = ({ children }: AppShellProps) => {
  const { facilitySlug = "", branchSlug = "" } = useTenantParams();
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const queryClient = useQueryClient();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [commandOpen, setCommandOpen] = useState(false);
  const [commandQuery, setCommandQuery] = useState("");
  const canUseChat = roleAllows(user?.role, routeRoles.chat);
  const { data: workspace = null } = useWorkspaceQuery(facilitySlug);
  const { data: branches = [] } = useBranchesQuery(facilitySlug);
  const currentBranch = useMemo(
    () =>
      branchSlug
        ? branches.find((item) => item.slug === branchSlug || item.id === user?.branchId) || null
        : user?.branchId
          ? branches.find((item) => item.id === user.branchId) || null
          : null,
    [branchSlug, branches, user?.branchId],
  );
  const { data: stats = null } = useDashboardStatsQuery(
    facilitySlug,
    user?.branchId || "",
    Boolean(user),
  );
  const { data: unreadResult } = useUnreadMessagesQuery(
    user?.id || user?.loginId || "",
    canUseChat,
  );
  const unreadMessages = unreadResult?.unread_count || 0;

  useEffect(() => {
    const stored = window.localStorage.getItem("hispro-v2.sidebar-collapsed");
    setCollapsed(stored === "true");
  }, []);

  useEffect(() => {
    setMobileOpen(false);
    setCommandOpen(false);
    setCommandQuery("");
  }, [location.pathname]);

  useEffect(() => {
    const handleWorkspaceUpdated = (event: Event) => {
      const detail = (event as CustomEvent<SavedFacilityWorkspace>).detail;
      if (detail?.facilitySlug === facilitySlug) {
        queryClient.setQueryData(workspaceQueryKeys.workspace(facilitySlug), detail);
      }
    };
    window.addEventListener(WORKSPACE_UPDATED_EVENT, handleWorkspaceUpdated);
    return () => window.removeEventListener(WORKSPACE_UPDATED_EVENT, handleWorkspaceUpdated);
  }, [facilitySlug, queryClient]);

  useEffect(() => {
    if (!commandOpen) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setCommandOpen(false);
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [commandOpen]);

  const selectedModules = normalizeModules(
    currentBranch
      ? currentBranch.modules || []
      : workspace?.selectedModules?.length
        ? workspace.selectedModules
        : defaultModules,
  );

  const visibleNav = navItems.filter((entry) => {
    if (entry.adminOnly && !["admin", "branch_admin"].includes(user?.role || "")) return false;
    if (entry.facilityAdminOnly && user?.role !== "admin") return false;
    return roleAllows(user?.role, entry.roles) && (!entry.module || isModuleEnabled(selectedModules, entry.module));
  });

  const groupedNav = navGroups
    .map((group) => ({ group, entries: visibleNav.filter((entry) => entry.group === group) }))
    .filter(({ entries }) => entries.length > 0);

  const branchContext = branchSlug || currentBranch?.slug || undefined;
  const workspaceName = currentBranch?.name || workspace?.facilityName || "Clinical workspace";
  const workspaceType = currentBranch ? "Branch workspace" : workspace?.facilityType || "Facility workspace";

  const filteredCommands = visibleNav.filter((entry) =>
    `${entry.label} ${entry.group}`.toLowerCase().includes(commandQuery.trim().toLowerCase()),
  );

  const badgeFor = (entry: NavEntry) =>
    entry.id === "alerts" ? stats?.active_alerts : entry.id === "chat" ? unreadMessages : undefined;

  const pathFor = (entry: NavEntry) => entry.path(facilitySlug, branchContext);

  const isActive = (entry: NavEntry) => {
    const path = pathFor(entry);
    return location.pathname === path || (entry.id === "patients" && location.pathname.startsWith(`${path}/`));
  };

  const handleCollapse = () => {
    setCollapsed((current) => {
      window.localStorage.setItem("hispro-v2.sidebar-collapsed", String(!current));
      return !current;
    });
  };

  const handleLogout = () => {
    logout();
    navigate(
      facilitySlug
        ? branchSlug
          ? getBranchLoginPath(facilitySlug, branchSlug)
          : getFacilityLoginPath(facilitySlug)
        : "/login",
      { replace: true },
    );
  };

  const navigation = (mobile = false) => (
    <nav className="scrollbar-clinical flex-1 overflow-y-auto px-3 py-4" aria-label="Workspace navigation">
      {groupedNav.map(({ group, entries }) => (
        <div key={group} className="mb-5 last:mb-0">
          {(!collapsed || mobile) && (
            <p className="mb-2 px-2 text-[10px] font-semibold uppercase text-sidebar-foreground/45">
              {group}
            </p>
          )}
          <div className="space-y-1">
            {entries.map((entry) => (
              <NavLink
                key={entry.id}
                entry={entry}
                to={pathFor(entry)}
                active={isActive(entry)}
                collapsed={collapsed && !mobile}
                badge={badgeFor(entry)}
              />
            ))}
          </div>
        </div>
      ))}
    </nav>
  );

  return (
    <div className="v2-grid flex min-h-screen bg-background">
      <aside
        className={`sticky top-0 hidden h-screen shrink-0 flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground transition-[width] duration-200 lg:flex ${collapsed ? "w-[76px]" : "w-[272px]"}`}
      >
        <div className={`flex h-[72px] items-center border-b border-sidebar-border ${collapsed ? "justify-center px-2" : "justify-between px-4"}`}>
          <Link to="/" className="flex min-w-0 items-center gap-3" aria-label="HIS Pro home">
            <img src={logo} alt="" className="h-9 w-9 shrink-0 rounded-md bg-white/[0.08] object-contain p-1" />
            {!collapsed && (
              <div className="min-w-0">
                <p className="truncate text-base font-bold text-white">HIS.Pro</p>
                <p className="text-[10px] font-semibold uppercase text-sidebar-primary">Clinical OS 2.0</p>
              </div>
            )}
          </Link>
          {!collapsed && (
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={handleCollapse}
              className="h-8 w-8 text-sidebar-foreground/60 hover:bg-sidebar-accent hover:text-white"
              title="Collapse navigation"
            >
              <PanelLeftClose />
            </Button>
          )}
        </div>

        {collapsed && (
          <button
            type="button"
            onClick={handleCollapse}
            className="mx-auto mt-3 flex h-8 w-8 items-center justify-center rounded-md text-sidebar-foreground/60 hover:bg-sidebar-accent hover:text-white"
            title="Expand navigation"
          >
            <PanelLeftOpen className="h-4 w-4" />
          </button>
        )}

        {navigation()}

        <div className="border-t border-sidebar-border p-3">
          <div className={`flex items-center ${collapsed ? "justify-center" : "gap-3"}`}>
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-sidebar-primary text-xs font-bold text-sidebar-primary-foreground">
              {initials(user?.fullName)}
            </div>
            {!collapsed && (
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-semibold text-white">{user?.fullName || user?.loginId}</p>
                <p className="truncate text-xs capitalize text-sidebar-foreground/55">{user?.role?.replaceAll("_", " ")}</p>
              </div>
            )}
            <button
              type="button"
              onClick={handleLogout}
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-sidebar-foreground/55 hover:bg-sidebar-accent hover:text-white"
              title="Log out"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </aside>

      <div className="min-w-0 flex-1">
        <header className="sticky top-0 z-30 flex h-[72px] items-center gap-3 border-b border-border bg-card/95 px-3 shadow-[0_4px_20px_rgba(18,51,49,0.04)] backdrop-blur-md sm:px-5 lg:px-6">
          <button
            type="button"
            onClick={() => setMobileOpen(true)}
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-border bg-card text-foreground lg:hidden"
            aria-label="Open navigation"
          >
            <Menu className="h-5 w-5" />
          </button>

          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <Building2 className="hidden h-4 w-4 shrink-0 text-primary sm:block" />
              <p className="truncate text-sm font-semibold text-foreground">{workspaceName}</p>
            </div>
            <p className="truncate text-xs capitalize text-muted-foreground">{workspaceType}</p>
          </div>

          <div className="hidden items-center gap-3 rounded-md border border-border bg-muted/55 px-3 py-1.5 xl:flex">
            <ClinicalPulse compact />
            <div className="border-l border-border pl-3">
              <p className="text-[10px] font-semibold uppercase text-muted-foreground">System status</p>
              <div className="flex items-center gap-1.5 text-xs font-semibold text-foreground">
                <span className="h-1.5 w-1.5 animate-status-pulse rounded-full bg-emerald-500" />
                Live
              </div>
            </div>
          </div>

          <button
            type="button"
            onClick={() => setCommandOpen(true)}
            className="hidden h-9 w-52 items-center gap-2 rounded-md border border-input bg-background px-3 text-sm text-muted-foreground transition-colors hover:border-primary/40 hover:bg-card md:flex"
          >
            <Search className="h-4 w-4" />
            <span className="truncate">Find a workspace tool</span>
          </button>

          <button
            type="button"
            onClick={() => setCommandOpen(true)}
            className="flex h-9 w-9 items-center justify-center rounded-md border border-border bg-card text-muted-foreground hover:text-foreground md:hidden"
            aria-label="Search workspace"
          >
            <Search className="h-4 w-4" />
          </button>

          {visibleNav.find((entry) => entry.id === "chat") && (
            <HeaderIconLink
              to={pathFor(visibleNav.find((entry) => entry.id === "chat")!)}
              label="Messages"
              icon={MessageSquare}
              badge={unreadMessages}
            />
          )}
          {visibleNav.find((entry) => entry.id === "alerts") && (
            <HeaderIconLink
              to={pathFor(visibleNav.find((entry) => entry.id === "alerts")!)}
              label="Alerts"
              icon={Bell}
              badge={stats?.active_alerts}
              critical
            />
          )}
        </header>

        <div className="min-w-0">{children}</div>
      </div>

      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            className="fixed inset-0 z-50 bg-foreground/30 backdrop-blur-sm lg:hidden"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setMobileOpen(false)}
          >
            <motion.aside
              className="flex h-full w-[min(86vw,320px)] flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground shadow-2xl"
              initial={{ x: "-100%" }}
              animate={{ x: 0 }}
              exit={{ x: "-100%" }}
              transition={{ type: "spring", damping: 30, stiffness: 320 }}
              onClick={(event) => event.stopPropagation()}
            >
              <div className="flex h-[72px] items-center justify-between border-b border-sidebar-border px-4">
                <Link to="/" className="flex items-center gap-3">
                  <img src={logo} alt="" className="h-9 w-9 rounded-md bg-white/[0.08] object-contain p-1" />
                  <div>
                    <p className="text-base font-bold text-white">HIS.Pro</p>
                    <p className="text-[10px] font-semibold uppercase text-sidebar-primary">Clinical OS 2.0</p>
                  </div>
                </Link>
                <button
                  type="button"
                  onClick={() => setMobileOpen(false)}
                  className="flex h-9 w-9 items-center justify-center rounded-md text-sidebar-foreground/65 hover:bg-sidebar-accent hover:text-white"
                  aria-label="Close navigation"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
              {navigation(true)}
              <div className="border-t border-sidebar-border p-3">
                <button
                  type="button"
                  onClick={handleLogout}
                  className="flex w-full items-center gap-3 rounded-md px-3 py-2.5 text-sm font-semibold text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-white"
                >
                  <LogOut className="h-4 w-4" />
                  Log out
                </button>
              </div>
            </motion.aside>
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {commandOpen && (
          <motion.div
            className="fixed inset-0 z-[60] flex items-start justify-center bg-foreground/25 px-4 pt-[12vh] backdrop-blur-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setCommandOpen(false)}
          >
            <motion.div
              role="dialog"
              aria-modal="true"
              aria-label="Find a workspace tool"
              className="w-full max-w-xl overflow-hidden rounded-lg border border-border bg-card shadow-[0_24px_70px_rgba(18,51,49,0.22)]"
              initial={{ opacity: 0, y: -12, scale: 0.985 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -8, scale: 0.99 }}
              onClick={(event) => event.stopPropagation()}
            >
              <div className="flex items-center gap-3 border-b border-border px-4">
                <Search className="h-4 w-4 text-primary" />
                <Input
                  autoFocus
                  value={commandQuery}
                  onChange={(event) => setCommandQuery(event.target.value)}
                  placeholder="Search patients, care, operations, governance..."
                  className="h-12 border-0 bg-transparent px-0 shadow-none focus-visible:ring-0"
                />
                <button
                  type="button"
                  onClick={() => setCommandOpen(false)}
                  className="flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground"
                  aria-label="Close search"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
              <div className="scrollbar-clinical max-h-[52vh] overflow-y-auto p-2">
                {filteredCommands.length ? (
                  filteredCommands.map((entry) => (
                    <button
                      key={entry.id}
                      type="button"
                      onClick={() => navigate(pathFor(entry))}
                      className="flex w-full items-center gap-3 rounded-md px-3 py-3 text-left hover:bg-muted"
                    >
                      <span className="flex h-9 w-9 items-center justify-center rounded-md bg-primary/[0.08] text-primary">
                        <entry.icon className="h-4 w-4" />
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm font-semibold text-foreground">{entry.label}</span>
                        <span className="block text-xs text-muted-foreground">{entry.group}</span>
                      </span>
                      <ChevronRight className="h-4 w-4 text-muted-foreground" />
                    </button>
                  ))
                ) : (
                  <div className="px-4 py-10 text-center text-sm text-muted-foreground">No available workspace tool matches your search.</div>
                )}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

const NavLink = ({
  entry,
  to,
  active,
  collapsed,
  badge,
}: {
  entry: NavEntry;
  to: string;
  active: boolean;
  collapsed: boolean;
  badge?: number;
}) => (
  <Link
    to={to}
    title={collapsed ? entry.label : undefined}
    aria-label={entry.label}
    className={`relative flex h-10 items-center rounded-md text-sm font-medium transition-colors ${
      collapsed ? "justify-center px-2" : "gap-3 px-3"
    } ${
      active
        ? "bg-sidebar-primary text-sidebar-primary-foreground"
        : "text-sidebar-foreground/68 hover:bg-sidebar-accent hover:text-white"
    }`}
  >
    <entry.icon className="h-[17px] w-[17px] shrink-0" />
    {!collapsed && <span className="min-w-0 flex-1 truncate">{entry.label}</span>}
    {Boolean(badge) && (
      <span className={`${collapsed ? "absolute right-0.5 top-0.5 h-2 w-2" : "min-w-5 px-1.5 py-0.5 text-center text-[10px]"} rounded-full bg-[#ef6b5b] font-bold text-white`}>
        {!collapsed && badge}
      </span>
    )}
  </Link>
);

const HeaderIconLink = ({
  to,
  label,
  icon: Icon,
  badge,
  critical = false,
}: {
  to: string;
  label: string;
  icon: ElementType;
  badge?: number;
  critical?: boolean;
}) => (
  <Link
    to={to}
    className="relative flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-border bg-card text-muted-foreground transition-colors hover:border-primary/35 hover:text-foreground"
    aria-label={label}
    title={label}
  >
    <Icon className="h-4 w-4" />
    {Boolean(badge) && (
      <span className={`absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full px-1 text-[9px] font-bold text-white ${critical ? "bg-[#d84c3f]" : "bg-[#168fb7]"}`}>
        {badge && badge > 99 ? "99+" : badge}
      </span>
    )}
  </Link>
);

export default AppShell;
