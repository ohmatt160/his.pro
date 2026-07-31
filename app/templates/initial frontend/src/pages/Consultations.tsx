import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTenantParams } from "@/context/TenantRoutingContext";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  CalendarDays,
  CheckCircle2,
  ClipboardList,
  FileHeart,
  FlaskConical,
  Pill,
  Save,
  ScanLine,
  Stethoscope,
  Users,
} from "lucide-react";
import { apiClient } from "@/api/client";
import { getPatientOptions } from "@/api/patients";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  type Consultation,
  emptyConsultationForm,
  formFromConsultation,
  payloadFromConsultationForm,
} from "@/lib/consultations";
import { getWorkspaceDashboardPath, getWorkspaceRoutePath } from "@/lib/facility-workspace";
import {
  addSettledError,
  hasResourceErrors,
  settledValue,
  type ResourceErrors,
} from "@/lib/resource-loading";
import { useRealtimeRefresh } from "@/hooks/useRealtimeRefresh";

type Appointment = {
  id: string;
  patient_id: string;
  appointment_date: string;
  scheduled_time?: string | null;
  status: string;
  reason?: string | null;
};

type Patient = {
  id: string;
  first_name: string;
  last_name: string;
  full_name?: string;
};

type PatientListResponse = {
  patients: Patient[];
};

type ConsultationResource = "appointments" | "patients" | "consultations";

const activeAppointmentStatuses = ["SCHEDULED", "CONFIRMED", "IN_PROGRESS"];

