import { motion } from "framer-motion";
import { UserPlus, Puzzle, Rocket } from "lucide-react";

const steps = [
  {
    icon: UserPlus,
    title: "Create the facility",
    desc: "Register the hospital owner and establish an isolated facility workspace.",
    step: "01",
  },
  {
    icon: Puzzle,
    title: "Configure operations",
    desc: "Enable the departments, branches, roles, and modules your team uses.",
    step: "02",
  },
  {
    icon: Rocket,
    title: "Verify and launch",
    desc: "Migrate approved data, train staff, run acceptance checks, then open clinical use.",
    step: "03",
  },
];

const HowItWorks = () => (
  <section id="workflow" className="scroll-mt-16 py-24">
    <div className="container mx-auto px-4">
      <div className="text-center max-w-2xl mx-auto mb-16">
        <h2 className="text-3xl font-extrabold sm:text-4xl">
          A controlled path from setup to clinical use
        </h2>
      </div>
      <div className="grid md:grid-cols-3 gap-8 max-w-4xl mx-auto">
        {steps.map((s, i) => (
          <motion.div
            key={s.step}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: i * 0.15, duration: 0.5 }}
            className="text-center relative"
          >
            <div className="text-6xl font-black text-primary/10 mb-4">{s.step}</div>
            <div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-lg bg-teal-800">
              <s.icon className="h-7 w-7 text-primary-foreground" />
            </div>
            <h3 className="text-xl font-bold text-foreground mb-2">{s.title}</h3>
            <p className="text-muted-foreground leading-relaxed">{s.desc}</p>
            {i < 2 && (
              <div className="hidden md:block absolute top-16 -right-4 w-8 text-primary/20 text-3xl">→</div>
            )}
          </motion.div>
        ))}
      </div>
    </div>
  </section>
);

export default HowItWorks;
