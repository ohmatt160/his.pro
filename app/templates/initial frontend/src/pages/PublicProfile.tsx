import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { ExternalLink, Globe, Plus, Save, Trash2 } from "lucide-react";
import { apiClient } from "@/api/client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";

type PublicService = {
  id?: string;
  name: string;
  price?: number | null;
  duration?: string | null;
  description?: string | null;
};

type PublicDepartment = {
  id: string;
  name: string;
  location?: string;
  is_visible: boolean;
  services: PublicService[];
  staff_ids: string[];
  working_hours?: Record<string, string>;
  photos?: string[];
};

type PublicProfileData = {
  is_public: boolean;
  display_name: string;
  description: string;
  phone: string;
  email: string;
  photos: string[];
  departments: PublicDepartment[];
};

const emptyProfile: PublicProfileData = {
  is_public: false,
  display_name: "",
  description: "",
  phone: "",
  email: "",
  photos: [],
  departments: [],
};

const PublicProfile = () => {
  const { facilitySlug = "" } = useParams();
  const [profile, setProfile] = useState<PublicProfileData>(emptyProfile);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");
  const [activeDepartmentId, setActiveDepartmentId] = useState("");
  const [serviceForm, setServiceForm] = useState({ name: "", price: "", duration: "" });

  const activeDepartment = useMemo(
    () => profile.departments.find((department) => department.id === activeDepartmentId) || profile.departments[0],
    [activeDepartmentId, profile.departments]
  );

  useEffect(() => {
    if (!facilitySlug) {
      return;
    }
    setLoading(true);
    apiClient
      .get<PublicProfileData>(`/facilities/${facilitySlug}/public-profile`)
      .then((data) => {
        setProfile(data);
        setActiveDepartmentId(data.departments[0]?.id || "");
        setError("");
      })
      .catch((loadError) => {
        setError(loadError instanceof Error ? loadError.message : "Public profile could not be loaded.");
      })
      .finally(() => setLoading(false));
  }, [facilitySlug]);

  const persistProfile = async (nextProfile: PublicProfileData, successMessage = "Public profile saved.") => {
    const previousProfile = profile;
    setProfile(nextProfile);
    setError("");
    setStatus("Saving...");
    try {
      const updated = await apiClient.put<PublicProfileData>(
        `/facilities/${facilitySlug}/public-profile`,
        nextProfile
      );
      setProfile(updated);
      setStatus(successMessage);
    } catch (saveError) {
      setProfile(previousProfile);
      setError(saveError instanceof Error ? saveError.message : "Public profile update failed.");
      setStatus("");
    }
  };

  const updateDepartment = (departmentId: string, update: Partial<PublicDepartment>) => {
    setProfile((current) => ({
      ...current,
      departments: current.departments.map((department) =>
        department.id === departmentId ? { ...department, ...update } : department
      ),
    }));
  };

  const saveProfile = async (event?: FormEvent) => {
    event?.preventDefault();
    await persistProfile(profile);
  };

  const togglePublicProfile = (is_public: boolean) => {
    persistProfile(
      { ...profile, is_public },
      is_public ? "Public profile is now visible." : "Public profile is now private."
    );
  };

  const toggleDepartmentVisibility = (departmentId: string, is_visible: boolean) => {
    const nextProfile = {
      ...profile,
      departments: profile.departments.map((department) =>
        department.id === departmentId ? { ...department, is_visible } : department
      ),
    };
    persistProfile(
      nextProfile,
      is_visible ? "Department is now visible publicly." : "Department is now hidden publicly."
    );
  };

  const addService = () => {
    if (!activeDepartment || !serviceForm.name.trim()) {
      return;
    }
    const services = [
      ...(activeDepartment.services || []),
      {
        name: serviceForm.name.trim(),
        price: serviceForm.price ? Number(serviceForm.price) : null,
        duration: serviceForm.duration.trim() || null,
      },
    ];
    updateDepartment(activeDepartment.id, { services });
    setServiceForm({ name: "", price: "", duration: "" });
  };

  const removeService = (serviceIndex: number) => {
    if (!activeDepartment) {
      return;
    }
    updateDepartment(activeDepartment.id, {
      services: activeDepartment.services.filter((_, index) => index !== serviceIndex),
    });
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background px-4">
        <p className="text-base font-medium text-muted-foreground">Loading public profile...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-card/80 px-6 py-4 backdrop-blur-lg">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="mb-2 flex items-center gap-2 text-sm text-muted-foreground">
              <Globe className="h-4 w-4" /> Public Profile
            </div>
            <h1 className="text-2xl font-extrabold tracking-tight">Public Profile Settings</h1>
            <p className="text-sm text-muted-foreground">
              Choose what patients can see for this facility and its departments.
            </p>
          </div>
          <Button asChild variant="outline" className="gap-2">
            <Link to={`/hospital/${facilitySlug}`}>
              <ExternalLink className="h-4 w-4" /> Preview
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
              <CardTitle className="flex items-center justify-between gap-3 text-base">
                Main Profile
                <span className="flex items-center gap-2 text-sm font-normal text-muted-foreground">
                  Visible on HIS.Pro
                  <Switch
                    checked={profile.is_public}
                    onCheckedChange={togglePublicProfile}
                  />
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={saveProfile} className="grid gap-4 sm:grid-cols-2">
                <Field label="Display Name" value={profile.display_name} onChange={(display_name) => setProfile((current) => ({ ...current, display_name }))} required />
                <Field label="Phone" value={profile.phone} onChange={(phone) => setProfile((current) => ({ ...current, phone }))} />
                <Field label="Email" type="email" value={profile.email} onChange={(email) => setProfile((current) => ({ ...current, email }))} />
                <div className="sm:col-span-2">
                  <Label>Description</Label>
                  <Textarea
                    className="mt-1.5"
                    value={profile.description}
                    onChange={(event) => setProfile((current) => ({ ...current, description: event.target.value }))}
                  />
                </div>
                <div className="flex items-center justify-between gap-3 sm:col-span-2">
                  <p className="text-sm text-emerald-700">{status}</p>
                  <Button type="submit" className="gradient-cta gap-2 border-0 text-primary-foreground">
                    <Save className="h-4 w-4" /> Save Profile
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>

          <Card className="border-border/60">
            <CardHeader>
              <CardTitle className="text-base">Department Visibility</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {profile.departments.length === 0 ? (
                <p className="rounded-lg border border-dashed border-border/70 p-4 text-sm text-muted-foreground">
                  Department controls appear after the facility is switched to multi-clinic mode in Settings.
                </p>
              ) : (
                profile.departments.map((department) => (
                  <button
                    key={department.id}
                    type="button"
                    onClick={() => setActiveDepartmentId(department.id)}
                    className={`flex w-full items-center justify-between gap-3 rounded-lg border p-4 text-left transition-colors ${
                      activeDepartment?.id === department.id ? "border-primary bg-primary/10" : "border-border/60"
                    }`}
                  >
                    <span>
                      <span className="block font-semibold text-foreground">{department.name}</span>
                      <span className="block text-sm text-muted-foreground">{department.location || "No location set"}</span>
                    </span>
                    <span className="flex items-center gap-3">
                      <Badge variant={department.is_visible ? "default" : "secondary"}>
                        {department.is_visible ? "Visible" : "Hidden"}
                      </Badge>
                      <Switch
                        checked={department.is_visible}
                        onClick={(event) => event.stopPropagation()}
                        onCheckedChange={(is_visible) => toggleDepartmentVisibility(department.id, is_visible)}
                      />
                    </span>
                  </button>
                ))
              )}
            </CardContent>
          </Card>
        </div>

        <aside className="space-y-6">
          <Card className="border-border/60">
            <CardHeader>
              <CardTitle className="text-base">
                {activeDepartment ? `${activeDepartment.name} Settings` : "Department Settings"}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {!activeDepartment ? (
                <p className="text-sm text-muted-foreground">Select or create a department first.</p>
              ) : (
                <>
                  <div className="space-y-2">
                    <Label>Services & Pricing</Label>
                    {(activeDepartment.services || []).length === 0 ? (
                      <p className="rounded-lg border border-dashed border-border/70 p-3 text-sm text-muted-foreground">
                        No public services listed.
                      </p>
                    ) : (
                      <div className="space-y-2">
                        {activeDepartment.services.map((service, index) => (
                          <div key={`${service.name}-${index}`} className="flex items-center justify-between gap-3 rounded-lg border border-border/60 p-3">
                            <div>
                              <p className="text-sm font-semibold text-foreground">{service.name}</p>
                              <p className="text-xs text-muted-foreground">
                                {service.price ? `₦${service.price.toLocaleString()}` : "No price"} {service.duration ? `· ${service.duration}` : ""}
                              </p>
                            </div>
                            <Button type="button" size="icon" variant="ghost" onClick={() => removeService(index)} aria-label="Remove service">
                              <Trash2 className="h-4 w-4 text-destructive" />
                            </Button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="grid gap-3">
                    <Field label="Service Name" value={serviceForm.name} onChange={(name) => setServiceForm((current) => ({ ...current, name }))} />
                    <Field label="Price" type="number" value={serviceForm.price} onChange={(price) => setServiceForm((current) => ({ ...current, price }))} />
                    <Field label="Duration" value={serviceForm.duration} onChange={(duration) => setServiceForm((current) => ({ ...current, duration }))} />
                    <Button type="button" variant="outline" className="gap-2" onClick={addService}>
                      <Plus className="h-4 w-4" /> Add Service
                    </Button>
                  </div>

                  <Button type="button" className="gradient-cta w-full gap-2 border-0 text-primary-foreground" onClick={() => saveProfile()}>
                    <Save className="h-4 w-4" /> Save Department Settings
                  </Button>
                </>
              )}
            </CardContent>
          </Card>
        </aside>
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

export default PublicProfile;

