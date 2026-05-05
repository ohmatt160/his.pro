import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  ArrowRight,
  Building2,
  Check,
  Eye,
  EyeOff,
  Globe,
  Lock,
  Mail,
  Phone,
  User,
} from "lucide-react";
import { Link, useNavigate } from "react-router-dom";

const modules = [
  {
    id: "reception",
    label: "Reception & Registration",
    desc: "Patient registration, appointments, queues, and check-in.",
  },
  {
    id: "records",
    label: "Shared Patient Record",
    desc: "One longitudinal patient chart shared across every department.",
  },
  {
    id: "consultations",
    label: "Doctors & Consultations",
    desc: "Consult notes, diagnoses, treatment plans, and clinical orders.",
  },
  {
    id: "nursing",
    label: "Nursing & Wards",
    desc: "Vitals, nursing notes, medication rounds, and inpatient handoff.",
  },
  {
    id: "lab",
    label: "Laboratory",
    desc: "Test ordering, sample tracking, and result delivery.",
  },
  {
    id: "pharmacy",
    label: "Pharmacy",
    desc: "Prescriptions, dispensing, and medication tracking.",
  },
  {
    id: "billing",
    label: "Billing & Claims",
    desc: "Invoices, payments, and insurance workflow.",
  },
  {
    id: "radiology",
    label: "Radiology",
    desc: "Imaging requests, reports, and scan workflow.",
  },
  {
    id: "inventory",
    label: "Inventory & Stores",
    desc: "Stock control for drugs, consumables, and supplies.",
  },
];

const defaultModulesByFacilityType: Record<string, string[]> = {
  clinic: ["reception", "records", "consultations", "pharmacy", "billing"],
  hospital: [
    "reception",
    "records",
    "consultations",
    "nursing",
    "pharmacy",
    "billing",
  ],
  lab: ["reception", "records", "lab", "billing", "inventory"],
};

const stepLabels = ["Facility Info", "Select Modules", "Admin Account"];

const getDefaultModules = (facilityType: string) =>
  defaultModulesByFacilityType[facilityType] ?? defaultModulesByFacilityType.hospital;

