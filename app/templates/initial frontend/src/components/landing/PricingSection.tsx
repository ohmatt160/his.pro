import { Button } from "@/components/ui/button";
import { Building2, Check, GitBranch, Stethoscope } from "lucide-react";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";

const deploymentPaths = [
  {
    icon: Stethoscope,
    name: "Clinic",
    desc: "A focused workspace for outpatient care and lean operating teams.",
    features: ["Patient registration and queue", "Consultations and records", "Billing and pharmacy modules"],
    highlight: false,
  },
  {
    icon: Building2,
    name: "Hospital",
    desc: "Connected clinical, diagnostic, pharmacy, and revenue operations.",
    features: ["Department-based staff access", "Lab, radiology, wards, and inventory", "Operational reports and audit review"],
    highlight: true,
  },
  {
    icon: GitBranch,
    name: "Multi-branch network",
    desc: "One tenant with explicit branch membership and configurable modules.",
    features: ["Branch-aware access controls", "Per-branch module configuration", "Central administration and reporting"],
    highlight: false,
  },
];

const PricingSection = () => (
    <section id="deployment" className="scroll-mt-16 bg-slate-100 py-24">
      <div className="container mx-auto px-4">
        <div className="text-center max-w-2xl mx-auto mb-12">
          <h2 className="text-3xl font-extrabold sm:text-4xl">
            Choose the operating model that fits your facility
          </h2>
          <p className="mt-4 text-muted-foreground text-lg">
            Module selection, migration scope, training, and infrastructure are
            confirmed during launch planning.
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto">
          {deploymentPaths.map((plan, i) => (
            <motion.div
              key={plan.name}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1, duration: 0.4 }}
              className={`relative rounded-lg border p-8 ${
                plan.highlight
                  ? "border-teal-700 bg-teal-900 text-white shadow-xl"
                  : "border-slate-200 bg-white text-slate-950 shadow-sm"
              }`}
            >
              <plan.icon className={`mb-5 h-7 w-7 ${plan.highlight ? "text-emerald-300" : "text-teal-700"}`} />
              <h3 className={`text-xl font-bold mb-1 ${plan.highlight ? "" : "text-foreground"}`}>{plan.name}</h3>
              <p className={`text-sm mb-6 ${plan.highlight ? "opacity-80" : "text-muted-foreground"}`}>{plan.desc}</p>
              <ul className="space-y-3 mb-8">
                {plan.features.map((f) => (
                  <li key={f} className="flex items-center gap-2 text-sm">
                    <Check className={`h-4 w-4 flex-shrink-0 ${plan.highlight ? "text-emerald-300" : "text-emerald-600"}`} />
                    <span className={plan.highlight ? "opacity-90" : "text-foreground"}>{f}</span>
                  </li>
                ))}
              </ul>
              <Button
                asChild
                className={`w-full ${
                  plan.highlight
                    ? "bg-white text-teal-950 hover:bg-slate-100"
                    : "bg-emerald-600 text-white hover:bg-emerald-700"
                }`}
              >
                <Link to="/get-started">Plan this deployment</Link>
              </Button>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
);

export default PricingSection;
