import { Heart } from "lucide-react";
import logo from "@/lib/assets/logo.png";

const footerLinks = {
  Product: ["Features", "Modules", "Pricing", "Integrations"],
  Company: ["About", "Blog", "Careers", "Contact"],
  Support: ["Help Center", "Documentation", "API Reference", "Status"],
  Legal: ["Terms", "Privacy", "Security", "HIPAA"],
};

const Footer = () => (
  <footer className="border-t border-border bg-muted/30 py-16">
    <div className="container mx-auto px-4">
      <div className="grid grid-cols-2 md:grid-cols-5 gap-8 mb-12">
        <div className="col-span-2 md:col-span-1">
          <a href="#" className="inline-flex items-center gap-3">
            <img src={logo} alt="HIS.Pro" className="h-12 w-auto object-contain" />
            <span className="text-2xl font-extrabold leading-none">
              <span className="text-gradient">HIS</span>
              <span className="text-foreground">.Pro</span>
            </span>
          </a>
          <p className="text-sm text-muted-foreground mt-3 leading-relaxed">
            The modular cloud HIS platform built for modern healthcare.
          </p>
        </div>
        {Object.entries(footerLinks).map(([title, links]) => (
          <div key={title}>
            <h4 className="font-bold text-foreground text-sm mb-4">{title}</h4>
            <ul className="space-y-2.5">
              {links.map((link) => (
                <li key={link}>
                  <a href="#" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
                    {link}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      <div className="border-t border-border pt-8 flex flex-col sm:flex-row items-center justify-between gap-4">
        <p className="text-sm text-muted-foreground flex items-center gap-1.5">
          Made with <Heart className="h-3.5 w-3.5 text-destructive fill-destructive" /> for African Healthcare
        </p>
        <p className="text-sm text-muted-foreground">
          © {new Date().getFullYear()} HIS.Pro. All rights reserved.
        </p>
      </div>
    </div>
  </footer>
);

export default Footer;
