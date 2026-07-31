import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTenantParams } from "@/context/TenantRoutingContext";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  ClipboardPlus,
  ClipboardList,
  Ban,
  Eye,
  FileHeart,
  HeartPulse,
  Pencil,
  Plus,
  Search,
  Stethoscope,
  Users,
} from "lucide-react";
import { apiClient } from "@/api/client";
import { getPatientOptions } from "@/api/patients";
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
import { Textarea } from "@/components/ui/textarea";
import { getWorkspaceDashboardPath, getWorkspaceRoutePath } from "@/lib/facility-workspace";
import { createIdempotencyKey } from "@/lib/idempotency";
import {
  addSettledError,
  hasResourceErrors,
  settledValue,
  type ResourceErrors,
} from "@/lib/resource-loading";
import { useRealtimeRefresh } from "@/hooks/useRealtimeRefresh";
import { useAuth } from "@/context/AuthContext";

type Patient = {
  id: string;
  first_name: string;
  last_name: string;
  full_name?: string;
};

type PatientListResponse = {
  patients: Patient[];
};

type MedicalRecord = {
  id: string;
  patient_id: string;
  chief_complaint?: string | null;
  vital_signs?: Record<string, string | number>;
  symptoms?: string[];
  diagnosis?: string[];
  treatment_plan?: string | null;
  follow_up_date?: string | null;
  notes?: string | null;
  status: "ACTIVE" | "VOIDED" | string;
  void_reason?: string | null;
  voided_at?: string | null;
  created_at: string;
};

type MedicalRecordResource = "patients" | "records";

const emptyRecordForm = {
  patient_id: "",
  chief_complaint: "",
  temperature: "",
  blood_pressure: "",
  pulse: "",
  respiratory_rate: "",
  symptoms: "",
  diagnosis: "",
  treatment_plan: "",
  follow_up_date: "",
  notes: "",
};

const toList = (value: string) =>
  value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);

const recordToForm = (record: MedicalRecord) => ({
  patient_id: record.patient_id,
  chief_complaint: record.chief_complaint || "",
  temperature: String(record.vital_signs?.temperature || ""),
  blood_pressure: String(record.vital_signs?.blood_pressure || ""),
  pulse: String(record.vital_signs?.pulse || ""),
  respiratory_rate: String(record.vital_signs?.respiratory_rate || ""),
  symptoms: (record.symptoms || []).join(", "),
  diagnosis: (record.diagnosis || []).join(", "),
  treatment_plan: record.treatment_plan || "",
  follow_up_date: record.follow_up_date || "",
  notes: record.notes || "",
});

