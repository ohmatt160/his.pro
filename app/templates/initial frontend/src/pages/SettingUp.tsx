import { useEffect, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  LayoutDashboard,
  Database,
  ShieldCheck,
  Layers,
  Settings,
  Sparkles,
  CheckCircle2,
} from "lucide-react";
import {
  type FacilityWorkspaceData,
  getFacilityReadyPath,
  saveFacilityWorkspace,
} from "@/lib/facility-workspace";
import { ensureAdminStaffAccount } from "@/lib/facility-staff";

const steps = [
  { icon: Database, label: "Setting up your database", sub: "Creating tables & schemas…" },
  { icon: Layers, label: "Arranging your modules", sub: "Reception, records, billing, pharmacy…" },
  { icon: Settings, label: "Configuring workflows", sub: "Customizing to your facility…" },
  { icon: ShieldCheck, label: "Applying security policies", sub: "HIPAA-ready encryption…" },
  { icon: LayoutDashboard, label: "Building your dashboard", sub: "Laying out widgets & analytics…" },
  { icon: Sparkles, label: "Final touches", sub: "Almost there…" },
];

const SettingUp = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const setupData = location.state as
    | (FacilityWorkspaceData & { adminPassword?: string })
    | null;

  const [active, setActive] = useState(0);
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (!setupData) {
      navigate("/get-started", { replace: true });
      return;
    }

    const interval = setInterval(() => {
      setActive((prev) => {
        if (prev >= steps.length - 1) {
          clearInterval(interval);
          setTimeout(() => {
            setDone(true);
            const { adminPassword, ...workspaceInput } = setupData;
            const workspace = saveFacilityWorkspace(workspaceInput);

            ensureAdminStaffAccount({
              facilitySlug: workspace.facilitySlug,
              fullName: workspace.fullName,
              email: workspace.email,
              phone: workspace.phone,
              password: adminPassword,
            });

            setTimeout(() => {
              navigate(getFacilityReadyPath(workspace.facilitySlug), {
                replace: true,
                state: workspace,
              });
            }, 1600);
          }, 600);
          return prev;
        }
        return prev + 1;
      });
    }, 1200);
    return () => clearInterval(interval);
  }, [navigate, setupData]);

  const progress = ((active + 1) / steps.length) * 100;

  return (
    <div className="min-h-screen bg-background flex items-center justify-center relative overflow-hidden">
      {/* Animated bg blobs */}
      <motion.div
        className="absolute w-[500px] h-[500px] rounded-full bg-primary/5 blur-3xl"
        animate={{ x: [0, 40, 0], y: [0, -30, 0] }}
        transition={{ duration: 8, repeat: Infinity }}
        style={{ top: "-10%", right: "-5%" }}
      />
      <motion.div
        className="absolute w-[400px] h-[400px] rounded-full bg-accent/5 blur-3xl"
        animate={{ x: [0, -30, 0], y: [0, 40, 0] }}
        transition={{ duration: 10, repeat: Infinity }}
        style={{ bottom: "-10%", left: "-5%" }}
      />

      <div className="relative z-10 w-full max-w-lg px-6 text-center">
        <AnimatePresence mode="wait">
          {!done ? (
            <motion.div key="loading" exit={{ opacity: 0, scale: 0.95 }}>
              {/* Spinner ring */}
              <div className="mx-auto mb-8 relative w-24 h-24">
                <motion.div
                  className="absolute inset-0 rounded-full border-4 border-primary/20"
                  style={{ borderTopColor: "hsl(var(--primary))" }}
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                />
                <div className="absolute inset-0 flex items-center justify-center">
                  <motion.div
                    key={active}
                    initial={{ scale: 0, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    exit={{ scale: 0, opacity: 0 }}
                    transition={{ type: "spring", stiffness: 300 }}
                  >
                    {(() => {
                      const Icon = steps[active].icon;
                      return <Icon className="h-8 w-8 text-primary" />;
                    })()}
                  </motion.div>
                </div>
              </div>

              <h1 className="text-2xl font-extrabold tracking-tight mb-2 text-foreground">
                Setting up your <span className="text-gradient">HIS</span>
              </h1>

              {/* Active step label */}
              <AnimatePresence mode="wait">
                <motion.div
                  key={active}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="mb-8"
                >
                  <p className="text-foreground font-medium">{steps[active].label}</p>
                  <p className="text-sm text-muted-foreground">{steps[active].sub}</p>
                </motion.div>
              </AnimatePresence>

              {/* Progress bar */}
              <div className="w-full h-2 rounded-full bg-muted overflow-hidden mb-6">
                <motion.div
                  className="h-full rounded-full gradient-cta"
                  animate={{ width: `${progress}%` }}
                  transition={{ duration: 0.5, ease: "easeOut" }}
                />
              </div>

              {/* Steps checklist */}
              <div className="space-y-2 text-left">
                {steps.map((step, i) => {
                  const Icon = step.icon;
                  const isActive = i === active;
                  const isDone = i < active;
                  return (
                    <motion.div
                      key={i}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.1 }}
                      className={`flex items-center gap-3 px-4 py-2.5 rounded-xl transition-all duration-300 ${
                        isActive
                          ? "bg-primary/10 border border-primary/20"
                          : isDone
                          ? "opacity-60"
                          : "opacity-30"
                      }`}
                    >
                      {isDone ? (
                        <CheckCircle2 className="h-5 w-5 text-accent shrink-0" />
                      ) : (
                        <Icon className={`h-5 w-5 shrink-0 ${isActive ? "text-primary" : "text-muted-foreground"}`} />
                      )}
                      <div>
                        <p className={`text-sm font-medium ${isDone ? "line-through text-muted-foreground" : "text-foreground"}`}>
                          {step.label}
                        </p>
                      </div>
                      {isActive && (
                        <motion.div
                          className="ml-auto h-2 w-2 rounded-full bg-primary"
                          animate={{ scale: [1, 1.4, 1] }}
                          transition={{ duration: 1, repeat: Infinity }}
                        />
                      )}
                    </motion.div>
                  );
                })}
              </div>
            </motion.div>
          ) : (
            <motion.div
              key="done"
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ type: "spring", stiffness: 200 }}
              className="flex flex-col items-center"
            >
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ type: "spring", delay: 0.1 }}
                className="w-20 h-20 rounded-full gradient-cta flex items-center justify-center mb-6 shadow-xl"
              >
                <CheckCircle2 className="h-10 w-10 text-primary-foreground" />
              </motion.div>
              <h1 className="text-3xl font-extrabold tracking-tight mb-2 text-foreground">
                You're all set! 🎉
              </h1>
              <p className="text-muted-foreground">Preparing your facility access link…</p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};

export default SettingUp;
