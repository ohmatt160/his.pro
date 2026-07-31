import { motion } from "framer-motion";
import { CreditCard, FlaskConical, Stethoscope } from "lucide-react";

const careTeams = [
  {
    icon: Stethoscope,
    team: "Clinical team",
    workflow: "Review the patient timeline, document encounters, order diagnostics, and follow results from one patient context.",
  },
  {
    icon: FlaskConical,
    team: "Diagnostics and pharmacy",
    workflow: "Receive authorized orders, update fulfillment status, and return results or dispensing activity to the care team.",
  },
  {
    icon: CreditCard,
    team: "Reception and billing",
    workflow: "Register patients once, coordinate appointments and queues, issue invoices, and record traceable payments.",
  },
];

const Testimonials = () => (
  <section className="py-24">
    <div className="container mx-auto px-4">
      <div className="text-center max-w-2xl mx-auto mb-16">
        <h2 className="text-3xl font-extrabold sm:text-4xl">
          One patient journey, clear responsibilities
        </h2>
      </div>
      <div className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto">
        {careTeams.map((item, i) => (
          <motion.div
            key={item.team}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: i * 0.1, duration: 0.4 }}
            className="border-t-2 border-teal-700 px-1 py-6"
          >
            <item.icon className="mb-5 h-7 w-7 text-teal-700" />
            <h3 className="mb-3 text-lg font-bold text-foreground">{item.team}</h3>
            <p className="leading-relaxed text-muted-foreground">{item.workflow}</p>
          </motion.div>
        ))}
      </div>
    </div>
  </section>
);

export default Testimonials;
