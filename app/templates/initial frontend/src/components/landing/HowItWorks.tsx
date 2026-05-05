import { motion } from "framer-motion";
import { UserPlus, Puzzle, Rocket } from "lucide-react";

const steps = [
  {
    icon: UserPlus,
    title: "Sign Up",
    desc: "Create your clinic or hospital profile in under 2 minutes.",
    step: "01",
  },
  {
    icon: Puzzle,
    title: "Choose Modules",
    desc: "Pick the features you need — OPD, Lab, Pharmacy, and more.",
    step: "02",
  },
  {
    icon: Rocket,
    title: "Go Live",
    desc: "Launch your HIS and start managing patients right away.",
    step: "03",
  },
];

const HowItWorks = () => (
  <section className="py-24">
    <div className="container mx-auto px-4">
      <div className="text-center max-w-2xl mx-auto mb-16">
        <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight">
          Launch Your HIS in{" "}
          <span className="text-gradient">3 Simple Steps</span>
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
            <div className="w-16 h-16 rounded-2xl gradient-hero flex items-center justify-center mx-auto mb-5 shadow-lg">
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
