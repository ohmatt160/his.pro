import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTenantParams } from "@/context/TenantRoutingContext";
import {
  Activity,
  Archive,
  ArrowLeft,
  BedDouble,
  CalendarDays,
  ClipboardList,
  Edit3,
  FileHeart,
  FlaskConical,
  Pill,
  Receipt,
  ScanLine,
  User,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useAuth } from "@/context/AuthContext";
import { invalidatePatientOptions } from "@/api/patients";
import {
  archivePatientRecord,
  formatTimelineDate,
  getPatientTimeline,
  timelineModuleLabels,
  timelineModuleTone,
  type PatientTimelineEvent,
  type PatientTimelinePatient,
  updatePatientRecord,
} from "@/lib/patient-timeline";
import { getWorkspaceRoutePath } from "@/lib/facility-workspace";

const moduleIcons: Record<string, React.ElementType> = {
  reception: CalendarDays,
  records: FileHeart,
  lab: FlaskConical,
  radiology: ScanLine,
  pharmacy: Pill,
  billing: Receipt,
  nursing: BedDouble,
};

const emptyEditForm = {
  first_name: "",
  last_name: "",
  date_of_birth: "",
  gender: "OTHER",
  phone: "",
  email: "",
  address: "",
  blood_type: "",
  emergency_contact_name: "",
  emergency_contact_phone: "",
};

const bloodTypes = ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"];

