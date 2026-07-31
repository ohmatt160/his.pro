import { useEffect, useMemo, useState, type ElementType } from "react";
import { motion } from "framer-motion";
import { Link, useNavigate } from "react-router-dom";
import { useTenantParams } from "@/context/TenantRoutingContext";
import {
  Activity,
  ArrowUpRight,
  Bell,
  Building2,
  CalendarDays,
  ClipboardList,
  FlaskConical,
  Layers3,
  Pill,
  ShieldCheck,
  Stethoscope,
  UserPlus,
  Users,
} from "lucide-react";
import ClinicalPulse from "@/components/ClinicalPulse";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useAuth } from "@/context/AuthContext";
import {
  getBranchStaffAccessPath,
  getStaffAccessPath,
} from "@/lib/facility-staff";
import {
  getWorkspaceRoutePath,
  type SavedFacilityWorkspace,
} from "@/lib/facility-workspace";
import {
  getModuleById,
  normalizeModules,
  type FacilityModuleId,
} from "@/lib/modules";
import {
  useDashboardStatsQuery,
  useFacilityQuery,
  useWorkspaceQuery,
} from "@/hooks/useWorkspaceQueries";

type FacilityBranch = {
  id: string;
  name: string;
  slug?: string;
  modules?: string[];
};

type Metric = {
  label: string;
  value: number;
  detail: string;
  icon: ElementType;
  tone: "teal" | "blue" | "coral" | "amber";
};

type QuickAction = {
  label: string;
  description: string;
  icon: ElementType;
  to: string;
  module: FacilityModuleId;
};

const toneClasses: Record<Metric["tone"], string> = {
  teal: "bg-primary/10 text-primary",
  blue: "bg-[#168fb7]/10 text-[#168fb7]",
  coral: "bg-[#d84c3f]/10 text-[#d84c3f]",
  amber: "bg-amber-500/12 text-amber-700",
};

const pageMotion = {
  hidden: {},
  show: { transition: { staggerChildren: 0.055 } },
};

const sectionMotion = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0, transition: { duration: 0.32, ease: "easeOut" } },
};

