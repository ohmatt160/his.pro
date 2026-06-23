import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Activity,
  ArrowLeft,
  CalendarClock,
  CalendarDays,
  CheckCircle2,
  Clock,
  ListChecks,
  Plus,
  Search,
  Stethoscope,
  Users,
} from "lucide-react";
import { apiClient } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
import {
  getFacilityClinicians,
  getStaffAccessPath,
  type FacilityStaffAccount,
} from "@/lib/facility-staff";
import { getWorkspaceDashboardPath, getWorkspaceRoutePath } from "@/lib/facility-workspace";
import { addSettledError, getResourceError, settledValue } from "@/lib/resource-loading";

type Patient = {
  id: string;
  full_name?: string;
  first_name: string;
  last_name: string;
  phone?: string | null;
};

type PatientListResponse = {
  patients: Patient[];
  total: number;
};

type Appointment = {
  id: string;
  patient_id: string;
  doctor_id: string;
  appointment_date: string;
  scheduled_time?: string | null;
  duration_minutes: number;
  status: string;
  reason?: string | null;
  notes?: string | null;
};

type QueueEntry = {
  id: string;
  patient_id: string;
  appointment_id?: string | null;
  patient_name?: string | null;
  department: string;
  status: string;
  queue_number: number;
  priority: string;
};

type AppointmentResourceName = "patients" | "clinicians" | "appointments" | "queue";

type AppointmentResourceState = {
  patients: Patient[];
  clinicians: FacilityStaffAccount[];
  appointments: Appointment[];
  queue: QueueEntry[];
  errors: Partial<Record<AppointmentResourceName, string>>;
};

const emptyForm = {
  patient_id: "",
  doctor_id: "",
  date: "",
  time: "",
  duration_minutes: "30",
  reason: "",
  notes: "",
};

export const loadAppointmentResources = async (
  facilitySlug: string
): Promise<AppointmentResourceState> => {
  const [patientResult, staffResult, appointmentResult, queueResult] =
    await Promise.allSettled([
      apiClient.get<PatientListResponse>("/patients?page=1&per_page=100"),
      getFacilityClinicians(facilitySlug),
      apiClient.get<Appointment[]>("/appointments"),
      apiClient.get<{ queue_entries: QueueEntry[] }>("/queue?per_page=100"),
    ]);

  const errors: AppointmentResourceState["errors"] = {};
  addSettledError(errors, "patients", patientResult, "Patients could not be loaded.");
  addSettledError(errors, "clinicians", staffResult, "Clinicians could not be loaded.");
  addSettledError(errors, "appointments", appointmentResult, "Appointments could not be loaded.");
  addSettledError(errors, "queue", queueResult, "Queue could not be loaded.");

  return {
    patients: settledValue(patientResult, { patients: [], total: 0 }).patients,
    clinicians: settledValue(staffResult, []),
    appointments: settledValue(appointmentResult, []),
    queue: settledValue(queueResult, { queue_entries: [] }).queue_entries,
    errors,
  };
};

