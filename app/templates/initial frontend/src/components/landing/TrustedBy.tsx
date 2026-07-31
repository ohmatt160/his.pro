import { Building2, Radio, ShieldCheck, Workflow } from "lucide-react";

const operatingPrinciples = [
  { icon: ShieldCheck, label: "Tenant and branch permission boundaries" },
  { icon: Radio, label: "Realtime workflow notifications" },
  { icon: Building2, label: "Single-site and multi-branch operation" },
  { icon: Workflow, label: "Connected clinical and revenue workflows" },
];

const TrustedBy = () => (
  <section className="border-y border-slate-200 bg-white py-8">
    <div className="container mx-auto grid gap-5 px-4 sm:grid-cols-2 lg:grid-cols-4">
        {operatingPrinciples.map(({ icon: Icon, label }) => (
          <div key={label} className="flex items-center gap-3">
            <Icon className="h-5 w-5 shrink-0 text-teal-700" />
            <span className="text-sm font-semibold leading-snug text-slate-700">{label}</span>
          </div>
        ))}
    </div>
  </section>
);

export default TrustedBy;
