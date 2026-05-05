import { Button } from "@/components/ui/button";
import { Play, ArrowRight } from "lucide-react";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import heroMockupReplacement from "@/lib/assets/heromockupreplacement.jpg";

const HeroSection = () => {
  return (
    <section className="relative min-h-[96vh] overflow-hidden pt-24 lg:pt-20">
      <div className="absolute inset-0 bg-background" />
      <div className="absolute inset-y-0 right-0 w-full lg:w-[58%]">
        <div
          className="absolute inset-0 bg-cover bg-right bg-no-repeat opacity-95"
          style={{ backgroundImage: `url(${heroMockupReplacement})` }}
        />
        <div className="absolute inset-0 bg-[linear-gradient(180deg,hsl(var(--background)/0.78)_0%,hsl(var(--background)/0.46)_24%,hsl(var(--background)/0.58)_100%)] lg:bg-[linear-gradient(90deg,hsl(var(--background))_0%,hsl(var(--background)/0.9)_18%,hsl(var(--background)/0.66)_32%,hsl(var(--background)/0.22)_50%,transparent_70%)]" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_78%_22%,hsl(var(--primary)/0.1),transparent_28%),radial-gradient(circle_at_72%_78%,hsl(var(--accent)/0.1),transparent_32%)]" />
      </div>
      <div className="absolute inset-0 hero-pattern opacity-45" />

      <div className="absolute top-24 right-[8%] h-72 w-72 rounded-full bg-primary/8 blur-3xl" />
      <div className="absolute bottom-16 left-0 h-96 w-96 rounded-full bg-accent/8 blur-3xl" />

      <div className="container relative z-10 mx-auto px-4">
        <div className="flex min-h-[86vh] items-center">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7 }}
            className="max-w-xl pb-14 pt-10 lg:pb-20 lg:pt-16"
          >
            <div className="mb-6 inline-flex items-center rounded-full border border-white/60 bg-white/55 px-4 py-2 text-[0.68rem] font-bold uppercase tracking-[0.28em] text-primary shadow-[0_22px_45px_-28px_hsl(var(--foreground)/0.35)] backdrop-blur-xl">
              Modular Care Infrastructure
            </div>

            <h1 className="text-4xl font-extrabold leading-tight tracking-tight sm:text-5xl lg:text-6xl">
              Build Your Custom{" "}
              <span className="text-gradient">Health Information System</span>{" "}
              — In Minutes
            </h1>

            <p className="mt-6 max-w-lg text-lg leading-relaxed text-muted-foreground">
              Empower your clinic or hospital with a fully modular, cloud-powered
              HIS tailored to your needs. Select workflows, choose modules, and
              go live today.
            </p>

            <div className="mt-8 flex flex-wrap gap-4">
              <Button
                asChild
                size="lg"
                className="gradient-cta gap-2 border-0 px-8 text-base text-primary-foreground shadow-xl animate-pulse-glow"
              >
                <Link to="/get-started">
                  Start Free Trial <ArrowRight className="h-4 w-4" />
                </Link>
              </Button>
              <Button
                size="lg"
                variant="outline"
                className="gap-2 border-white/55 bg-white/45 px-8 text-base text-foreground backdrop-blur-md hover:bg-white/60"
              >
                <Play className="h-4 w-4" /> Watch Demo
              </Button>
            </div>

            <div className="mt-10 flex flex-wrap items-center gap-6 text-sm text-muted-foreground">
              <span className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-accent" /> No credit card required
              </span>
              <span className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-accent" /> Setup in 5 minutes
              </span>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
};

export default HeroSection;