const Consultations = () => {
  const navigate = useNavigate();
  const { facilitySlug = "", branchSlug = "" } = useTenantParams();
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [consultations, setConsultations] = useState<Consultation[]>([]);
  const [activeConsultation, setActiveConsultation] = useState<Consultation | null>(null);
  const [form, setForm] = useState(emptyConsultationForm);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [dataErrors, setDataErrors] = useState<ResourceErrors<ConsultationResource>>({});
  const dashboardPath = getWorkspaceDashboardPath(facilitySlug, branchSlug || undefined);

  const paths = {
    patients: getWorkspaceRoutePath(facilitySlug, "patients", branchSlug || undefined),
    records: getWorkspaceRoutePath(facilitySlug, "records", branchSlug || undefined),
    appointments: getWorkspaceRoutePath(facilitySlug, "appointments", branchSlug || undefined),
    laboratory: getWorkspaceRoutePath(facilitySlug, "laboratory", branchSlug || undefined),
    pharmacy: getWorkspaceRoutePath(facilitySlug, "pharmacy", branchSlug || undefined),
    radiology: getWorkspaceRoutePath(facilitySlug, "radiology", branchSlug || undefined),
  };

  const loadData = async () => {
    setLoading(true);
    try {
      const [appointmentResponse, patientResponse, consultationResponse] =
        await Promise.allSettled([
          apiClient.get<Appointment[]>("/appointments"),
          getPatientOptions<Patient>(),
          apiClient.get<Consultation[]>("/consultations"),
        ]);

      const errors: ResourceErrors<ConsultationResource> = {};
      addSettledError(errors, "appointments", appointmentResponse, "Appointments could not be loaded.");
      addSettledError(errors, "patients", patientResponse, "Patients could not be loaded.");
      addSettledError(errors, "consultations", consultationResponse, "Consultations could not be loaded.");

      const nextAppointments = settledValue(appointmentResponse, []);
      const nextPatients = settledValue(patientResponse, { patients: [] }).patients;
      const nextConsultations = settledValue(consultationResponse, []);

      setAppointments(nextAppointments);
      setPatients(nextPatients);
      setConsultations(nextConsultations);
      setDataErrors(errors);

      if (activeConsultation) {
        const refreshed = nextConsultations.find((item) => item.id === activeConsultation.id);
        if (refreshed) {
          setActiveConsultation(refreshed);
          setForm(formFromConsultation(refreshed));
        }
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData().catch(() => {
      setLoading(false);
    });
  }, []);

  useRealtimeRefresh({
    eventTypes: ["consultation.*", "appointment.*", "patient.*", "lab_order.*", "prescription.*", "radiology.*"],
    onRefresh: () => loadData().catch(() => undefined),
  });

  const patientById = useMemo(
    () => new Map(patients.map((patient) => [patient.id, patient])),
    [patients]
  );

  const consultationByAppointment = useMemo(
    () =>
      new Map(
        consultations
          .filter((consultation) => consultation.appointment_id)
          .map((consultation) => [consultation.appointment_id, consultation])
      ),
    [consultations]
  );

  const worklist = appointments
    .filter((appointment) =>
      activeAppointmentStatuses.includes(appointment.status.toUpperCase())
    )
    .sort(
      (left, right) =>
        new Date(left.scheduled_time || left.appointment_date).getTime() -
        new Date(right.scheduled_time || right.appointment_date).getTime()
    );

  const completedCount = consultations.filter((item) => item.status === "completed").length;

  const patientName = (patientId: string) => {
    const patient = patientById.get(patientId);
    return (
      patient?.full_name ||
      [patient?.first_name, patient?.last_name].filter(Boolean).join(" ") ||
      "Unknown patient"
    );
  };

  const setField = (key: keyof typeof emptyConsultationForm, value: string) => {
    setForm((current) => ({ ...current, [key]: value }));
    setError("");
  };

  const startConsultation = async (appointment: Appointment) => {
    setSaving(true);
    setError("");
    try {
      const consultation = await apiClient.post<Consultation>("/consultations/start", {
        patient_id: appointment.patient_id,
        appointment_id: appointment.id,
        chief_complaint: appointment.reason || "",
      });
      setActiveConsultation(consultation);
      setForm(formFromConsultation(consultation));
      await loadData();
    } catch (startError) {
      setError(startError instanceof Error ? startError.message : "Consultation could not be started.");
    } finally {
      setSaving(false);
    }
  };

  const openConsultation = (consultation: Consultation) => {
    setActiveConsultation(consultation);
    setForm(formFromConsultation(consultation));
    setError("");
  };

  const saveConsultation = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!activeConsultation) {
      return;
    }

    setSaving(true);
    setError("");
    try {
      const updated = await apiClient.put<Consultation>(
        `/consultations/${activeConsultation.id}`,
        payloadFromConsultationForm(form)
      );
      setActiveConsultation(updated);
      setForm(formFromConsultation(updated));
      await loadData();
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Consultation could not be saved.");
    } finally {
      setSaving(false);
    }
  };

  const completeConsultation = async () => {
    if (!activeConsultation) {
      return;
    }

    setSaving(true);
    setError("");
    try {
      const completed = await apiClient.post<Consultation>(
        `/consultations/${activeConsultation.id}/complete`
      );
      setActiveConsultation(completed);
      setForm(formFromConsultation(completed));
      await loadData();
    } catch (completeError) {
      setError(
        completeError instanceof Error
          ? completeError.message
          : "Consultation could not be completed."
      );
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
            <h1 className="text-2xl font-extrabold tracking-tight">Consultations</h1>
            <p className="text-sm text-muted-foreground">
              Start patient visits, record clinical notes, place orders, and close encounters.
            </p>
          </div>
          <Button asChild className="gradient-cta gap-2 border-0 text-primary-foreground">
            <Link to={paths.appointments}>
              <CalendarDays className="h-4 w-4" /> Schedule Visit
            </Link>
          </Button>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-6 p-6">
        {hasResourceErrors(dataErrors) && (
          <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
            Some consultation data could not be loaded. Available sections are still usable.
          </div>
        )}

        <div className="grid gap-4 md:grid-cols-4">
          <Metric label="Worklist" value={String(worklist.length)} icon={ClipboardList} />
          <Metric label="Open Notes" value={String(consultations.length - completedCount)} icon={FileHeart} />
          <Metric label="Completed" value={String(completedCount)} icon={CheckCircle2} />
          <Metric label="Patients" value={String(patients.length)} icon={Users} />
        </div>

        <div className="grid gap-6 lg:grid-cols-[.85fr_1.15fr]">
          <Card className="border-border/60">
            <CardHeader>
              <CardTitle className="text-base">Doctor Worklist</CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? (
                <p className="py-8 text-center text-sm text-muted-foreground">
                  Loading consultations...
                </p>
              ) : worklist.length === 0 ? (
                <p className="py-8 text-center text-sm text-muted-foreground">
                  No active appointments are ready for consultation.
                </p>
              ) : (
                <div className="space-y-3">
                  {worklist.slice(0, 20).map((appointment, index) => {
                    const consultation = consultationByAppointment.get(appointment.id);
                    const scheduledAt = appointment.scheduled_time || appointment.appointment_date;
                    return (
                      <motion.div
                        key={appointment.id}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: index * 0.03 }}
                        className="rounded-xl border border-border/60 bg-card p-4"
                      >
                        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                          <div>
                            <div className="flex flex-wrap items-center gap-2">
                              <p className="font-semibold text-foreground">
                                {patientName(appointment.patient_id)}
                              </p>
                              <Badge variant="outline">
                                {appointment.status.replaceAll("_", " ")}
                              </Badge>
                            </div>
                            <p className="mt-1 text-sm text-muted-foreground">
                              {appointment.reason || "Consultation"} ·{" "}
                              {new Date(scheduledAt).toLocaleString()}
                            </p>
                          </div>
                          {consultation ? (
                            <Button size="sm" variant="outline" onClick={() => openConsultation(consultation)}>
                              Open Note
                            </Button>
                          ) : (
                            <Button
                              size="sm"
                              className="gradient-cta border-0 text-primary-foreground"
                              disabled={saving}
                              onClick={() => startConsultation(appointment)}
                            >
                              Start
                            </Button>
                          )}
                        </div>
                      </motion.div>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="border-border/60">
            <CardHeader>
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <CardTitle className="text-base">Clinical Note</CardTitle>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {activeConsultation
                      ? `${activeConsultation.patient_name} · ${activeConsultation.status.replaceAll("_", " ")}`
                      : "Select or start a consultation from the worklist."}
                  </p>
                </div>
                {activeConsultation && (
                  <Badge variant={activeConsultation.status === "completed" ? "default" : "outline"}>
                    {activeConsultation.status.replaceAll("_", " ")}
                  </Badge>
                )}
              </div>
            </CardHeader>
            <CardContent>
              {!activeConsultation ? (
                <div className="py-16 text-center">
                  <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-muted">
                    <Stethoscope className="h-6 w-6 text-muted-foreground" />
                  </div>
                  <p className="font-semibold text-foreground">No consultation selected</p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Start with a patient appointment to open the doctor workspace.
                  </p>
                </div>
              ) : (
                <form onSubmit={saveConsultation} className="grid gap-4 sm:grid-cols-2">
                  <div className="sm:col-span-2">
                    <Label>Chief Complaint</Label>
                    <Textarea
                      className="mt-1.5 min-h-20"
                      value={form.chief_complaint}
                      onChange={(event) => setField("chief_complaint", event.target.value)}
                    />
                  </div>

                  <Field label="Temperature" value={form.temperature} onChange={(value) => setField("temperature", value)} />
                  <Field label="Blood Pressure" value={form.blood_pressure} onChange={(value) => setField("blood_pressure", value)} />
                  <Field label="Pulse" value={form.pulse} onChange={(value) => setField("pulse", value)} />
                  <Field label="Respiratory Rate" value={form.respiratory_rate} onChange={(value) => setField("respiratory_rate", value)} />
                  <Field label="Symptoms" value={form.symptoms} placeholder="Comma-separated" onChange={(value) => setField("symptoms", value)} />
                  <Field label="Diagnosis" value={form.diagnosis} placeholder="Comma-separated" onChange={(value) => setField("diagnosis", value)} />
                  <Field label="Prescriptions" value={form.prescriptions} placeholder="Medication names" onChange={(value) => setField("prescriptions", value)} />
                  <Field label="Follow-up Date" type="date" value={form.follow_up_date} onChange={(value) => setField("follow_up_date", value)} />
                  <Field label="Lab Orders" value={form.lab_orders} placeholder="FBC, Malaria test" onChange={(value) => setField("lab_orders", value)} />
                  <Field label="Radiology Orders" value={form.radiology_orders} placeholder="Chest X-ray, Ultrasound" onChange={(value) => setField("radiology_orders", value)} />

                  <div className="sm:col-span-2">
                    <Label>Treatment Plan</Label>
                    <Textarea
                      className="mt-1.5 min-h-24"
                      value={form.treatment_plan}
                      onChange={(event) => setField("treatment_plan", event.target.value)}
                    />
                  </div>
                  <div className="sm:col-span-2">
                    <Label>Notes</Label>
                    <Textarea
                      className="mt-1.5 min-h-24"
                      value={form.notes}
                      onChange={(event) => setField("notes", event.target.value)}
                    />
                  </div>

                  {error && (
                    <p className="rounded-lg border border-destructive/20 bg-destructive/10 px-3 py-2 text-sm text-destructive sm:col-span-2">
                      {error}
                    </p>
                  )}

                  <div className="flex flex-col gap-3 sm:col-span-2 sm:flex-row sm:justify-end">
                    <Button type="button" variant="outline" asChild>
                      <Link to={paths.records}>Records</Link>
                    </Button>
                    <Button type="button" variant="outline" asChild>
                      <Link to={paths.laboratory}>
                        <FlaskConical className="mr-2 h-4 w-4" /> Lab
                      </Link>
                    </Button>
                    <Button type="button" variant="outline" asChild>
                      <Link to={paths.radiology}>
                        <ScanLine className="mr-2 h-4 w-4" /> Imaging
                      </Link>
                    </Button>
                    <Button type="submit" disabled={saving} className="gap-2">
                      <Save className="h-4 w-4" /> Save
                    </Button>
                    <Button
                      type="button"
                      disabled={saving || activeConsultation.status === "completed"}
                      className="gradient-cta border-0 text-primary-foreground"
                      onClick={completeConsultation}
                    >
                      Complete
                    </Button>
                  </div>
                </form>
              )}
            </CardContent>
          </Card>
        </div>

        <div className="flex flex-wrap justify-end gap-2">
          <Button asChild variant="outline" className="gap-2">
            <Link to={paths.pharmacy}>
              <Pill className="h-4 w-4" /> Pharmacy
            </Link>
          </Button>
          <Button asChild variant="outline" className="gap-2">
            <Link to={paths.patients}>
              <Users className="h-4 w-4" /> Patient Registry
            </Link>
          </Button>
        </div>
      </main>
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

const Field = ({
  label,
  value,
  onChange,
  type = "text",
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
  placeholder?: string;
}) => (
  <div>
    <Label>{label}</Label>
    <Input
      className="mt-1.5"
      type={type}
      value={value}
      placeholder={placeholder}
      onChange={(event) => onChange(event.target.value)}
    />
  </div>
);

export default Consultations;
