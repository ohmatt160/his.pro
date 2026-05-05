import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Menu, X } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { Link } from "react-router-dom";
import logo from "@/lib/assets/logo.png";

const navLinks = ["Features", "Modules", "Pricing", "Blog", "Contact"];

const Navbar = () => {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <nav className="fixed inset-x-0 top-4 z-50 px-4">
      <div className="relative mx-auto max-w-6xl overflow-hidden rounded-[1.75rem] border border-white/50 bg-white/20 shadow-[0_28px_90px_-48px_hsl(var(--foreground)/0.55)] backdrop-blur-2xl">
        <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(135deg,hsl(0_0%_100%_/_0.52),hsl(0_0%_100%_/_0.16)_40%,hsl(var(--primary)_/_0.08)_100%)]" />
        <div className="pointer-events-none absolute inset-x-12 top-0 h-px bg-white/90" />
        <div className="pointer-events-none absolute -left-12 top-[-120%] h-40 w-56 rounded-full bg-white/60 blur-3xl" />
        <div className="pointer-events-none absolute -right-20 bottom-[-140%] h-52 w-64 rounded-full bg-primary/10 blur-3xl" />

        <div className="relative flex h-16 items-center justify-between px-4 sm:px-5 lg:px-6">
          <a href="#" className="flex items-center gap-2.5">
            <img src={logo} alt="HIS.Pro" className="h-10 w-auto object-contain" />
            <span className="text-2xl font-extrabold leading-none tracking-tight">
              <span className="text-gradient">HIS</span>
              <span className="text-foreground">.Pro</span>
            </span>
          </a>

          <div className="hidden items-center gap-8 md:flex">
            {navLinks.map((link) => (
              <a
                key={link}
                href={`#${link.toLowerCase()}`}
                className="text-sm font-medium text-foreground/70 transition-colors hover:text-foreground"
              >
                {link}
              </a>
            ))}
          </div>

          <div className="hidden items-center gap-3 md:flex">
            <Button
              variant="ghost"
              size="sm"
              className="text-foreground/70 hover:bg-white/20 hover:text-foreground"
            >
              Book a Demo
            </Button>
            <Button
              asChild
              size="sm"
              className="gradient-cta border-0 text-primary-foreground shadow-lg animate-pulse-glow"
            >
              <Link to="/get-started">Get Started</Link>
            </Button>
          </div>

          <button
            className="rounded-full p-2 text-foreground/80 transition-colors hover:bg-white/20 md:hidden"
            onClick={() => setMobileOpen(!mobileOpen)}
          >
            {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>

        <AnimatePresence>
          {mobileOpen && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="relative overflow-hidden border-t border-white/20 bg-white/12 md:hidden"
            >
              <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(180deg,hsl(0_0%_100%_/_0.18),transparent)] backdrop-blur-2xl" />
              <div className="relative flex flex-col gap-3 px-4 py-4">
                {navLinks.map((link) => (
                  <a
                    key={link}
                    href={`#${link.toLowerCase()}`}
                    className="rounded-xl px-3 py-2 text-sm font-medium text-foreground/75 transition-colors hover:bg-white/15 hover:text-foreground"
                    onClick={() => setMobileOpen(false)}
                  >
                    {link}
                  </a>
                ))}
                <Button asChild className="gradient-cta mt-2 border-0 text-primary-foreground">
                  <Link to="/get-started">Get Started</Link>
                </Button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </nav>
  );
};

export default Navbar;