const Appointments = () => {
  const navigate = useNavigate();
  const { facilitySlug = "", branchSlug = "" } = useParams();
  const [patients, setPatients] = useState<Patient[]>([]);
  const [staff, setStaff] = useState<FacilityStaffAccount[]>([]);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [queue, setQueue] = useState<QueueEntry[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [error, setError] = useState("");
  const [dataErrors, setDataErrors] = useState<AppointmentResourceState["errors"]>({});

  const dashboardPath = getWorkspaceDashboardPath(facilitySlug, branchSlug || undefined);
  const patientsPath = getWorkspaceRoutePath(facilitySlug, "patients", branchSlug || undefined);
  const staffPath = getStaffAccessPath(facilitySlug);

  const clinicians = useMemo(
    () => staff.filter((member) => member.role === "doctor" || member.role === "admin"),
    [staff]
  );

  const patientById = useMemo(
    () => new Map(patients.map((patient) => [patient.id, patient])),
    [patients]
  );

  const loadData = async () => {
    setLoading(true);
    try {
      const resources = await loadAppointmentResources(facilitySlug);
      setPatients(resources.patients);
      setStaff(resources.clinicians);
      setAppointments(resources.appointments);
      setQueue(resources.queue);
      setDataErrors(resources.errors);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData().catch(() => setLoading(false));
  }, [facilitySlug]);

  const filteredAppointments = appointments.filter((appointment) => {
    const query = search.trim().toLowerCase();
    if (!query) {
      return true;
    }
    const patient = patientById.get(appointment.patient_id);
    const patientName =
      patient?.full_name || `${patient?.first_name || ""} ${patient?.last_name || ""}`;
    return (
      patientName.toLowerCase().includes(query) ||
      appointment.status.toLowerCase().includes(query) ||
      (appointment.reason || "").toLowerCase().includes(query)
    );
  });

  const updateForm = (key: keyof typeof emptyForm, value: string) => {
    setForm((current) => ({ ...current, [key]: value }));
    setError("");
  };

  const handleCreate = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const doctorId = form.doctor_id || clinicians[0]?.staffRecordId || "";
    if (!form.patient_id || !doctorId || !form.date || !form.time) {
      setError("Patient, clinician, date, and time are required.");
      return;
    }

    try {
      await apiClient.post<Appointment>("/appointments", {
        patient_id: form.patient_id,
        doctor_id: doctorId,
        appointment_date: `${form.date}T${form.time}:00`,
        duration_minutes: Number(form.duration_minutes) || 30,
        reason: form.reason.trim() || undefined,
        notes: form.notes.trim() || undefined,
      });
      setForm(emptyForm);
      setShowCreate(false);
      await loadData();
    } catch (createError) {
      setError(
        createError instanceof Error
          ? createError.message
          : "Appointment scheduling failed."
      );
    }
  };

  const updateStatus = async (appointmentId: string, status: string) => {
    try {
      await apiClient.put<Appointment>(`/appointments/${appointmentId}`, { status });
      await loadData();
    } catch (statusError) {
      setError(getResourceError(statusError, "Appointment status could not be updated."));
    }
  };

  const addToQueue = async (appointment: Appointment) => {
    try {
      await apiClient.post<QueueEntry>("/queue", {
        patient_id: appointment.patient_id,
        appointment_id: appointment.id,
        department: "Front Desk",
        priority: "normal",
      });
      await loadData();
    } catch (queueError) {
      setError(getResourceError(queueError, "Patient could not be added to queue."));
    }
  };

  const isInQueue = (appointmentId: string) =>
    queue.some((entry) => entry.appointment_id === appointmentId);

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
            <h1 className="text-2xl font-extrabold tracking-tight">
              Appointments & Queue
            </h1>
            <p className="text-sm text-muted-foreground">
              Schedule visits and move patients into today&apos;s queue.
            </p>
          </div>
          <div className="flex gap-2">
            <Button asChild variant="outline">
              <Link to={patientsPath}>Patients</Link>
            </Button>
            <Button asChild variant="outline">
              <Link to={staffPath}>Clinicians</Link>
            </Button>
            <Button
              onClick={() => setShowCreate(true)}
              className="gradient-cta gap-2 border-0 text-primary-foreground"
            >
              <Plus className="h-4 w-4" /> Schedule
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-6 p-6">
        {Object.keys(dataErrors).length > 0 && (
          <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
            Some appointment data could not be loaded. Available sections are still usable.
          </div>
        )}

        <div className="grid gap-4 md:grid-cols-4">
          <Metric label="Appointments" value={String(appointments.length)} icon={CalendarDays} />
          <Metric label="Scheduled" value={String(appointments.filter((item) => item.status === "SCHEDULED").length)} icon={Clock} />
          <Metric label="In Queue" value={String(queue.filter((item) => item.status === "waiting").length)} icon={ListChecks} />
          <Metric label="Completed" value={String(appointments.filter((item) => item.status === "COMPLETED").length)} icon={CheckCircle2} />
        </div>

        <div className="grid gap-6 lg:grid-cols-[1fr_.42fr]">
          <Card className="border-border/60">
            <CardHeader>
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <CardTitle className="text-base">Schedule</CardTitle>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                    placeholder="Search appointments"
                    className="w-64 pl-9"
                  />
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {loading ? (
                <p className="py-12 text-center text-sm text-muted-foreground">
                  Loading appointments...
                </p>
              ) : dataErrors.appointments ? (
                <SectionError
                  title="Appointments unavailable"
                  message="Patient and clinician selection can still work while appointments reload."
                  onRetry={loadData}
                />
              ) : filteredAppointments.length === 0 ? (
                <EmptyState onCreate={() => setShowCreate(true)} />
              ) : (
                <div className="space-y-2">
                  {filteredAppointments.map((appointment, index) => {
                    const patient = patientById.get(appointment.patient_id);
                    const patientName =
                      patient?.full_name ||
                      `${patient?.first_name || "Unknown"} ${patient?.last_name || "patient"}`;
                    const scheduledAt = appointment.scheduled_time || appointment.appointment_date;
                    return (
                      <motion.div
                        key={appointment.id}
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: index * 0.03 }}
                        className="grid gap-3 rounded-xl border border-border/60 p-4 md:grid-cols-[1.2fr_.8fr_.8fr_1fr]"
                      >
                        <div>
                          <p className="font-semibold text-foreground">{patientName}</p>
                          <p className="text-xs text-muted-foreground">
                            {appointment.reason || "General visit"}
                          </p>
                        </div>
                        <Info icon={CalendarClock} value={new Date(scheduledAt).toLocaleString()} />
                        <Info icon={Activity} value={appointment.status.replaceAll("_", " ")} />
                        <div className="flex flex-wrap justify-end gap-2">
                          {!isInQueue(appointment.id) && appointment.status !== "COMPLETED" && (
                            <Button size="sm" variant="outline" onClick={() => addToQueue(appointment)}>
                              Add to queue
                            </Button>
                          )}
                          {appointment.status !== "COMPLETED" && (
                            <Button size="sm" onClick={() => updateStatus(appointment.id, "COMPLETED")}>
                              Complete
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
              <CardTitle className="text-base">Active Queue</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {dataErrors.queue ? (
                <SectionError
                  title="Queue unavailable"
                  message="Scheduling still works; queue can be retried separately."
                  onRetry={loadData}
                />
              ) : queue.length === 0 ? (
                <p className="py-8 text-center text-sm text-muted-foreground">
                  No patients in queue.
                </p>
              ) : (
                queue.map((entry) => (
                  <div key={entry.id} className="rounded-xl border border-border/60 p-3">
                    <div className="flex items-center justify-between">
                      <p className="font-semibold text-foreground">
                        #{entry.queue_number} {entry.patient_name || "Patient"}
                      </p>
                      <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium capitalize text-primary">
                        {entry.status.replaceAll("_", " ")}
                      </span>
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {entry.department} · {entry.priority}
                    </p>
                  </div>
                ))
              )}
            </CardContent>
          </Card>
        </div>
      </main>

      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>Schedule Appointment</DialogTitle>
            <DialogDescription>
              Select a registered patient and clinician for the visit.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleCreate} className="grid gap-4 pt-2 sm:grid-cols-2">
            <div>
              <Label>Patient *</Label>
              <Select value={form.patient_id} onValueChange={(value) => updateForm("patient_id", value)}>
                <SelectTrigger className="mt-1.5">
                  <SelectValue placeholder="Select patient" />
                </SelectTrigger>
                <SelectContent>
                  {patients.length === 0 ? (
                    <SelectItem value="no-patients" disabled>
                      No patients found
                    </SelectItem>
                  ) : patients.map((patient) => (
                    <SelectItem key={patient.id} value={patient.id}>
                      {patient.full_name || `${patient.first_name} ${patient.last_name}`}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {patients.length === 0 && (
                <p className="mt-1 text-xs text-muted-foreground">
                  {dataErrors.patients
                    ? "Patients could not be loaded. Retry or check your session."
                    : "Register a patient first, then return to schedule."}
                </p>
              )}
            </div>
            <div>
              <Label>Clinician *</Label>
              <Select value={form.doctor_id} onValueChange={(value) => updateForm("doctor_id", value)}>
                <SelectTrigger className="mt-1.5">
                  <SelectValue placeholder="Select clinician" />
                </SelectTrigger>
                <SelectContent>
                  {clinicians.length === 0 ? (
                    <SelectItem value="no-clinicians" disabled>
                      No clinicians found
                    </SelectItem>
                  ) : clinicians.map((doctor) => (
                    <SelectItem key={doctor.staffRecordId} value={doctor.staffRecordId}>
                      {doctor.fullName} · {doctor.role === "admin" ? "Admin" : "Doctor"}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {clinicians.length === 0 && (
                <p className="mt-1 text-xs text-muted-foreground">
                  {dataErrors.clinicians
                    ? "Clinicians could not be loaded. Retry or add a clinician from Staff."
                    : "Add a doctor or active admin account before scheduling."}
                </p>
              )}
            </div>
            <Field label="Date" type="date" value={form.date} onChange={(value) => updateForm("date", value)} required />
            <Field label="Time" type="time" value={form.time} onChange={(value) => updateForm("time", value)} required />
            <Field label="Duration minutes" type="number" value={form.duration_minutes} onChange={(value) => updateForm("duration_minutes", value)} />
            <Field label="Reason" value={form.reason} onChange={(value) => updateForm("reason", value)} />
            <div className="sm:col-span-2">
              <Field label="Notes" value={form.notes} onChange={(value) => updateForm("notes", value)} />
            </div>
            {error && (
              <p className="rounded-lg border border-destructive/20 bg-destructive/10 px-3 py-2 text-sm text-destructive sm:col-span-2">
                {error}
              </p>
            )}
            <div className="flex gap-3 sm:col-span-2">
              <Button type="button" variant="outline" className="flex-1" onClick={() => setShowCreate(false)}>
                Cancel
              </Button>
              <Button type="submit" className="gradient-cta flex-1 border-0 text-primary-foreground">
                Schedule
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
};

const Metric = ({ label, value, icon: Icon }: { label: string; value: string; icon: React.ElementType }) => (
  <Card className="border-border/60">
    <CardContent className="flex items-center gap-4 p-5">
      <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10">
        <Icon className="h-5 w-5 text-primary" />
      </div>
      <div>
        <p className="text-2xl font-extrabold">{value}</p>
        <p className="text-xs text-muted-foreground">{label}</p>
      </div>
    </CardContent>
  </Card>
);

const Info = ({ icon: Icon, value }: { icon: React.ElementType; value: string }) => (
  <span className="flex min-w-0 items-center gap-2 text-sm text-muted-foreground">
    <Icon className="h-4 w-4 shrink-0" />
    <span className="truncate capitalize">{value}</span>
  </span>
);

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
    <Label>{label}{required ? " *" : ""}</Label>
    <Input className="mt-1.5" type={type} value={value} onChange={(event) => onChange(event.target.value)} required={required} />
  </div>
);

const EmptyState = ({ onCreate }: { onCreate: () => void }) => (
  <div className="py-16 text-center">
    <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-muted">
      <Stethoscope className="h-6 w-6 text-muted-foreground" />
    </div>
    <p className="font-semibold text-foreground">No appointments yet</p>
    <p className="mt-1 text-sm text-muted-foreground">
      Schedule the first patient visit.
    </p>
    <Button onClick={onCreate} className="gradient-cta mt-4 border-0 text-primary-foreground">
      Schedule Appointment
    </Button>
  </div>
);

const SectionError = ({
  title,
  message,
  onRetry,
}: {
  title: string;
  message: string;
  onRetry: () => void;
}) => (
  <div className="rounded-xl border border-dashed border-amber-200 bg-amber-50/60 px-4 py-8 text-center">
    <p className="font-semibold text-amber-900">{title}</p>
    <p className="mx-auto mt-1 max-w-sm text-sm text-amber-800">{message}</p>
    <Button type="button" variant="outline" size="sm" className="mt-4" onClick={onRetry}>
      Retry
    </Button>
  </div>
);

export default Appointments;
