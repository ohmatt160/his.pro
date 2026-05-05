const logos = [
  "City Clinic Lagos",
  "MedCare Kenya",
  "HealthFirst Ghana",
  "Sunrise Hospital",
  "AfriMed Solutions",
  "CarePoint Rwanda",
  "VitalHealth Tanzania",
  "PrimeCare Uganda",
];

const TrustedBy = () => (
  <section className="py-12 border-y border-border/50 bg-muted/30">
    <div className="container mx-auto px-4 text-center mb-6">
      <p className="text-sm font-medium text-muted-foreground">
        Trusted by <span className="text-foreground font-semibold">50+</span> healthcare providers across Africa
      </p>
    </div>
    <div className="overflow-hidden">
      <div className="flex animate-marquee gap-12 w-max">
        {[...logos, ...logos].map((name, i) => (
          <div
            key={i}
            className="flex items-center gap-2 px-6 py-3 rounded-lg bg-background/80 border border-border/50 whitespace-nowrap"
          >
            <div className="w-8 h-8 rounded-lg gradient-hero flex items-center justify-center text-primary-foreground text-xs font-bold">
              {name.charAt(0)}
            </div>
            <span className="text-sm font-medium text-muted-foreground">{name}</span>
          </div>
        ))}
      </div>
    </div>
  </section>
);

export default TrustedBy;
