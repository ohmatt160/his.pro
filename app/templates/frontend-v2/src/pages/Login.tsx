import { useEffect, useMemo, useState, type FormEvent, type ReactNode } from "react";
import { motion } from "framer-motion";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useTenantParams } from "@/context/TenantRoutingContext";
import {
  ArrowRight,
  Building2,
  Eye,
  EyeOff,
  LockKeyhole,
  ShieldCheck,
} from "lucide-react";
import ClinicalPulse from "@/components/ClinicalPulse";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import logo from "@/lib/assets/logo.png";
import clinicalCommandCenter from "@/lib/assets/clinical-command-center-v2.jpg";
import { useAuth } from "@/context/AuthContext";
import {
  getBranchLoginPath,
  getFacilityLoginLink,
  getFacilityLoginPath,
  getStaffPortalPath,
} from "@/lib/facility-staff";
import {
  createFacilitySlug,
  getFacilityPlatformLink,
  getFacilityWorkspace,
  getWorkspaceDashboardPath,
  type SavedFacilityWorkspace,
} from "@/lib/facility-workspace";
import {
  getCanonicalSubdomainFromHostname,
  getCanonicalTenantUrl,
} from "@/lib/tenant-routing";

const Login = () => {
  const navigate = useNavigate();
  const { facilitySlug = "", branchSlug = "" } = useTenantParams();
  const [searchParams] = useSearchParams();
  const { user, login, logout, sessionMessage, clearSessionMessage } = useAuth();
  const [workspaceInput, setWorkspaceInput] = useState("");
  const [loginValue, setLoginValue] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [workspace, setWorkspace] = useState<SavedFacilityWorkspace | null | undefined>(undefined);

  useEffect(() => {
    if (!facilitySlug) return;
    setWorkspace(undefined);
    getFacilityWorkspace(facilitySlug).then(setWorkspace).catch(() => setWorkspace(null));
  }, [facilitySlug]);

  const forceAccountSwitch = searchParams.get("switch") === "1";
  const signedInToThisFacility = Boolean(
    user &&
      facilitySlug &&
      user.facilitySlug === facilitySlug &&
      (!branchSlug || user.branchSlug === branchSlug || user.branchSlugs?.includes(branchSlug)),
  );
  const isWorkspaceAdmin = user?.role === "admin" || user?.role === "branch_admin";
  const signedInDestination = isWorkspaceAdmin
    ? getWorkspaceDashboardPath(facilitySlug, branchSlug || user?.branchSlug || undefined)
    : getStaffPortalPath(facilitySlug);
  const facilityLink = facilitySlug
    ? workspace?.canonicalSubdomain
      ? getFacilityPlatformLink(facilitySlug, workspace.canonicalSubdomain)
      : getFacilityLoginLink(facilitySlug)
    : "";

  const workspaceTarget = useMemo(() => {
    const trimmed = workspaceInput.trim();
    if (!trimmed) return { directUrl: "", slug: "" };

    if (/^https?:\/\//i.test(trimmed)) {
      try {
        const url = new URL(trimmed);
        const canonicalSubdomain = getCanonicalSubdomainFromHostname(url.hostname);
        if (canonicalSubdomain) {
          return {
            directUrl: getCanonicalTenantUrl(canonicalSubdomain, "/login"),
            slug: "",
          };
        }

        const segments = url.pathname.split("/").filter(Boolean);
        const routePrefix = segments[0];
        const slug = ["dashboard", "hospital", "login", "portal", "workspace-ready"].includes(
          routePrefix,
        )
          ? segments[1]
          : segments[0];
        return { directUrl: "", slug: slug ? createFacilitySlug(slug) : "" };
      } catch {
        return { directUrl: "", slug: "" };
      }
    }

    return { directUrl: "", slug: createFacilitySlug(trimmed) };
  }, [workspaceInput]);
  const parsedSlug = workspaceTarget.slug;

  const handleContinueSession = () => navigate(signedInDestination, { replace: true });

  const handleSwitchAccount = () => {
    logout();
    clearSessionMessage();
    setLoginValue("");
    setPassword("");
    setError("");
    const loginPath = branchSlug
      ? getBranchLoginPath(facilitySlug, branchSlug)
      : getFacilityLoginPath(facilitySlug);
    navigate(`${loginPath}?switch=1`, { replace: true });
  };

  const handleWorkspaceContinue = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!parsedSlug && !workspaceTarget.directUrl) return;
    window.location.assign(
      workspaceTarget.directUrl || getFacilityLoginLink(parsedSlug),
    );
  };

  const handleSignIn = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!facilitySlug || !workspace) return;
    if (!loginValue.trim() || !password.trim()) {
      setError("Enter your login ID or work email and password.");
      return;
    }

    setError("");
    setLoading(true);
    try {
      const account = await login({
        facilitySlug,
        branchSlug: branchSlug || undefined,
        login: loginValue,
        password,
      });
      if (account.role === "admin" || account.role === "branch_admin") {
        navigate(
          getWorkspaceDashboardPath(facilitySlug, branchSlug || account.branchSlug || undefined),
          { replace: true },
        );
        return;
      }
      navigate(getStaffPortalPath(facilitySlug), { replace: true });
    } catch {
      setError("Invalid login ID, work email, or password.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="relative min-h-screen overflow-x-hidden bg-[#123331]">
      <img
        src={clinicalCommandCenter}
        alt=""
        className="absolute inset-0 h-full w-full object-cover object-[38%_center]"
      />
      <div className="absolute inset-0 bg-[#123331]/28" />

      <div className="relative z-10 flex min-h-screen flex-col lg:flex-row">
        <section className="flex min-h-[34vh] flex-1 flex-col justify-between px-5 py-5 text-white sm:px-8 sm:py-7 lg:min-h-screen lg:px-10 lg:py-8 xl:px-14 xl:py-10">
          <Link to="/" className="flex w-fit items-center gap-3" aria-label="HIS Pro home">
            <img src={logo} alt="" className="h-10 w-10 rounded-md bg-white/[0.88] object-contain p-1" />
            <div>
              <p className="text-lg font-bold">HIS.Pro</p>
              <p className="text-[10px] font-semibold uppercase text-[#8fe9d7]">Clinical OS 2.0</p>
            </div>
          </Link>

          <motion.div
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45 }}
            className="max-w-lg pb-3 lg:pb-12"
          >
            <div className="mb-4 flex min-w-0 items-center gap-3">
              <ClinicalPulse className="h-10 w-28 shrink-0 sm:w-40" />
              <span className="whitespace-nowrap rounded-full border border-white/25 bg-[#123331]/55 px-3 py-1 text-[10px] font-semibold uppercase backdrop-blur-md">
                Protected workspace
              </span>
            </div>
            <h1 className="text-balance text-2xl font-bold leading-tight sm:text-3xl lg:text-[36px]">
              {workspace?.facilityName || "Enter the right clinical workspace"}
            </h1>
            <p className="mt-3 max-w-md text-sm leading-6 text-white/76 sm:text-base">
              {workspace
                ? branchSlug
                  ? "Use the staff identity assigned to this branch."
                  : "Use the staff identity issued by your facility administrator."
                : "Each facility has its own sign-in boundary, staff access policy, and clinical data scope."}
            </p>
            {workspace && (
              <div className="mt-5 flex items-center gap-2 text-xs text-white/72">
                <ShieldCheck className="h-4 w-4 text-[#8fe9d7]" />
                <span className="truncate">{branchSlug ? `${branchSlug} branch` : facilitySlug}</span>
              </div>
            )}
          </motion.div>

          <div className="hidden items-center justify-between text-[11px] text-white/55 lg:flex">
            <span>{new Date().getFullYear()} HIS.Pro</span>
            <div className="flex items-center gap-4">
              <Link to="/privacy" className="hover:text-white">Privacy</Link>
              <Link to="/terms" className="hover:text-white">Terms</Link>
            </div>
          </div>
        </section>

        <section className="flex w-full items-center justify-center border-t border-white/20 bg-card/[0.97] px-5 py-8 backdrop-blur-xl sm:px-8 lg:min-h-screen lg:w-[500px] lg:border-l lg:border-t-0 xl:w-[540px]">
          <motion.div
            initial={{ opacity: 0, x: 12 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.4 }}
            className="w-full max-w-[390px]"
          >
            {!facilitySlug && (
              <AuthSection
                icon={<Building2 className="h-5 w-5" />}
                kicker="Workspace access"
                title="Open facility sign in"
                description="Enter the facility slug or the sign-in link shared by your administrator."
              >
                <form onSubmit={handleWorkspaceContinue} className="space-y-5">
                  <div>
                    <Label htmlFor="workspace-identifier">Facility link or slug</Label>
                    <Input
                      id="workspace-identifier"
                      placeholder="sunrise-medical-centre"
                      value={workspaceInput}
                      onChange={(event) => setWorkspaceInput(event.target.value)}
                      className="mt-2 h-11"
                      autoComplete="organization"
                    />
                  </div>
                  <Button
                    type="submit"
                    className="h-11 w-full justify-between"
                    disabled={!parsedSlug && !workspaceTarget.directUrl}
                  >
                    Continue
                    <ArrowRight className="h-4 w-4" />
                  </Button>
                  <p className="text-center text-xs text-muted-foreground">
                    Setting up a new hospital?{" "}
                    <Link to="/get-started" className="font-semibold text-primary hover:underline">
                      Create a facility workspace
                    </Link>
                  </p>
                </form>
              </AuthSection>
            )}

            {facilitySlug && workspace === undefined && (
              <div className="py-14 text-center">
                <ClinicalPulse className="mx-auto w-48" />
                <p className="mt-3 text-sm font-semibold text-muted-foreground">Verifying workspace...</p>
              </div>
            )}

            {facilitySlug && workspace === null && (
              <AuthSection
                icon={<Building2 className="h-5 w-5" />}
                kicker="Workspace unavailable"
                title="Facility sign in not found"
                description="The workspace does not exist or this sign-in link is no longer available."
              >
                <div className="space-y-3">
                  <Button asChild className="h-11 w-full justify-between">
                    <Link to="/get-started">Create facility workspace <ArrowRight className="h-4 w-4" /></Link>
                  </Button>
                  <Button asChild variant="outline" className="h-11 w-full">
                    <Link to="/login">Open another facility</Link>
                  </Button>
                </div>
              </AuthSection>
            )}

            {workspace && signedInToThisFacility && !forceAccountSwitch && user && (
              <AuthSection
                icon={<ShieldCheck className="h-5 w-5" />}
                kicker={workspace.facilityName}
                title="Session already active"
                description={`Continue as ${user.fullName || user.loginId}, or switch to another authorized account.`}
              >
                <div className="space-y-3">
                  <Button type="button" onClick={handleContinueSession} className="h-11 w-full justify-between">
                    Continue to workspace <ArrowRight className="h-4 w-4" />
                  </Button>
                  <Button type="button" variant="outline" onClick={handleSwitchAccount} className="h-11 w-full">
                    Switch account
                  </Button>
                </div>
              </AuthSection>
            )}

            {workspace && (!signedInToThisFacility || forceAccountSwitch) && (
              <AuthSection
                icon={<LockKeyhole className="h-5 w-5" />}
                kicker={workspace.facilityName}
                title="Staff sign in"
                description={branchSlug ? "Sign in with an account assigned to this branch." : "Sign in with your facility-issued staff account."}
              >
                <form onSubmit={handleSignIn} className="space-y-5">
                  <div>
                    <Label htmlFor="staff-login">Login ID or work email</Label>
                    <Input
                      id="staff-login"
                      placeholder="DOC-001 or doctor@facility.com"
                      value={loginValue}
                      onChange={(event) => {
                        setLoginValue(event.target.value);
                        setError("");
                        clearSessionMessage();
                      }}
                      className="mt-2 h-11"
                      autoComplete="username"
                    />
                  </div>
                  <div>
                    <Label htmlFor="staff-password">Password</Label>
                    <div className="relative mt-2">
                      <Input
                        id="staff-password"
                        type={showPassword ? "text" : "password"}
                        placeholder="Enter your password"
                        value={password}
                        onChange={(event) => {
                          setPassword(event.target.value);
                          setError("");
                          clearSessionMessage();
                        }}
                        className="h-11 pr-11"
                        autoComplete="current-password"
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword((current) => !current)}
                        className="absolute right-2 top-1/2 flex h-8 w-8 -translate-y-1/2 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground"
                        aria-label={showPassword ? "Hide password" : "Show password"}
                        title={showPassword ? "Hide password" : "Show password"}
                      >
                        {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </button>
                    </div>
                  </div>

                  {(error || sessionMessage) && (
                    <motion.div
                      initial={{ opacity: 0, y: -4 }}
                      animate={{ opacity: 1, y: 0 }}
                      role="alert"
                      className={`rounded-md border px-3 py-2.5 text-sm ${
                        error
                          ? "border-destructive/25 bg-destructive/[0.08] text-destructive"
                          : "border-amber-500/25 bg-amber-500/[0.08] text-amber-800"
                      }`}
                    >
                      {error || sessionMessage}
                    </motion.div>
                  )}

                  <Button type="submit" className="h-11 w-full justify-between" disabled={loading}>
                    <span>{loading ? "Signing in..." : "Sign in"}</span>
                    {loading ? (
                      <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/35 border-t-white" />
                    ) : (
                      <ArrowRight className="h-4 w-4" />
                    )}
                  </Button>
                </form>

                <div className="mt-5 flex items-start gap-2 border-t border-border pt-4 text-xs leading-5 text-muted-foreground">
                  <LockKeyhole className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                  <p>Temporary credentials and account recovery are managed by your facility administrator.</p>
                </div>
                {facilityLink && <p className="mt-4 truncate text-center text-[11px] text-muted-foreground">{facilityLink}</p>}
              </AuthSection>
            )}
          </motion.div>
        </section>
      </div>
    </main>
  );
};

const AuthSection = ({
  icon,
  kicker,
  title,
  description,
  children,
}: {
  icon: ReactNode;
  kicker: string;
  title: string;
  description: string;
  children: ReactNode;
}) => (
  <section>
    <span className="flex h-10 w-10 items-center justify-center rounded-md bg-primary/10 text-primary">{icon}</span>
    <p className="v2-kicker mt-5 truncate text-primary">{kicker}</p>
    <h2 className="mt-1 text-2xl font-bold text-foreground">{title}</h2>
    <p className="mt-2 text-sm leading-6 text-muted-foreground">{description}</p>
    <div className="mt-7">{children}</div>
  </section>
);

export default Login;
