import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  ArrowLeft,
  Building2,
  ClipboardList,
  KeyRound,
  LogOut,
  Save,
  ShieldCheck,
  User,
} from "lucide-react";
import { apiClient, type AuthUser } from "@/api/client";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import {
  describeSessionDevice,
  getActiveSessions,
  type ActiveSession,
} from "@/lib/auth-session";
import { getFacilityDashboardPath } from "@/lib/facility-workspace";

type Facility = {
  id: string;
  name: string;
  slug: string;
  type: string;
  country?: string | null;
  address?: string | null;
  phone?: string | null;
  email?: string | null;
  settings: Record<string, unknown>;
};

type UserProfile = {
  id: string;
  username: string;
  email: string;
  role: string;
  first_name?: string | null;
  last_name?: string | null;
  phone?: string | null;
  facility_slug?: string | null;
};

const emptyFacilityForm = {
  name: "",
  type: "hospital",
  country: "",
  address: "",
  phone: "",
  email: "",
};

const emptyProfileForm = {
  username: "",
  email: "",
  first_name: "",
  last_name: "",
  phone: "",
};

const emptyPasswordForm = {
  current_password: "",
  new_password: "",
};

const Settings = () => {
  const navigate = useNavigate();
  const { facilitySlug = "" } = useParams();
  const { logoutEverywhere } = useAuth();
  const [facility, setFacility] = useState<Facility | null>(null);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [sessions, setSessions] = useState<ActiveSession[]>([]);
  const [facilityForm, setFacilityForm] = useState(emptyFacilityForm);
  const [profileForm, setProfileForm] = useState(emptyProfileForm);
  const [passwordForm, setPasswordForm] = useState(emptyPasswordForm);
  const [loading, setLoading] = useState(true);
  const [facilityStatus, setFacilityStatus] = useState("");
  const [profileStatus, setProfileStatus] = useState("");
  const [passwordStatus, setPasswordStatus] = useState("");
  const [sessionStatus, setSessionStatus] = useState("");
  const [error, setError] = useState("");

  const dashboardPath = getFacilityDashboardPath(facilitySlug);
  const auditLogsPath = `/dashboard/${facilitySlug}/audit-logs`;

  const loadSettings = async () => {
    setLoading(true);
    try {
      const [facilityResponse, profileResponse] = await Promise.all([
        apiClient.get<Facility>(`/facilities/${facilitySlug}`),
        apiClient.get<UserProfile>("/users/me"),
      ]);
      getActiveSessions().then(setSessions).catch(() => setSessions([]));
      setFacility(facilityResponse);
      setProfile(profileResponse);
      setFacilityForm({
        name: facilityResponse.name || "",
        type: facilityResponse.type || "hospital",
        country: facilityResponse.country || "",
        address: facilityResponse.address || "",
        phone: facilityResponse.phone || "",
        email: facilityResponse.email || "",
      });
      setProfileForm({
        username: profileResponse.username || "",
        email: profileResponse.email || "",
        first_name: profileResponse.first_name || "",
        last_name: profileResponse.last_name || "",
        phone: profileResponse.phone || "",
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSettings().catch(() => {
      setLoading(false);
      setError("Unable to load settings.");
    });
  }, [facilitySlug]);

  const saveFacility = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!facility) {
      return;
    }

    setError("");
    setFacilityStatus("");
    try {
      const updated = await apiClient.put<Facility>(`/facilities/${facility.slug}`, {
        name: facilityForm.name.trim(),
        type: facilityForm.type,
        country: facilityForm.country.trim() || undefined,
        address: facilityForm.address.trim() || undefined,
        phone: facilityForm.phone.trim() || undefined,
        email: facilityForm.email.trim() || undefined,
      });
      setFacility(updated);
      setFacilityStatus("Facility settings saved.");
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Facility update failed.");
    }
  };

  const saveProfile = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");
    setProfileStatus("");

    try {
      const updated = await apiClient.put<UserProfile>("/users/me", {
        username: profileForm.username.trim(),
        email: profileForm.email.trim(),
        first_name: profileForm.first_name.trim() || undefined,
        last_name: profileForm.last_name.trim() || undefined,
        phone: profileForm.phone.trim() || undefined,
      });
      setProfile(updated);
      const currentUser = apiClient.getUser();
      if (currentUser) {
        const nextUser: AuthUser = {
          ...currentUser,
          loginId: updated.username,
          fullName: `${updated.first_name || ""} ${updated.last_name || ""}`.trim() || updated.username,
          email: updated.email,
        };
        apiClient.setUser(nextUser);
      }
      setProfileStatus("Profile saved.");
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Profile update failed.");
    }
  };

  const changePassword = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");
    setPasswordStatus("");

    if (passwordForm.new_password.length < 8) {
      setError("New password must be at least 8 characters.");
      return;
    }

    try {
      await apiClient.post("/users/me/change-password", passwordForm);
      setPasswordForm(emptyPasswordForm);
      setPasswordStatus("Password changed.");
    } catch (passwordError) {
      setError(passwordError instanceof Error ? passwordError.message : "Password change failed.");
    }
  };

  const handleLogoutEverywhere = async () => {
    setError("");
    setSessionStatus("");
    try {
      await logoutEverywhere();
      setSessionStatus("All active sessions were closed.");
      navigate(`/login/${facilitySlug}`, { replace: true });
    } catch (sessionError) {
      setError(sessionError instanceof Error ? sessionError.message : "Could not close sessions.");
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background px-4">
        <p className="text-base font-medium text-muted-foreground">
          Loading settings...
        </p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-card/80 px-6 py-4 backdrop-blur-lg">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <Button
              variant="ghost"
              className="mb-2 -ml-3 gap-2 text-muted-foreground"
              onClick={() => navigate(dashboardPath)}
            >
              <ArrowLeft className="h-4 w-4" /> Dashboard
            </Button>
            <h1 className="text-2xl font-extrabold tracking-tight">Settings</h1>
            <p className="text-sm text-muted-foreground">
              Manage facility and account settings.
            </p>
          </div>
          <Button asChild variant="outline" className="gap-2">
            <Link to={auditLogsPath}>
              <ClipboardList className="h-4 w-4" /> Audit Logs
            </Link>
          </Button>
        </div>
      </header>

      <main className="mx-auto grid max-w-7xl gap-6 p-6 lg:grid-cols-[1fr_420px]">
        <div className="space-y-6">
          {error && (
            <p className="rounded-lg border border-destructive/20 bg-destructive/10 px-3 py-2 text-sm text-destructive">
              {error}
            </p>
          )}

          <Card className="border-border/60">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Building2 className="h-4 w-4 text-primary" /> Facility
              </CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={saveFacility} className="grid gap-4 sm:grid-cols-2">
                <Field label="Name" value={facilityForm.name} onChange={(value) => setFacilityForm((current) => ({ ...current, name: value }))} required />
                <div>
                  <Label>Type</Label>
                  <Select value={facilityForm.type} onValueChange={(value) => setFacilityForm((current) => ({ ...current, type: value }))}>
                    <SelectTrigger className="mt-1.5">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="hospital">Hospital</SelectItem>
                      <SelectItem value="clinic">Clinic</SelectItem>
                      <SelectItem value="lab">Lab</SelectItem>
                      <SelectItem value="pharmacy">Pharmacy</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <Field label="Country" value={facilityForm.country} onChange={(value) => setFacilityForm((current) => ({ ...current, country: value }))} />
                <Field label="Phone" value={facilityForm.phone} onChange={(value) => setFacilityForm((current) => ({ ...current, phone: value }))} />
                <Field label="Email" type="email" value={facilityForm.email} onChange={(value) => setFacilityForm((current) => ({ ...current, email: value }))} />
                <div className="sm:col-span-2">
                  <Label>Address</Label>
                  <Textarea className="mt-1.5" value={facilityForm.address} onChange={(event) => setFacilityForm((current) => ({ ...current, address: event.target.value }))} />
                </div>
                <SubmitRow status={facilityStatus} label="Save Facility" />
              </form>
            </CardContent>
          </Card>

          <Card className="border-border/60">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <User className="h-4 w-4 text-primary" /> Profile
              </CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={saveProfile} className="grid gap-4 sm:grid-cols-2">
                <Field label="Username" value={profileForm.username} onChange={(value) => setProfileForm((current) => ({ ...current, username: value }))} required />
                <Field label="Email" type="email" value={profileForm.email} onChange={(value) => setProfileForm((current) => ({ ...current, email: value }))} required />
                <Field label="First Name" value={profileForm.first_name} onChange={(value) => setProfileForm((current) => ({ ...current, first_name: value }))} />
                <Field label="Last Name" value={profileForm.last_name} onChange={(value) => setProfileForm((current) => ({ ...current, last_name: value }))} />
                <Field label="Phone" value={profileForm.phone} onChange={(value) => setProfileForm((current) => ({ ...current, phone: value }))} />
                <SubmitRow status={profileStatus} label="Save Profile" />
              </form>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card className="h-fit border-border/60">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <KeyRound className="h-4 w-4 text-primary" /> Password
              </CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={changePassword} className="space-y-4">
                <Field label="Current Password" type="password" value={passwordForm.current_password} onChange={(value) => setPasswordForm((current) => ({ ...current, current_password: value }))} required />
                <Field label="New Password" type="password" value={passwordForm.new_password} onChange={(value) => setPasswordForm((current) => ({ ...current, new_password: value }))} required />
                <div className="flex items-center justify-between gap-3 pt-2">
                  <p className="text-sm text-emerald-700">{passwordStatus}</p>
                  <Button type="submit" className="gradient-cta gap-2 border-0 text-primary-foreground">
                    <Save className="h-4 w-4" /> Change Password
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>

          <Card className="h-fit border-border/60">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <ShieldCheck className="h-4 w-4 text-primary" /> Sessions
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {sessions.length === 0 ? (
                <p className="rounded-xl border border-border/60 p-3 text-sm text-muted-foreground">
                  Active session details are unavailable.
                </p>
              ) : (
                <div className="space-y-2">
                  {sessions.map((session) => (
                    <div key={session.id} className="rounded-xl border border-border/60 p-3">
                      <div className="flex items-center justify-between gap-2">
                        <p className="text-sm font-semibold text-foreground">
                          {describeSessionDevice(session)}
                        </p>
                        {session.is_current && (
                          <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
                            Current
                          </span>
                        )}
                      </div>
                      <p className="mt-1 text-xs text-muted-foreground">
                        Last seen {new Date(session.last_seen_at).toLocaleString()}
                      </p>
                      {session.ip_address && (
                        <p className="mt-1 text-xs text-muted-foreground">
                          IP {session.ip_address}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              )}
              {sessionStatus && <p className="text-sm text-emerald-700">{sessionStatus}</p>}
              <Button type="button" variant="destructive" className="w-full gap-2" onClick={handleLogoutEverywhere}>
                <LogOut className="h-4 w-4" /> Logout Everywhere
              </Button>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
};

const Field = ({
  label,
  value,
  onChange,
  type = "text",
  required,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
  required?: boolean;
}) => (
  <div>
    <Label>
      {label}
      {required ? " *" : ""}
    </Label>
    <Input
      className="mt-1.5"
      type={type}
      value={value}
      onChange={(event) => onChange(event.target.value)}
      required={required}
    />
  </div>
);

const SubmitRow = ({ status, label }: { status: string; label: string }) => (
  <div className="flex items-center justify-between gap-3 sm:col-span-2">
    <p className="text-sm text-emerald-700">{status}</p>
    <Button type="submit" className="gradient-cta gap-2 border-0 text-primary-foreground">
      <Save className="h-4 w-4" /> {label}
    </Button>
  </div>
);

export default Settings;
