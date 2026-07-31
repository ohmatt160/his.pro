import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Menu, X } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { Link } from "react-router-dom";
import logo from "@/lib/assets/logo.png";

const navLinks = [
  { label: "Capabilities", href: "#features" },
  { label: "Modules", href: "#modules" },
  { label: "Workflow", href: "#workflow" },
  { label: "Deployment", href: "#deployment" },
];

const Navbar = () => {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <nav className="fixed inset-x-0 top-0 z-50 border-b border-slate-200 bg-white/95 shadow-sm backdrop-blur">
      <div className="container mx-auto flex h-16 items-center justify-between px-4">
          <Link to="/" className="flex items-center gap-2.5" aria-label="HIS.Pro home">
            <img src={logo} alt="" className="h-9 w-auto object-contain" />
            <span className="text-xl font-extrabold leading-none text-slate-950">HIS.Pro</span>
          </Link>

          <div className="hidden items-center gap-8 md:flex">
            {navLinks.map((link) => (
              <a
                key={link.href}
                href={link.href}
                className="text-sm font-medium text-slate-600 transition-colors hover:text-slate-950"
              >
                {link.label}
              </a>
            ))}
          </div>

          <div className="hidden items-center gap-3 md:flex">
            <Button asChild variant="ghost" size="sm">
              <Link to="/login">Open workspace</Link>
            </Button>
            <Button asChild size="sm" className="bg-emerald-600 text-white hover:bg-emerald-700">
              <Link to="/get-started">Start setup</Link>
            </Button>
          </div>

          <button
            type="button"
            className="rounded-md p-2 text-slate-700 transition-colors hover:bg-slate-100 md:hidden"
            onClick={() => setMobileOpen(!mobileOpen)}
            aria-expanded={mobileOpen}
            aria-controls="landing-mobile-menu"
            aria-label={mobileOpen ? "Close navigation" : "Open navigation"}
          >
            {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>

        <AnimatePresence>
          {mobileOpen && (
            <motion.div
              id="landing-mobile-menu"
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="absolute inset-x-0 top-16 overflow-hidden border-b border-slate-200 bg-white shadow-lg md:hidden"
            >
              <div className="container mx-auto flex flex-col gap-1 px-4 py-4">
                {navLinks.map((link) => (
                  <a
                    key={link.href}
                    href={link.href}
                    className="rounded-md px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
                    onClick={() => setMobileOpen(false)}
                  >
                    {link.label}
                  </a>
                ))}
                <Button asChild variant="outline" className="mt-2">
                  <Link to="/login" onClick={() => setMobileOpen(false)}>Open workspace</Link>
                </Button>
                <Button asChild className="mt-1 bg-emerald-600 text-white hover:bg-emerald-700">
                  <Link to="/get-started" onClick={() => setMobileOpen(false)}>Start setup</Link>
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
