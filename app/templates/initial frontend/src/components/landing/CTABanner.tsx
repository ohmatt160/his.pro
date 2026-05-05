import { Button } from "@/components/ui/button";
import { ArrowRight } from "lucide-react";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";

const CTABanner = () => (
  <section className="py-24">
    <div className="container mx-auto px-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        className="gradient-hero rounded-3xl p-12 sm:p-16 text-center relative overflow-hidden"
      >
        <div className="absolute inset-0 opacity-10">
          <div className="absolute top-10 left-10 w-40 h-40 rounded-full border-2 border-primary-foreground/30" />
          <div className="absolute bottom-10 right-20 w-60 h-60 rounded-full border border-primary-foreground/20" />
        </div>
        <div className="relative z-10">
          <h2 className="text-3xl sm:text-4xl font-extrabold text-primary-foreground mb-4">
            Ready to digitize your facility?
          </h2>
          <p className="text-primary-foreground/80 text-lg max-w-lg mx-auto mb-8">
            Start your free trial today and go live in under 10 minutes. No credit card required.
          </p>
          <Button
            asChild
            size="lg"
            className="gradient-cta text-primary-foreground border-0 shadow-xl gap-2 text-base px-10 animate-pulse-glow"
          >
            <Link to="/get-started">
              Start Free Trial <ArrowRight className="h-4 w-4" />
            </Link>
          </Button>
        </div>
      </motion.div>
    </div>
  </section>
);

export default CTABanner;
