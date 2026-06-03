import { useEffect, useState } from "react";
import { useLocation, Link, useNavigate, useParams } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Building2,
  Globe,
  User,
  Mail,
  Phone,
  Layers,
  Activity,
  Users,
  CalendarDays,
  Bell,
  ShieldCheck,
  Settings,
  LogOut,
  Search,
  LayoutDashboard,
  ClipboardList,
  Stethoscope,
  FlaskConical,
  Pill,
  Receipt,
  FileHeart,
  ScanLine,
  Package,
  Truck,
  BedDouble,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/context/AuthContext";
import {
  getFacilityLoginPath,
  getStaffAccessPath,
} from "@/lib/facility-staff";
import {
  getFacilityWorkspace,
  type SavedFacilityWorkspace,
} from "@/lib/facility-workspace";
import {
  getModuleById,
  getModulePath,
  isModuleEnabled,
  normalizeModules,
} from "@/lib/modules";
import { apiClient } from "@/api/client";

type DashboardStats = {
  patient_count: number;
  today_appointments: number;
  pending_lab_orders: number;
  pending_radiology_orders: number;
  low_inventory_items: number;
  active_alerts: number;
  active_queue_count: number;
};

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.08 } },
};

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 },
};

const Dashboard = () => {
  const navigate = useNavigate();
  const { facilitySlug } = useParams();
  const { user, logout } = useAuth();
  const location = useLocation();
  const routedData = (location.state as SavedFacilityWorkspace | null) || null;
  const [workspace, setWorkspace] = useState<SavedFacilityWorkspace | null>(
    routedData
  );
  const [isLoading, setIsLoading] = useState(!Boolean(routedData));
  const [dashboardStats, setDashboardStats] = useState<DashboardStats | null>(
    null
  );

  useEffect(() => {
    if (!workspace && facilitySlug) {
      setIsLoading(true);
      getFacilityWorkspace(facilitySlug)
        .then((result) => {
          if (result) {
            setWorkspace(result);
          } else {
            navigate(`/login/${facilitySlug}`, { replace: true });
          }
        })
        .finally(() => setIsLoading(false));
    }
  }, [facilitySlug, workspace, navigate]);

  useEffect(() => {
    if (!facilitySlug || !user) {
      return;
    }

    apiClient
      .get<DashboardStats>(
        `/dashboard/stats?facility_slug=${encodeURIComponent(facilitySlug)}`
      )
      .then(setDashboardStats)
      .catch(() => setDashboardStats(null));
  }, [facilitySlug, user]);

  useEffect(() => {
    if (!facilitySlug || !user || user.role !== "ADMIN") {
      return;
    }

    apiClient
      .get<{
        name: string;
        slug: string;
        type: string;
        country?: string | null;
        phone?: string | null;
        email?: string | null;
        modules?: string[];
        created_at?: string;
      }>(`/facilities/${facilitySlug}`)
      .then((facility) => {
        setWorkspace((current) => ({
          facilityName: facility.name,
          facilityType: facility.type,
          country: facility.country || current?.country || "",
          fullName: current?.fullName || user.fullName || "Admin",
          email: facility.email || current?.email || user.email || "",
          phone: facility.phone || current?.phone || "",
          selectedModules: normalizeModules(facility.modules),
          facilitySlug: facility.slug,
          createdAt: facility.created_at || current?.createdAt || new Date().toISOString(),
        }));
      })
      .catch(() => undefined);
  }, [facilitySlug, user]);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background px-4">
        <p className="text-base font-medium text-muted-foreground">
          Loading dashboard…
        </p>
      </div>
    );
  }

  const data = workspace ?? {};
  const resolvedFacilitySlug =
    facilitySlug || workspace?.facilitySlug || "";
  const staffAccessPath = resolvedFacilitySlug
    ? getStaffAccessPath(resolvedFacilitySlug)
    : "";
  const rawSelectedModules =
    (data.selectedModules as string[] | undefined) || [
      "reception",
      "records",
      "consultations",
      "nursing",
      "pharmacy",
      "billing",
    ];
  const selectedModules = normalizeModules(rawSelectedModules);
  const moduleEnabled = (moduleId: Parameters<typeof isModuleEnabled>[1]) =>
    isModuleEnabled(selectedModules, moduleId);
  const patientsPath = resolvedFacilitySlug && moduleEnabled("reception")
    ? `/dashboard/${resolvedFacilitySlug}/patients`
    : "";
  const appointmentsPath = resolvedFacilitySlug && moduleEnabled("reception")
    ? `/dashboard/${resolvedFacilitySlug}/appointments`
    : "";
  const billingPath = resolvedFacilitySlug && moduleEnabled("billing")
    ? `/dashboard/${resolvedFacilitySlug}/billing`
    : "";
  const laboratoryPath = resolvedFacilitySlug && moduleEnabled("lab")
    ? `/dashboard/${resolvedFacilitySlug}/laboratory`
    : "";
  const pharmacyPath = resolvedFacilitySlug && moduleEnabled("pharmacy")
    ? `/dashboard/${resolvedFacilitySlug}/pharmacy`
    : "";
  const radiologyPath = resolvedFacilitySlug && moduleEnabled("radiology")
    ? `/dashboard/${resolvedFacilitySlug}/radiology`
    : "";
  const inventoryPath = resolvedFacilitySlug && moduleEnabled("inventory")
    ? `/dashboard/${resolvedFacilitySlug}/inventory`
    : "";
  const queuePath = resolvedFacilitySlug && moduleEnabled("reception")
    ? `/dashboard/${resolvedFacilitySlug}/queue`
    : "";
  const consultationsPath = resolvedFacilitySlug && moduleEnabled("consultations")
    ? `/dashboard/${resolvedFacilitySlug}/consultations`
    : "";
  const wardsPath = resolvedFacilitySlug && moduleEnabled("nursing")
    ? `/dashboard/${resolvedFacilitySlug}/wards`
    : "";
  const reportsPath = resolvedFacilitySlug && moduleEnabled("reports")
    ? `/dashboard/${resolvedFacilitySlug}/reports`
    : "";
  const recordsPath = resolvedFacilitySlug && moduleEnabled("records")
    ? `/dashboard/${resolvedFacilitySlug}/records`
    : "";
  const alertsPath = resolvedFacilitySlug
    ? `/dashboard/${resolvedFacilitySlug}/alerts`
    : "";
  const auditLogsPath = resolvedFacilitySlug
    ? `/dashboard/${resolvedFacilitySlug}/audit-logs`
    : "";
  const settingsPath = resolvedFacilitySlug
    ? `/dashboard/${resolvedFacilitySlug}/settings`
    : "";
  const suppliersPath = resolvedFacilitySlug && moduleEnabled("inventory")
    ? `/dashboard/${resolvedFacilitySlug}/suppliers`
    : "";
  const facilityLoginPath = resolvedFacilitySlug
    ? getFacilityLoginPath(resolvedFacilitySlug)
    : "/login";
  const dashboardPath = resolvedFacilitySlug
    ? `/dashboard/${resolvedFacilitySlug}`
    : "";
  const modulePaths = Object.fromEntries(
    selectedModules.map((id) => [id, getModulePath(resolvedFacilitySlug, id)])
  );

  const facilityName = (data.facilityName as string) || "My Facility";
  const facilityType = (data.facilityType as string) || "clinic";
  const country = (data.country as string) || "—";
  const fullName = (data.fullName as string) || "Admin";
  const email = (data.email as string) || "—";
  const phone = (data.phone as string) || "—";
  const updatedStats = [
    {
      label: "Total Patients",
      value: String(dashboardStats?.patient_count ?? 0),
      icon: Users,
      change: "Live count",
    },
    {
      label: "Appointments Today",
      value: String(dashboardStats?.today_appointments ?? 0),
      icon: CalendarDays,
      change: "Today",
    },
    {
      label: "Active Queue",
      value: String(dashboardStats?.active_queue_count ?? 0),
      icon: Activity,
      change: "Waiting + in care",
    },
    {
      label: "Active Modules",
      value: String(selectedModules.length),
      icon: Layers,
      change: "Configured",
    },
  ];

  const handleLogout = () => {
    logout();
    navigate(facilitySlug ? facilityLoginPath : "/", { replace: true });
  };

  return (
    <div className="min-h-screen bg-background flex">
      {/* Sidebar */}
      <motion.aside
        initial={{ x: -260 }}
        animate={{ x: 0 }}
        transition={{ type: "spring", stiffness: 200, damping: 25 }}
        className="hidden lg:flex flex-col w-64 border-r border-border bg-card"
      >
        <div className="p-5 border-b border-border">
          <Link to="/" className="text-xl font-extrabold tracking-tight">
            <span className="text-gradient">HIS</span>
            <span className="text-foreground">.Pro</span>
          </Link>
          <p className="text-xs text-muted-foreground mt-1 capitalize">{facilityType} Dashboard</p>
        </div>

        <nav className="flex-1 p-3 space-y-1">
          <SidebarLink icon={LayoutDashboard} label="Dashboard" to={dashboardPath} active={location.pathname === dashboardPath} />
          {staffAccessPath && (
            <SidebarLink icon={ShieldCheck} label="Staff & Access" to={staffAccessPath} active={location.pathname === staffAccessPath} />
          )}
          {alertsPath && <SidebarLink icon={Bell} label="Alerts" to={alertsPath} active={location.pathname === alertsPath} badge={dashboardStats?.active_alerts} />}
          {auditLogsPath && <SidebarLink icon={ClipboardList} label="Audit Logs" to={auditLogsPath} active={location.pathname === auditLogsPath} />}
          {reportsPath && <SidebarLink icon={Activity} label="Reports" to={reportsPath} active={location.pathname === reportsPath} />}
          {patientsPath && <SidebarLink icon={Users} label="Patients" to={patientsPath} active={location.pathname === patientsPath} />}
          {queuePath && <SidebarLink icon={ClipboardList} label="Reception Queue" to={queuePath} active={location.pathname === queuePath} />}
          {consultationsPath && <SidebarLink icon={Stethoscope} label="Consultations" to={consultationsPath} active={location.pathname === consultationsPath} />}
          {wardsPath && <SidebarLink icon={BedDouble} label="Wards" to={wardsPath} active={location.pathname === wardsPath} />}
          {recordsPath && <SidebarLink icon={FileHeart} label="Medical Records" to={recordsPath} active={location.pathname === recordsPath} />}
          {appointmentsPath && <SidebarLink icon={CalendarDays} label="Appointments" to={appointmentsPath} active={location.pathname === appointmentsPath} />}
          {billingPath && <SidebarLink icon={Receipt} label="Billing" to={billingPath} active={location.pathname === billingPath} />}
          {laboratoryPath && <SidebarLink icon={FlaskConical} label="Laboratory" to={laboratoryPath} active={location.pathname === laboratoryPath} />}
          {pharmacyPath && <SidebarLink icon={Pill} label="Pharmacy" to={pharmacyPath} active={location.pathname === pharmacyPath} />}
          {radiologyPath && <SidebarLink icon={ScanLine} label="Radiology" to={radiologyPath} active={location.pathname === radiologyPath} />}
          {inventoryPath && <SidebarLink icon={Package} label="Inventory" to={inventoryPath} active={location.pathname === inventoryPath} />}
          {suppliersPath && <SidebarLink icon={Truck} label="Suppliers" to={suppliersPath} active={location.pathname === suppliersPath} />}
        </nav>

        <div className="p-3 border-t border-border space-y-1">
          {settingsPath && <SidebarLink icon={Settings} label="Settings" to={settingsPath} />}
          <SidebarLink icon={LogOut} label="Log Out" onClick={handleLogout} />
        </div>
      </motion.aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-h-screen">
        {/* Top bar */}
        <motion.header
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="h-16 border-b border-border bg-card/80 backdrop-blur-lg flex items-center justify-between px-6"
        >
          <div className="flex items-center gap-3">
            <div className="lg:hidden text-xl font-extrabold tracking-tight">
              <span className="text-gradient">HIS</span>
              <span className="text-foreground">.Pro</span>
            </div>
            <div className="relative hidden sm:block">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input placeholder="Search…" className="pl-9 h-9 w-64 bg-muted/50 border-0" />
            </div>
          </div>
          <div className="flex items-center gap-3">
            {staffAccessPath && (
              <Button asChild variant="outline" className="hidden sm:inline-flex">
                <Link to={staffAccessPath}>Staff & Access</Link>
              </Button>
            )}
            <Button variant="ghost" size="icon" className="relative">
              <Bell className="h-5 w-5 text-muted-foreground" />
              {Boolean(dashboardStats?.active_alerts) && (
                <span className="absolute top-1 right-1 rounded-full bg-accent px-1.5 text-[10px] font-bold text-accent-foreground">
                  {dashboardStats?.active_alerts}
                </span>
              )}
            </Button>
            <div className="w-9 h-9 rounded-full gradient-hero flex items-center justify-center text-primary-foreground font-bold text-sm">
              {fullName.charAt(0).toUpperCase()}
            </div>
          </div>
        </motion.header>

        {/* Content */}
        <main className="flex-1 p-6 overflow-auto">
          <motion.div variants={container} initial="hidden" animate="show" className="space-y-6">
            {/* Welcome */}
            <motion.div variants={item}>
              <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
                Welcome, <span className="text-gradient">{fullName.split(" ")[0]}</span> 👋
              </h1>
              <p className="text-muted-foreground mt-1">
                Your HIS for <strong className="text-foreground">{facilityName}</strong> is ready.
              </p>
            </motion.div>

            {/* Stats */}
            <motion.div variants={item} className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              {updatedStats.map((stat, i) => {
                const Icon = stat.icon;
                return (
                  <Card key={i} className="border-border/60 hover:shadow-md transition-shadow">
                    <CardContent className="p-5">
                      <div className="flex items-center justify-between mb-3">
                        <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
                          <Icon className="h-5 w-5 text-primary" />
                        </div>
                        <span className="text-[11px] text-muted-foreground">{stat.change}</span>
                      </div>
                      <p className="text-2xl font-extrabold text-foreground">{stat.value}</p>
                      <p className="text-xs text-muted-foreground mt-0.5">{stat.label}</p>
                    </CardContent>
                  </Card>
                );
              })}
            </motion.div>

            <div className="grid lg:grid-cols-3 gap-6">
              {/* Facility Info */}
              <motion.div variants={item} className="lg:col-span-1">
                <Card className="border-border/60 h-full">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base font-bold flex items-center gap-2">
                      <Building2 className="h-4 w-4 text-primary" /> Facility Info
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3 text-sm">
                    <InfoRow icon={Building2} label="Name" value={facilityName} />
                    <InfoRow icon={Layers} label="Type" value={facilityType} capitalize />
                    <InfoRow icon={Globe} label="Country" value={country} />
                    <InfoRow icon={User} label="Admin" value={fullName} />
                    <InfoRow icon={Mail} label="Email" value={email} />
                    {phone !== "—" && <InfoRow icon={Phone} label="Phone" value={phone} />}
                    {resolvedFacilitySlug && (
                      <div className="pt-3">
                        <Button asChild variant="outline" className="w-full justify-center">
                          <Link to={facilityLoginPath}>Open facility login</Link>
                        </Button>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </motion.div>

              {/* Active Modules */}
              <motion.div variants={item} className="lg:col-span-2">
                <Card className="border-border/60 h-full">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base font-bold flex items-center gap-2">
                      <Layers className="h-4 w-4 text-primary" /> Active Modules
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                      {selectedModules.map((id, i) => {
                        const module = getModuleById(id);
                        const Icon = module?.icon || Layers;
                        return (
                          <motion.div
                            key={id}
                            initial={{ opacity: 0, scale: 0.8 }}
                            animate={{ opacity: 1, scale: 1 }}
                            transition={{ delay: 0.3 + i * 0.08 }}
                            className="glass-card rounded-xl p-4 flex items-center gap-3 border border-primary/10 hover:border-primary/30 transition-colors cursor-pointer group"
                            onClick={() => {
                              const modulePath = modulePaths[id];
                              if (modulePath) {
                                navigate(modulePath);
                              }
                            }}
                          >
                            <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center group-hover:bg-primary/20 transition-colors">
                              <Icon className="h-5 w-5 text-primary" />
                            </div>
                            <div>
                              <p className="font-semibold text-sm text-foreground">{module?.label || id}</p>
                              <p className="text-[11px] text-accent font-medium">Active</p>
                            </div>
                          </motion.div>
                        );
                      })}
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            </div>

            {/* Quick actions */}
            <motion.div variants={item}>
              <Card className="border-border/60">
                <CardHeader className="pb-3">
                  <CardTitle className="text-base font-bold">Quick Actions</CardTitle>
                </CardHeader>
                <CardContent className="flex flex-wrap gap-3">
                  {staffAccessPath && (
                    <Button asChild className="gradient-cta text-primary-foreground border-0 gap-2">
                      <Link to={staffAccessPath}>
                        <Users className="h-4 w-4" /> Add Staff
                      </Link>
                    </Button>
                  )}
                  {appointmentsPath && (
                    <Button asChild variant="outline" className="gap-2">
                      <Link to={appointmentsPath}>
                        <CalendarDays className="h-4 w-4" /> Schedule Appointment
                      </Link>
                    </Button>
                  )}
                  {patientsPath && (
                    <Button asChild variant="outline" className="gap-2">
                      <Link to={patientsPath}>
                        <Users className="h-4 w-4" /> Patient Registry
                      </Link>
                    </Button>
                  )}
                  {recordsPath && (
                    <Button asChild variant="outline" className="gap-2">
                      <Link to={recordsPath}>
                        <FileHeart className="h-4 w-4" /> Medical Records
                      </Link>
                    </Button>
                  )}
                  {billingPath && (
                    <Button asChild variant="outline" className="gap-2">
                      <Link to={billingPath}>
                        <Receipt className="h-4 w-4" /> Billing
                      </Link>
                    </Button>
                  )}
                  {laboratoryPath && (
                    <Button asChild variant="outline" className="gap-2">
                      <Link to={laboratoryPath}>
                        <FlaskConical className="h-4 w-4" /> Laboratory
                      </Link>
                    </Button>
                  )}
                  {pharmacyPath && (
                    <Button asChild variant="outline" className="gap-2">
                      <Link to={pharmacyPath}>
                        <Pill className="h-4 w-4" /> Pharmacy
                      </Link>
                    </Button>
                  )}
                  {radiologyPath && (
                    <Button asChild variant="outline" className="gap-2">
                      <Link to={radiologyPath}>
                        <ScanLine className="h-4 w-4" /> Radiology
                      </Link>
                    </Button>
                  )}
                  {inventoryPath && (
                    <Button asChild variant="outline" className="gap-2">
                      <Link to={inventoryPath}>
                        <Package className="h-4 w-4" /> Inventory
                      </Link>
                    </Button>
                  )}
                  {suppliersPath && (
                    <Button asChild variant="outline" className="gap-2">
                      <Link to={suppliersPath}>
                        <Truck className="h-4 w-4" /> Suppliers
                      </Link>
                    </Button>
                  )}
                  {queuePath && (
                    <Button asChild variant="outline" className="gap-2">
                      <Link to={queuePath}>
                        <ClipboardList className="h-4 w-4" /> Reception Queue
                      </Link>
                    </Button>
                  )}
                  {consultationsPath && (
                    <Button asChild variant="outline" className="gap-2">
                      <Link to={consultationsPath}>
                        <Stethoscope className="h-4 w-4" /> Consultations
                      </Link>
                    </Button>
                  )}
                  {wardsPath && (
                    <Button asChild variant="outline" className="gap-2">
                      <Link to={wardsPath}>
                        <BedDouble className="h-4 w-4" /> Wards
                      </Link>
                    </Button>
                  )}
                  {reportsPath && (
                    <Button asChild variant="outline" className="gap-2">
                      <Link to={reportsPath}>
                        <Activity className="h-4 w-4" /> Reports
                      </Link>
                    </Button>
                  )}
                  {alertsPath && (
                    <Button asChild variant="outline" className="gap-2">
                      <Link to={alertsPath}>
                        <Bell className="h-4 w-4" /> Alerts
                        {Boolean(dashboardStats?.active_alerts) && (
                          <span className="rounded-full bg-primary px-2 py-0.5 text-xs font-semibold text-primary-foreground">
                            {dashboardStats?.active_alerts}
                          </span>
                        )}
                      </Link>
                    </Button>
                  )}
                  {auditLogsPath && (
                    <Button asChild variant="outline" className="gap-2">
                      <Link to={auditLogsPath}>
                        <ClipboardList className="h-4 w-4" /> Audit Logs
                      </Link>
                    </Button>
                  )}
                  {facilityLoginPath && (
                    <Button asChild variant="outline" className="gap-2">
                      <Link to={facilityLoginPath}>
                        <Mail className="h-4 w-4" /> Facility Login
                      </Link>
                    </Button>
                  )}
                  <Button asChild variant="outline" className="gap-2">
                    <Link to={settingsPath} className="inline-flex items-center gap-2">
                      <Settings className="h-4 w-4" /> System Settings
                    </Link>
                  </Button>
                </CardContent>
              </Card>
            </motion.div>
          </motion.div>
        </main>
      </div>
    </div>
  );
};

const SidebarLink = ({
  icon: Icon,
  label,
  active,
  to,
  onClick,
  badge,
}: {
  icon: React.ElementType;
  label: string;
  active?: boolean;
  to?: string;
  onClick?: () => void;
  badge?: number;
}) => {
  const className = `w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors ${
    active
      ? "bg-primary/10 text-primary"
      : "text-muted-foreground hover:bg-muted hover:text-foreground"
  }`;

  if (to) {
    return (
      <Link to={to} className={className}>
        <Icon className="h-4 w-4 shrink-0" />
        <span className="flex-1">{label}</span>
        {Boolean(badge) && (
          <span className="rounded-full bg-primary px-2 py-0.5 text-xs font-semibold text-primary-foreground">
            {badge}
          </span>
        )}
      </Link>
    );
  }

  return (
    <button type="button" onClick={onClick} className={className}>
      <Icon className="h-4 w-4 shrink-0" />
      {label}
    </button>
  );
};

const InfoRow = ({ icon: Icon, label, value, capitalize }: { icon: React.ElementType; label: string; value: string; capitalize?: boolean }) => (
  <div className="flex items-center justify-between">
    <span className="flex items-center gap-2 text-muted-foreground">
      <Icon className="h-3.5 w-3.5" /> {label}
    </span>
    <span className={`font-medium text-foreground ${capitalize ? "capitalize" : ""}`}>{value}</span>
  </div>
);

export default Dashboard;
