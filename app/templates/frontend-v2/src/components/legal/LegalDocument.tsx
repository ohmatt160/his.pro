import type { ReactNode } from "react";
import { ArrowLeft, Printer } from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import logo from "@/lib/assets/logo.png";

type LegalSection = {
  title: string;
  content: ReactNode;
};

type LegalDocumentProps = {
  title: string;
  summary: string;
  effectiveDate: string;
  sections: LegalSection[];
};

const LegalDocument = ({
  title,
  summary,
  effectiveDate,
  sections,
}: LegalDocumentProps) => (
  <div className="min-h-screen bg-background">
    <header className="border-b border-border bg-card">
      <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-4 sm:px-6">
        <Link to="/" className="flex items-center gap-2">
          <img src={logo} alt="HIS.Pro" className="h-9 w-auto object-contain" />
          <span className="text-xl font-extrabold">
            <span className="text-gradient">HIS</span>.Pro
          </span>
        </Link>
        <div className="flex items-center gap-2 print:hidden">
          <Button asChild variant="ghost" size="sm">
            <Link to="/">
              <ArrowLeft className="h-4 w-4" /> Home
            </Link>
          </Button>
          <Button variant="outline" size="icon" onClick={() => window.print()} title="Print document">
            <Printer className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </header>

    <main className="mx-auto max-w-5xl px-4 py-10 sm:px-6 sm:py-14">
      <div className="border-b border-border pb-8">
        <p className="text-sm font-semibold text-primary">HIS.Pro Legal</p>
        <h1 className="mt-2 text-3xl font-extrabold tracking-tight sm:text-4xl">{title}</h1>
        <p className="mt-4 max-w-3xl leading-7 text-muted-foreground">{summary}</p>
        <p className="mt-4 text-sm text-muted-foreground">
          Effective date: <span className="font-semibold text-foreground">{effectiveDate}</span>
        </p>
      </div>

      <article className="space-y-10 py-10">
        {sections.map((section, index) => (
          <section key={section.title} id={`section-${index + 1}`} className="scroll-mt-8">
            <h2 className="text-xl font-bold">
              {index + 1}. {section.title}
            </h2>
            <div className="mt-4 space-y-4 text-[15px] leading-7 text-muted-foreground [&_a]:font-medium [&_a]:text-primary [&_a]:underline [&_li]:pl-1 [&_strong]:text-foreground [&_ul]:ml-5 [&_ul]:list-disc [&_ol]:ml-5 [&_ol]:list-decimal">
              {section.content}
            </div>
          </section>
        ))}
      </article>

      <div className="border-t border-border pt-8 text-sm leading-6 text-muted-foreground">
        These documents should be reviewed by qualified counsel before signing enterprise agreements
        or entering a new jurisdiction.
      </div>
    </main>
  </div>
);

export default LegalDocument;
