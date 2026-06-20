import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Building2, Clock, Globe, Phone } from "lucide-react";
import { apiClient } from "@/api/client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type PublicService = {
  id?: string | null;
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
};

type PublicProfileData = {
  is_public: boolean;
  display_name: string;
  description: string;
  phone: string;
  email: string;
  departments: PublicDepartment[];
};

const PublicHospital = () => {
  const { facilitySlug = "" } = useParams();
  const [profile, setProfile] = useState<PublicProfileData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!facilitySlug) return;
    apiClient
      .get<PublicProfileData>(`/facilities/${facilitySlug}/public-profile`)
      .then((data) => {
        setProfile(data);
        setError("");
      })
      .catch((loadError) => {
        setError(loadError instanceof Error ? loadError.message : "Public profile could not be loaded.");
      })
      .finally(() => setLoading(false));
  }, [facilitySlug]);

  const visibleDepartments = useMemo(
    () => (profile?.departments || []).filter((department) => department.is_visible),
    [profile?.departments]
  );

  if (loading) {
    return <div className="flex min-h-screen items-center justify-center bg-background text-muted-foreground">Loading hospital profile...</div>;
  }

  if (error || !profile) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background px-4">
        <Card className="max-w-md border-border/60">
          <CardContent className="p-6 text-center">
            <p className="font-semibold text-foreground">Profile unavailable</p>
            <p className="mt-2 text-sm text-muted-foreground">{error || "This hospital profile is not available yet."}</p>
            <Button asChild variant="outline" className="mt-5"><Link to="/">Back home</Link></Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-card/80 px-6 py-4 backdrop-blur-lg">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4">
          <Button asChild variant="ghost" className="gap-2"><Link to={`/dashboard/${facilitySlug}/public-profile`}><ArrowLeft className="h-4 w-4" /> Back</Link></Button>
          <Badge variant={profile.is_public ? "default" : "secondary"}>{profile.is_public ? "Public" : "Private preview"}</Badge>
        </div>
      </header>
      <main className="mx-auto max-w-6xl space-y-6 p-6">
        <section className="rounded-2xl border border-border/60 bg-card p-6">
          <div className="flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <div className="mb-3 flex items-center gap-2 text-sm text-primary"><Globe className="h-4 w-4" /> HIS.Pro Hospital Profile</div>
              <h1 className="text-3xl font-extrabold tracking-tight text-foreground">{profile.display_name}</h1>
              <p className="mt-3 max-w-3xl text-muted-foreground">{profile.description || "Care services and clinic information will appear here."}</p>
            </div>
            <div className="space-y-2 text-sm text-muted-foreground">
              {profile.phone && <p className="flex items-center gap-2"><Phone className="h-4 w-4" /> {profile.phone}</p>}
              {profile.email && <p>{profile.email}</p>}
            </div>
          </div>
        </section>

        <section className="grid gap-4 md:grid-cols-2">
          {visibleDepartments.length === 0 ? (
            <Card className="border-border/60 md:col-span-2"><CardContent className="p-8 text-center text-sm text-muted-foreground">No public departments are visible yet.</CardContent></Card>
          ) : visibleDepartments.map((department) => (
            <Card key={department.id} className="border-border/60">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base"><Building2 className="h-4 w-4 text-primary" /> {department.name}</CardTitle>
                {department.location && <p className="text-sm text-muted-foreground">{department.location}</p>}
              </CardHeader>
              <CardContent className="space-y-3">
                {(department.services || []).length === 0 ? <p className="text-sm text-muted-foreground">No services listed yet.</p> : department.services.map((service, index) => (
                  <div key={`${service.name}-${index}`} className="flex items-center justify-between gap-3 rounded-lg border border-border/60 p-3">
                    <div>
                      <p className="text-sm font-semibold text-foreground">{service.name}</p>
                      {service.duration && <p className="flex items-center gap-1 text-xs text-muted-foreground"><Clock className="h-3 w-3" /> {service.duration}</p>}
                    </div>
                    <p className="text-sm font-semibold text-foreground">{service.price ? `NGN ${service.price.toLocaleString()}` : "Ask clinic"}</p>
                  </div>
                ))}
              </CardContent>
            </Card>
          ))}
        </section>
      </main>
    </div>
  );
};

export default PublicHospital;
