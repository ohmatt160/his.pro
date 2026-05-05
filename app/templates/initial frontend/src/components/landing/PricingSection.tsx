import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Check } from "lucide-react";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";

const plans = [
  {
    name: "Starter",
    monthly: 29,
    yearly: 23,
    desc: "Perfect for small clinics getting started",
    features: ["Up to 3 modules", "1 location", "Basic support", "500 patient records", "Email notifications"],
    highlight: false,
  },
  {
    name: "Professional",
    monthly: 79,
    yearly: 63,
    desc: "For growing facilities that need more power",
    features: ["Up to 8 modules", "3 locations", "Priority support", "Unlimited records", "SMS & Email alerts", "API access", "Custom reports"],
    highlight: true,
  },
  {
    name: "Enterprise",
    monthly: null,
    yearly: null,
    desc: "For hospital networks with custom requirements",
    features: ["Unlimited modules", "Unlimited locations", "Dedicated SLA", "Custom integrations", "On-premise option", "Training & onboarding", "24/7 support"],
    highlight: false,
  },
];

const PricingSection = () => {
  const [yearly, setYearly] = useState(false);

  return (
    <section id="pricing" className="py-24 bg-muted/30">
      <div className="container mx-auto px-4">
        <div className="text-center max-w-2xl mx-auto mb-12">
          <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight">
            Simple, <span className="text-gradient">Transparent Pricing</span>
          </h2>
          <p className="mt-4 text-muted-foreground text-lg">
            Start free. Scale as you grow.
          </p>

          <div className="flex items-center justify-center gap-3 mt-8">
            <span className={`text-sm font-medium ${!yearly ? "text-foreground" : "text-muted-foreground"}`}>Monthly</span>
            <button
              onClick={() => setYearly(!yearly)}
              className={`relative w-12 h-6 rounded-full transition-colors ${yearly ? "bg-primary" : "bg-border"}`}
            >
              <div className={`absolute top-0.5 w-5 h-5 rounded-full bg-primary-foreground shadow transition-transform ${yearly ? "translate-x-6" : "translate-x-0.5"}`} />
            </button>
            <span className={`text-sm font-medium ${yearly ? "text-foreground" : "text-muted-foreground"}`}>
              Yearly <span className="text-accent text-xs font-bold ml-1">Save 20%</span>
            </span>
          </div>
        </div>

        <div className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto">
          {plans.map((plan, i) => (
            <motion.div
              key={plan.name}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1, duration: 0.4 }}
              className={`rounded-2xl p-8 relative ${
                plan.highlight
                  ? "gradient-hero text-primary-foreground shadow-2xl scale-105"
                  : "glass-card"
              }`}
            >
              {plan.highlight && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-4 py-1 rounded-full bg-accent text-accent-foreground text-xs font-bold">
                  Recommended
                </div>
              )}
              <h3 className={`text-xl font-bold mb-1 ${plan.highlight ? "" : "text-foreground"}`}>{plan.name}</h3>
              <p className={`text-sm mb-6 ${plan.highlight ? "opacity-80" : "text-muted-foreground"}`}>{plan.desc}</p>
              <div className="mb-6">
                {plan.monthly ? (
                  <>
                    <span className="text-4xl font-extrabold">${yearly ? plan.yearly : plan.monthly}</span>
                    <span className={`text-sm ml-1 ${plan.highlight ? "opacity-70" : "text-muted-foreground"}`}>/month</span>
                  </>
                ) : (
                  <span className="text-4xl font-extrabold">Custom</span>
                )}
              </div>
              <ul className="space-y-3 mb-8">
                {plan.features.map((f) => (
                  <li key={f} className="flex items-center gap-2 text-sm">
                    <Check className={`h-4 w-4 flex-shrink-0 ${plan.highlight ? "text-accent" : "text-accent"}`} />
                    <span className={plan.highlight ? "opacity-90" : "text-foreground"}>{f}</span>
                  </li>
                ))}
              </ul>
              {plan.monthly ? (
                <Button
                  asChild
                  className={`w-full ${
                    plan.highlight
                      ? "bg-primary-foreground text-primary hover:bg-primary-foreground/90"
                      : "gradient-cta text-primary-foreground border-0"
                  }`}
                >
                  <Link to="/get-started">Start Free Trial</Link>
                </Button>
              ) : (
                <Button
                  className={`w-full ${
                    plan.highlight
                      ? "bg-primary-foreground text-primary hover:bg-primary-foreground/90"
                      : "gradient-cta text-primary-foreground border-0"
                  }`}
                >
                  Contact Sales
                </Button>
              )}
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default PricingSection;
