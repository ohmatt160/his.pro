import { useEffect, type ElementType } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Activity,
  AlertCircle,
  BedDouble,
  Bell,
  CalendarDays,
  CheckCircle2,
  ClipboardList,
  Clock,
  FileText,
  FlaskConical,
  LayoutDashboard,
  LogOut,
  MessageSquare,
  Package,
  Pill,
  Receipt,
  Search,
  Settings,
  Shield,
  Stethoscope,
  TrendingUp,
  UserSquare2,
  Users,
  Waves,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  clearStaffSession,
  getFacilityLoginPath,
  getStaffByLoginId,
  getStaffRoleLabel,
  getStaffSession,
  type StaffRole,
} from "@/lib/facility-staff";
import {
  getFacilityDashboardPath,
  getFacilityWorkspace,
} from "@/lib/facility-workspace";

type QuickAction = {
  label: string;
  icon: ElementType;
  color: string;
};

type QueueItem = {
  primary: string;
  secondary: string;
  time: string;
  status: string;
  tone: "success" | "warning" | "critical";
  action: string;
};

type ActivityItem = {
  action: string;
  subject: string;
  time: string;
  icon: ElementType;
};

type AlertItem = {
  text: string;
  severity: "warning" | "critical";
};

type StatCard = {
  label: string;
  value: string;
  icon: ElementType;
  color: string;
};

type NavItem = {
  label: string;
  icon: ElementType;
  badge?: string;
};

type RoleConfig = {
  subtitle: string;
  searchPlaceholder: string;
  queueTitle: string;
  queueCountLabel: string;
  primaryAction: {
    label: string;
    icon: ElementType;
  };
  quickActions: QuickAction[];
  queueItems: QueueItem[];
  stats: StatCard[];
  recentActivity: ActivityItem[];
  alerts: AlertItem[];
  accessModules: string[];
  sidebarMain: NavItem[];
  sidebarTools: NavItem[];
};

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.06 } },
};

const item = {
  hidden: { opacity: 0, y: 14 },
  show: { opacity: 1, y: 0 },
};