const PatientTimeline = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { facilitySlug = "", branchSlug = "", patientId = "" } = useTenantParams();
  const [patient, setPatient] = useState<PatientTimelinePatient | null>(null);
  const [events, setEvents] = useState<PatientTimelineEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [editOpen, setEditOpen] = useState(false);
  const [archiveOpen, setArchiveOpen] = useState(false);
  const [editForm, setEditForm] = useState(emptyEditForm);
  const [actionError, setActionError] = useState("");
  const [saving, setSaving] = useState(false);
  const [archiving, setArchiving] = useState(false);
  const savingRef = useRef(false);
  const archivingRef = useRef(false);

  useEffect(() => {
    if (!patientId) {
      return;
    }

    setLoading(true);
    setError("");
    getPatientTimeline(patientId)
      .then((response) => {
        setPatient(response.patient);
        setEvents(response.events);
      })
      .catch((timelineError) => {
        setError(
          timelineError instanceof Error
            ? timelineError.message
            : "Unable to load patient timeline."
        );
        setEvents([]);
      })
      .finally(() => setLoading(false));
  }, [patientId]);

  const moduleCounts = useMemo(
    () =>
      events.reduce<Record<string, number>>((acc, event) => {
        acc[event.module] = (acc[event.module] || 0) + 1;
        return acc;
      }, {}),
    [events]
  );

  const patientName =
    patient?.full_name ||
    [patient?.first_name, patient?.last_name].filter(Boolean).join(" ") ||
    "Patient";
  const canEdit = Boolean(
    user && ["admin", "branch_admin", "reception", "doctor"].includes(user.role)
  );
  const canArchive = Boolean(
    user && ["admin", "branch_admin"].includes(user.role)
  );

  const openEdit = () => {
    if (!patient) return;
    setEditForm({
      first_name: patient.first_name || "",
      last_name: patient.last_name || "",
      date_of_birth: patient.date_of_birth || "",
      gender: patient.gender || "OTHER",
      phone: patient.phone || "",
      email: patient.email || "",
      address: patient.address || "",
      blood_type: patient.blood_type || "",
      emergency_contact_name: patient.emergency_contact_name || "",
      emergency_contact_phone: patient.emergency_contact_phone || "",
    });
    setActionError("");
    setEditOpen(true);
  };

  const savePatient = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (savingRef.current || !patientId) return;
    if (
      !editForm.first_name.trim() ||
      !editForm.last_name.trim() ||
      !editForm.date_of_birth
    ) {
      setActionError("First name, last name, and date of birth are required.");
      return;
    }

    savingRef.current = true;
    setSaving(true);
    setActionError("");
    try {
      const updated = await updatePatientRecord(patientId, {
        first_name: editForm.first_name.trim(),
        last_name: editForm.last_name.trim(),
        date_of_birth: editForm.date_of_birth,
        gender: editForm.gender,
        phone: editForm.phone.trim(),
        email: editForm.email.trim(),
        address: editForm.address.trim(),
        blood_type: editForm.blood_type || undefined,
        emergency_contact_name: editForm.emergency_contact_name.trim(),
        emergency_contact_phone: editForm.emergency_contact_phone.trim(),
      });
      setPatient(updated);
      invalidatePatientOptions();
      setEditOpen(false);
    } catch (saveError) {
      setActionError(
        saveError instanceof Error
          ? saveError.message
          : "Patient details could not be updated."
      );
    } finally {
      savingRef.current = false;
      setSaving(false);
    }
  };

  const archivePatient = async () => {
    if (archivingRef.current || !patientId) return;
    archivingRef.current = true;
    setArchiving(true);
    setActionError("");
    try {
      await archivePatientRecord(patientId);
      invalidatePatientOptions();
      navigate(
        getWorkspaceRoutePath(
          facilitySlug,
          "patients",
          branchSlug || undefined
        ),
        { replace: true }
      );
    } catch (archiveError) {
      setActionError(
        archiveError instanceof Error
          ? archiveError.message
          : "Patient record could not be archived."
      );
      setArchiveOpen(false);
    } finally {
      archivingRef.current = false;
      setArchiving(false);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-card/80 px-6 py-4 backdrop-blur-lg">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <Button
              variant="ghost"
              className="mb-2 -ml-3 gap-2 text-muted-foreground"
              onClick={() => navigate(getWorkspaceRoutePath(facilitySlug, "patients", branchSlug || undefined))}
            >
              <ArrowLeft className="h-4 w-4" /> Patients
            </Button>
            <h1 className="text-2xl font-extrabold tracking-tight">
              Patient Record
            </h1>
            <p className="text-sm text-muted-foreground">
              Demographics and longitudinal care history for {patientName}.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {canEdit && (
              <Button type="button" variant="outline" className="gap-2" onClick={openEdit} disabled={!patient}>
                <Edit3 className="h-4 w-4" /> Edit
              </Button>
            )}
            {canArchive && (
              <Button type="button" variant="outline" className="gap-2 text-destructive hover:text-destructive" onClick={() => setArchiveOpen(true)} disabled={!patient}>
                <Archive className="h-4 w-4" /> Archive
              </Button>
            )}
            <Button asChild variant="outline">
              <Link to={getWorkspaceRoutePath(facilitySlug, "records", branchSlug || undefined)}>Records</Link>
            </Button>
            <Button asChild variant="outline">
              <Link to={getWorkspaceRoutePath(facilitySlug, "consultations", branchSlug || undefined)}>
                Consultations
              </Link>
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto grid max-w-7xl gap-6 p-6 lg:grid-cols-[340px_1fr]">
        <aside className="space-y-4">
          <Card className="border-border/60">
            <CardContent className="p-5">
              <div className="flex items-start gap-3">
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10">
                  <User className="h-6 w-6 text-primary" />
                </div>
                <div>
                  <p className="font-bold text-foreground">{patientName}</p>
                  <p className="text-xs text-muted-foreground">
                    ID {patientId.slice(0, 8)}
                  </p>
                </div>
              </div>
              <div className="mt-5 space-y-2 text-sm">
                <ProfileRow label="DOB" value={patient?.date_of_birth || "-"} />
                <ProfileRow label="Gender" value={patient?.gender || "-"} />
                <ProfileRow label="Blood Type" value={patient?.blood_type || "-"} />
                <ProfileRow label="Phone" value={patient?.phone || "-"} />
                <ProfileRow label="Email" value={patient?.email || "-"} />
                <ProfileRow label="Address" value={patient?.address || "-"} />
                <ProfileRow
                  label="Emergency"
                  value={
                    [patient?.emergency_contact_name, patient?.emergency_contact_phone]
                      .filter(Boolean)
                      .join(" · ") || "-"
                  }
                />
              </div>
            </CardContent>
          </Card>

          <Card className="border-border/60">
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-base">
                <Activity className="h-4 w-4 text-primary" /> Timeline Summary
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <SummaryRow label="Total Events" value={String(events.length)} />
              {Object.entries(moduleCounts).map(([module, count]) => (
                <SummaryRow
                  key={module}
                  label={timelineModuleLabels[module] || module}
                  value={String(count)}
                />
              ))}
            </CardContent>
          </Card>
        </aside>

        <section>
          <Card className="border-border/60">
            <CardHeader>
              <CardTitle className="text-base">Care History</CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? (
                <p className="py-16 text-center text-sm text-muted-foreground">
                  Loading timeline...
                </p>
              ) : error ? (
                <p className="rounded-lg border border-destructive/20 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                  {error}
                </p>
              ) : events.length === 0 ? (
                <div className="py-16 text-center">
                  <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-muted">
                    <ClipboardList className="h-6 w-6 text-muted-foreground" />
                  </div>
                  <p className="font-semibold text-foreground">No timeline events yet</p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Events appear here as care moves across departments.
                  </p>
                </div>
              ) : (
                <div className="relative space-y-4 pl-6">
                  <div className="absolute bottom-0 left-2 top-0 w-px bg-border" />
                  {events.map((event) => (
                    <TimelineItem key={event.id} event={event} />
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </section>
      </main>

      <Dialog
        open={editOpen}
        onOpenChange={(open) => {
          if (!saving) {
            setEditOpen(open);
            if (!open) setActionError("");
          }
        }}
      >
        <DialogContent className="max-h-[92vh] overflow-y-auto sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>Edit patient details</DialogTitle>
            <DialogDescription>
              Update demographic and contact information. Clinical events remain unchanged.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={savePatient} className="grid gap-4 pt-2 sm:grid-cols-2">
            <EditField label="First Name" value={editForm.first_name} onChange={(first_name) => setEditForm((current) => ({ ...current, first_name }))} required />
            <EditField label="Last Name" value={editForm.last_name} onChange={(last_name) => setEditForm((current) => ({ ...current, last_name }))} required />
            <EditField label="Date of Birth" type="date" value={editForm.date_of_birth} onChange={(date_of_birth) => setEditForm((current) => ({ ...current, date_of_birth }))} required />
            <div>
              <Label>Gender</Label>
              <Select value={editForm.gender} onValueChange={(gender) => setEditForm((current) => ({ ...current, gender }))}>
                <SelectTrigger className="mt-1.5"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="MALE">Male</SelectItem>
                  <SelectItem value="FEMALE">Female</SelectItem>
                  <SelectItem value="OTHER">Other</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <EditField label="Phone" value={editForm.phone} onChange={(phone) => setEditForm((current) => ({ ...current, phone }))} />
            <EditField label="Email" type="email" value={editForm.email} onChange={(email) => setEditForm((current) => ({ ...current, email }))} />
            <EditField label="Address" value={editForm.address} onChange={(address) => setEditForm((current) => ({ ...current, address }))} />
            <div>
              <Label>Blood Type</Label>
              <Select value={editForm.blood_type || "none"} onValueChange={(value) => setEditForm((current) => ({ ...current, blood_type: value === "none" ? "" : value }))}>
                <SelectTrigger className="mt-1.5"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">Not recorded</SelectItem>
                  {bloodTypes.map((type) => <SelectItem key={type} value={type}>{type}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <EditField label="Emergency Contact" value={editForm.emergency_contact_name} onChange={(emergency_contact_name) => setEditForm((current) => ({ ...current, emergency_contact_name }))} />
            <EditField label="Emergency Phone" value={editForm.emergency_contact_phone} onChange={(emergency_contact_phone) => setEditForm((current) => ({ ...current, emergency_contact_phone }))} />
            {actionError && (
              <p className="rounded-lg border border-destructive/20 bg-destructive/10 px-3 py-2 text-sm text-destructive sm:col-span-2">{actionError}</p>
            )}
            <div className="flex gap-3 sm:col-span-2">
              <Button type="button" variant="outline" className="flex-1" disabled={saving} onClick={() => setEditOpen(false)}>Cancel</Button>
              <Button type="submit" className="flex-1" disabled={saving}>{saving ? "Saving..." : "Save changes"}</Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      <AlertDialog open={archiveOpen} onOpenChange={(open) => !archiving && setArchiveOpen(open)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Archive this patient record?</AlertDialogTitle>
            <AlertDialogDescription>
              The patient will disappear from active workflows, but clinical and audit history will be retained. This is safer than permanent deletion.
            </AlertDialogDescription>
          </AlertDialogHeader>
          {actionError && <p className="text-sm text-destructive">{actionError}</p>}
          <AlertDialogFooter>
            <AlertDialogCancel disabled={archiving}>Cancel</AlertDialogCancel>
            <AlertDialogAction disabled={archiving} onClick={(event) => { event.preventDefault(); void archivePatient(); }} className="bg-destructive text-destructive-foreground hover:bg-destructive/90">
              {archiving ? "Archiving..." : "Archive patient"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};

const TimelineItem = ({ event }: { event: PatientTimelineEvent }) => {
  const Icon = moduleIcons[event.module] || Activity;
  const tone =
    timelineModuleTone[event.module] ||
    "border-border bg-muted text-muted-foreground";

  return (
    <article className="relative rounded-xl border border-border/60 bg-card p-4">
      <div className="absolute -left-[31px] top-5 flex h-8 w-8 items-center justify-center rounded-full border border-border bg-background">
        <Icon className="h-4 w-4 text-primary" />
      </div>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <span className={`rounded-full border px-2 py-0.5 text-xs font-semibold ${tone}`}>
              {timelineModuleLabels[event.module] || event.module}
            </span>
            {event.status && (
              <span className="rounded-full bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground">
                {event.status}
              </span>
            )}
          </div>
          <h2 className="mt-2 text-sm font-bold text-foreground">{event.title}</h2>
          {event.description && (
            <p className="mt-1 line-clamp-3 text-sm text-muted-foreground">
              {event.description}
            </p>
          )}
        </div>
        <time className="shrink-0 text-xs font-medium text-muted-foreground">
          {formatTimelineDate(event.occurred_at)}
        </time>
      </div>
    </article>
  );
};

const ProfileRow = ({ label, value }: { label: string; value: string }) => (
  <div className="flex items-center justify-between gap-3">
    <span className="text-muted-foreground">{label}</span>
    <span className="text-right font-medium text-foreground">{value}</span>
  </div>
);

const EditField = ({
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
    <Label>{label}{required ? " *" : ""}</Label>
    <Input className="mt-1.5" type={type} value={value} required={required} onChange={(event) => onChange(event.target.value)} />
  </div>
);

const SummaryRow = ({ label, value }: { label: string; value: string }) => (
  <div className="flex items-center justify-between rounded-lg border border-border/60 px-3 py-2 text-sm">
    <span className="text-muted-foreground">{label}</span>
    <span className="font-bold text-foreground">{value}</span>
  </div>
);

export default PatientTimeline;
