import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  Activity,
  ArrowLeft,
  BedDouble,
  ClipboardList,
  FileText,
  Pill,
  Plus,
  Save,
  Users,
} from "lucide-react";
import { apiClient } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
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
import { Textarea } from "@/components/ui/textarea";
import { getFacilityDashboardPath } from "@/lib/facility-workspace";
import {
  emptyObservationForm,
  observationPayload,
  type WardAdmission,
  type WardBed,
} from "@/lib/wards";

type Patient = {
  id: string;
  first_name: string;
  last_name: string;
  full_name?: string;
  phone?: string | null;
};

type PatientListResponse = {
  patients: Patient[];
};

const emptyBedForm = {
  ward_name: "Observation Ward",
  bed_number: "",
  notes: "",
};

const emptyAdmissionForm = {
  patient_id: "",
  bed_id: "",
  ward_name: "Observation Ward",
  reason: "",
  acuity: "normal",
};

const Wards = () => {
  const navigate = useNavigate();
  const { facilitySlug = "" } = useParams();
  const [patients, setPatients] = useState<Patient[]>([]);
  const [beds, setBeds] = useState<WardBed[]>([]);
  const [admissions, setAdmissions] = useState<WardAdmission[]>([]);
  const [selectedAdmission, setSelectedAdmission] = useState<WardAdmission | null>(null);
  const [bedForm, setBedForm] = useState(emptyBedForm);
  const [admissionForm, setAdmissionForm] = useState(emptyAdmissionForm);
  const [observationForm, setObservationForm] = useState(emptyObservationForm);
  const [showBedDialog, setShowBedDialog] = useState(false);
  const [showAdmissionDialog, setShowAdmissionDialog] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const dashboardPath = getFacilityDashboardPath(facilitySlug);

  const paths = {
    patients: `/dashboard/${facilitySlug}/patients`,
    records: `/dashboard/${facilitySlug}/records`,
    pharmacy: `/dashboard/${facilitySlug}/pharmacy`,
    queue: `/dashboard/${facilitySlug}/queue`,
  };

  const loadData = async () => {
    setLoading(true);
    try {
      const [patientResponse, bedResponse, admissionResponse] = await Promise.all([
        apiClient.get<PatientListResponse>("/patients?page=1&per_page=100"),
        apiClient.get<WardBed[]>("/wards/beds"),
        apiClient.get<WardAdmission[]>("/wards/admissions?status=ACTIVE"),
      ]);
      setPatients(patientResponse.patients);
      setBeds(bedResponse);
      setAdmissions(admissionResponse);
      if (selectedAdmission) {
        const refreshed = admissionResponse.find((item) => item.id === selectedAdmission.id);
        setSelectedAdmission(refreshed || null);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData().catch(() => setLoading(false));
  }, []);

  const patientById = useMemo(
    () => new Map(patients.map((patient) => [patient.id, patient])),
    [patients]
  );

  const summary = useMemo(
    () => ({
      beds: beds.length,
      available: beds.filter((bed) => bed.status === "AVAILABLE").length,
      active: admissions.length,
      urgent: admissions.filter((admission) => admission.acuity === "urgent").length,
    }),
    [admissions, beds]
  );

  const patientName = (patientId: string) => {
    const patient = patientById.get(patientId);
    return (
      patient?.full_name ||
      [patient?.first_name, patient?.last_name].filter(Boolean).join(" ") ||
      "Unknown patient"
    );
  };

  const createBed = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!bedForm.ward_name.trim() || !bedForm.bed_number.trim()) {
      setError("Ward name and bed number are required.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      await apiClient.post<WardBed>("/wards/beds", {
        ward_name: bedForm.ward_name.trim(),
        bed_number: bedForm.bed_number.trim(),
        notes: bedForm.notes.trim() || undefined,
      });
      setBedForm(emptyBedForm);
      setShowBedDialog(false);
      await loadData();
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : "Bed could not be created.");
    } finally {
      setSaving(false);
    }
  };

  const admitPatient = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!admissionForm.patient_id || !admissionForm.ward_name.trim()) {
      setError("Patient and ward are required.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      const admission = await apiClient.post<WardAdmission>("/wards/admissions", {
        patient_id: admissionForm.patient_id,
        bed_id: admissionForm.bed_id || undefined,
        ward_name: admissionForm.ward_name.trim(),
        reason: admissionForm.reason.trim() || undefined,
        acuity: admissionForm.acuity,
      });
      setAdmissionForm(emptyAdmissionForm);
      setSelectedAdmission(admission);
      setShowAdmissionDialog(false);
      await loadData();
    } catch (admitError) {
      setError(admitError instanceof Error ? admitError.message : "Admission could not be created.");
    } finally {
      setSaving(false);
    }
  };

  const addObservation = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selectedAdmission) {
      return;
    }
    setSaving(true);
    setError("");
    try {
      const updated = await apiClient.post<WardAdmission>(
        `/wards/admissions/${selectedAdmission.id}/observations`,
        observationPayload(observationForm)
      );
      setSelectedAdmission(updated);
      setObservationForm(emptyObservationForm);
      await loadData();
    } catch (observationError) {
      setError(
        observationError instanceof Error
          ? observationError.message
          : "Observation could not be recorded."
      );
    } finally {
      setSaving(false);
    }
  };

  const dischargeAdmission = async () => {
    if (!selectedAdmission) {
      return;
    }
    setSaving(true);
    setError("");
    try {
      await apiClient.post<WardAdmission>(`/wards/admissions/${selectedAdmission.id}/discharge`);
      setSelectedAdmission(null);
      await loadData();
    } catch (dischargeError) {
      setError(dischargeError instanceof Error ? dischargeError.message : "Discharge failed.");
    } finally {
      setSaving(false);
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
              onClick={() => navigate(dashboardPath)}
            >
              <ArrowLeft className="h-4 w-4" /> Dashboard
            </Button>
            <h1 className="text-2xl font-extrabold tracking-tight">Nursing & Wards</h1>
            <p className="text-sm text-muted-foreground">
              Manage beds, admissions, nursing observations, medication rounds, and discharge.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" className="gap-2" onClick={() => setShowBedDialog(true)}>
              <Plus className="h-4 w-4" /> Bed
            </Button>
            <Button className="gradient-cta gap-2 border-0 text-primary-foreground" onClick={() => setShowAdmissionDialog(true)}>
              <BedDouble className="h-4 w-4" /> Admit
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-6 p-6">
        <div className="grid gap-4 md:grid-cols-4">
          <Metric label="Beds" value={String(summary.beds)} icon={BedDouble} />
          <Metric label="Available" value={String(summary.available)} icon={ClipboardList} />
          <Metric label="Active Care" value={String(summary.active)} icon={Activity} />
          <Metric label="Urgent" value={String(summary.urgent)} icon={FileText} />
        </div>

        <div className="grid gap-6 lg:grid-cols-[.95fr_1.05fr]">
          <Card className="border-border/60">
            <CardHeader>
              <CardTitle className="text-base">Active Admissions</CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? (
                <p className="py-8 text-center text-sm text-muted-foreground">Loading ward workspace...</p>
              ) : admissions.length === 0 ? (
                <p className="py-8 text-center text-sm text-muted-foreground">
                  No active ward admissions.
                </p>
              ) : (
                <div className="space-y-3">
                  {admissions.map((admission) => (
                    <button
                      key={admission.id}
                      type="button"
                      onClick={() => setSelectedAdmission(admission)}
                      className={`w-full rounded-xl border p-4 text-left transition-colors ${
                        selectedAdmission?.id === admission.id
                          ? "border-primary bg-primary/5"
                          : "border-border/60 bg-card hover:border-primary/30"
                      }`}
                    >
                      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                        <div>
                          <div className="flex flex-wrap items-center gap-2">
                            <p className="font-semibold text-foreground">
                              {admission.patient_name || patientName(admission.patient_id)}
                            </p>
                            <Badge variant={admission.acuity === "urgent" ? "destructive" : "secondary"}>
                              {admission.acuity}
                            </Badge>
                            <Badge variant="outline">{admission.status}</Badge>
                          </div>
                          <p className="mt-1 text-sm text-muted-foreground">
                            {admission.ward_name}
                            {admission.bed_number ? ` · Bed ${admission.bed_number}` : " · No bed assigned"}
                          </p>
                          <p className="mt-1 text-xs text-muted-foreground">
                            {admission.reason || "No admission reason recorded"}
                          </p>
                        </div>
                        <span className="text-xs text-muted-foreground">
                          {new Date(admission.admitted_at).toLocaleString()}
                        </span>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="border-border/60">
            <CardHeader>
              <CardTitle className="text-base">
                {selectedAdmission ? selectedAdmission.patient_name : "Nursing Record"}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {!selectedAdmission ? (
                <div className="py-16 text-center">
                  <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-muted">
                    <BedDouble className="h-6 w-6 text-muted-foreground" />
                  </div>
                  <p className="font-semibold text-foreground">No admission selected</p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Select a patient admission to record observations.
                  </p>
                </div>
              ) : (
                <div className="space-y-5">
                  <div className="grid gap-3 sm:grid-cols-3">
                    <Info label="Ward" value={selectedAdmission.ward_name} />
                    <Info label="Bed" value={selectedAdmission.bed_number || "Unassigned"} />
                    <Info label="Notes" value={String(selectedAdmission.nursing_notes.length)} />
                  </div>

                  <form onSubmit={addObservation} className="grid gap-4 sm:grid-cols-2">
                    <Field label="Temperature" value={observationForm.temperature} onChange={(value) => setObservationForm((current) => ({ ...current, temperature: value }))} />
                    <Field label="Blood Pressure" value={observationForm.blood_pressure} onChange={(value) => setObservationForm((current) => ({ ...current, blood_pressure: value }))} />
                    <Field label="Pulse" value={observationForm.pulse} onChange={(value) => setObservationForm((current) => ({ ...current, pulse: value }))} />
                    <Field label="Respiratory Rate" value={observationForm.respiratory_rate} onChange={(value) => setObservationForm((current) => ({ ...current, respiratory_rate: value }))} />
                    <div className="sm:col-span-2">
                      <Label>Nursing Note</Label>
                      <Textarea
                        className="mt-1.5 min-h-20"
                        value={observationForm.note}
                        onChange={(event) => setObservationForm((current) => ({ ...current, note: event.target.value }))}
                      />
                    </div>
                    <div className="sm:col-span-2">
                      <Label>Medication Round</Label>
                      <Input
                        className="mt-1.5"
                        value={observationForm.medication_round}
                        onChange={(event) => setObservationForm((current) => ({ ...current, medication_round: event.target.value }))}
                      />
                    </div>
                    {error && <FormError message={error} />}
                    <div className="flex flex-col gap-3 sm:col-span-2 sm:flex-row sm:justify-end">
                      <Button type="button" variant="outline" asChild>
                        <Link to={paths.records}>
                          <FileText className="mr-2 h-4 w-4" /> Records
                        </Link>
                      </Button>
                      <Button type="button" variant="outline" asChild>
                        <Link to={paths.pharmacy}>
                          <Pill className="mr-2 h-4 w-4" /> Medication
                        </Link>
                      </Button>
                      <Button type="submit" disabled={saving} className="gap-2">
                        <Save className="h-4 w-4" /> Save
                      </Button>
                      <Button type="button" disabled={saving} variant="destructive" onClick={dischargeAdmission}>
                        Discharge
                      </Button>
                    </div>
                  </form>

                  <div className="space-y-2">
                    <p className="text-sm font-semibold text-foreground">Latest Observations</p>
                    {selectedAdmission.observations.length === 0 ? (
                      <p className="text-sm text-muted-foreground">No observations recorded yet.</p>
                    ) : (
                      selectedAdmission.observations.slice(-4).reverse().map((entry, index) => (
                        <div key={`${selectedAdmission.id}-${index}`} className="rounded-xl border border-border/60 p-3 text-sm">
                          <p className="font-medium text-foreground">
                            {typeof entry.note === "string" ? entry.note : "Observation recorded"}
                          </p>
                          <p className="mt-1 text-xs text-muted-foreground">
                            {typeof entry.medication_round === "string" && entry.medication_round
                              ? entry.medication_round
                              : "No medication note"}
                          </p>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        <Card className="border-border/60">
          <CardHeader>
            <CardTitle className="text-base">Bed Board</CardTitle>
          </CardHeader>
          <CardContent>
            {beds.length === 0 ? (
              <p className="py-8 text-center text-sm text-muted-foreground">
                No beds have been added yet.
              </p>
            ) : (
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                {beds.map((bed) => (
                  <div key={bed.id} className="rounded-xl border border-border/60 p-4">
                    <div className="flex items-center justify-between gap-2">
                      <p className="font-semibold text-foreground">{bed.bed_number}</p>
                      <Badge variant={bed.status === "AVAILABLE" ? "secondary" : bed.status === "OCCUPIED" ? "default" : "outline"}>
                        {bed.status}
                      </Badge>
                    </div>
                    <p className="mt-1 text-sm text-muted-foreground">{bed.ward_name}</p>
                    {bed.notes && <p className="mt-2 text-xs text-muted-foreground">{bed.notes}</p>}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <div className="flex justify-end">
          <Button asChild variant="outline" className="gap-2">
            <Link to={paths.patients}>
              <Users className="h-4 w-4" /> Patient Registry
            </Link>
          </Button>
        </div>
      </main>

      <Dialog open={showBedDialog} onOpenChange={setShowBedDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Bed</DialogTitle>
            <DialogDescription>Create a bed for admission tracking.</DialogDescription>
          </DialogHeader>
          <form onSubmit={createBed} className="space-y-4">
            <Field label="Ward" value={bedForm.ward_name} onChange={(value) => setBedForm((current) => ({ ...current, ward_name: value }))} />
            <Field label="Bed Number" value={bedForm.bed_number} onChange={(value) => setBedForm((current) => ({ ...current, bed_number: value }))} />
            <div>
              <Label>Notes</Label>
              <Textarea className="mt-1.5" value={bedForm.notes} onChange={(event) => setBedForm((current) => ({ ...current, notes: event.target.value }))} />
            </div>
            {error && <FormError message={error} />}
            <DialogActions disabled={saving} submitLabel="Create Bed" onCancel={() => setShowBedDialog(false)} />
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={showAdmissionDialog} onOpenChange={setShowAdmissionDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Admit Patient</DialogTitle>
            <DialogDescription>Assign a patient to a ward and available bed.</DialogDescription>
          </DialogHeader>
          <form onSubmit={admitPatient} className="space-y-4">
            <div>
              <Label>Patient</Label>
              <Select value={admissionForm.patient_id} onValueChange={(value) => setAdmissionForm((current) => ({ ...current, patient_id: value }))}>
                <SelectTrigger className="mt-1.5">
                  <SelectValue placeholder="Select patient" />
                </SelectTrigger>
                <SelectContent>
                  {patients.map((patient) => (
                    <SelectItem key={patient.id} value={patient.id}>
                      {patient.full_name || `${patient.first_name} ${patient.last_name}`}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Field label="Ward" value={admissionForm.ward_name} onChange={(value) => setAdmissionForm((current) => ({ ...current, ward_name: value }))} />
            <div>
              <Label>Bed</Label>
              <Select value={admissionForm.bed_id || "none"} onValueChange={(value) => setAdmissionForm((current) => ({ ...current, bed_id: value === "none" ? "" : value }))}>
                <SelectTrigger className="mt-1.5">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">No bed assigned</SelectItem>
                  {beds.filter((bed) => bed.status === "AVAILABLE").map((bed) => (
                    <SelectItem key={bed.id} value={bed.id}>
                      {bed.ward_name} · {bed.bed_number}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Acuity</Label>
              <Select value={admissionForm.acuity} onValueChange={(value) => setAdmissionForm((current) => ({ ...current, acuity: value }))}>
                <SelectTrigger className="mt-1.5">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="normal">Normal</SelectItem>
                  <SelectItem value="urgent">Urgent</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Reason</Label>
              <Textarea className="mt-1.5" value={admissionForm.reason} onChange={(event) => setAdmissionForm((current) => ({ ...current, reason: event.target.value }))} />
            </div>
            {error && <FormError message={error} />}
            <DialogActions disabled={saving} submitLabel="Admit Patient" onCancel={() => setShowAdmissionDialog(false)} />
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
};

const Metric = ({ label, value, icon: Icon }: { label: string; value: string; icon: React.ElementType }) => (
  <Card className="border-border/60">
    <CardContent className="flex items-center gap-3 p-5">
      <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10">
        <Icon className="h-5 w-5 text-primary" />
      </div>
      <div>
        <p className="text-2xl font-extrabold text-foreground">{value}</p>
        <p className="text-xs text-muted-foreground">{label}</p>
      </div>
    </CardContent>
  </Card>
);

const Info = ({ label, value }: { label: string; value: string }) => (
  <div className="rounded-xl border border-border/60 p-3">
    <p className="text-xs text-muted-foreground">{label}</p>
    <p className="mt-1 truncate font-semibold text-foreground">{value}</p>
  </div>
);

const Field = ({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) => (
  <div>
    <Label>{label}</Label>
    <Input className="mt-1.5" value={value} onChange={(event) => onChange(event.target.value)} />
  </div>
);

const DialogActions = ({
  disabled,
  submitLabel,
  onCancel,
}: {
  disabled: boolean;
  submitLabel: string;
  onCancel: () => void;
}) => (
  <div className="flex gap-3">
    <Button type="button" variant="outline" className="flex-1" onClick={onCancel}>
      Cancel
    </Button>
    <Button type="submit" disabled={disabled} className="gradient-cta flex-1 border-0 text-primary-foreground">
      {submitLabel}
    </Button>
  </div>
);

const FormError = ({ message }: { message: string }) => (
  <p className="rounded-lg border border-destructive/20 bg-destructive/10 px-3 py-2 text-sm text-destructive">
    {message}
  </p>
);

export default Wards;