const GetStarted = () => {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [selectedModules, setSelectedModules] = useState<string[]>(
    getDefaultModules("hospital")
  );
  const [form, setForm] = useState({
    facilityName: "",
    facilityType: "hospital",
    fullName: "",
    email: "",
    phone: "",
    password: "",
    confirmPassword: "",
    country: "",
  });

  const toggleModule = (id: string) => {
    setSelectedModules((previous) =>
      previous.includes(id)
        ? previous.filter((module) => module !== id)
        : [...previous, id]
    );
  };

  const updateForm = (key: string, value: string) =>
    setForm((previous) => ({ ...previous, [key]: value }));

  const facilityDisplayName = form.facilityName || "your facility";
  const passwordChecks = [
    {
      label: "At least 8 characters",
      valid: form.password.length >= 8,
    },
    {
      label: "One uppercase letter",
      valid: /[A-Z]/.test(form.password),
    },
    {
      label: "One lowercase letter",
      valid: /[a-z]/.test(form.password),
    },
    {
      label: "One number",
      valid: /\d/.test(form.password),
    },
  ];
  const passwordScore = passwordChecks.filter((check) => check.valid).length;
  const passwordStrength =
    form.password.length === 0
      ? "None"
      : passwordScore <= 2
      ? "Weak"
      : passwordScore === 3
      ? "Medium"
      : "Strong";
  const passwordStrengthClass =
    passwordStrength === "Strong"
      ? "text-accent"
      : passwordStrength === "Medium"
      ? "text-cta-warm"
      : "text-destructive";
  const passwordBarClass =
    passwordStrength === "Strong"
      ? "bg-accent"
      : passwordStrength === "Medium"
      ? "bg-cta-warm"
      : "bg-destructive";
  const passwordsMatch =
    form.password.length > 0 && form.password === form.confirmPassword;
  const isPasswordValid = passwordChecks.every((check) => check.valid);

  const canProceed =
    step === 1
      ? Boolean(form.facilityName && form.facilityType)
      : step === 2
      ? selectedModules.length > 0
      : Boolean(
          form.fullName &&
            form.email &&
            form.password &&
            form.confirmPassword &&
            isPasswordValid &&
            passwordsMatch
        );

  const handleCreateWorkspace = () => {
    if (!canProceed) {
      return;
    }

    navigate("/setting-up", {
      state: {
        facilityName: form.facilityName,
        facilityType: form.facilityType,
        country: form.country,
        fullName: form.fullName,
        email: form.email,
        phone: form.phone,
        adminPassword: form.password,
        selectedModules,
      },
    });
  };

  return (
    <div className="relative min-h-screen overflow-hidden bg-background">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute right-0 top-0 h-[600px] w-[600px] translate-x-1/4 -translate-y-1/2 rounded-full bg-primary/5 blur-3xl" />
        <div className="absolute bottom-0 left-0 h-[500px] w-[500px] -translate-x-1/4 translate-y-1/3 rounded-full bg-accent/5 blur-3xl" />
      </div>

      <div className="relative z-10 border-b border-border/50 bg-background/80 backdrop-blur-lg">
        <div className="container mx-auto flex h-16 items-center justify-between px-4">
          <Link to="/" className="text-2xl font-extrabold tracking-tight">
            <span className="text-gradient">HIS</span>
            <span className="text-foreground">.Pro</span>
          </Link>
          <Link
            to="/"
            className="flex items-center gap-1 text-sm text-muted-foreground transition-colors hover:text-foreground"
          >
            <ArrowLeft className="h-3.5 w-3.5" /> Back to home
          </Link>
        </div>
      </div>

      <div className="relative z-10 container mx-auto max-w-4xl px-4 py-12">
        <div className="mb-12 flex items-center justify-center gap-2">
          {[1, 2, 3].map((currentStep) => (
            <div key={currentStep} className="flex items-center gap-2">
              <div
                className={`flex h-10 w-10 items-center justify-center rounded-full text-sm font-bold transition-all duration-300 ${
                  step > currentStep
                    ? "gradient-cta text-primary-foreground"
                    : step === currentStep
                    ? "bg-primary text-primary-foreground shadow-lg shadow-primary/30"
                    : "bg-muted text-muted-foreground"
                }`}
              >
                {step > currentStep ? (
                  <Check className="h-4 w-4" />
                ) : (
                  currentStep
                )}
              </div>
              {currentStep < 3 && (
                <div
                  className={`h-1 w-16 rounded-full transition-all duration-300 sm:w-24 ${
                    step > currentStep ? "bg-accent" : "bg-muted"
                  }`}
                />
              )}
            </div>
          ))}
        </div>

        <div className="-mt-4 mb-12 flex justify-center gap-8 text-xs text-muted-foreground">
          {stepLabels.map((label, index) => (
            <span
              key={label}
              className={step >= index + 1 ? "font-medium text-foreground" : ""}
            >
              {label}
            </span>
          ))}
        </div>

        <motion.div
          key={step}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
          transition={{ duration: 0.3 }}
        >
          {step === 1 && (
            <div>
              <div className="mb-10 text-center">
                <h1 className="mb-3 text-3xl font-extrabold tracking-tight sm:text-4xl">
                  Tell Us About Your{" "}
                  <span className="text-gradient">Facility</span>
                </h1>
                <p className="mx-auto max-w-md text-muted-foreground">
                  This gives us the right context before you choose modules and
                  create the administrator account.
                </p>
              </div>

              <div className="mx-auto max-w-md space-y-5">
                <div className="space-y-2">
                  <Label
                    htmlFor="facilityName"
                    className="flex items-center gap-2 text-sm font-medium"
                  >
                    <Building2 className="h-4 w-4 text-primary" /> Facility Name
                  </Label>
                  <Input
                    id="facilityName"
                    placeholder="e.g. Sunrise Medical Centre"
                    value={form.facilityName}
                    onChange={(event) =>
                      updateForm("facilityName", event.target.value)
                    }
                    className="h-12 border-border/60 bg-background focus:border-primary"
                  />
                </div>

                <div className="space-y-2">
                  <Label className="text-sm font-medium">Facility Type</Label>
                  <div className="grid grid-cols-3 gap-2">
                    {["clinic", "hospital", "lab"].map((type) => (
                      <button
                        key={type}
                        onClick={() => {
                          updateForm("facilityType", type);
                          setSelectedModules(getDefaultModules(type));
                        }}
                        className={`rounded-xl border-2 px-4 py-3 text-sm font-medium capitalize transition-all ${
                          form.facilityType === type
                            ? "border-primary bg-primary/5 text-primary"
                            : "border-border/60 text-muted-foreground hover:border-primary/30"
                        }`}
                      >
                        {type}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="space-y-2">
                  <Label
                    htmlFor="country"
                    className="flex items-center gap-2 text-sm font-medium"
                  >
                    <Globe className="h-4 w-4 text-primary" /> Country
                  </Label>
                  <Input
                    id="country"
                    placeholder="e.g. Kenya"
                    value={form.country}
                    onChange={(event) => updateForm("country", event.target.value)}
                    className="h-12 border-border/60 bg-background focus:border-primary"
                  />
                </div>
              </div>
            </div>
          )}

          {step === 2 && (
            <div>
              <div className="mb-10 text-center">
                <h1 className="mb-3 text-3xl font-extrabold tracking-tight sm:text-4xl">
                  Choose Your Starting{" "}
                  <span className="text-gradient">Modules</span>
                </h1>
                <p className="mx-auto max-w-md text-muted-foreground">
                  We preselected the core modules usually needed for a{" "}
                  <span className="font-medium capitalize text-foreground">
                    {form.facilityType}
                  </span>{" "}
                  so data can move cleanly across reception, clinical teams,
                  diagnostics, pharmacy, and billing. Adjust them for{" "}
                  <span className="font-medium text-foreground">
                    {facilityDisplayName}
                  </span>
                  .
                </p>
              </div>

              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                {modules.map((module) => {
                  const selected = selectedModules.includes(module.id);

                  return (
                    <button
                      key={module.id}
                      onClick={() => toggleModule(module.id)}
                      className={`group relative rounded-xl border-2 p-5 text-left transition-all duration-200 glass-card ${
                        selected
                          ? "border-primary bg-primary/5 shadow-lg shadow-primary/10"
                          : "border-transparent hover:border-primary/30"
                      }`}
                    >
                      {selected && (
                        <div className="absolute right-2 top-2 flex h-5 w-5 items-center justify-center rounded-full bg-primary">
                          <Check className="h-3 w-3 text-primary-foreground" />
                        </div>
                      )}
                      <p className="text-sm font-bold text-foreground">
                        {module.label}
                      </p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {module.desc}
                      </p>
                    </button>
                  );
                })}
              </div>

              <p className="mt-6 text-center text-sm text-muted-foreground">
                {selectedModules.length} module
                {selectedModules.length !== 1 ? "s" : ""} selected
              </p>
            </div>
          )}

          {step === 3 && (
            <div>
              <div className="mb-10 text-center">
                <h1 className="mb-3 text-3xl font-extrabold tracking-tight sm:text-4xl">
                  Create the <span className="text-gradient">Admin Account</span>
                </h1>
                <p className="mx-auto max-w-md text-muted-foreground">
                  This will be the primary administrator account for{" "}
                  <span className="font-medium text-foreground">
                    {facilityDisplayName}
                  </span>
                  . It can manage setup, users, and configuration after launch.
                </p>
              </div>

              <div className="mx-auto max-w-md space-y-5">
                <div className="space-y-2">
                  <Label
                    htmlFor="fullName"
                    className="flex items-center gap-2 text-sm font-medium"
                  >
                    <User className="h-4 w-4 text-primary" /> Administrator Full
                    Name
                  </Label>
                  <Input
                    id="fullName"
                    placeholder="e.g. Dr. Amina Yusuf"
                    value={form.fullName}
                    onChange={(event) =>
                      updateForm("fullName", event.target.value)
                    }
                    className="h-12 border-border/60 bg-background focus:border-primary"
                  />
                </div>

                <div className="space-y-2">
                  <Label
                    htmlFor="email"
                    className="flex items-center gap-2 text-sm font-medium"
                  >
                    <Mail className="h-4 w-4 text-primary" /> Work Email Address
                  </Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="admin@hospital.com"
                    value={form.email}
                    onChange={(event) => updateForm("email", event.target.value)}
                    className="h-12 border-border/60 bg-background focus:border-primary"
                  />
                </div>

                <div className="space-y-2">
                  <Label
                    htmlFor="phone"
                    className="flex items-center gap-2 text-sm font-medium"
                  >
                    <Phone className="h-4 w-4 text-primary" /> Admin Phone
                    (optional)
                  </Label>
                  <Input
                    id="phone"
                    placeholder="+254 700 000 000"
                    value={form.phone}
                    onChange={(event) => updateForm("phone", event.target.value)}
                    className="h-12 border-border/60 bg-background focus:border-primary"
                  />
                </div>

                <div className="space-y-2">
                  <Label
                    htmlFor="password"
                    className="flex items-center gap-2 text-sm font-medium"
                  >
                    <Lock className="h-4 w-4 text-primary" /> Create Password
                  </Label>
                  <div className="relative">
                    <Input
                      id="password"
                      type={showPassword ? "text" : "password"}
                      placeholder="Min 8 characters"
                      value={form.password}
                      onChange={(event) =>
                        updateForm("password", event.target.value)
                      }
                      className="h-12 border-border/60 bg-background pr-12 focus:border-primary"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword((value) => !value)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground transition-colors hover:text-foreground"
                      aria-label={showPassword ? "Hide password" : "Show password"}
                    >
                      {showPassword ? (
                        <EyeOff className="h-4 w-4" />
                      ) : (
                        <Eye className="h-4 w-4" />
                      )}
                    </button>
                  </div>
                  <div className="pt-2">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-muted-foreground">
                        Password strength
                      </span>
                      <span
                        className={`font-semibold ${
                          form.password.length === 0
                            ? "text-muted-foreground"
                            : passwordStrengthClass
                        }`}
                      >
                        {passwordStrength}
                      </span>
                    </div>
                    <div className="mt-2 h-2 rounded-full bg-muted">
                      <div
                        className={`h-2 rounded-full transition-all duration-300 ${
                          form.password.length === 0 ? "bg-muted" : passwordBarClass
                        }`}
                        style={{ width: `${(passwordScore / passwordChecks.length) * 100}%` }}
                      />
                    </div>
                    <div className="mt-3 grid gap-2 sm:grid-cols-2">
                      {passwordChecks.map((check) => (
                        <div
                          key={check.label}
                          className="flex items-center gap-2 text-xs"
                        >
                          <span
                            className={`flex h-4 w-4 items-center justify-center rounded-full ${
                              check.valid
                                ? "bg-accent/15 text-accent"
                                : "bg-muted text-muted-foreground"
                            }`}
                          >
                            <Check className="h-3 w-3" />
                          </span>
                          <span
                            className={
                              check.valid
                                ? "text-foreground"
                                : "text-muted-foreground"
                            }
                          >
                            {check.label}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label
                    htmlFor="confirmPassword"
                    className="flex items-center gap-2 text-sm font-medium"
                  >
                    <Lock className="h-4 w-4 text-primary" /> Confirm Password
                  </Label>
                  <div className="relative">
                    <Input
                      id="confirmPassword"
                      type={showConfirmPassword ? "text" : "password"}
                      placeholder="Re-enter password"
                      value={form.confirmPassword}
                      onChange={(event) =>
                        updateForm("confirmPassword", event.target.value)
                      }
                      className="h-12 border-border/60 bg-background pr-12 focus:border-primary"
                    />
                    <button
                      type="button"
                      onClick={() => setShowConfirmPassword((value) => !value)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground transition-colors hover:text-foreground"
                      aria-label={
                        showConfirmPassword
                          ? "Hide confirm password"
                          : "Show confirm password"
                      }
                    >
                      {showConfirmPassword ? (
                        <EyeOff className="h-4 w-4" />
                      ) : (
                        <Eye className="h-4 w-4" />
                      )}
                    </button>
                  </div>
                  {form.confirmPassword.length > 0 && (
                    <p
                      className={`text-xs ${
                        passwordsMatch ? "text-accent" : "text-destructive"
                      }`}
                    >
                      {passwordsMatch
                        ? "Passwords match"
                        : "Passwords do not match"}
                    </p>
                  )}
                </div>
              </div>
            </div>
          )}
        </motion.div>

        <div className="mx-auto mt-12 flex max-w-md items-center justify-between">
          {step > 1 ? (
            <Button
              variant="ghost"
              onClick={() => setStep(step - 1)}
              className="gap-2 text-muted-foreground"
            >
              <ArrowLeft className="h-4 w-4" /> Back
            </Button>
          ) : (
            <div />
          )}

          {step < 3 ? (
            <Button
              onClick={() => setStep(step + 1)}
              disabled={!canProceed}
              className="gradient-cta gap-2 border-0 px-8 text-primary-foreground shadow-lg"
            >
              Continue <ArrowRight className="h-4 w-4" />
            </Button>
          ) : (
            <Button
              onClick={handleCreateWorkspace}
              disabled={!canProceed}
              className="gradient-cta gap-2 border-0 px-8 text-primary-foreground shadow-xl animate-pulse-glow"
            >
              Create Facility Workspace <ArrowRight className="h-4 w-4" />
            </Button>
          )}
        </div>

        {step === 3 && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mx-auto mt-10 max-w-md rounded-xl p-5 glass-card"
          >
            <p className="mb-3 text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Facility Setup Summary
            </p>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Facility</span>
                <span className="font-medium text-foreground">
                  {form.facilityName || "—"}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Type</span>
                <span className="font-medium capitalize text-foreground">
                  {form.facilityType}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Modules</span>
                <span className="font-medium text-foreground">
                  {selectedModules.length} selected
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Administrator</span>
                <span className="font-medium text-foreground">
                  {form.fullName || "—"}
                </span>
              </div>
              <div className="mt-1 flex flex-wrap justify-end gap-1.5">
                {selectedModules.map((id) => (
                  <span
                    key={id}
                    className="rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium capitalize text-primary"
                  >
                    {modules.find((module) => module.id === id)?.label}
                  </span>
                ))}
              </div>
            </div>
          </motion.div>
        )}

        <p className="mt-8 text-center text-xs text-muted-foreground">
          By continuing on behalf of your facility, you agree to our{" "}
          <a href="#" className="underline hover:text-foreground">
            Terms of Service
          </a>{" "}
          and{" "}
          <a href="#" className="underline hover:text-foreground">
            Privacy Policy
          </a>
          .
        </p>
      </div>
    </div>
  );
};

export default GetStarted;
