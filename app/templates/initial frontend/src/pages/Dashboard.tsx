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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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

type FacilityDepartment = {
  id: string;
  name: string;
  location?: string;
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
  const [departments, setDepartments] = useState<FacilityDepartment[]>([]);
  const [selectedDepartmentId, setSelectedDepartmentId] = useState("all");

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

    const departmentQuery =
      selectedDepartmentId !== "all" ? `&department_id=${encodeURIComponent(selectedDepartmentId)}` : "";

    apiClient
      .get<DashboardStats>(
        `/dashboard/stats?facility_slug=${encodeURIComponent(facilitySlug)}${departmentQuery}`
      )
      .then(setDashboardStats)
      .catch(() => setDashboardStats(null));
  }, [facilitySlug, user, selectedDepartmentId]);

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
        hospital_type?: string;
        departments?: FacilityDepartment[];
        created_at?: string;
      }>(`/facilities/${facilitySlug}`)
      .then((facility) => {
        setDepartments(facility.hospital_type === "multi_clinic" ? facility.departments || [] : []);
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
        <main className="min-h-screen overflow-auto bg-background p-6">
          <motion.div variants={container} initial="hidden" animate="show" className="space-y-6">
            {/* Welcome */}
            <motion.div variants={item}>
              <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
                <div>
                  <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
                    Welcome, <span className="text-gradient">{fullName.split(" ")[0]}</span>
                  </h1>
                  <p className="text-muted-foreground mt-1">
                    Your HIS for <strong className="text-foreground">{facilityName}</strong> is ready.
                  </p>
                </div>
                {departments.length > 0 && user?.role === "admin" && (
                  <div className="w-full sm:w-72">
                    <Select value={selectedDepartmentId} onValueChange={setSelectedDepartmentId}>
                      <SelectTrigger>
                        <SelectValue placeholder="Select department" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All Departments</SelectItem>
                        {departments.map((department) => (
                          <SelectItem key={department.id} value={department.id}>
                            {department.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                )}
              </div>
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
