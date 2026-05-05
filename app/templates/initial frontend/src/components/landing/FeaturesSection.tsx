import { motion } from "framer-motion";
import {
  Building2,
  FileText,
  Pill,
  FlaskConical,
  BarChart3,
  ShieldCheck,
  CreditCard,
  CalendarDays,
} from "lucide-react";

const features = [
  { icon: Building2, title: "OPD & IPD Management", desc: "Streamline outpatient and inpatient workflows with smart queuing and bed management." },
  { icon: FileText, title: "Electronic Health Records", desc: "Comprehensive digital patient records accessible across departments instantly." },
  { icon: Pill, title: "Pharmacy Management", desc: "Track inventory, manage prescriptions, and automate dispensing workflows." },
  { icon: FlaskConical, title: "Lab & Diagnostics", desc: "Order tests, track samples, and deliver results digitally to clinicians." },
  { icon: BarChart3, title: "Analytics & Reports", desc: "Real-time dashboards and exportable reports for data-driven decisions." },
  { icon: ShieldCheck, title: "Role-Based Security", desc: "Granular access controls ensuring data privacy and regulatory compliance." },
  { icon: CreditCard, title: "Billing & Insurance", desc: "Automated invoicing, insurance claims processing, and payment tracking." },
  { icon: CalendarDays, title: "Appointments & Scheduling", desc: "Online booking, automated reminders, and calendar management." },
];

const FeaturesSection = () => (
  <section id="features" className="py-24 relative">
    <div className="absolute inset-0 hero-pattern opacity-50" />
    <div className="container mx-auto px-4 relative z-10">
      <div className="text-center max-w-2xl mx-auto mb-16">
        <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight">
          Everything You Need to Run a{" "}
          <span className="text-gradient">Modern Health Facility</span>
        </h2>
        <p className="mt-4 text-muted-foreground text-lg">
          From patient check-in to lab results — HIS.Pro covers it.
        </p>
      </div>
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {features.map((f, i) => (
          <motion.div
            key={f.title}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: i * 0.05, duration: 0.4 }}
            className="glass-card rounded-xl p-6 hover:shadow-xl hover:-translate-y-1 transition-all duration-300 group cursor-default"
          >
            <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center mb-4 group-hover:bg-primary/20 transition-colors">
              <f.icon className="h-6 w-6 text-primary" />
            </div>
            <h3 className="font-bold text-foreground mb-2">{f.title}</h3>
            <p className="text-sm text-muted-foreground leading-relaxed">{f.desc}</p>
          </motion.div>
        ))}
      </div>
    </div>
  </section>
);

export default FeaturesSection;
