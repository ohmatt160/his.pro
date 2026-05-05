import { useMemo, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { motion } from "framer-motion";
import {
  ArrowRight,
  Building2,
  Eye,
  EyeOff,
  Layers,
  Lock,
  Shield,
  Users,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import logo from "@/lib/assets/logo.png";
import {
  authenticateStaff,
  getFacilityLoginLink,
  getFacilityLoginPath,
  getStaffPortalPath,
  saveStaffSession,
} from "@/lib/facility-staff";
import {
  createFacilitySlug,
  getFacilityDashboardPath,
  getFacilityWorkspace,
} from "@/lib/facility-workspace";

const features = [
  { icon: Shield, text: "256-bit encrypted sessions" },
  { icon: Layers, text: "Role-based access control" },
  { icon: Users, text: "Multi-department workspace" },
];

const Login = () => {
  const navigate = useNavigate();
  const { facilitySlug = "" } = useParams();
  const [workspaceInput, setWorkspaceInput] = useState("");
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const workspace = facilitySlug ? getFacilityWorkspace(facilitySlug) : null;
  const facilityLink = facilitySlug ? getFacilityLoginLink(facilitySlug) : "";

  const parsedSlug = useMemo(() => {
    const trimmed = workspaceInput.trim();

    if (!trimmed) {
      return "";
    }

    const withoutOrigin = trimmed.replace(/^https?:\/\/[^/]+/i, "");
    const segments = withoutOrigin.split("/").filter(Boolean);
    const lastSegment = segments.at(-1) ?? trimmed;

    return createFacilitySlug(lastSegment);
  }, [workspaceInput]);

  const handleWorkspaceContinue = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!parsedSlug) {
      return;
    }

    navigate(getFacilityLoginPath(parsedSlug));
  };

  const handleSignIn = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!facilitySlug || !workspace) {
      return;
    }

    if (!login.trim() || !password.trim()) {
      setError("Please enter your login ID or email and password.");
      return;
    }

    setError("");
    setLoading(true);

    window.setTimeout(() => {
      const account = authenticateStaff({
        facilitySlug,
        login,
        password,
      });

      if (!account) {
        setLoading(false);
        setError("Invalid login ID, work email, or password.");
        return;
      }

      saveStaffSession({
        facilitySlug,
        loginId: account.loginId,
        role: account.role,
      });

      if (account.role === "admin") {
        navigate(getFacilityDashboardPath(facilitySlug), {
          replace: true,
          state: workspace,
        });
        return;
      }

      navigate(getStaffPortalPath(facilitySlug), {
        replace: true,
        state: { loginId: account.loginId },
      });
    }, 450);
  };

  return (
    <div className="min-h-screen flex">
      <div className="gradient-hero relative hidden overflow-hidden lg:flex lg:w-[45%] xl:w-[42%]">
        <div className="absolute inset-0 hero-pattern opacity-40" />
        <div className="absolute -left-20 top-20 h-72 w-72 rounded-full bg-white/5 blur-3xl" />
        <div className="absolute bottom-20 right-10 h-56 w-56 rounded-full bg-white/5 blur-3xl" />

        <div className="relative z-10 flex w-full flex-col justify-between p-12 xl:p-16">
          <div>
            <Link to="/" className="inline-flex items-center gap-3">
              <img
                src={logo}
                alt="HIS.Pro"
                className="h-11 w-11 rounded-xl bg-white/10 object-contain p-1.5 backdrop-blur-sm"
              />
              <span className="text-2xl font-extrabold tracking-tight text-white">
                HIS<span className="text-white/60">.Pro</span>
              </span>
            </Link>
          </div>

          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2, duration: 0.6 }}
            className="space-y-8"
          >
            <div>
              <h1 className="mb-3 text-3xl font-extrabold leading-tight text-white xl:text-4xl">
                {workspace
                  ? `Access ${workspace.facilityName}`
                  : "Your facility workspace awaits"}
              </h1>
              <p className="max-w-sm text-base leading-relaxed text-white/70">
                {workspace
                  ? "Sign in with the credentials your facility administrator issued so you can enter the shared care workspace."
                  : "Open the facility login shared by your administrator to sign into the right hospital or clinic workspace."}
              </p>
            </div>

            <div className="space-y-4">
              {features.map((feature, index) => (
                <motion.div
                  key={feature.text}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.4 + index * 0.1 }}
                  className="flex items-center gap-3"
                >
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-white/10 backdrop-blur-sm">
                    <feature.icon className="h-4 w-4 text-white/80" />
                  </div>
                  <span className="text-sm font-medium text-white/80">
                    {feature.text}
                  </span>
                </motion.div>
              ))}
            </div>

            {workspace && (
              <div className="rounded-2xl border border-white/12 bg-white/8 p-5">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-white/55">
                  Shared login link
                </p>
                <p className="mt-3 break-all text-sm text-white/80">
                  {facilityLink}
                </p>
              </div>
            )}
          </motion.div>

          <p className="text-xs text-white/40">
            {new Date().getFullYear()} HIS.Pro
          </p>
        </div>
      </div>

      <div className="flex flex-1 items-center justify-center bg-background p-6 sm:p-10">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="w-full max-w-sm"
        >
          <div className="mb-10 flex items-center gap-3 lg:hidden">
            <img
              src={logo}
              alt="HIS.Pro"
              className="h-10 w-10 rounded-xl bg-primary/10 object-contain p-1.5"
            />
            <span className="text-xl font-extrabold tracking-tight">
              <span className="text-gradient">HIS</span>
              <span className="text-foreground">.Pro</span>
            </span>
          </div>

          {!facilitySlug && (
            <>
              <div className="mb-8">
                <div className="mb-2 flex items-center gap-2">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10">
                    <Building2 className="h-4 w-4 text-primary" />
                  </div>
                </div>
                <h2 className="text-2xl font-extrabold tracking-tight text-foreground">
                  Open your facility login
                </h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  Paste the facility link shared by your administrator or enter
                  the facility slug.
                </p>
              </div>

              <form onSubmit={handleWorkspaceContinue} className="space-y-5">
                <div>
                  <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Facility link or slug
                  </Label>
                  <Input
                    placeholder="e.g. sunrise-medical-centre"
                    value={workspaceInput}
                    onChange={(event) => setWorkspaceInput(event.target.value)}
                    className="mt-1.5 h-11"
                  />
                </div>

                <Button
                  type="submit"
                  className="gradient-cta h-11 w-full gap-2 border-0 text-sm font-semibold text-primary-foreground shadow-lg"
                  disabled={!parsedSlug}
                >
                  Continue <ArrowRight className="h-4 w-4" />
                </Button>
              </form>
            </>
          )}

          {facilitySlug && !workspace && (
            <>
              <div className="mb-8">
                <div className="mb-2 flex items-center gap-2">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-destructive/10">
                    <Building2 className="h-4 w-4 text-destructive" />
                  </div>
                </div>
                <h2 className="text-2xl font-extrabold tracking-tight text-foreground">
                  Facility login not found
                </h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  This facility workspace does not exist yet, or the link is no
                  longer valid.
                </p>
              </div>

              <div className="space-y-3">
                <Button
                  asChild
                  className="gradient-cta h-11 w-full gap-2 border-0 text-sm font-semibold text-primary-foreground shadow-lg"
                >
                  <Link to="/get-started">
                    Create facility workspace <ArrowRight className="h-4 w-4" />
                  </Link>
                </Button>
                <Button asChild variant="outline" className="h-11 w-full">
                  <Link to="/login">Open another facility link</Link>
                </Button>
              </div>
            </>
          )}

          {workspace && (
            <>
              <div className="mb-8">
                <div className="mb-2 flex items-center gap-2">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10">
                    <Building2 className="h-4 w-4 text-primary" />
                  </div>
                </div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary/75">
                  {workspace.facilityName}
                </p>
                <h2 className="mt-2 text-2xl font-extrabold tracking-tight text-foreground">
                  Staff Sign In
                </h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  Enter the login ID or work email and password provided by your
                  facility administrator.
                </p>
              </div>

              <form onSubmit={handleSignIn} className="space-y-5">
                <div>
                  <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Login ID or Work Email
                  </Label>
                  <Input
                    placeholder="e.g. DOC-001 or doctor@facility.com"
                    value={login}
                    onChange={(event) => {
                      setLogin(event.target.value);
                      setError("");
                    }}
                    className="mt-1.5 h-11"
                    autoComplete="username"
                  />
                </div>

                <div>
                  <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Password
                  </Label>
                  <div className="relative mt-1.5">
                    <Input
                      type={showPassword ? "text" : "password"}
                      placeholder="Enter your password"
                      value={password}
                      onChange={(event) => {
                        setPassword(event.target.value);
                        setError("");
                      }}
                      className="h-11 pr-11"
                      autoComplete="current-password"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword((current) => !current)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground transition-colors hover:text-foreground"
                    >
                      {showPassword ? (
                        <EyeOff className="h-4 w-4" />
                      ) : (
                        <Eye className="h-4 w-4" />
                      )}
                    </button>
                  </div>
                </div>

                {error && (
                  <motion.div
                    initial={{ opacity: 0, y: -4 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="rounded-lg border border-destructive/20 bg-destructive/10 px-3 py-2.5 text-sm text-destructive"
                  >
                    {error}
                  </motion.div>
                )}

                <Button
                  type="submit"
                  className="gradient-cta h-11 w-full gap-2 border-0 text-sm font-semibold text-primary-foreground shadow-lg"
                  disabled={loading}
                >
                  {loading ? (
                    <motion.div
                      animate={{ rotate: 360 }}
                      transition={{
                        repeat: Number.POSITIVE_INFINITY,
                        duration: 1,
                        ease: "linear",
                      }}
                      className="h-5 w-5 rounded-full border-2 border-white/30 border-t-white"
                    />
                  ) : (
                    <>
                      Sign In <ArrowRight className="h-4 w-4" />
                    </>
                  )}
                </Button>
              </form>

              <div className="mt-8 rounded-xl border border-border/50 bg-muted/50 p-4">
                <div className="flex items-start gap-2.5">
                  <Lock className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
                  <p className="text-xs leading-relaxed text-muted-foreground">
                    <span className="font-semibold text-foreground">
                      First time signing in?
                    </span>{" "}
                    Use the login ID and temporary password shared by your
                    facility administrator.
                  </p>
                </div>
              </div>

              <p className="mt-6 text-center text-xs text-muted-foreground">
                Need help? Contact your facility administrator.
              </p>
            </>
          )}
        </motion.div>
      </div>
    </div>
  );
};

export default Login;
