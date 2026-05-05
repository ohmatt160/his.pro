import { useMemo, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { motion } from "framer-motion";
import {
  ArrowRight,
  Building2,
  CheckCircle2,
  Copy,
  ExternalLink,
  Globe,
  Link2,
  User,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { getFacilityLoginPath, getStaffAccessPath } from "@/lib/facility-staff";
import {
  getFacilityDashboardPath,
  getFacilityPlatformLink,
  getFacilityWorkspace,
  type SavedFacilityWorkspace,
} from "@/lib/facility-workspace";

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

const WorkspaceReady = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { facilitySlug = "" } = useParams();
  const routeState = (location.state as SavedFacilityWorkspace | null) || null;
  const storedWorkspace = facilitySlug
    ? getFacilityWorkspace(facilitySlug)
    : null;
  const workspace = routeState ?? storedWorkspace;
  const [copied, setCopied] = useState(false);

  const facilityLink = useMemo(
    () => getFacilityPlatformLink(facilitySlug),
    [facilitySlug]
  );
  const dashboardPath = getFacilityDashboardPath(facilitySlug);
  const staffAccessPath = getStaffAccessPath(facilitySlug);
  const facilityLoginPath = getFacilityLoginPath(facilitySlug);

  if (!workspace) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background px-4">
        <div className="max-w-md text-center">
          <h1 className="text-2xl font-extrabold tracking-tight text-foreground">
            Workspace not found
          </h1>
          <p className="mt-3 text-muted-foreground">
            We could not load the facility setup details for this link.
          </p>
          <Button
            className="gradient-cta mt-6 border-0 text-primary-foreground"
            onClick={() => navigate("/get-started", { replace: true })}
          >
            Go back to Get Started
          </Button>
        </div>
      </div>
    );
  }

  const copyLink = async () => {
    try {
      await navigator.clipboard.writeText(facilityLink);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      setCopied(false);
    }
  };

  return (
    <div className="relative min-h-screen overflow-hidden bg-background">
      <div className="pointer-events-none absolute inset-0 hero-pattern opacity-70" />
      <div className="pointer-events-none absolute right-0 top-0 h-[520px] w-[520px] translate-x-1/4 -translate-y-1/2 rounded-full bg-primary/8 blur-3xl" />
      <div className="pointer-events-none absolute bottom-0 left-0 h-[420px] w-[420px] -translate-x-1/4 translate-y-1/3 rounded-full bg-accent/8 blur-3xl" />

      <div className="relative z-10 container mx-auto px-4 py-16">
        <div className="mx-auto max-w-4xl">
          <motion.div
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            className="surface-panel overflow-hidden p-8 sm:p-10"
          >
            <div className="grid gap-8 lg:grid-cols-[1.08fr_.92fr] lg:items-start">
              <div>
                <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-accent/12 text-accent">
                  <CheckCircle2 className="h-7 w-7" />
                </div>
                <p className="mt-6 text-xs font-bold uppercase tracking-[0.24em] text-primary/80">
                  Workspace ready
                </p>
                <h1 className="mt-4 text-3xl font-extrabold tracking-tight text-foreground sm:text-4xl">
                  {workspace.facilityName} is now live on HIS.Pro
                </h1>
                <p className="mt-4 max-w-xl text-lg leading-relaxed text-muted-foreground">
                  Your facility workspace has been created. This is the access
                  link your organization will use on the platform.
                </p>

                <div className="mt-8 rounded-[1.5rem] border border-primary/12 bg-primary/[0.04] p-4 sm:p-5">
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0">
                      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-primary/75">
                        Facility login link
                      </p>
                      <p className="mt-3 break-all text-sm font-medium text-foreground sm:text-base">
                        {facilityLink}
                      </p>
                    </div>
                    <div className="hidden h-11 w-11 flex-shrink-0 items-center justify-center rounded-2xl bg-primary/10 text-primary sm:flex">
                      <Link2 className="h-5 w-5" />
                    </div>
                  </div>

                  <div className="mt-5 flex flex-wrap gap-3">
                    <Button
                      onClick={copyLink}
                      className="gradient-cta gap-2 border-0 text-primary-foreground"
                    >
                      <Copy className="h-4 w-4" />
                      {copied ? "Copied" : "Copy link"}
                    </Button>
                    <Button asChild variant="outline" className="gap-2">
                      <Link to={facilityLoginPath}>
                        Open login page <ExternalLink className="h-4 w-4" />
                      </Link>
                    </Button>
                  </div>
                </div>

                <p className="mt-5 text-sm leading-6 text-muted-foreground">
                  This is the shared entry point for your facility. Add staff
                  profiles first, then share this login page together with each
                  person's login ID and temporary password.
                </p>
              </div>

              <div className="surface-muted p-5 sm:p-6">
                <p className="text-xs font-bold uppercase tracking-[0.2em] text-primary/70">
                  Workspace details
                </p>
                <div className="mt-5 space-y-4 text-sm">
                  <DetailRow
                    icon={Building2}
                    label="Facility"
                    value={workspace.facilityName}
                  />
                  <DetailRow
                    icon={Globe}
                    label="Country"
                    value={workspace.country || "—"}
                  />
                  <DetailRow
                    icon={User}
                    label="Administrator"
                    value={workspace.fullName}
                  />
                </div>

                <div className="mt-6">
                  <p className="text-xs font-bold uppercase tracking-[0.2em] text-primary/70">
                    Active modules
                  </p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {workspace.selectedModules.map((moduleId) => (
                      <span
                        key={moduleId}
                        className="rounded-full bg-white px-3 py-1 text-xs font-medium text-foreground shadow-sm"
                      >
                        {moduleLabels[moduleId] || moduleId}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="mt-8 flex flex-col gap-3">
                  <Button
                    asChild
                    className="gradient-cta gap-2 border-0 text-primary-foreground"
                  >
                    <Link to={staffAccessPath}>
                      Set up staff access <ArrowRight className="h-4 w-4" />
                    </Link>
                  </Button>
                  <Button asChild variant="outline">
                    <Link to={dashboardPath} state={workspace}>
                      Continue to dashboard
                    </Link>
                  </Button>
                  <Button asChild variant="ghost">
                    <Link to="/">Back to landing page</Link>
                  </Button>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
};

const DetailRow = ({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
}) => (
  <div className="flex items-center justify-between gap-3">
    <span className="flex items-center gap-2 text-muted-foreground">
      <Icon className="h-4 w-4" />
      {label}
    </span>
    <span className="text-right font-medium text-foreground">{value}</span>
  </div>
);

export default WorkspaceReady;
