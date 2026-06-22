import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  ArrowLeft,
  Building2,
  ClipboardList,
  Edit3,
  KeyRound,
  Layers,
  LogOut,
  Plus,
  Save,
  ShieldCheck,
  Trash2,
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
import { Switch } from "@/components/ui/switch";
import {
  describeSessionDevice,
  getActiveSessions,
  type ActiveSession,
} from "@/lib/auth-session";
import {
  setCachedFacilityWorkspace,
  getFacilityDashboardPath,
} from "@/lib/facility-workspace";
import { moduleCatalog, normalizeModules, type FacilityModuleId } from "@/lib/modules";
import {
  addSettledError,
  hasResourceErrors,
  settledValue,
  type ResourceErrors,
} from "@/lib/resource-loading";

type Facility = {
  id: string;
  name: string;
  slug: string;
  type: string;
  country?: string | null;
  address?: string | null;
  phone?: string | null;
  email?: string | null;
  hospital_type?: "single" | "multi_clinic";
  departments?: Department[];
  branches?: Branch[];
  modules: string[];
  settings: Record<string, unknown>;
};

type Branch = {
  id: string;
  name: string;
  slug?: string;
  location?: string;
  phone_extension?: string;
  services?: string[];
  modules?: string[];
  is_visible?: boolean;
  login_url_path?: string;
  dashboard_url_path?: string;
};

type Department = Branch;

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

const emptyDepartmentForm = {
  name: "",
  location: "",
  phone_extension: "",
  services: "",
};

type SettingsResource = "facility" | "profile";