const roleConfigs: Record<Exclude<StaffRole, "admin">, RoleConfig> = {
  doctor: {
    subtitle:
      "Review consultations, update clinical notes, and make treatment decisions from one connected clinical workspace.",
    searchPlaceholder: "Search patients, records...",
    queueTitle: "Today's Schedule",
    queueCountLabel: "appointments today",
    primaryAction: {
      label: "Start Consultation",
      icon: Stethoscope,
    },
    quickActions: [
      {
        label: "New Consultation",
        icon: Stethoscope,
        color: "bg-blue-500/10 text-blue-600",
      },
      {
        label: "Patient Lookup",
        icon: Users,
        color: "bg-primary/10 text-primary",
      },
      {
        label: "Write Prescription",
        icon: Pill,
        color: "bg-purple-500/10 text-purple-600",
      },
      {
        label: "Order Lab Test",
        icon: FlaskConical,
        color: "bg-cyan-500/10 text-cyan-600",
      },
      {
        label: "View Schedule",
        icon: CalendarDays,
        color: "bg-amber-500/10 text-amber-600",
      },
      {
        label: "Medical Records",
        icon: FileText,
        color: "bg-emerald-500/10 text-emerald-600",
      },
    ],
    queueItems: [
      {
        primary: "Adewale Okonkwo",
        secondary: "Follow-up consultation",
        time: "9:00 AM",
        status: "Confirmed",
        tone: "success",
        action: "Open",
      },
      {
        primary: "Fatima Ibrahim",
        secondary: "New patient review",
        time: "9:30 AM",
        status: "Confirmed",
        tone: "success",
        action: "Open",
      },
      {
        primary: "James Okoro",
        secondary: "Lab result review",
        time: "10:15 AM",
        status: "Pending",
        tone: "warning",
        action: "Prepare",
      },
      {
        primary: "Blessing Adekunle",
        secondary: "Routine check-up",
        time: "11:00 AM",
        status: "Confirmed",
        tone: "success",
        action: "Open",
      },
      {
        primary: "Emeka Nwosu",
        secondary: "Consultation",
        time: "11:45 AM",
        status: "Pending",
        tone: "warning",
        action: "Review",
      },
    ],
    stats: [
      {
        label: "Patients Today",
        value: "24",
        icon: Users,
        color: "bg-primary/10 text-primary",
      },
      {
        label: "Completed",
        value: "18",
        icon: TrendingUp,
        color: "bg-accent/10 text-accent",
      },
    ],
    recentActivity: [
      {
        action: "Completed consultation",
        subject: "Mary Chukwu",
        time: "2 min ago",
        icon: CheckCircle2,
      },
      {
        action: "Prescription sent to pharmacy",
        subject: "Usman Bello",
        time: "15 min ago",
        icon: Pill,
      },
      {
        action: "Lab results received",
        subject: "Grace Obi",
        time: "1 hr ago",
        icon: FlaskConical,
      },
      {
        action: "Admitted to ward",
        subject: "David Ajayi",
        time: "2 hrs ago",
        icon: BedDouble,
      },
    ],
    alerts: [
      { text: "3 lab results pending review", severity: "warning" },
      {
        text: "Drug interaction alert for patient #4821",
        severity: "critical",
      },
    ],
    accessModules: [
      "Shared Patient Record",
      "Doctors & Consultations",
      "Laboratory",
      "Pharmacy",
    ],
    sidebarMain: [
      { label: "My Dashboard", icon: LayoutDashboard },
      { label: "Patients", icon: Users },
      { label: "Schedule", icon: CalendarDays },
      { label: "Consultations", icon: Stethoscope },
      { label: "Tasks", icon: ClipboardList },
    ],
    sidebarTools: [
      { label: "Prescriptions", icon: Pill },
      { label: "Lab Orders", icon: FlaskConical },
      { label: "Medical Records", icon: FileText },
      { label: "Messages", icon: MessageSquare, badge: "3" },
    ],
  },
  nurse: {
    subtitle:
      "Track ward activity, record vitals, manage medication rounds, and keep patient handoff clean across shifts.",
    searchPlaceholder: "Search patients, ward tasks...",
    queueTitle: "Ward Task Board",
    queueCountLabel: "tasks on shift",
    primaryAction: {
      label: "Open Ward Board",
      icon: BedDouble,
    },
    quickActions: [
      {
        label: "Record Vitals",
        icon: Activity,
        color: "bg-emerald-500/10 text-emerald-600",
      },
      {
        label: "Medication Round",
        icon: Pill,
        color: "bg-purple-500/10 text-purple-600",
      },
      {
        label: "Update Notes",
        icon: FileText,
        color: "bg-blue-500/10 text-blue-600",
      },
      {
        label: "Patient Lookup",
        icon: Users,
        color: "bg-primary/10 text-primary",
      },
      {
        label: "Bed Board",
        icon: BedDouble,
        color: "bg-amber-500/10 text-amber-600",
      },
      {
        label: "Shift Handover",
        icon: MessageSquare,
        color: "bg-cyan-500/10 text-cyan-600",
      },
    ],
    queueItems: [
      {
        primary: "Bed 12 · Chioma Adebayo",
        secondary: "Vitals and pain assessment",
        time: "8:30 AM",
        status: "Due",
        tone: "warning",
        action: "Open",
      },
      {
        primary: "Bed 7 · Daniel Ojo",
        secondary: "Medication round",
        time: "9:00 AM",
        status: "Priority",
        tone: "critical",
        action: "Administer",
      },
      {
        primary: "Bed 4 · Nkem Okafor",
        secondary: "Nursing note update",
        time: "9:20 AM",
        status: "In Progress",
        tone: "success",
        action: "Continue",
      },
      {
        primary: "New admission · Tobi Lawal",
        secondary: "Ward handoff checklist",
        time: "10:05 AM",
        status: "Pending",
        tone: "warning",
        action: "Review",
      },
    ],
    stats: [
      {
        label: "Patients in Care",
        value: "18",
        icon: Users,
        color: "bg-primary/10 text-primary",
      },
      {
        label: "Rounds Due",
        value: "6",
        icon: Pill,
        color: "bg-accent/10 text-accent",
      },
    ],
    recentActivity: [
      {
        action: "Vitals recorded",
        subject: "Chioma Adebayo",
        time: "6 min ago",
        icon: Activity,
      },
      {
        action: "Medication administered",
        subject: "Daniel Ojo",
        time: "18 min ago",
        icon: Pill,
      },
      {
        action: "Shift note updated",
        subject: "Ward B",
        time: "42 min ago",
        icon: FileText,
      },
      {
        action: "Patient transferred",
        subject: "Tobi Lawal",
        time: "1 hr ago",
        icon: BedDouble,
      },
    ],
    alerts: [
      { text: "2 medication rounds are overdue", severity: "warning" },
      {
        text: "New admission awaiting bed assignment",
        severity: "critical",
      },
    ],
    accessModules: [
      "Shared Patient Record",
      "Nursing & Wards",
      "Pharmacy",
    ],
    sidebarMain: [
      { label: "My Dashboard", icon: LayoutDashboard },
      { label: "Patients", icon: Users },
      { label: "Ward Board", icon: BedDouble },
      { label: "Tasks", icon: ClipboardList },
      { label: "Handover", icon: Waves },
    ],
    sidebarTools: [
      { label: "Medication Rounds", icon: Pill },
      { label: "Nursing Notes", icon: FileText },
      { label: "Vitals", icon: Activity },
      { label: "Messages", icon: MessageSquare, badge: "2" },
    ],
  },
  reception: {
    subtitle:
      "Handle arrivals, registrations, appointment flow, and patient check-in without losing continuity across the facility.",
    searchPlaceholder: "Search patients, bookings...",
    queueTitle: "Front Desk Queue",
    queueCountLabel: "arrivals expected",
    primaryAction: {
      label: "Register Patient",
      icon: Users,
    },
    quickActions: [
      {
        label: "Register Patient",
        icon: Users,
        color: "bg-primary/10 text-primary",
      },
      {
        label: "Book Appointment",
        icon: CalendarDays,
        color: "bg-amber-500/10 text-amber-600",
      },
      {
        label: "Update Queue",
        icon: ClipboardList,
        color: "bg-blue-500/10 text-blue-600",
      },
      {
        label: "Verify Coverage",
        icon: Shield,
        color: "bg-cyan-500/10 text-cyan-600",
      },
      {
        label: "Collect Payment",
        icon: Receipt,
        color: "bg-emerald-500/10 text-emerald-600",
      },
      {
        label: "Patient Lookup",
        icon: FileText,
        color: "bg-purple-500/10 text-purple-600",
      },
    ],
    queueItems: [
      {
        primary: "Amina Sule",
        secondary: "Walk-in registration",
        time: "8:50 AM",
        status: "Waiting",
        tone: "warning",
        action: "Check in",
      },
      {
        primary: "Joel Etim",
        secondary: "Follow-up appointment",
        time: "9:10 AM",
        status: "Confirmed",
        tone: "success",
        action: "Open",
      },
      {
        primary: "Grace Nwankwo",
        secondary: "Insurance verification",
        time: "9:25 AM",
        status: "Issue",
        tone: "critical",
        action: "Resolve",
      },
      {
        primary: "Bisi Adeola",
        secondary: "Lab-only visit",
        time: "9:40 AM",
        status: "Queued",
        tone: "warning",
        action: "Update",
      },
    ],
    stats: [
      {
        label: "Arrivals Today",
        value: "31",
        icon: Users,
        color: "bg-primary/10 text-primary",
      },
      {
        label: "Checked In",
        value: "22",
        icon: CheckCircle2,
        color: "bg-accent/10 text-accent",
      },
    ],
    recentActivity: [
      {
        action: "Patient registered",
        subject: "Chinedu Umeh",
        time: "5 min ago",
        icon: Users,
      },
      {
        action: "Appointment rescheduled",
        subject: "Bisi Adeola",
        time: "19 min ago",
        icon: CalendarDays,
      },
      {
        action: "Payment handed to billing",
        subject: "Walk-in #203",
        time: "34 min ago",
        icon: Receipt,
      },
      {
        action: "Patient chart opened",
        subject: "Amina Sule",
        time: "56 min ago",
        icon: FileText,
      },
    ],
    alerts: [
      { text: "4 appointments are still waiting for check-in", severity: "warning" },
      {
        text: "Insurance verification failed for Grace Nwankwo",
        severity: "critical",
      },
    ],
    accessModules: [
      "Reception & Registration",
      "Shared Patient Record",
      "Billing & Claims",
    ],
    sidebarMain: [
      { label: "My Dashboard", icon: LayoutDashboard },
      { label: "Arrivals", icon: Users },
      { label: "Appointments", icon: CalendarDays },
      { label: "Check-ins", icon: UserSquare2 },
      { label: "Billing", icon: Receipt },
    ],
    sidebarTools: [
      { label: "Patient Records", icon: FileText },
      { label: "Claims", icon: Receipt },
      { label: "Messages", icon: MessageSquare, badge: "4" },
    ],
  },
  pharmacist: {
    subtitle:
      "Process prescriptions, monitor dispensing, and stay ahead of stock movement from one pharmacy operations view.",
    searchPlaceholder: "Search prescriptions, stock...",
    queueTitle: "Dispensing Queue",
    queueCountLabel: "prescriptions queued",
    primaryAction: {
      label: "Dispense Medication",
      icon: Pill,
    },
    quickActions: [
      {
        label: "Dispense Medication",
        icon: Pill,
        color: "bg-purple-500/10 text-purple-600",
      },
      {
        label: "Review Stock",
        icon: Package,
        color: "bg-primary/10 text-primary",
      },
      {
        label: "Pending Scripts",
        icon: ClipboardList,
        color: "bg-blue-500/10 text-blue-600",
      },
      {
        label: "Billing Handovers",
        icon: Receipt,
        color: "bg-emerald-500/10 text-emerald-600",
      },
      {
        label: "Drug Alerts",
        icon: AlertCircle,
        color: "bg-rose-500/10 text-rose-600",
      },
      {
        label: "Inventory",
        icon: Package,
        color: "bg-amber-500/10 text-amber-600",
      },
    ],
    queueItems: [
      {
        primary: "Usman Bello",
        secondary: "Amoxicillin + Paracetamol",
        time: "9:05 AM",
        status: "Ready",
        tone: "success",
        action: "Dispense",
      },
      {
        primary: "Ngozi Eze",
        secondary: "Antihypertensive refill",
        time: "9:20 AM",
        status: "Pending",
        tone: "warning",
        action: "Review",
      },
      {
        primary: "Musa Ibrahim",
        secondary: "Controlled medication approval",
        time: "9:35 AM",
        status: "Alert",
        tone: "critical",
        action: "Check",
      },
      {
        primary: "Adaobi Nkem",
        secondary: "Pickup handover",
        time: "10:00 AM",
        status: "Ready",
        tone: "success",
        action: "Release",
      },
    ],
    stats: [
      {
        label: "Prescriptions Today",
        value: "26",
        icon: Pill,
        color: "bg-primary/10 text-primary",
      },
      {
        label: "Stock Alerts",
        value: "3",
        icon: Package,
        color: "bg-accent/10 text-accent",
      },
    ],
    recentActivity: [
      {
        action: "Medication dispensed",
        subject: "Usman Bello",
        time: "4 min ago",
        icon: Pill,
      },
      {
        action: "Stock level updated",
        subject: "Amlodipine 5mg",
        time: "17 min ago",
        icon: Package,
      },
      {
        action: "Billing handover sent",
        subject: "Pickup #772",
        time: "41 min ago",
        icon: Receipt,
      },
      {
        action: "Prescription clarified",
        subject: "Ngozi Eze",
        time: "1 hr ago",
        icon: ClipboardList,
      },
    ],
    alerts: [
      { text: "3 medications are below restock threshold", severity: "warning" },
      {
        text: "Drug interaction requires pharmacist review",
        severity: "critical",
      },
    ],
    accessModules: ["Pharmacy", "Billing & Claims", "Inventory & Stores"],
    sidebarMain: [
      { label: "My Dashboard", icon: LayoutDashboard },
      { label: "Prescriptions", icon: Pill },
      { label: "Pickup Queue", icon: ClipboardList },
      { label: "Stock", icon: Package },
      { label: "Claims", icon: Receipt },
    ],
    sidebarTools: [
      { label: "Inventory", icon: Package },
      { label: "Billing", icon: Receipt },
      { label: "Messages", icon: MessageSquare, badge: "2" },
    ],
  },
  lab: {
    subtitle:
      "Receive test orders, track samples, and release results back into the shared patient record with less back-and-forth.",
    searchPlaceholder: "Search tests, samples...",
    queueTitle: "Lab Worklist",
    queueCountLabel: "tests queued",
    primaryAction: {
      label: "Open Lab Queue",
      icon: FlaskConical,
    },
    quickActions: [
      {
        label: "Record Sample",
        icon: FlaskConical,
        color: "bg-cyan-500/10 text-cyan-600",
      },
      {
        label: "Release Result",
        icon: CheckCircle2,
        color: "bg-emerald-500/10 text-emerald-600",
      },
      {
        label: "Print Labels",
        icon: FileText,
        color: "bg-primary/10 text-primary",
      },
      {
        label: "Specimen Tracking",
        icon: ClipboardList,
        color: "bg-blue-500/10 text-blue-600",
      },
      {
        label: "Review Analyzer",
        icon: Activity,
        color: "bg-amber-500/10 text-amber-600",
      },
      {
        label: "Patient Lookup",
        icon: Users,
        color: "bg-purple-500/10 text-purple-600",
      },
    ],
    queueItems: [
      {
        primary: "Patient #1042",
        secondary: "Full blood count",
        time: "8:55 AM",
        status: "Queued",
        tone: "warning",
        action: "Start",
      },
      {
        primary: "Patient #2191",
        secondary: "Malaria parasite test",
        time: "9:10 AM",
        status: "In Progress",
        tone: "success",
        action: "Update",
      },
      {
        primary: "Patient #3278",
        secondary: "Liver function panel",
        time: "9:35 AM",
        status: "QC Alert",
        tone: "critical",
        action: "Review",
      },
      {
        primary: "Patient #4410",
        secondary: "Urinalysis",
        time: "10:00 AM",
        status: "Pending",
        tone: "warning",
        action: "Prepare",
      },
    ],
    stats: [
      {
        label: "Tests Queued",
        value: "14",
        icon: FlaskConical,
        color: "bg-primary/10 text-primary",
      },
      {
        label: "Results Pending",
        value: "6",
        icon: Activity,
        color: "bg-accent/10 text-accent",
      },
    ],
    recentActivity: [
      {
        action: "Sample recorded",
        subject: "Patient #2191",
        time: "5 min ago",
        icon: FlaskConical,
      },
      {
        action: "Result released",
        subject: "Patient #1106",
        time: "22 min ago",
        icon: CheckCircle2,
      },
      {
        action: "QC check flagged",
        subject: "Analyzer B",
        time: "39 min ago",
        icon: AlertCircle,
      },
      {
        action: "Order received from doctor",
        subject: "Patient #3278",
        time: "1 hr ago",
        icon: ClipboardList,
      },
    ],
    alerts: [
      { text: "6 results are pending release", severity: "warning" },
      {
        text: "Quality control exception detected on Analyzer B",
        severity: "critical",
      },
    ],
    accessModules: ["Laboratory", "Shared Patient Record"],
    sidebarMain: [
      { label: "My Dashboard", icon: LayoutDashboard },
      { label: "Test Queue", icon: FlaskConical },
      { label: "Samples", icon: ClipboardList },
      { label: "Results", icon: FileText },
      { label: "Quality", icon: Activity },
    ],
    sidebarTools: [
      { label: "Shared Record", icon: FileText },
      { label: "Messages", icon: MessageSquare, badge: "1" },
    ],
  },
};