const MedicalRecords = () => {
  const navigate = useNavigate();
  const { facilitySlug = "", branchSlug = "" } = useTenantParams();
  const { user } = useAuth();
  const [patients, setPatients] = useState<Patient[]>([]);
  const [records, setRecords] = useState<MedicalRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [viewingRecord, setViewingRecord] = useState<MedicalRecord | null>(null);
  const [editingRecord, setEditingRecord] = useState<MedicalRecord | null>(null);
  const [voidingRecord, setVoidingRecord] = useState<MedicalRecord | null>(null);
  const [voidReason, setVoidReason] = useState("");
  const [saving, setSaving] = useState(false);
  const [voiding, setVoiding] = useState(false);
  const saveRef = useRef(false);
  const createKeyRef = useRef("");
  const voidRef = useRef(false);
  const [form, setForm] = useState(emptyRecordForm);
  const [error, setError] = useState("");
  const [dataErrors, setDataErrors] = useState<ResourceErrors<MedicalRecordResource>>({});

  const dashboardPath = getWorkspaceDashboardPath(facilitySlug, branchSlug || undefined);

  const patientNames = useMemo(
    () =>
      patients.reduce<Record<string, string>>((acc, patient) => {
        acc[patient.id] =
          patient.full_name || `${patient.first_name} ${patient.last_name}`.trim();
        return acc;
      }, {}),
    [patients]
  );

  const visibleRecords = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) {
      return records;
    }
    return records.filter((record) => {
      const patientName = patientNames[record.patient_id] || "";
      return (
        patientName.toLowerCase().includes(query) ||
        (record.chief_complaint || "").toLowerCase().includes(query) ||
        (record.diagnosis || []).join(" ").toLowerCase().includes(query)
      );
    });
  }, [patientNames, records, search]);

  const summary = useMemo(
    () => ({
      patients: new Set(records.map((record) => record.patient_id)).size,
      diagnoses: records.reduce(
        (sum, record) => sum + (record.diagnosis?.length || 0),
        0
      ),
      followUps: records.filter((record) => record.follow_up_date).length,
    }),
    [records]
  );

  const loadRecords = async () => {
    setLoading(true);
    try {
      const [patientResponse, recordResponse] = await Promise.allSettled([
        getPatientOptions<Patient>(),
        apiClient.get<MedicalRecord[]>("/emr"),
      ]);

      const errors: ResourceErrors<MedicalRecordResource> = {};
      addSettledError(errors, "patients", patientResponse, "Patients could not be loaded.");
      addSettledError(errors, "records", recordResponse, "Medical records could not be loaded.");

      setPatients(settledValue(patientResponse, { patients: [] }).patients);
      setRecords(settledValue(recordResponse, []));
      setDataErrors(errors);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRecords().catch(() => {
      setLoading(false);
    });
  }, []);

  useRealtimeRefresh({
    eventTypes: ["record.*", "consultation.*", "lab_result.*", "prescription.*", "radiology.*", "patient.*"],
    onRefresh: () => loadRecords().catch(() => undefined),
  });

  const updateForm = (key: keyof typeof emptyRecordForm, value: string) => {
    setForm((current) => ({ ...current, [key]: value }));
    setError("");
  };

  const closeRecordForm = () => {
    if (saving) {
      return;
    }
    setShowCreate(false);
    setEditingRecord(null);
    setForm(emptyRecordForm);
    setError("");
  };

  const saveRecord = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (saveRef.current) {
      return;
    }
    setError("");

    if (!form.patient_id || !form.chief_complaint.trim()) {
      setError("Patient and chief complaint are required.");
      return;
    }

    const payload = {
      patient_id: form.patient_id,
      chief_complaint: form.chief_complaint.trim(),
      vital_signs: {
        temperature: form.temperature.trim(),
        blood_pressure: form.blood_pressure.trim(),
        pulse: form.pulse.trim(),
        respiratory_rate: form.respiratory_rate.trim(),
      },
      symptoms: toList(form.symptoms),
      diagnosis: toList(form.diagnosis),
      treatment_plan: form.treatment_plan.trim() || undefined,
      follow_up_date: form.follow_up_date || undefined,
      notes: form.notes.trim() || undefined,
    };

    saveRef.current = true;
    setSaving(true);
    try {
      if (editingRecord) {
        const { patient_id: _patientId, ...updates } = payload;
        await apiClient.put<MedicalRecord>(`/emr/${editingRecord.id}`, updates);
      } else {
        createKeyRef.current ||= createIdempotencyKey("medical-record");
        await apiClient.request<MedicalRecord>("/emr", {
          method: "POST",
          headers: { "Idempotency-Key": createKeyRef.current },
          body: payload,
        });
      }
      setForm(emptyRecordForm);
      setShowCreate(false);
      setEditingRecord(null);
      createKeyRef.current = "";
      await loadRecords();
    } catch (recordError) {
      setError(recordError instanceof Error ? recordError.message : "Medical record creation failed.");
    } finally {
      saveRef.current = false;
      setSaving(false);
    }
  };

  const voidRecord = async () => {
    if (!voidingRecord || voidRef.current) {
      return;
    }
    const reason = voidReason.trim();
    if (reason.length < 5) {
      setError("Enter a reason of at least 5 characters.");
      return;
    }

    voidRef.current = true;
    setVoiding(true);
    setError("");
    try {
      await apiClient.request(
        `/emr/${voidingRecord.id}?reason=${encodeURIComponent(reason)}`,
        { method: "DELETE" }
      );
      setVoidingRecord(null);
      setVoidReason("");
      await loadRecords();
    } catch (recordError) {
      setError(
        recordError instanceof Error
          ? recordError.message
          : "Medical record could not be voided."
      );
    } finally {
      voidRef.current = false;
      setVoiding(false);
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
            <h1 className="text-2xl font-extrabold tracking-tight">Medical Records</h1>
            <p className="text-sm text-muted-foreground">
              Record consultations, vitals, diagnoses, and care plans.
            </p>
          </div>
          <Button
            onClick={() => {
              setForm(emptyRecordForm);
              setEditingRecord(null);
              setError("");
              createKeyRef.current = createIdempotencyKey("medical-record");
              setShowCreate(true);
            }}
            className="gradient-cta gap-2 border-0 text-primary-foreground"
          >
            <Plus className="h-4 w-4" /> New Record
          </Button>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-6 p-6">
        {hasResourceErrors(dataErrors) && (
          <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
            Some medical record data could not be loaded. Available sections are still usable.
          </div>
        )}

        <div className="grid gap-4 md:grid-cols-4">
          <Metric label="Records" value={String(records.length)} icon={FileHeart} />
          <Metric label="Patients" value={String(summary.patients)} icon={Users} />
          <Metric label="Diagnoses" value={String(summary.diagnoses)} icon={Stethoscope} />
          <Metric label="Follow-ups" value={String(summary.followUps)} icon={ClipboardPlus} />
        </div>

        <Card className="border-border/60">
          <CardHeader>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <CardTitle className="text-base">Clinical Records</CardTitle>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Search patient, complaint, diagnosis"
                  className="w-full pl-9 sm:w-80"
                />
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {loading ? (
              <p className="py-12 text-center text-sm text-muted-foreground">
                Loading records...
              </p>
            ) : visibleRecords.length === 0 ? (
              <EmptyState />
            ) : (
              <div className="space-y-2">
                {visibleRecords.map((record, index) => (
                  <motion.div
                    key={record.id}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.03 }}
                    className={`grid gap-3 rounded-xl border p-4 transition-colors lg:grid-cols-[1.1fr_1fr_1fr_.8fr_auto] ${
                      record.status === "VOIDED"
                        ? "border-destructive/30 bg-destructive/5"
                        : "border-border/60 hover:border-primary/30"
                    }`}
                  >
                    <div>
                      <p className="font-semibold text-foreground">
                        {patientNames[record.patient_id] || "Unknown patient"}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {record.chief_complaint || "No complaint recorded"}
                      </p>
                      {record.status === "VOIDED" && (
                        <span className="mt-1 inline-flex rounded bg-destructive/10 px-2 py-0.5 text-xs font-semibold text-destructive">
                          Voided
                        </span>
                      )}
                    </div>
                    <Info
                      icon={HeartPulse}
                      value={[
                        record.vital_signs?.blood_pressure,
                        record.vital_signs?.temperature,
                      ].filter(Boolean).join(" · ") || "No vitals"}
                    />
                    <div>
                      <p className="text-sm font-medium text-foreground">
                        {(record.diagnosis || []).join(", ") || "No diagnosis"}
                      </p>
                      <p className="line-clamp-1 text-xs text-muted-foreground">
                        {record.treatment_plan || record.notes || "No care plan"}
                      </p>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {record.follow_up_date ? `Follow-up ${record.follow_up_date}` : "No follow-up"}
                    </p>
                    <div className="flex flex-wrap justify-end gap-2">
                      <Button type="button" variant="outline" size="icon" title="View record" onClick={() => setViewingRecord(record)}>
                        <Eye className="h-4 w-4" />
                      </Button>
                      {record.status !== "VOIDED" && (
                        <Button type="button" variant="outline" size="icon" title="Edit record" onClick={() => {
                          setForm(recordToForm(record));
                          setEditingRecord(record);
                          setError("");
                        }}>
                          <Pencil className="h-4 w-4" />
                        </Button>
                      )}
                      {record.status !== "VOIDED" && ["admin", "branch_admin"].includes(user?.role || "") && (
                        <Button type="button" variant="outline" size="icon" className="text-destructive hover:text-destructive" title="Void record" onClick={() => {
                          setError("");
                          setVoidReason("");
                          setVoidingRecord(record);
                        }}>
                          <Ban className="h-4 w-4" />
                        </Button>
                      )}
                      <Button asChild variant="outline" size="icon" title="Patient timeline">
                        <Link to={getWorkspaceRoutePath(facilitySlug, `patients/${record.patient_id}/timeline`, branchSlug || undefined)}>
                          <ClipboardList className="h-4 w-4" />
                        </Link>
                      </Button>
                    </div>
                  </motion.div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <div className="flex justify-end">
          <Button asChild variant="outline" className="gap-2">
            <Link to={getWorkspaceRoutePath(facilitySlug, "patients", branchSlug || undefined)}>
              <Users className="h-4 w-4" /> Patient Registry
            </Link>
          </Button>
        </div>
      </main>

      <Dialog
        open={showCreate || Boolean(editingRecord)}
        onOpenChange={(open) => !open && closeRecordForm()}
      >
        <DialogContent className="max-h-[92vh] overflow-y-auto sm:max-w-3xl">
          <DialogHeader>
            <DialogTitle>{editingRecord ? "Edit Medical Record" : "New Medical Record"}</DialogTitle>
            <DialogDescription>
              {editingRecord
                ? "Update this clinical entry. Every change is audit logged."
                : "Create a clinical entry for a patient."}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={saveRecord} className="grid gap-4 pt-2 sm:grid-cols-2">
            <div>
              <Label>Patient *</Label>
              <Select disabled={Boolean(editingRecord)} value={form.patient_id} onValueChange={(value) => updateForm("patient_id", value)}>
                <SelectTrigger className="mt-1.5">
                  <SelectValue placeholder="Select patient" />
                </SelectTrigger>
                <SelectContent>
                  {patients.map((patient) => (
                    <SelectItem key={patient.id} value={patient.id}>
                      {patientNames[patient.id]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Field label="Chief Complaint" value={form.chief_complaint} onChange={(value) => updateForm("chief_complaint", value)} required />
            <Field label="Temperature" value={form.temperature} onChange={(value) => updateForm("temperature", value)} />
            <Field label="Blood Pressure" value={form.blood_pressure} onChange={(value) => updateForm("blood_pressure", value)} />
            <Field label="Pulse" value={form.pulse} onChange={(value) => updateForm("pulse", value)} />
            <Field label="Respiratory Rate" value={form.respiratory_rate} onChange={(value) => updateForm("respiratory_rate", value)} />
            <Field label="Symptoms" value={form.symptoms} onChange={(value) => updateForm("symptoms", value)} placeholder="Comma-separated" />
            <Field label="Diagnosis" value={form.diagnosis} onChange={(value) => updateForm("diagnosis", value)} placeholder="Comma-separated" />
            <div className="sm:col-span-2">
              <Label>Treatment Plan</Label>
              <Textarea className="mt-1.5" value={form.treatment_plan} onChange={(event) => updateForm("treatment_plan", event.target.value)} />
            </div>
            <Field label="Follow-up Date" type="date" value={form.follow_up_date} onChange={(value) => updateForm("follow_up_date", value)} />
            <div className="sm:col-span-2">
              <Label>Notes</Label>
              <Textarea className="mt-1.5" value={form.notes} onChange={(event) => updateForm("notes", event.target.value)} />
            </div>
            {error && <FormError message={error} />}
            <DialogActions
              disabled={saving}
              onCancel={closeRecordForm}
              submitLabel={
                saving
                  ? "Saving..."
                  : editingRecord
                    ? "Save Changes"
                    : "Create Record"
              }
            />
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={Boolean(viewingRecord)} onOpenChange={(open) => !open && setViewingRecord(null)}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>Clinical Record</DialogTitle>
            <DialogDescription>
              {viewingRecord ? patientNames[viewingRecord.patient_id] || "Patient" : "Patient"}
            </DialogDescription>
          </DialogHeader>
          {viewingRecord && (
            <div className="space-y-4 text-sm">
              {viewingRecord.status === "VOIDED" && (
                <div className="rounded-md border border-destructive/30 bg-destructive/5 p-3 text-destructive">
                  Voided: {viewingRecord.void_reason || "No reason recorded"}
                </div>
              )}
              <RecordDetail label="Chief complaint" value={viewingRecord.chief_complaint} />
              <RecordDetail label="Symptoms" value={(viewingRecord.symptoms || []).join(", ")} />
              <RecordDetail label="Diagnosis" value={(viewingRecord.diagnosis || []).join(", ")} />
              <RecordDetail label="Treatment plan" value={viewingRecord.treatment_plan} />
              <RecordDetail label="Notes" value={viewingRecord.notes} />
            </div>
          )}
        </DialogContent>
      </Dialog>

      <Dialog
        open={Boolean(voidingRecord)}
        onOpenChange={(open) => {
          if (!open && !voiding) {
            setVoidingRecord(null);
            setVoidReason("");
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Void Medical Record</DialogTitle>
            <DialogDescription>
              The entry will remain in the audit history and cannot be edited afterward.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <Label htmlFor="void-reason">Reason</Label>
            <Textarea
              id="void-reason"
              value={voidReason}
              onChange={(event) => setVoidReason(event.target.value)}
              placeholder="Explain why this record must be voided"
            />
            {error && <FormError message={error} />}
            <div className="flex gap-3">
              <Button type="button" variant="outline" className="flex-1" disabled={voiding} onClick={() => setVoidingRecord(null)}>
                Cancel
              </Button>
              <Button type="button" variant="destructive" className="flex-1" disabled={voiding || voidReason.trim().length < 5} onClick={voidRecord}>
                {voiding ? "Voiding..." : "Void Record"}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

const Metric = ({
  label,
  value,
  icon: Icon,
}: {
  label: string;
  value: string;
  icon: React.ElementType;
}) => (
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

const EmptyState = () => (
  <div className="py-16 text-center">
    <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-muted">
      <FileHeart className="h-6 w-6 text-muted-foreground" />
    </div>
    <p className="font-semibold text-foreground">No medical records found</p>
    <p className="mt-1 text-sm text-muted-foreground">
      Create the first consultation record for a patient.
    </p>
  </div>
);

const Info = ({ icon: Icon, value }: { icon: React.ElementType; value: string }) => (
  <span className="flex min-w-0 items-center gap-2 text-sm text-muted-foreground">
    <Icon className="h-4 w-4 shrink-0" />
    <span className="truncate">{value}</span>
  </span>
);

const Field = ({
  label,
  value,
  onChange,
  type = "text",
  required,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
  required?: boolean;
  placeholder?: string;
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
      placeholder={placeholder}
      onChange={(event) => onChange(event.target.value)}
      required={required}
    />
  </div>
);

const DialogActions = ({
  onCancel,
  submitLabel,
  disabled,
}: {
  onCancel: () => void;
  submitLabel: string;
  disabled?: boolean;
}) => (
  <div className="flex gap-3 sm:col-span-2">
    <Button type="button" variant="outline" className="flex-1" disabled={disabled} onClick={onCancel}>
      Cancel
    </Button>
    <Button type="submit" disabled={disabled} className="gradient-cta flex-1 border-0 text-primary-foreground">
      {submitLabel}
    </Button>
  </div>
);

const RecordDetail = ({
  label,
  value,
}: {
  label: string;
  value?: string | null;
}) => (
  <div>
    <p className="text-xs font-semibold uppercase text-muted-foreground">{label}</p>
    <p className="mt-1 whitespace-pre-wrap text-foreground">{value || "Not recorded"}</p>
  </div>
);

const FormError = ({ message }: { message: string }) => (
  <p className="rounded-lg border border-destructive/20 bg-destructive/10 px-3 py-2 text-sm text-destructive sm:col-span-2">
    {message}
  </p>
);

export default MedicalRecords;
