import { Button } from "@/components/ui/button";
import { Activity, ArrowRight, Building2, Radio, ShieldCheck } from "lucide-react";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import heroMockupReplacement from "@/lib/assets/heromockupreplacement.jpg";

const HeroSection = () => {
  return (
    <section className="relative min-h-[88svh] overflow-hidden bg-slate-950 pt-16 text-white">
      <img
        src={heroMockupReplacement}
        alt=""
        className="absolute inset-0 h-full w-full object-cover object-center"
        aria-hidden="true"
      />
      <div className="absolute inset-0 bg-slate-950/75" />

      <div className="container relative z-10 mx-auto px-4">
        <div className="flex min-h-[calc(88svh-4rem)] items-center py-16">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7 }}
            className="max-w-3xl"
          >
            <div className="mb-6 inline-flex items-center gap-2 border-l-2 border-emerald-400 pl-3 text-sm font-semibold text-emerald-200">
              <Activity className="h-4 w-4" />
              Hospital operations, connected in real time
            </div>

            <h1 className="text-5xl font-extrabold leading-tight sm:text-6xl lg:text-7xl">
              HIS.Pro
            </h1>

            <p className="mt-5 max-w-2xl text-xl font-semibold leading-relaxed text-white sm:text-2xl">
              A secure clinical and operational workspace for hospitals, clinics,
              and multi-branch care teams.
            </p>
            <p className="mt-4 max-w-2xl text-base leading-relaxed text-slate-200 sm:text-lg">
              Coordinate registration, appointments, records, diagnostics,
              pharmacy, billing, inventory, and reporting without losing tenant
              or branch boundaries.
            </p>

            <div className="mt-8 flex flex-wrap gap-4">
              <Button
                asChild
                size="lg"
                className="gap-2 bg-emerald-500 px-7 text-base text-slate-950 hover:bg-emerald-400"
              >
                <Link to="/get-started">
                  Set up a facility <ArrowRight className="h-4 w-4" />
                </Link>
              </Button>
              <Button
                asChild
                size="lg"
                variant="outline"
                className="gap-2 border-white/60 bg-transparent px-7 text-base text-white hover:bg-white hover:text-slate-950"
              >
                <a href="#workflow">See the workflow</a>
              </Button>
            </div>

            <div className="mt-10 grid max-w-2xl gap-4 border-t border-white/25 pt-6 text-sm text-slate-100 sm:grid-cols-3">
              <span className="flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 text-emerald-300" />
                Tenant-isolated access
              </span>
              <span className="flex items-center gap-2">
                <Building2 className="h-4 w-4 text-cyan-300" />
                Branch-aware workflows
              </span>
              <span className="flex items-center gap-2">
                <Radio className="h-4 w-4 text-amber-300" />
                Live operational updates
              </span>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
};

export default HeroSection;
