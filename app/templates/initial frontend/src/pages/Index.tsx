import Navbar from "@/components/landing/Navbar";
import HeroSection from "@/components/landing/HeroSection";
import TrustedBy from "@/components/landing/TrustedBy";
import FeaturesSection from "@/components/landing/FeaturesSection";
import ModuleSelector from "@/components/landing/ModuleSelector";
import HowItWorks from "@/components/landing/HowItWorks";
import PricingSection from "@/components/landing/PricingSection";
import Testimonials from "@/components/landing/Testimonials";
import CTABanner from "@/components/landing/CTABanner";
import Footer from "@/components/landing/Footer";
import FloatingChat from "@/components/landing/FloatingChat";

const Index = () => (
  <div className="min-h-screen bg-background">
    <Navbar />
    <HeroSection />
    <TrustedBy />
    <FeaturesSection />
    <ModuleSelector />
    <HowItWorks />
    <PricingSection />
    <Testimonials />
    <CTABanner />
    <Footer />
    <FloatingChat />
  </div>
);

export default Index;
