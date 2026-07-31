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
  Check,
  Users,
} from "lucide-react";

const modules = [
  { id: "reception", icon: Building2, label: "Reception" },
  { id: "records", icon: FileText, label: "Records" },
  { id: "pharmacy", icon: Pill, label: "Pharmacy" },
  { id: "lab", icon: FlaskConical, label: "Lab" },
  { id: "reports", icon: BarChart3, label: "Reports" },
  { id: "billing", icon: CreditCard, label: "Billing" },
  { id: "consultations", icon: CalendarDays, label: "Consultations" },
  { id: "nursing", icon: Users, label: "Nursing" },
];

const ModuleSelector = () => {
  const [selected, setSelected] = useState<string[]>(["reception", "records", "lab"]);

  const toggle = (id: string) => {
    setSelected((prev) =>
      prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id]
    );
  };

  return (
    <section id="modules" className="scroll-mt-16 bg-muted/30 py-24">
      <div className="container mx-auto px-4">
        <div className="text-center max-w-2xl mx-auto mb-12">
          <h2 className="text-3xl font-extrabold sm:text-4xl">
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
                aria-pressed={active}
                className={`relative min-h-28 rounded-lg border p-5 text-center transition-all duration-300 ${
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
                    className="absolute right-2 top-2 flex h-5 w-5 items-center justify-center rounded-full bg-accent"
                  >
                    <Check className="h-3 w-3 text-accent-foreground" />
                  </motion.div>
                )}
              </motion.button>
            );
          })}
        </div>

        <div className="mx-auto max-w-3xl border-t border-slate-300 pt-6">
          <p className="mb-4 text-sm font-semibold text-slate-700">Selected workspace modules</p>
          <div className="flex min-h-10 flex-wrap gap-2">
            <AnimatePresence>
              {selected.map((id) => {
                const mod = modules.find((m) => m.id === id)!;
                return (
                  <motion.div
                    key={id}
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.8 }}
                    className="flex items-center gap-2 rounded-md border border-teal-200 bg-white px-3 py-2"
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
        </div>
      </div>
    </section>
  );
};

export default ModuleSelector;