const StaffPortal = () => {
  const navigate = useNavigate();
  const { facilitySlug = "" } = useParams();
  const workspace = facilitySlug ? getFacilityWorkspace(facilitySlug) : null;
  const session = getStaffSession();
  const staff =
    facilitySlug && session?.facilitySlug === facilitySlug
      ? getStaffByLoginId(facilitySlug, session.loginId)
      : null;

  useEffect(() => {
    if (!facilitySlug || !workspace) {
      navigate("/", { replace: true });
      return;
    }

    if (!session || session.facilitySlug !== facilitySlug || !staff) {
      navigate(getFacilityLoginPath(facilitySlug), { replace: true });
      return;
    }

    if (staff.role === "admin") {
      navigate(getFacilityDashboardPath(facilitySlug), {
        replace: true,
        state: workspace,
      });
    }
  }, [facilitySlug, navigate, session, staff, workspace]);

  if (!workspace || !staff || staff.role === "admin") {
    return null;
  }

  const config = roleConfigs[staff.role];
  const firstName = staff.fullName.split(" ")[0] || staff.fullName;
  const initials = staff.fullName
    .split(" ")
    .map((name) => name[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
  const currentHour = new Date().getHours();
  const greeting =
    currentHour < 12
      ? "Good morning"
      : currentHour < 17
      ? "Good afternoon"
      : "Good evening";
  const PrimaryIcon = config.primaryAction.icon;

  const handleLogout = () => {
    clearStaffSession();
    navigate(getFacilityLoginPath(facilitySlug), { replace: true });
  };

  return (
    <div className="min-h-screen bg-background flex">
      <motion.aside
        initial={{ x: -260 }}
        animate={{ x: 0 }}
        transition={{ type: "spring", stiffness: 200, damping: 25 }}
        className="hidden w-64 flex-col border-r border-border bg-card lg:flex"
      >
        <div className="border-b border-border p-5">
          <Link to="/" className="text-xl font-extrabold tracking-tight">
            <span className="text-gradient">HIS</span>
            <span className="text-foreground">.Pro</span>
          </Link>
          <p className="mt-1 text-xs text-muted-foreground">
            {workspace.facilityName}
          </p>
        </div>

        <nav className="flex-1 space-y-1 p-3">
          {config.sidebarMain.map((entry, index) => (
            <SidebarLink
              key={entry.label}
              icon={entry.icon}
              label={entry.label}
              badge={entry.badge}
              active={index === 0}
            />
          ))}
          <div className="px-3 pb-1 pt-3">
            <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
              Tools
            </p>
          </div>
          {config.sidebarTools.map((entry) => (
            <SidebarLink
              key={entry.label}
              icon={entry.icon}
              label={entry.label}
              badge={entry.badge}
            />
          ))}
        </nav>

        <div className="space-y-1 border-t border-border p-3">
          <SidebarLink icon={Settings} label="Preferences" />
          <SidebarLink icon={LogOut} label="Sign Out" onClick={handleLogout} />
        </div>
      </motion.aside>

      <div className="flex min-h-screen flex-1 flex-col">
        <motion.header
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex h-16 items-center justify-between border-b border-border bg-card/80 px-6 backdrop-blur-lg"
        >
          <div className="flex items-center gap-3">
            <div className="text-xl font-extrabold tracking-tight lg:hidden">
              <span className="text-gradient">HIS</span>
              <span className="text-foreground">.Pro</span>
            </div>
            <div className="relative hidden sm:block">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder={config.searchPlaceholder}
                className="h-9 w-72 border-0 bg-muted/50 pl-9"
              />
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Button variant="ghost" size="icon" className="relative">
              <Bell className="h-5 w-5 text-muted-foreground" />
              <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-destructive" />
            </Button>
            <div className="flex items-center gap-2.5">
              <div className="flex h-9 w-9 items-center justify-center rounded-full gradient-hero text-xs font-bold text-primary-foreground">
                {initials}
              </div>
              <div className="hidden sm:block">
                <p className="text-sm font-semibold leading-tight text-foreground">
                  {staff.fullName}
                </p>
                <p className="text-[11px] text-muted-foreground">
                  {getStaffRoleLabel(staff.role)} · {staff.department}
                </p>
              </div>
            </div>
          </div>
        </motion.header>

        <main className="flex-1 overflow-auto p-6">
          <motion.div
            variants={container}
            initial="hidden"
            animate="show"
            className="mx-auto max-w-6xl space-y-6"
          >
            <motion.div
              variants={item}
              className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between"
            >
              <div>
                <h1 className="text-2xl font-extrabold tracking-tight sm:text-3xl">
                  {greeting},{" "}
                  <span className="text-gradient">{firstName}</span>
                </h1>
                <p className="mt-1 flex items-center gap-2 text-muted-foreground">
                  <Clock className="h-3.5 w-3.5" />
                  {new Date().toLocaleDateString("en-US", {
                    weekday: "long",
                    month: "long",
                    day: "numeric",
                    year: "numeric",
                  })}
                  <span className="text-border">·</span>
                  <span className="text-sm">
                    {config.queueItems.length} {config.queueCountLabel}
                  </span>
                </p>
              </div>

              <Button className="gradient-cta gap-2 border-0 text-primary-foreground shadow-lg">
                <PrimaryIcon className="h-4 w-4" /> {config.primaryAction.label}
              </Button>
            </motion.div>

            {config.alerts.length > 0 && (
              <motion.div variants={item} className="space-y-2">
                {config.alerts.map((alert) => (
                  <div
                    key={alert.text}
                    className={`flex items-center gap-3 rounded-xl border px-4 py-3 text-sm font-medium ${
                      alert.severity === "critical"
                        ? "border-destructive/20 bg-destructive/5 text-destructive"
                        : "border-amber-200 bg-amber-50 text-amber-700"
                    }`}
                  >
                    <AlertCircle className="h-4 w-4 shrink-0" />
                    {alert.text}
                    <Button
                      variant="ghost"
                      size="sm"
                      className="ml-auto h-7 text-xs"
                    >
                      Review
                    </Button>
                  </div>
                ))}
              </motion.div>
            )}

            <motion.div variants={item}>
              <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-muted-foreground">
                Quick Actions
              </h2>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
                {config.quickActions.map((action) => (
                  <motion.button
                    key={action.label}
                    whileHover={{ y: -2 }}
                    whileTap={{ scale: 0.97 }}
                    className="group flex flex-col items-center gap-2.5 rounded-xl border border-border/50 bg-card p-4 transition-all hover:border-primary/20 hover:shadow-md"
                  >
                    <div
                      className={`flex h-11 w-11 items-center justify-center rounded-xl transition-transform group-hover:scale-110 ${action.color}`}
                    >
                      <action.icon className="h-5 w-5" />
                    </div>
                    <span className="text-center text-xs font-semibold leading-tight text-foreground">
                      {action.label}
                    </span>
                  </motion.button>
                ))}
              </div>
            </motion.div>

            <div className="grid gap-6 lg:grid-cols-5">
              <motion.div variants={item} className="lg:col-span-3">
                <Card className="h-full border-border/60">
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <CardTitle className="flex items-center gap-2 text-base font-bold">
                        <CalendarDays className="h-4 w-4 text-primary" />{" "}
                        {config.queueTitle}
                      </CardTitle>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="gap-1 text-xs text-primary"
                      >
                        View All
                      </Button>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    {config.queueItems.map((entry, index) => (
                      <motion.div
                        key={`${entry.primary}-${entry.time}`}
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.3 + index * 0.06 }}
                        className="group flex items-center gap-3 rounded-xl px-3 py-2.5 transition-colors hover:bg-muted/40"
                      >
                        <div className="w-14 shrink-0 text-center">
                          <p className="text-xs font-bold text-foreground">
                            {entry.time}
                          </p>
                        </div>
                        <div className="h-8 w-px bg-border/60" />
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-semibold text-foreground">
                            {entry.primary}
                          </p>
                          <p className="text-[11px] text-muted-foreground">
                            {entry.secondary}
                          </p>
                        </div>
                        <span
                          className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold ${
                            entry.tone === "success"
                              ? "border-emerald-200 bg-emerald-100 text-emerald-700"
                              : entry.tone === "critical"
                              ? "border-rose-200 bg-rose-100 text-rose-700"
                              : "border-amber-200 bg-amber-100 text-amber-700"
                          }`}
                        >
                          {entry.status}
                        </span>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-7 text-xs opacity-0 transition-opacity group-hover:opacity-100"
                        >
                          {entry.action}
                        </Button>
                      </motion.div>
                    ))}
                  </CardContent>
                </Card>
              </motion.div>

              <motion.div variants={item} className="space-y-4 lg:col-span-2">
                <div className="grid grid-cols-2 gap-3">
                  {config.stats.map((stat) => (
                    <Card key={stat.label} className="border-border/60">
                      <CardContent className="p-4 text-center">
                        <div
                          className={`mx-auto mb-2 flex h-10 w-10 items-center justify-center rounded-xl ${stat.color}`}
                        >
                          <stat.icon className="h-5 w-5" />
                        </div>
                        <p className="text-xl font-extrabold text-foreground">
                          {stat.value}
                        </p>
                        <p className="text-[11px] text-muted-foreground">
                          {stat.label}
                        </p>
                      </CardContent>
                    </Card>
                  ))}
                </div>

                <Card className="border-border/60">
                  <CardHeader className="pb-2">
                    <CardTitle className="flex items-center gap-2 text-sm font-bold">
                      <Activity className="h-3.5 w-3.5 text-primary" /> Recent
                      Activity
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {config.recentActivity.map((activity) => (
                      <div
                        key={`${activity.action}-${activity.time}`}
                        className="flex items-start gap-3"
                      >
                        <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-muted">
                          <activity.icon className="h-3.5 w-3.5 text-muted-foreground" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="text-xs font-medium text-foreground">
                            {activity.action}
                          </p>
                          <p className="text-[11px] text-muted-foreground">
                            {activity.subject} · {activity.time}
                          </p>
                        </div>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              </motion.div>
            </div>

            <div className="grid gap-6 lg:grid-cols-[1.2fr_.8fr]">
              <motion.div variants={item}>
                <Card className="border-border/60">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base font-bold">
                      Access Scope
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="flex flex-wrap gap-2">
                      {config.accessModules.map((module) => (
                        <Badge key={module} variant="secondary">
                          {module}
                        </Badge>
                      ))}
                    </div>
                    <p className="mt-4 text-sm text-muted-foreground">
                      Access is scoped to your role within{" "}
                      <span className="font-medium text-foreground">
                        {workspace.facilityName}
                      </span>
                      .
                    </p>
                  </CardContent>
                </Card>
              </motion.div>

              <motion.div variants={item}>
                <Card className="border-border/60">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base font-bold">
                      Staff Profile
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3 text-sm">
                    <ProfileRow
                      label="Role"
                      value={getStaffRoleLabel(staff.role)}
                    />
                    <ProfileRow label="Department" value={staff.department} />
                    <ProfileRow label="Login ID" value={staff.loginId} />
                    <ProfileRow label="Facility" value={workspace.facilityName} />
                  </CardContent>
                </Card>
              </motion.div>
            </div>
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
  badge,
  onClick,
}: {
  icon: ElementType;
  label: string;
  active?: boolean;
  badge?: string;
  onClick?: () => void;
}) => (
  <button
    type="button"
    onClick={onClick}
    className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors ${
      active
        ? "bg-primary/10 text-primary"
        : "text-muted-foreground hover:bg-muted hover:text-foreground"
    }`}
  >
    <Icon className="h-4 w-4 shrink-0" />
    <span className="flex-1 text-left">{label}</span>
    {badge && (
      <span className="flex h-5 w-5 items-center justify-center rounded-full bg-destructive text-[10px] font-bold text-destructive-foreground">
        {badge}
      </span>
    )}
  </button>
);

const ProfileRow = ({ label, value }: { label: string; value: string }) => (
  <div className="flex items-center justify-between">
    <span className="text-muted-foreground">{label}</span>
    <span className="text-right font-medium text-foreground">{value}</span>
  </div>
);

export default StaffPortal;
