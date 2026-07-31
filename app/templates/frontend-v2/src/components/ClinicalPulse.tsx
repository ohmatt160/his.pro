import { cn } from "@/lib/utils";

type ClinicalPulseProps = {
  className?: string;
  compact?: boolean;
};

const ClinicalPulse = ({ className, compact = false }: ClinicalPulseProps) => (
  <div
    aria-hidden="true"
    className={cn(
      "relative overflow-hidden",
      compact ? "h-7 w-24" : "h-12 w-full",
      className,
    )}
  >
    <svg
      viewBox="0 0 240 48"
      className="h-full w-full"
      preserveAspectRatio="none"
      focusable="false"
    >
      <path
        d="M0 25 H49 L58 25 L65 15 L73 38 L82 5 L91 31 L99 25 H146 L154 25 L161 18 L168 33 L176 12 L184 29 L191 25 H240"
        fill="none"
        stroke="hsl(var(--border))"
        strokeWidth="1.2"
        vectorEffect="non-scaling-stroke"
      />
      <path
        d="M0 25 H49 L58 25 L65 15 L73 38 L82 5 L91 31 L99 25 H146 L154 25 L161 18 L168 33 L176 12 L184 29 L191 25 H240"
        className="clinical-pulse-path"
        fill="none"
        stroke="hsl(var(--sidebar-primary))"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="2"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
    <span className="clinical-scan-line absolute inset-y-1 left-0 w-px bg-primary/70" />
  </div>
);

export default ClinicalPulse;
