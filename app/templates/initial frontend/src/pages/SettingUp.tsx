import { useCallback, useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Building2, CheckCircle2, Loader2, RotateCcw, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  type FacilityWorkspaceData,
  getFacilityReadyPath,
  saveFacilityWorkspace,
} from "@/lib/facility-workspace";

type SetupLocationState = FacilityWorkspaceData & {
  adminPassword?: string;
  onboardingToken?: string;
};

const SettingUp = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const setupData = location.state as SetupLocationState | null;
  const inFlight = useRef(false);
  const redirectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [status, setStatus] = useState<"working" | "done" | "error">("working");
  const [error, setError] = useState("");

  const createWorkspace = useCallback(async () => {
    if (!setupData || inFlight.current) {
      return;
    }

    inFlight.current = true;
    setStatus("working");
    setError("");

    try {
      const workspace = await saveFacilityWorkspace(
        setupData,
        setupData.onboardingToken
      );
      setStatus("done");
      redirectTimer.current = setTimeout(() => {
        navigate(getFacilityReadyPath(workspace.facilitySlug), {
          replace: true,
          state: workspace,
        });
      }, 700);
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : "The facility workspace could not be created."
      );
      setStatus("error");
      inFlight.current = false;
    }
  }, [navigate, setupData]);

  useEffect(() => {
    if (!setupData) {
      navigate("/get-started", { replace: true });
      return;
    }

    void createWorkspace();
    return () => {
      if (redirectTimer.current) {
        clearTimeout(redirectTimer.current);
      }
    };
  }, [createWorkspace, navigate, setupData]);

  return (
    <main className="flex min-h-screen items-center justify-center bg-background px-6 py-12">
      <motion.section
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-lg border-y border-border py-12 text-center"
        aria-live="polite"
      >
        {status === "working" && (
          <>
            <div className="relative mx-auto mb-7 flex h-20 w-20 items-center justify-center rounded-full border border-primary/25 bg-primary/5">
              <Loader2 className="h-9 w-9 animate-spin text-primary" aria-hidden="true" />
            </div>
            <p className="mb-3 text-sm font-semibold uppercase text-primary">
              Secure onboarding
            </p>
            <h1 className="mb-3 text-3xl font-extrabold text-foreground">
              Creating {setupData?.facilityName || "your facility"}
            </h1>
            <p className="mx-auto max-w-md text-muted-foreground">
              HIS.Pro is creating the facility and administrator together, then
              applying the selected modules. You can leave this tab open.
            </p>
            <div className="mx-auto mt-8 flex max-w-sm items-center justify-center gap-2 border-t border-border pt-5 text-sm text-muted-foreground">
              <ShieldCheck className="h-4 w-4 text-primary" aria-hidden="true" />
              No workspace is exposed until setup completes.
            </div>
          </>
        )}

        {status === "done" && (
          <>
            <div className="mx-auto mb-7 flex h-20 w-20 items-center justify-center rounded-full bg-emerald-600 text-white">
              <CheckCircle2 className="h-10 w-10" aria-hidden="true" />
            </div>
            <h1 className="mb-3 text-3xl font-extrabold text-foreground">
              Workspace created
            </h1>
            <p className="text-muted-foreground">
              Your administrator access is ready. Opening the secure workspace now.
            </p>
          </>
        )}

        {status === "error" && (
          <>
            <div className="mx-auto mb-7 flex h-20 w-20 items-center justify-center rounded-full border border-destructive/30 bg-destructive/5">
              <Building2 className="h-9 w-9 text-destructive" aria-hidden="true" />
            </div>
            <h1 className="mb-3 text-3xl font-extrabold text-foreground">
              Setup needs attention
            </h1>
            <p className="mx-auto max-w-md text-muted-foreground">{error}</p>
            <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
              <Button variant="outline" onClick={() => navigate("/get-started", { replace: true })}>
                Review details
              </Button>
              <Button onClick={() => void createWorkspace()} className="gap-2">
                <RotateCcw className="h-4 w-4" aria-hidden="true" />
                Retry setup
              </Button>
            </div>
          </>
        )}
      </motion.section>
    </main>
  );
};

export default SettingUp;
