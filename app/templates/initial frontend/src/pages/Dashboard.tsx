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
  TrendingUp,
  Bell,
  ShieldCheck,
  Settings,
  LogOut,
  Search,
  LayoutDashboard,
  Stethoscope,
  FlaskConical,
  Pill,
  Receipt,
  FileHeart,
  ScanLine,
  Package,
  BedDouble,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  clearStaffSession,
  getFacilityLoginPath,
  getStaffAccessPath,
  getStaffSession,
} from "@/lib/facility-staff";
import {
  getFacilityWorkspace,
  type SavedFacilityWorkspace,
} from "@/lib/facility-workspace";

const moduleIcons: Record<string, React.ElementType> = {
  reception: Users,
  records: FileHeart,
  consultations: Stethoscope,
  nursing: BedDouble,
  lab: FlaskConical,
  pharmacy: Pill,
  billing: Receipt,
  radiology: ScanLine,
  inventory: Package,
};

const moduleLabels: Record<string, string> = {
  reception: "Reception & Registration",
  records: "Shared Patient Record",
  consultations: "Doctors & Consultations",
  nursing: "Nursing & Wards",
  lab: "Laboratory",
  pharmacy: "Pharmacy",
  billing: "Billing & Claims",
  radiology: "Radiology",
  inventory: "Inventory & Stores",
};

const statsCards = [
  { label: "Total Patients", value: "0", icon: Users, change: "New system" },
  { label: "Appointments Today", value: "0", icon: CalendarDays, change: "No appointments yet" },
  { label: "Active Modules", value: "—", icon: Layers, change: "Configured" },
  { label: "System Health", value: "100%", icon: TrendingUp, change: "All systems go" },
];

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
  const location = useLocation();
  const routedData = (location.state as SavedFacilityWorkspace | null) || null;
  const storedData = facilitySlug ? getFacilityWorkspace(facilitySlug) : null;
  const data = routedData ?? storedData ?? {};
  const resolvedFacilitySlug =
    facilitySlug ||
    routedData?.facilitySlug ||
    storedData?.facilitySlug ||
    "";
  const staffAccessPath = resolvedFacilitySlug
    ? getStaffAccessPath(resolvedFacilitySlug)
    : "";
  const facilityLoginPath = resolvedFacilitySlug
    ? getFacilityLoginPath(resolvedFacilitySlug)
    : "/login";
  const session = getStaffSession();

  const facilityName = (data.facilityName as string) || "My Facility";
  const facilityType = (data.facilityType as string) || "clinic";
  const country = (data.country as string) || "—";
  const fullName = (data.fullName as string) || "Admin";
  const email = (data.email as string) || "—";
  const phone = (data.phone as string) || "—";
  const selectedModules =
    (data.selectedModules as string[]) || [
      "reception",
      "records",
      "consultations",
      "nursing",
      "pharmacy",
      "billing",
    ];

  const updatedStats = statsCards.map((s) =>
    s.label === "Active Modules" ? { ...s, value: String(selectedModules.length) } : s
  );

  const handleLogout = () => {
    clearStaffSession();
    navigate(session ? facilityLoginPath : "/", { replace: true });
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
          <SidebarLink icon={LayoutDashboard} label="Dashboard" active />
          {staffAccessPath && (
            <SidebarLink icon={ShieldCheck} label="Staff & Access" to={staffAccessPath} />
          )}
          <SidebarLink icon={Activity} label="Analytics" />
          <SidebarLink icon={Users} label="Patients" />
          <SidebarLink icon={CalendarDays} label="Appointments" />
          <div className="pt-3 pb-1 px-3">
            <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-widest">Modules</p>
          </div>
          {selectedModules.map((id) => {
            const Icon = moduleIcons[id] || Layers;
            return <SidebarLink key={id} icon={Icon} label={moduleLabels[id] || id} />;
          })}
        </nav>

        <div className="p-3 border-t border-border space-y-1">
          <SidebarLink icon={Settings} label="Settings" />
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
              <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-accent" />
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
                        const Icon = moduleIcons[id] || Layers;
                        return (
                          <motion.div
                            key={id}
                            initial={{ opacity: 0, scale: 0.8 }}
                            animate={{ opacity: 1, scale: 1 }}
                            transition={{ delay: 0.3 + i * 0.08 }}
                            className="glass-card rounded-xl p-4 flex items-center gap-3 border border-primary/10 hover:border-primary/30 transition-colors cursor-pointer group"
                          >
                            <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center group-hover:bg-primary/20 transition-colors">
                              <Icon className="h-5 w-5 text-primary" />
                            </div>
                            <div>
                              <p className="font-semibold text-sm text-foreground">{moduleLabels[id] || id}</p>
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
                  <Button variant="outline" className="gap-2">
                    <CalendarDays className="h-4 w-4" /> Schedule Appointment
                  </Button>
                  {resolvedFacilitySlug && (
                    <Button asChild variant="outline" className="gap-2">
                      <Link to={facilityLoginPath}>
                        <Mail className="h-4 w-4" /> Facility Login
                      </Link>
                    </Button>
                  )}
                  <Button variant="outline" className="gap-2">
                    <Settings className="h-4 w-4" /> System Settings
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
}: {
  icon: React.ElementType;
  label: string;
  active?: boolean;
  to?: string;
  onClick?: () => void;
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
        {label}
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
