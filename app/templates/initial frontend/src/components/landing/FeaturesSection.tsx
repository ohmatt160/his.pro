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
  { icon: BarChart3, title: "Analytics & Reports", desc: "Operational dashboards and exportable reports for daily decisions." },
  { icon: ShieldCheck, title: "Role-Based Security", desc: "Tenant, branch, module, and role boundaries backed by audit trails." },
  { icon: CreditCard, title: "Billing & Payments", desc: "Create invoices, record payments, preserve receipts, and monitor balances." },
  { icon: CalendarDays, title: "Appointments & Queue", desc: "Coordinate bookings, arrival queues, consultation flow, and follow-up." },
];

const FeaturesSection = () => (
  <section id="features" className="scroll-mt-16 py-24">
    <div className="container mx-auto px-4">
      <div className="text-center max-w-2xl mx-auto mb-16">
        <h2 className="text-3xl font-extrabold sm:text-4xl">
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
            className="group rounded-lg border border-slate-200 bg-white p-6 shadow-sm transition-all duration-300 hover:-translate-y-1 hover:shadow-lg"
          >
            <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-teal-50 transition-colors group-hover:bg-teal-100">
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