const Settings = () => {
  const navigate = useNavigate();
  const { facilitySlug = "", branchSlug = "" } = useParams();
  const { user, logoutEverywhere } = useAuth();
  const [facility, setFacility] = useState<Facility | null>(null);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [sessions, setSessions] = useState<ActiveSession[]>([]);
  const [facilityForm, setFacilityForm] = useState(emptyFacilityForm);
  const [profileForm, setProfileForm] = useState(emptyProfileForm);
  const [passwordForm, setPasswordForm] = useState(emptyPasswordForm);
  const [moduleSelection, setModuleSelection] = useState<FacilityModuleId[]>([]);
  const [hospitalType, setHospitalType] = useState<"single" | "multi_clinic">("single");
  const [departmentForm, setDepartmentForm] = useState(emptyDepartmentForm);
  const [editingDepartmentId, setEditingDepartmentId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [facilityStatus, setFacilityStatus] = useState("");
  const [hospitalTypeStatus, setHospitalTypeStatus] = useState("");
  const [departmentStatus, setDepartmentStatus] = useState("");
  const [modulesStatus, setModulesStatus] = useState("");
  const [profileStatus, setProfileStatus] = useState("");
  const [passwordStatus, setPasswordStatus] = useState("");
  const [sessionStatus, setSessionStatus] = useState("");
  const [error, setError] = useState("");
  const [dataErrors, setDataErrors] = useState<ResourceErrors<SettingsResource>>({});

  const dashboardPath = getFacilityDashboardPath(facilitySlug);
  const auditLogsPath = `/dashboard/${facilitySlug}/audit-logs`;
  const isBranchAdmin = user?.role === "branch_admin";

  const getCurrentBranch = (source: Facility | null = facility) => {
    const branches = source?.branches || source?.departments || [];
    return (
      branches.find((branch) => user?.branchId && branch.id === user.branchId) ||
      branches.find((branch) => branchSlug && branch.slug === branchSlug) ||
      branches[0] ||
      null
    );
  };

  const loadSettings = async () => {
    setLoading(true);
    try {
      const [facilityResponse, profileResponse] = await Promise.allSettled([
        apiClient.get<Facility>(`/facilities/${facilitySlug}`),
        apiClient.get<UserProfile>("/users/me"),
      ]);
      getActiveSessions().then(setSessions).catch(() => setSessions([]));

      const errors: ResourceErrors<SettingsResource> = {};
      addSettledError(errors, "facility", facilityResponse, "Facility settings could not be loaded.");
      addSettledError(errors, "profile", profileResponse, "Profile settings could not be loaded.");

      const nextFacility = settledValue<Facility | null>(facilityResponse, null);
      const nextProfile = settledValue<UserProfile | null>(profileResponse, null);

      setFacility(nextFacility);
      setProfile(nextProfile);
      setDataErrors(errors);

      if (nextFacility) {
        const currentBranch = getCurrentBranch(nextFacility);
        setModuleSelection(
          normalizeModules(isBranchAdmin && currentBranch ? currentBranch.modules || [] : nextFacility.modules)
        );
        setHospitalType(nextFacility.hospital_type || "single");
        setFacilityForm({
          name: nextFacility.name || "",
          type: nextFacility.type || "hospital",
          country: nextFacility.country || "",
          address: nextFacility.address || "",
          phone: nextFacility.phone || "",
          email: nextFacility.email || "",
        });
      }

      if (nextProfile) {
        setProfileForm({
          username: nextProfile.username || "",
          email: nextProfile.email || "",
          first_name: nextProfile.first_name || "",
          last_name: nextProfile.last_name || "",
          phone: nextProfile.phone || "",
        });
      }
    } finally {
      setLoading(false);
    }
  };

  const toggleModule = (moduleId: FacilityModuleId, checked: boolean) => {
    setModulesStatus("");
    setModuleSelection((current) => {
      if (checked) {
        return current.includes(moduleId) ? current : [...current, moduleId];
      }

      return current.filter((id) => id !== moduleId);
    });
  };

  const saveModules = async () => {
    if (!facility || (!isBranchAdmin && moduleSelection.length === 0)) {
      setError("At least one module must stay enabled.");
      return;
    }

    setError("");
    setModulesStatus("");
    try {
      if (isBranchAdmin) {
        const branch = getCurrentBranch();
        if (!branch) {
          setError("Your branch could not be found. Please sign in through your branch portal again.");
          return;
        }

        const updatedBranch = await apiClient.put<Branch>(
          `/facilities/${facility.slug}/branches/${branch.id}/modules`,
          { modules: moduleSelection }
        );
        setFacility((current) => {
          if (!current) {
            return current;
          }
          const branches = current.branches || current.departments || [];
          const nextBranches = branches.map((item) => (item.id === updatedBranch.id ? updatedBranch : item));
          return { ...current, branches: nextBranches, departments: nextBranches };
        });
        setModuleSelection(normalizeModules(updatedBranch.modules));
        setModulesStatus("Branch modules saved.");
        return;
      }

      const updated = await apiClient.put<Facility>(
        `/facilities/${facility.slug}/modules`,
        moduleSelection
      );
      setFacility(updated);
      const selectedModules = normalizeModules(updated.modules);
      setModuleSelection(selectedModules);
      setCachedFacilityWorkspace({
        facilityName: updated.name,
        facilityType: updated.type,
        country: updated.country || "",
        fullName:
          `${profile?.first_name || ""} ${profile?.last_name || ""}`.trim() ||
          profile?.username ||
          "Admin",
        email: updated.email || profile?.email || "",
        phone: updated.phone || profile?.phone || "",
        selectedModules,
        facilitySlug: updated.slug,
        createdAt: new Date().toISOString(),
      });
      setModulesStatus("Modules saved.");
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Module update failed.");
    }
  };

  const saveHospitalType = async (nextType: "single" | "multi_clinic" = hospitalType) => {
    if (!facility) {
      return;
    }
    const previousType = hospitalType;
    setHospitalType(nextType);
    setError("");
    setHospitalTypeStatus("Saving hospital type...");
    try {
      const updated = await apiClient.put<Facility>(`/facilities/${facility.slug}/settings`, {
        hospital_type: nextType,
      });
      setFacility(updated);
      setHospitalType(updated.hospital_type || "single");
      setHospitalTypeStatus(
        updated.hospital_type === "multi_clinic"
          ? "Multi-branch mode enabled."
          : "Single hospital mode enabled."
      );
    } catch (saveError) {
      setHospitalType(previousType);
      setError(saveError instanceof Error ? saveError.message : "Hospital type update failed.");
      setHospitalTypeStatus("");
    }
  };

  const startEditingDepartment = (department: Department) => {
    setEditingDepartmentId(department.id);
    setDepartmentForm({
      name: department.name || "",
      location: department.location || "",
      phone_extension: department.phone_extension || "",
      services: (department.services || []).join(", "),
    });
    setDepartmentStatus("");
  };

  const resetDepartmentForm = () => {
    setEditingDepartmentId(null);
    setDepartmentForm(emptyDepartmentForm);
  };

  const saveDepartment = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!facility || !departmentForm.name.trim()) {
      return;
    }
    const payload = {
      name: departmentForm.name.trim(),
      location: departmentForm.location.trim(),
      phone_extension: departmentForm.phone_extension.trim(),
      services: departmentForm.services
        .split(",")
        .map((service) => service.trim())
        .filter(Boolean),
    };
    setError("");
    setDepartmentStatus("");
    try {
      const department = editingDepartmentId
        ? await apiClient.put<Department>(
            `/facilities/${facility.slug}/branches/${editingDepartmentId}`,
            payload
          )
        : await apiClient.post<Department>(`/facilities/${facility.slug}/branches`, payload);
      setFacility((current) => {
        if (!current) {
          return current;
        }
        const branches = current.branches || current.departments || [];
        const nextBranches = editingDepartmentId
          ? branches.map((item) => (item.id === department.id ? department : item))
          : [...branches, department];
        return { ...current, hospital_type: "multi_clinic", branches: nextBranches, departments: nextBranches };
      });
      setHospitalType("multi_clinic");
      setDepartmentStatus(editingDepartmentId ? "Branch saved." : "Branch added.");
      resetDepartmentForm();
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Branch update failed.");
    }
  };

  const deleteDepartment = async (departmentId: string) => {
    if (!facility) {
      return;
    }
    setError("");
    setDepartmentStatus("");
    try {
      await apiClient.del(`/facilities/${facility.slug}/branches/${departmentId}`);
      setFacility((current) => current
        ? { ...current, branches: (current.branches || current.departments || []).filter((department) => department.id !== departmentId), departments: (current.branches || current.departments || []).filter((department) => department.id !== departmentId) }
        : current);
      setDepartmentStatus("Branch removed.");
      if (editingDepartmentId === departmentId) {
        resetDepartmentForm();
      }
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : "Branch could not be removed.");
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
              {isBranchAdmin ? "Manage your branch account and module settings." : "Manage facility and account settings."}
            </p>
          </div>
          {!isBranchAdmin && (
            <Button asChild variant="outline" className="gap-2">
              <Link to={auditLogsPath}>
                <ClipboardList className="h-4 w-4" /> Audit Logs
              </Link>
            </Button>
          )}
        </div>
      </header>

      <main className="mx-auto grid max-w-7xl gap-6 p-6 lg:grid-cols-[1fr_420px]">
        <div className="space-y-6">
          {hasResourceErrors(dataErrors) && (
            <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
              Some settings data could not be loaded. Available sections are still usable.
            </p>
          )}

          {error && (
            <p className="rounded-lg border border-destructive/20 bg-destructive/10 px-3 py-2 text-sm text-destructive">
              {error}
            </p>
          )}

          {!isBranchAdmin && (
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
          )}

          {!isBranchAdmin && (
          <Card className="border-border/60">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Building2 className="h-4 w-4 text-primary" /> Hospital Type
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-5">
              <div className="grid gap-3 sm:grid-cols-2">
                <button
                  type="button"
                  onClick={() => saveHospitalType("single")}
                  className={`rounded-lg border p-4 text-left transition-colors ${
                    hospitalType === "single"
                      ? "border-primary bg-primary/10"
                      : "border-border/60 hover:bg-muted/40"
                  }`}
                >
                  <p className="font-semibold text-foreground">Single Hospital</p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    One facility, one shared workflow.
                  </p>
                </button>
                <button
                  type="button"
                  onClick={() => saveHospitalType("multi_clinic")}
                  className={`rounded-lg border p-4 text-left transition-colors ${
                    hospitalType === "multi_clinic"
                      ? "border-primary bg-primary/10"
                      : "border-border/60 hover:bg-muted/40"
                  }`}
                >
                  <p className="font-semibold text-foreground">Medical Campus / Multi-Branch</p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Separate clinics, buildings, or branches under one tenant.
                  </p>
                </button>
              </div>
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm text-emerald-700">{hospitalTypeStatus}</p>
                <Button type="button" className="gradient-cta gap-2 border-0 text-primary-foreground" onClick={() => saveHospitalType()}>
                  <Save className="h-4 w-4" /> Save Current Type
                </Button>
              </div>

              {hospitalType === "multi_clinic" && (
                <div className="space-y-4 border-t border-border/60 pt-5">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <h3 className="text-sm font-semibold text-foreground">Branches / Clinics</h3>
                      <p className="text-sm text-muted-foreground">Physical branches, clinics, buildings, wings, or service locations under this facility.</p>
                    </div>
                    {departmentStatus && <p className="text-sm text-emerald-700">{departmentStatus}</p>}
                  </div>

                  <div className="grid gap-3">
                    {(facility?.branches || facility?.departments || []).length === 0 ? (
                      <p className="rounded-lg border border-dashed border-border/70 p-4 text-sm text-muted-foreground">
                        No branches or clinics yet. Add the first location below.
                      </p>
                    ) : (
                      (facility?.branches || facility?.departments || []).map((department) => (
                        <div key={department.id} className="flex flex-col gap-3 rounded-lg border border-border/60 p-4 sm:flex-row sm:items-center sm:justify-between">
                          <div>
                            <p className="font-semibold text-foreground">{department.name}</p>
                            <p className="text-sm text-muted-foreground">{department.location || "No location set"}</p>
                            <p className="text-xs text-muted-foreground">
                              Public services: {(department.services || []).length || 0}
                            </p>
                            {department.login_url_path && (
                              <p className="mt-1 break-all font-mono text-[11px] text-muted-foreground">
                                Branch login: {`${window.location.origin}${department.login_url_path}`}
                              </p>
                            )}
                          </div>
                          <div className="flex gap-2">
                            <Button type="button" size="sm" variant="outline" className="gap-2" onClick={() => startEditingDepartment(department)}>
                              <Edit3 className="h-4 w-4" /> Edit
                            </Button>
                            <Button type="button" size="sm" variant="outline" className="gap-2 text-destructive" onClick={() => deleteDepartment(department.id)}>
                              <Trash2 className="h-4 w-4" /> Delete
                            </Button>
                          </div>
                        </div>
                      ))
                    )}
                  </div>

                  <form onSubmit={saveDepartment} className="grid gap-4 rounded-lg border border-border/60 p-4 sm:grid-cols-2">
                    <Field label="Branch / Clinic Name" value={departmentForm.name} onChange={(value) => setDepartmentForm((current) => ({ ...current, name: value }))} required />
                    <Field label="Location" value={departmentForm.location} onChange={(value) => setDepartmentForm((current) => ({ ...current, location: value }))} />
                    <Field label="Phone Extension" value={departmentForm.phone_extension} onChange={(value) => setDepartmentForm((current) => ({ ...current, phone_extension: value }))} />
                    <Field label="Public Services" value={departmentForm.services} onChange={(value) => setDepartmentForm((current) => ({ ...current, services: value }))} />
                    <div className="flex items-center justify-between gap-3 sm:col-span-2">
                      {editingDepartmentId ? (
                        <Button type="button" variant="outline" onClick={resetDepartmentForm}>
                          Cancel Edit
                        </Button>
                      ) : (
                        <span />
                      )}
                      <Button type="submit" className="gradient-cta gap-2 border-0 text-primary-foreground">
                        <Plus className="h-4 w-4" /> {editingDepartmentId ? "Save Branch" : "Add Branch"}
                      </Button>
                    </div>
                  </form>
                </div>
              )}
            </CardContent>
          </Card>
          )}

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

          <Card className="border-border/60">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Layers className="h-4 w-4 text-primary" /> {isBranchAdmin ? "Branch Modules" : "Modules"}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-3 sm:grid-cols-2">
                {moduleCatalog.map((module) => {
                  const Icon = module.icon;
                  const checked = moduleSelection.includes(module.id);

                  return (
                    <div
                      key={module.id}
                      className="flex min-h-[112px] items-start justify-between gap-3 rounded-lg border border-border/60 p-4"
                    >
                      <div className="flex gap-3">
                        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                          <Icon className="h-5 w-5 text-primary" />
                        </div>
                        <div>
                          <p className="text-sm font-semibold text-foreground">{module.label}</p>
                          <p className="mt-1 text-xs leading-5 text-muted-foreground">
                            {module.description}
                          </p>
                        </div>
                      </div>
                      <Switch
                        checked={checked}
                        onCheckedChange={(value) => toggleModule(module.id, value)}
                        aria-label={`${checked ? "Disable" : "Enable"} ${module.label}`}
                      />
                    </div>
                  );
                })}
              </div>
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm text-emerald-700">{modulesStatus}</p>
                <Button type="button" className="gradient-cta gap-2 border-0 text-primary-foreground" onClick={saveModules}>
                  <Save className="h-4 w-4" /> Save Modules
                </Button>
              </div>
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

