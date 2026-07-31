import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTenantParams } from "@/context/TenantRoutingContext";
import { motion } from "framer-motion";
import {
  Activity,
  ArrowLeft,
  CalendarDays,
  HeartPulse,
  Mail,
  MapPin,
  Phone,
  Plus,
  Search,
  ShieldCheck,
  User,
  ClipboardList,
  Users,
} from "lucide-react";
import { apiClient } from "@/api/client";
import { invalidatePatientOptions } from "@/api/patients";
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
import { useRealtimeRefresh } from "@/hooks/useRealtimeRefresh";
import { getBranchStaffAccessPath, getStaffAccessPath } from "@/lib/facility-staff";
import { getWorkspaceDashboardPath, getWorkspaceRoutePath } from "@/lib/facility-workspace";

type Patient = {
  id: string;
  first_name: string;
  last_name: string;
  full_name?: string;
  date_of_birth: string;
  gender?: string | null;
  phone?: string | null;
  email?: string | null;
  address?: string | null;
  blood_type?: string | null;
  emergency_contact_name?: string | null;
  emergency_contact_phone?: string | null;
  created_at: string;
};

type Department = {
  id: string;
  name: string;
};

type PatientListResponse = {
  patients: Patient[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
};

const emptyForm = {
  first_name: "",
  last_name: "",
  date_of_birth: "",
  gender: "MALE",
  phone: "",
  email: "",
  address: "",
  blood_type: "",
  emergency_contact_name: "",
  emergency_contact_phone: "",
};

const bloodTypes = ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"];

const createRegistrationKey = () =>
  `patient:${globalThis.crypto?.randomUUID?.() || `${Date.now()}:${Math.random()}`}`;

const Patients = () => {
  const navigate = useNavigate();
  const { facilitySlug = "", branchSlug = "" } = useTenantParams();
  const [patients, setPatients] = useState<Patient[]>([]);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [referralPatient, setReferralPatient] = useState<Patient | null>(null);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [referralForm, setReferralForm] = useState({
    to_department_id: "",
    reason: "",
    priority: "routine",
    notes: "",
  });
  const [form, setForm] = useState(emptyForm);
  const [error, setError] = useState("");
  const [creating, setCreating] = useState(false);
  const creatingRef = useRef(false);
  const registrationKeyRef = useRef("");

  const dashboardPath = getWorkspaceDashboardPath(facilitySlug, branchSlug || undefined);
  const staffPath = branchSlug
    ? getBranchStaffAccessPath(facilitySlug, branchSlug)
    : getStaffAccessPath(facilitySlug);

  const loadPatients = async (query = search) => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page: "1", per_page: "50" });
      if (query.trim()) {
        params.set("search", query.trim());
      }

      const response = await apiClient.get<PatientListResponse>(
        `/patients?${params.toString()}`
      );
      setPatients(response.patients);
      setTotal(response.total);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPatients().catch(() => {
      setPatients([]);
      setTotal(0);
      setLoading(false);
    });
    apiClient
      .get<Department[]>(`/facilities/${facilitySlug}/departments`)
      .then(setDepartments)
      .catch(() => setDepartments([]));
  }, []);

  useRealtimeRefresh({
    eventTypes: ["patient.*", "queue.*", "appointment.*", "staff.*"],
    onRefresh: () => loadPatients(search).catch(() => undefined),
  });

  const filteredSummary = useMemo(() => {
    const female = patients.filter((patient) => patient.gender === "FEMALE").length;
    const male = patients.filter((patient) => patient.gender === "MALE").length;
    return { female, male };
  }, [patients]);

  const updateForm = (key: keyof typeof emptyForm, value: string) => {
    setForm((current) => ({ ...current, [key]: value }));
    setError("");
  };

  const handleSearch = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    loadPatients(search).catch(() => undefined);
  };

  const openCreate = () => {
    registrationKeyRef.current = createRegistrationKey();
    setForm(emptyForm);
    setError("");
    setShowCreate(true);
  };

  const handleCreate = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (creatingRef.current) {
      return;
    }
    if (!form.first_name.trim() || !form.last_name.trim() || !form.date_of_birth) {
      setError("First name, last name, and date of birth are required.");
      return;
    }

    const payload = {
      first_name: form.first_name.trim(),
      last_name: form.last_name.trim(),
      date_of_birth: form.date_of_birth,
      gender: form.gender,
      phone: form.phone.trim() || undefined,
      email: form.email.trim() || undefined,
      address: form.address.trim() || undefined,
      blood_type: form.blood_type || undefined,
      emergency_contact_name: form.emergency_contact_name.trim() || undefined,
      emergency_contact_phone: form.emergency_contact_phone.trim() || undefined,
      medical_history: {},
    };

    try {
      creatingRef.current = true;
      setCreating(true);
      registrationKeyRef.current ||= createRegistrationKey();
      await apiClient.request<Patient>("/patients", {
        method: "POST",
        body: payload,
        headers: {
          "Idempotency-Key": registrationKeyRef.current,
        },
      });
      invalidatePatientOptions();
      setShowCreate(false);
      setForm(emptyForm);
      registrationKeyRef.current = "";
      await loadPatients("");
      setSearch("");
    } catch (createError) {
      setError(
        createError instanceof Error
          ? createError.message
          : "Patient registration failed."
      );
    } finally {
      creatingRef.current = false;
      setCreating(false);
    }
  };

  const openReferral = (patient: Patient) => {
    setReferralPatient(patient);
    setReferralForm({
      to_department_id: departments[0]?.id || "",
      reason: "",
      priority: "routine",
      notes: "",
    });
    setError("");
  };

  const sendReferral = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!referralPatient || !referralForm.to_department_id || !referralForm.reason.trim()) {
      setError("Choose a department and enter a referral reason.");
      return;
    }
    try {
      await apiClient.post("/referrals", {
        patient_id: referralPatient.id,
        to_department_id: referralForm.to_department_id,
        reason: referralForm.reason.trim(),
        priority: referralForm.priority,
        notes: referralForm.notes.trim() || undefined,
      });
      setReferralPatient(null);
      setReferralForm({ to_department_id: "", reason: "", priority: "routine", notes: "" });
    } catch (referralError) {
      setError(referralError instanceof Error ? referralError.message : "Referral could not be sent.");
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
            <h1 className="text-2xl font-extrabold tracking-tight">
              Patient Registry
            </h1>
            <p className="text-sm text-muted-foreground">
              Register and find patients for this facility.
            </p>
          </div>
          <div className="flex gap-2">
            <Button asChild variant="outline">
              <Link to={staffPath}>Staff</Link>
            </Button>
            <Button
              onClick={openCreate}
              className="gradient-cta gap-2 border-0 text-primary-foreground"
            >
              <Plus className="h-4 w-4" /> Register Patient
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-6 p-6">
        <div className="grid gap-4 md:grid-cols-4">
          <Metric label="Total Patients" value={String(total)} icon={Users} />
          <Metric label="Listed Now" value={String(patients.length)} icon={Activity} />
          <Metric label="Female" value={String(filteredSummary.female)} icon={User} />
          <Metric label="Male" value={String(filteredSummary.male)} icon={ShieldCheck} />
        </div>

        <Card className="border-border/60">
          <CardHeader>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <CardTitle className="text-base">Patients</CardTitle>
              <form onSubmit={handleSearch} className="flex gap-2">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                    placeholder="Search name"
                    className="w-64 pl-9"
                  />
                </div>
                <Button type="submit" variant="outline">
                  Search
                </Button>
              </form>
            </div>
          </CardHeader>
          <CardContent>
            {loading ? (
              <p className="py-12 text-center text-sm text-muted-foreground">
                Loading patients...
              </p>
            ) : patients.length === 0 ? (
              <div className="py-16 text-center">
                <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-muted">
                  <Users className="h-6 w-6 text-muted-foreground" />
                </div>
                <p className="font-semibold text-foreground">No patients found</p>
                <p className="mt-1 text-sm text-muted-foreground">
                  Register the first patient to start clinical workflows.
                </p>
              </div>
            ) : (
              <div className="space-y-2">
                {patients.map((patient, index) => (
                  <motion.div
                    key={patient.id}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.03 }}
                    className="grid gap-3 rounded-xl border border-border/60 p-4 transition-colors hover:border-primary/30 md:grid-cols-[1.3fr_.8fr_1fr_1fr_auto]"
                  >
                    <div>
                      <p className="font-semibold text-foreground">
                        {patient.full_name || `${patient.first_name} ${patient.last_name}`}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        ID {patient.id.slice(0, 8)}
                      </p>
                    </div>
                    <Info icon={CalendarDays} value={patient.date_of_birth || "No DOB"} />
                    <Info icon={HeartPulse} value={patient.blood_type || patient.gender || "No clinical basics"} />
                    <div className="space-y-1 text-sm text-muted-foreground">
                      <Info icon={Phone} value={patient.phone || "No phone"} />
                      {patient.email && <Info icon={Mail} value={patient.email} />}
                    </div>
                    <div className="flex flex-wrap gap-2 self-start">
                      {departments.length > 0 && (
                        <Button type="button" variant="outline" size="sm" className="gap-2" onClick={() => openReferral(patient)}>
                          <Users className="h-4 w-4" /> Refer
                        </Button>
                      )}
                      <Button asChild variant="outline" size="sm" className="gap-2">
                        <Link to={getWorkspaceRoutePath(facilitySlug, `patients/${patient.id}/timeline`, branchSlug || undefined)}>
                          <ClipboardList className="h-4 w-4" /> View record
                        </Link>
                      </Button>
                    </div>
                  </motion.div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </main>

      <Dialog
        open={showCreate}
        onOpenChange={(open) => {
          if (creating) return;
          setShowCreate(open);
          if (!open) {
            registrationKeyRef.current = "";
            setForm(emptyForm);
            setError("");
          }
        }}
      >
        <DialogContent className="max-h-[92vh] overflow-y-auto sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>Register Patient</DialogTitle>
            <DialogDescription>
              Create a patient record for this facility.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleCreate} className="grid gap-4 pt-2 sm:grid-cols-2">
            <Field label="First Name" value={form.first_name} onChange={(value) => updateForm("first_name", value)} required />
            <Field label="Last Name" value={form.last_name} onChange={(value) => updateForm("last_name", value)} required />
            <Field label="Date of Birth" type="date" value={form.date_of_birth} onChange={(value) => updateForm("date_of_birth", value)} required />
            <div>
              <Label>Gender</Label>
              <Select value={form.gender} onValueChange={(value) => updateForm("gender", value)}>
                <SelectTrigger className="mt-1.5">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="MALE">Male</SelectItem>
                  <SelectItem value="FEMALE">Female</SelectItem>
                  <SelectItem value="OTHER">Other</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <Field label="Phone" value={form.phone} onChange={(value) => updateForm("phone", value)} />
            <Field label="Email" type="email" value={form.email} onChange={(value) => updateForm("email", value)} />
            <div>
              <Label>Blood Type</Label>
              <Select value={form.blood_type || "none"} onValueChange={(value) => updateForm("blood_type", value === "none" ? "" : value)}>
                <SelectTrigger className="mt-1.5">
                  <SelectValue placeholder="Optional" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">Not recorded</SelectItem>
                  {bloodTypes.map((type) => (
                    <SelectItem key={type} value={type}>
                      {type}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Field label="Address" value={form.address} onChange={(value) => updateForm("address", value)} />
            <Field label="Emergency Contact" value={form.emergency_contact_name} onChange={(value) => updateForm("emergency_contact_name", value)} />
            <Field label="Emergency Phone" value={form.emergency_contact_phone} onChange={(value) => updateForm("emergency_contact_phone", value)} />

            {error && (
              <p className="rounded-lg border border-destructive/20 bg-destructive/10 px-3 py-2 text-sm text-destructive sm:col-span-2">
                {error}
              </p>
            )}

            <div className="flex gap-3 sm:col-span-2">
              <Button type="button" variant="outline" className="flex-1" disabled={creating} onClick={() => setShowCreate(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={creating} className="gradient-cta flex-1 border-0 text-primary-foreground">
                {creating ? "Registering..." : "Register Patient"}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={Boolean(referralPatient)} onOpenChange={(open) => !open && setReferralPatient(null)}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Refer Patient</DialogTitle>
            <DialogDescription>
              Send {referralPatient?.full_name || "this patient"} to another department.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={sendReferral} className="space-y-4 pt-2">
            <div>
              <Label>Receiving Department</Label>
              <Select
                value={referralForm.to_department_id}
                onValueChange={(to_department_id) => setReferralForm((current) => ({ ...current, to_department_id }))}
              >
                <SelectTrigger className="mt-1.5">
                  <SelectValue placeholder="Select department" />
                </SelectTrigger>
                <SelectContent>
                  {departments.map((department) => (
                    <SelectItem key={department.id} value={department.id}>
                      {department.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Field label="Reason" value={referralForm.reason} onChange={(reason) => setReferralForm((current) => ({ ...current, reason }))} required />
            <div>
              <Label>Priority</Label>
              <Select value={referralForm.priority} onValueChange={(priority) => setReferralForm((current) => ({ ...current, priority }))}>
                <SelectTrigger className="mt-1.5">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="routine">Routine</SelectItem>
                  <SelectItem value="urgent">Urgent</SelectItem>
                  <SelectItem value="emergency">Emergency</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <Field label="Notes" value={referralForm.notes} onChange={(notes) => setReferralForm((current) => ({ ...current, notes }))} />
            {error && (
              <p className="rounded-lg border border-destructive/20 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                {error}
              </p>
            )}
            <div className="flex gap-3">
              <Button type="button" variant="outline" className="flex-1" onClick={() => setReferralPatient(null)}>
                Cancel
              </Button>
              <Button type="submit" className="gradient-cta flex-1 border-0 text-primary-foreground">
                Send Referral
              </Button>
            </div>
          </form>
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

export default Patients;
