import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Building2,
  FileText,
  Pill,
  FlaskConical,
  BarChart3,
  CreditCard,
  CalendarDays,
  Users,
} from "lucide-react";

const modules = [
  { id: "opd", icon: Building2, label: "OPD / IPD" },
  { id: "ehr", icon: FileText, label: "EHR" },
  { id: "pharmacy", icon: Pill, label: "Pharmacy" },
  { id: "lab", icon: FlaskConical, label: "Lab" },
  { id: "analytics", icon: BarChart3, label: "Analytics" },
  { id: "billing", icon: CreditCard, label: "Billing" },
  { id: "appointments", icon: CalendarDays, label: "Scheduling" },
  { id: "staff", icon: Users, label: "Staff Mgmt" },
];

const ModuleSelector = () => {
  const [selected, setSelected] = useState<string[]>(["opd", "ehr", "lab"]);

  const toggle = (id: string) => {
    setSelected((prev) =>
      prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id]
    );
  };

  return (
    <section id="modules" className="py-24 bg-muted/30">
      <div className="container mx-auto px-4">
        <div className="text-center max-w-2xl mx-auto mb-12">
          <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight">
            Choose the Modules{" "}
            <span className="text-gradient">You Need</span>
          </h2>
          <p className="mt-4 text-muted-foreground text-lg">
            Build your custom HIS by selecting only what matters to your facility.
          </p>
        </div>

        <div className="max-w-4xl mx-auto grid grid-cols-2 sm:grid-cols-4 gap-4 mb-10">
          {modules.map((m) => {
            const active = selected.includes(m.id);
            return (
              <motion.button
                key={m.id}
                whileTap={{ scale: 0.96 }}
                onClick={() => toggle(m.id)}
                className={`relative rounded-xl p-5 text-center transition-all duration-300 border ${
                  active
                    ? "bg-primary/10 border-primary/40 shadow-md"
                    : "bg-background border-border hover:border-primary/20"
                }`}
              >
                <m.icon className={`h-7 w-7 mx-auto mb-2 transition-colors ${active ? "text-primary" : "text-muted-foreground"}`} />
                <span className={`text-sm font-semibold ${active ? "text-foreground" : "text-muted-foreground"}`}>
                  {m.label}
                </span>
                {active && (
                  <motion.div
                    layoutId="module-check"
                    className="absolute top-2 right-2 w-5 h-5 rounded-full bg-accent flex items-center justify-center"
                  >
                    <span className="text-accent-foreground text-xs">✓</span>
                  </motion.div>
                )}
              </motion.button>
            );
          })}
        </div>

        {/* Preview */}
        <div className="max-w-3xl mx-auto glass-card rounded-2xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-3 h-3 rounded-full bg-destructive/60" />
            <div className="w-3 h-3 rounded-full bg-cta-warm/60" />
            <div className="w-3 h-3 rounded-full bg-accent/60" />
            <span className="ml-2 text-xs text-muted-foreground">Your Custom HIS Preview</span>
          </div>
          <div className="flex flex-wrap gap-2 mb-4">
            <AnimatePresence>
              {selected.map((id) => {
                const mod = modules.find((m) => m.id === id)!;
                return (
                  <motion.div
                    key={id}
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.8 }}
                    className="flex items-center gap-2 px-3 py-2 rounded-lg bg-primary/10"
                  >
                    <mod.icon className="h-4 w-4 text-primary" />
                    <span className="text-sm font-medium text-foreground">{mod.label}</span>
                  </motion.div>
                );
              })}
            </AnimatePresence>
          </div>
          {selected.length === 0 && (
            <p className="text-sm text-muted-foreground text-center py-4">
              Select modules above to preview your HIS setup
            </p>
          )}
          {selected.length > 0 && (
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {selected.map((id) => {
                const mod = modules.find((m) => m.id === id)!;
                return (
                  <div key={id} className="rounded-lg bg-muted/50 p-3 flex items-center gap-2">
                    <mod.icon className="h-4 w-4 text-primary" />
                    <div>
                      <p className="text-xs font-semibold text-foreground">{mod.label}</p>
                      <p className="text-xs text-muted-foreground">Active</p>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </section>
  );
};

export default ModuleSelector;