const Dashboard = () => {
  const navigate = useNavigate();
  const { facilitySlug = "", branchSlug = "" } = useTenantParams();
  const { user } = useAuth();
  const [selectedBranchId, setSelectedBranchId] = useState("all");
  const workspaceQuery = useWorkspaceQuery(facilitySlug);
  const facilityQuery = useFacilityQuery(
    facilitySlug,
    Boolean(user && ["admin", "branch_admin"].includes(user.role)),
  );

  const facility = facilityQuery.data;
  const branches = useMemo<FacilityBranch[]>(() => {
    if (!facility || facility.hospital_type !== "multi_clinic") return [];
    return (facility.branches || facility.departments || []) as FacilityBranch[];
  }, [facility]);

  const routeBranch = useMemo(
    () =>
      branchSlug
        ? branches.find((branch) => branch.slug === branchSlug || branch.id === user?.branchId) || null
        : user?.branchId
          ? branches.find((branch) => branch.id === user.branchId) || null
          : null,
    [branchSlug, branches, user?.branchId],
  );

  const scopedBranchId = user?.branchId || (selectedBranchId !== "all" ? selectedBranchId : "");
  const { data: stats = null } = useDashboardStatsQuery(
    facilitySlug,
    scopedBranchId,
    Boolean(user),
  );

  useEffect(() => {
    if (
      facilitySlug &&
      workspaceQuery.isSuccess &&
      !workspaceQuery.data &&
      !facilityQuery.data
    ) {
      navigate(`/login/${facilitySlug}`, { replace: true });
    }
  }, [facilityQuery.data, facilitySlug, navigate, workspaceQuery.data, workspaceQuery.isSuccess]);

  if ((workspaceQuery.isPending || facilityQuery.isPending) && !workspaceQuery.data && !facility) {
    return (
      <main className="flex min-h-[calc(100vh-72px)] items-center justify-center bg-background px-4">
        <div className="text-center">
          <ClinicalPulse className="mx-auto w-48" />
          <p className="mt-3 text-sm font-semibold text-muted-foreground">Synchronizing clinical workspace...</p>
        </div>
      </main>
    );
  }

  const workspace: Partial<SavedFacilityWorkspace> = workspaceQuery.data || {};
  const activeModules = normalizeModules(
    routeBranch?.modules?.length
      ? routeBranch.modules
      : facility?.modules?.length
        ? facility.modules
        : workspace.selectedModules || [],
  );

  const branchContext = branchSlug || routeBranch?.slug || undefined;
  const route = (section: string) => getWorkspaceRoutePath(facilitySlug, section, branchContext);
  const facilityName = routeBranch
    ? `${routeBranch.name} / ${facility?.name || workspace.facilityName || "Facility"}`
    : facility?.name || workspace.facilityName || "Clinical workspace";
  const firstName = (user?.fullName || "Administrator").split(" ")[0];
  const today = new Intl.DateTimeFormat(undefined, {
    weekday: "long",
    day: "numeric",
    month: "long",
  }).format(new Date());

  const metrics: Metric[] = [
    { label: "Registered patients", value: stats?.patient_count ?? 0, detail: "Facility total", icon: Users, tone: "teal" },
    { label: "Appointments", value: stats?.today_appointments ?? 0, detail: "Scheduled today", icon: CalendarDays, tone: "blue" },
    { label: "Active queue", value: stats?.active_queue_count ?? 0, detail: "Waiting and in care", icon: Activity, tone: "amber" },
    { label: "Active alerts", value: stats?.active_alerts ?? 0, detail: "Needs review", icon: Bell, tone: "coral" },
  ];

  const staffPath = branchContext
    ? getBranchStaffAccessPath(facilitySlug, branchContext)
    : getStaffAccessPath(facilitySlug);

  const quickActionOptions: QuickAction[] = [
    { label: "Register patient", description: "Open patient registry", icon: UserPlus, to: route("patients"), module: "reception" },
    { label: "Reception queue", description: "Check in and route care", icon: ClipboardList, to: route("queue"), module: "reception" },
    { label: "Schedule visit", description: "Create an appointment", icon: CalendarDays, to: route("appointments"), module: "reception" },
    { label: "Consultations", description: "Open clinical encounters", icon: Stethoscope, to: route("consultations"), module: "consultations" },
    { label: "Laboratory", description: "Orders and results", icon: FlaskConical, to: route("laboratory"), module: "lab" },
    { label: "Pharmacy", description: "Prescriptions and dispense", icon: Pill, to: route("pharmacy"), module: "pharmacy" },
  ];
  const quickActions = quickActionOptions.filter((action) =>
    activeModules.includes(action.module),
  );

  const accessRows = [
    ["Role", user?.role?.replaceAll("_", " ") || "Not assigned"],
    ["Scope", routeBranch?.name || (user?.branchId ? "Assigned branch" : "Facility")],
    ["Modules", `${activeModules.length} active`],
  ];

  return (
    <main className="min-h-[calc(100vh-72px)] bg-background px-4 py-5 sm:px-6 sm:py-6 xl:px-8 xl:py-7">
      <motion.div
        variants={pageMotion}
        initial="hidden"
        animate="show"
        className="mx-auto max-w-[1600px] space-y-5"
      >
        <motion.header variants={sectionMotion} className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div className="min-w-0">
            <p className="v2-kicker">{today}</p>
            <h1 className="mt-1 text-2xl font-bold text-foreground sm:text-[28px]">Good day, {firstName}</h1>
            <p className="mt-1 truncate text-sm text-muted-foreground">{facilityName}</p>
          </div>
          {branches.length > 0 && user?.role === "admin" && (
            <div className="w-full md:w-72">
              <label className="v2-kicker mb-1.5 block" htmlFor="dashboard-branch-scope">Data scope</label>
              <Select value={selectedBranchId} onValueChange={setSelectedBranchId}>
                <SelectTrigger id="dashboard-branch-scope" className="h-10 bg-card">
                  <SelectValue placeholder="Select branch" />
                </SelectTrigger>
                <SelectContent className="max-h-72">
                  <SelectItem value="all">All branches</SelectItem>
                  {branches.map((branch) => (
                    <SelectItem key={branch.id} value={branch.id}>{branch.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}
        </motion.header>

        <motion.section variants={sectionMotion} className="v2-panel relative overflow-hidden bg-[#123331] px-4 py-4 text-white sm:px-5">
          <span className="clinical-scan-line absolute inset-y-0 left-0 w-px bg-[#2ed3b7]/70" />
          <div className="grid items-center gap-4 lg:grid-cols-[minmax(0,1.2fr)_minmax(300px,0.8fr)]">
            <div className="min-w-0">
              <div className="flex items-center gap-2 text-xs font-semibold text-[#73dfca]">
                <span className="h-1.5 w-1.5 animate-status-pulse rounded-full bg-[#73dfca]" />
                Clinical workspace live
              </div>
              <h2 className="mt-2 text-lg font-semibold">Care operations are synchronized</h2>
              <p className="mt-1 max-w-2xl text-sm leading-6 text-white/62">
                Patient flow, appointments, alerts, and enabled care modules are available within your assigned access scope.
              </p>
            </div>
            <div className="border-t border-white/10 pt-3 lg:border-l lg:border-t-0 lg:pl-6 lg:pt-0">
              <ClinicalPulse className="h-14" />
              <div className="mt-1 flex items-center justify-between text-[10px] font-semibold uppercase text-white/42">
                <span>Tenant isolated</span>
                <span>Realtime connected</span>
              </div>
            </div>
          </div>
        </motion.section>

        <motion.section variants={sectionMotion} className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {metrics.map((metric) => (
            <article key={metric.label} className="v2-panel min-w-0 p-4 sm:p-5">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="truncate text-xs font-medium text-muted-foreground">{metric.label}</p>
                  <p className="mt-2 text-2xl font-bold tabular-nums text-foreground sm:text-3xl">{metric.value.toLocaleString()}</p>
                  <p className="mt-1 truncate text-[11px] text-muted-foreground">{metric.detail}</p>
                </div>
                <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-md ${toneClasses[metric.tone]}`}>
                  <metric.icon className="h-[18px] w-[18px]" />
                </span>
              </div>
            </article>
          ))}
        </motion.section>

        <div className="grid gap-5 xl:grid-cols-[minmax(0,1.65fr)_minmax(320px,0.75fr)]">
          <div className="space-y-5">
            <motion.section variants={sectionMotion} className="v2-panel overflow-hidden">
              <div className="flex flex-col gap-3 border-b border-border px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-5">
                <div>
                  <p className="v2-kicker">Care access</p>
                  <h2 className="mt-1 text-base font-semibold text-foreground">Active clinical modules</h2>
                </div>
                <p className="text-xs text-muted-foreground">{activeModules.length} configured</p>
              </div>
              {activeModules.length ? (
                <div className="grid sm:grid-cols-2">
                  {activeModules.map((id, index) => {
                    const module = getModuleById(id);
                    const Icon = module?.icon || Layers3;
                    const path = route(module?.primaryPath || "");
                    return (
                      <Link
                        key={id}
                        to={path}
                        className={`group flex min-w-0 items-center gap-3 px-4 py-4 transition-colors hover:bg-muted/70 sm:px-5 ${index % 2 === 0 ? "sm:border-r" : ""} ${index < activeModules.length - 2 ? "border-b" : index < activeModules.length - 1 ? "border-b sm:border-b-0" : ""}`}
                      >
                        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-primary/[0.08] text-primary transition-colors group-hover:bg-primary group-hover:text-primary-foreground">
                          <Icon className="h-5 w-5" />
                        </span>
                        <span className="min-w-0 flex-1">
                          <span className="block truncate text-sm font-semibold text-foreground">{module?.label || id}</span>
                          <span className="mt-0.5 block text-xs text-muted-foreground">Open workspace</span>
                        </span>
                        <ArrowUpRight className="h-4 w-4 shrink-0 text-muted-foreground transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-primary" />
                      </Link>
                    );
                  })}
                </div>
              ) : (
                <div className="px-5 py-10 text-center text-sm text-muted-foreground">No clinical module is enabled for this workspace.</div>
              )}
            </motion.section>

            <motion.section variants={sectionMotion} className="v2-panel overflow-hidden">
              <div className="border-b border-border px-4 py-4 sm:px-5">
                <p className="v2-kicker">Flow monitor</p>
                <h2 className="mt-1 text-base font-semibold text-foreground">Today at a glance</h2>
              </div>
              <div className="grid divide-y divide-border sm:grid-cols-3 sm:divide-x sm:divide-y-0">
                <FlowMetric label="Scheduled" value={stats?.today_appointments ?? 0} icon={CalendarDays} />
                <FlowMetric label="In active queue" value={stats?.active_queue_count ?? 0} icon={ClipboardList} />
                <FlowMetric label="Open alerts" value={stats?.active_alerts ?? 0} icon={Bell} critical={Boolean(stats?.active_alerts)} />
              </div>
            </motion.section>
          </div>

          <div className="space-y-5">
            <motion.section variants={sectionMotion} className="v2-panel overflow-hidden">
              <div className="border-b border-border px-4 py-4 sm:px-5">
                <p className="v2-kicker">Direct actions</p>
                <h2 className="mt-1 text-base font-semibold text-foreground">Move care forward</h2>
              </div>
              <div className="divide-y divide-border">
                {quickActions.slice(0, 5).map((action) => (
                  <Link
                    key={action.label}
                    to={action.to}
                    className="group flex items-center gap-3 px-4 py-3.5 transition-colors hover:bg-muted/70 sm:px-5"
                  >
                    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-secondary text-foreground group-hover:bg-primary group-hover:text-primary-foreground">
                      <action.icon className="h-4 w-4" />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-semibold text-foreground">{action.label}</span>
                      <span className="block truncate text-xs text-muted-foreground">{action.description}</span>
                    </span>
                    <ArrowUpRight className="h-4 w-4 text-muted-foreground group-hover:text-primary" />
                  </Link>
                ))}
              </div>
            </motion.section>

            <motion.section variants={sectionMotion} className="v2-panel p-4 sm:p-5">
              <div className="flex items-center gap-3">
                <span className="flex h-10 w-10 items-center justify-center rounded-md bg-[#168fb7]/10 text-[#168fb7]">
                  <ShieldCheck className="h-5 w-5" />
                </span>
                <div>
                  <p className="v2-kicker">Access boundary</p>
                  <h2 className="mt-0.5 text-base font-semibold text-foreground">Current session</h2>
                </div>
              </div>
              <dl className="mt-4 divide-y divide-border border-y border-border">
                {accessRows.map(([label, value]) => (
                  <div key={label} className="flex items-center justify-between gap-4 py-3 text-sm">
                    <dt className="text-muted-foreground">{label}</dt>
                    <dd className="max-w-[60%] truncate text-right font-semibold capitalize text-foreground">{value}</dd>
                  </div>
                ))}
              </dl>
              {user?.role === "admin" || user?.role === "branch_admin" ? (
                <Button asChild variant="outline" className="mt-4 w-full justify-between">
                  <Link to={staffPath}>
                    Staff and permissions
                    <ArrowUpRight className="h-4 w-4" />
                  </Link>
                </Button>
              ) : null}
            </motion.section>

            <motion.section variants={sectionMotion} className="v2-panel-muted flex items-center gap-3 p-4">
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-card text-primary shadow-sm">
                <Building2 className="h-4 w-4" />
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-semibold text-foreground">{facilityName}</p>
                <p className="truncate text-xs text-muted-foreground">{facilitySlug}</p>
              </div>
            </motion.section>
          </div>
        </div>
      </motion.div>
    </main>
  );
};

const FlowMetric = ({
  label,
  value,
  icon: Icon,
  critical = false,
}: {
  label: string;
  value: number;
  icon: ElementType;
  critical?: boolean;
}) => (
  <div className="flex items-center gap-3 px-4 py-5 sm:px-5">
    <span className={`flex h-9 w-9 items-center justify-center rounded-md ${critical ? "bg-[#d84c3f]/10 text-[#d84c3f]" : "bg-primary/[0.08] text-primary"}`}>
      <Icon className="h-4 w-4" />
    </span>
    <div>
      <p className="text-xl font-bold tabular-nums text-foreground">{value.toLocaleString()}</p>
      <p className="text-xs text-muted-foreground">{label}</p>
    </div>
  </div>
);

export default Dashboard;
