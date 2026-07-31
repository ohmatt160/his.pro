import { Button } from "@/components/ui/button";
import { ArrowRight } from "lucide-react";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";

const CTABanner = () => (
  <section id="contact" className="bg-slate-950 py-20 text-white">
    <div className="container mx-auto px-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        className="mx-auto max-w-4xl text-center"
      >
          <h2 className="mb-4 text-3xl font-extrabold sm:text-4xl">
            Prepare your facility for a controlled HIS.Pro launch
          </h2>
          <p className="mx-auto mb-8 max-w-2xl text-lg text-slate-300">
            Configure your workspace, validate migrated data, assign staff access,
            and complete the go-live checklist before clinical use.
          </p>
          <div className="flex flex-wrap justify-center gap-3">
            <Button asChild size="lg" className="gap-2 bg-emerald-500 px-8 text-slate-950 hover:bg-emerald-400">
              <Link to="/get-started">
                Start facility setup <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
            <Button asChild size="lg" variant="outline" className="border-slate-500 bg-transparent text-white hover:bg-white hover:text-slate-950">
              <Link to="/login">Open an existing workspace</Link>
            </Button>
          </div>
      </motion.div>
    </div>
  </section>
);

export default CTABanner;
