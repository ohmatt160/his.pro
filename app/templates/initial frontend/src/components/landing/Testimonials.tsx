import { motion } from "framer-motion";
import { Star } from "lucide-react";

const testimonials = [
  {
    quote: "HIS.Pro transformed how we manage patient flow. Our waiting times dropped by 40% in the first month.",
    name: "Dr. Amina Yusuf",
    title: "Medical Director, City Clinic Lagos",
    initials: "AY",
  },
  {
    quote: "The modular approach is genius. We started with OPD and Pharmacy, then added Lab when we were ready.",
    name: "James Okonkwo",
    title: "Admin Manager, MedCare Kenya",
    initials: "JO",
  },
  {
    quote: "Finally, a system built for African healthcare realities. Fast, reliable, and affordable.",
    name: "Dr. Sarah Mensah",
    title: "CEO, HealthFirst Ghana",
    initials: "SM",
  },
];

const Testimonials = () => (
  <section className="py-24">
    <div className="container mx-auto px-4">
      <div className="text-center max-w-2xl mx-auto mb-16">
        <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight">
          What Healthcare Professionals{" "}
          <span className="text-gradient">Say</span>
        </h2>
      </div>
      <div className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto">
        {testimonials.map((t, i) => (
          <motion.div
            key={t.name}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: i * 0.1, duration: 0.4 }}
            className="glass-card rounded-xl p-6"
          >
            <div className="flex gap-1 mb-4">
              {[...Array(5)].map((_, j) => (
                <Star key={j} className="h-4 w-4 fill-cta-warm text-cta-warm" />
              ))}
            </div>
            <p className="text-foreground leading-relaxed mb-6 italic">"{t.quote}"</p>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full gradient-hero flex items-center justify-center text-primary-foreground text-sm font-bold">
                {t.initials}
              </div>
              <div>
                <p className="text-sm font-bold text-foreground">{t.name}</p>
                <p className="text-xs text-muted-foreground">{t.title}</p>
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  </section>
);

export default Testimonials;
