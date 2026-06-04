import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  CheckCircle2,
  PackagePlus,
  Pill,
  Plus,
  Search,
  ShoppingCart,
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
import { Textarea } from "@/components/ui/textarea";
import { getFacilityDashboardPath } from "@/lib/facility-workspace";
import {
  addSettledError,
  hasResourceErrors,
  settledValue,
  type ResourceErrors,
} from "@/lib/resource-loading";

type Patient = {
  id: string;
  first_name: string;
  last_name: string;
  full_name?: string;
};

type PatientListResponse = {
  patients: Patient[];
};

type Medication = {
  id: string;
  name: string;
  code: string;
  generic_name?: string | null;
  category?: string | null;
  unit?: string | null;
  strength?: string | null;
  price?: number | null;
  reorder_level?: number | null;
};

type Inventory = {
  id: string;
  medication_id: string;
  quantity: number;
  expiry_date?: string | null;
  batch_number?: string | null;
  location?: string | null;
};

type Prescription = {
  id: string;
  patient_id: string;
  status: "PENDING" | "DISPENSED" | "CANCELLED" | string;
  notes?: string | null;
  filled_at?: string | null;
  created_at: string;
};

type PharmacyResource = "patients" | "medications" | "prescriptions";

const emptyMedicationForm = {
  name: "",
  code: "",
  generic_name: "",
  category: "",
  unit: "tablet",
  strength: "",
  price: "",
  reorder_level: "10",
};

const emptyStockForm = {
  medication_id: "",
  quantity: "",
  expiry_date: "",
  batch_number: "",
  location: "",
};

const emptyPrescriptionForm = {
  patient_id: "",
  medication_id: "",
  quantity: "1",
  dosage: "",
  instructions: "",
  notes: "",
};

const formatCurrency = (value?: number | null) =>
  new Intl.NumberFormat("en-NG", {
    style: "currency",
    currency: "NGN",
    maximumFractionDigits: 0,
  }).format(value || 0);

const Pharmacy = () => {
  const navigate = useNavigate();
  const { facilitySlug = "" } = useParams();
  const [patients, setPatients] = useState<Patient[]>([]);
  const [medications, setMedications] = useState<Medication[]>([]);
  const [inventory, setInventory] = useState<Record<string, Inventory | null>>({});
  const [prescriptions, setPrescriptions] = useState<Prescription[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [showMedicationDialog, setShowMedicationDialog] = useState(false);
  const [showStockDialog, setShowStockDialog] = useState(false);
  const [showPrescriptionDialog, setShowPrescriptionDialog] = useState(false);
  const [medicationForm, setMedicationForm] = useState(emptyMedicationForm);
  const [stockForm, setStockForm] = useState(emptyStockForm);
  const [prescriptionForm, setPrescriptionForm] = useState(emptyPrescriptionForm);
  const [error, setError] = useState("");
  const [dataErrors, setDataErrors] = useState<ResourceErrors<PharmacyResource>>({});

  const dashboardPath = getFacilityDashboardPath(facilitySlug);

  const patientNames = useMemo(
    () =>
      patients.reduce<Record<string, string>>((acc, patient) => {
        acc[patient.id] =
          patient.full_name || `${patient.first_name} ${patient.last_name}`.trim();
        return acc;
      }, {}),
    [patients]
  );

  const medicationNames = useMemo(
    () =>
      medications.reduce<Record<string, string>>((acc, medication) => {
        acc[medication.id] = `${medication.name} ${medication.strength || ""}`.trim();
        return acc;
      }, {}),
    [medications]
  );

  const visiblePrescriptions = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) {
      return prescriptions;
    }

    return prescriptions.filter((prescription) => {
      const patientName = patientNames[prescription.patient_id] || "";
      return (
        patientName.toLowerCase().includes(query) ||
        prescription.status.toLowerCase().includes(query) ||
        (prescription.notes || "").toLowerCase().includes(query)
      );
    });
  }, [patientNames, prescriptions, search]);

  const summary = useMemo(
    () => ({
      stock: Object.values(inventory).reduce(
        (sum, item) => sum + (item?.quantity || 0),
        0
      ),
      pending: prescriptions.filter((item) => item.status === "PENDING").length,
      dispensed: prescriptions.filter((item) => item.status === "DISPENSED").length,
    }),
    [inventory, prescriptions]
  );

  const loadPharmacy = async () => {
    setLoading(true);
    try {
      const [patientResponse, medicationResponse, prescriptionResponse] =
        await Promise.allSettled([
          apiClient.get<PatientListResponse>("/patients?page=1&per_page=100"),
          apiClient.get<Medication[]>("/pharmacy/medications"),
          apiClient.get<Prescription[]>("/pharmacy/prescriptions"),
        ]);

      const errors: ResourceErrors<PharmacyResource> = {};
      addSettledError(errors, "patients", patientResponse, "Patients could not be loaded.");
      addSettledError(errors, "medications", medicationResponse, "Medications could not be loaded.");
      addSettledError(errors, "prescriptions", prescriptionResponse, "Prescriptions could not be loaded.");

      const nextPatients = settledValue(patientResponse, { patients: [] }).patients;
      const nextMedications = settledValue(medicationResponse, []);
      const nextPrescriptions = settledValue(prescriptionResponse, []);

      setPatients(nextPatients);
      setMedications(nextMedications);
      setPrescriptions(nextPrescriptions);
      setDataErrors(errors);

      const inventoryEntries = await Promise.all(
        nextMedications.map(async (medication) => {
          try {
            const item = await apiClient.get<Inventory>(
              `/pharmacy/inventory/${medication.id}`
            );
            return [medication.id, item] as const;
          } catch {
            return [medication.id, null] as const;
          }
        })
      );
      setInventory(Object.fromEntries(inventoryEntries));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPharmacy().catch(() => {
      setLoading(false);
    });
  }, []);

  const createMedication = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");

    if (!medicationForm.name.trim() || !medicationForm.code.trim()) {
      setError("Medication name and code are required.");
      return;
    }

    try {
      await apiClient.post<Medication>("/pharmacy/medications", {
        name: medicationForm.name.trim(),
        code: medicationForm.code.trim().toUpperCase(),
        generic_name: medicationForm.generic_name.trim() || undefined,
        category: medicationForm.category.trim() || undefined,
        unit: medicationForm.unit.trim() || undefined,
        strength: medicationForm.strength.trim() || undefined,
        price: medicationForm.price ? Number(medicationForm.price) : undefined,
        reorder_level: medicationForm.reorder_level
          ? Number(medicationForm.reorder_level)
          : undefined,
      });
      setMedicationForm(emptyMedicationForm);
      setShowMedicationDialog(false);
      await loadPharmacy();
    } catch (medicationError) {
      setError(
        medicationError instanceof Error
          ? medicationError.message
          : "Medication creation failed."
      );
    }
  };

  const addStock = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");

    const quantity = Number(stockForm.quantity);
    if (!stockForm.medication_id || !quantity || quantity <= 0) {
      setError("Medication and a valid quantity are required.");
      return;
    }

    try {
      await apiClient.post<Inventory>(
        `/pharmacy/inventory/${stockForm.medication_id}`,
        {
          quantity,
          expiry_date: stockForm.expiry_date || undefined,
          batch_number: stockForm.batch_number.trim() || undefined,
          location: stockForm.location.trim() || undefined,
        }
      );
      setStockForm(emptyStockForm);
      setShowStockDialog(false);
      await loadPharmacy();
    } catch (stockError) {
      setError(stockError instanceof Error ? stockError.message : "Stock update failed.");
    }
  };

  const createPrescription = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");

    const quantity = Number(prescriptionForm.quantity);
    if (!prescriptionForm.patient_id || !prescriptionForm.medication_id || !quantity) {
      setError("Patient, medication, and quantity are required.");
      return;
    }

    try {
      await apiClient.post<Prescription>("/pharmacy/prescriptions", {
        patient_id: prescriptionForm.patient_id,
        items: [
          {
            medication_id: prescriptionForm.medication_id,
            quantity,
            dosage: prescriptionForm.dosage.trim() || undefined,
            instructions: prescriptionForm.instructions.trim() || undefined,
          },
        ],
        notes: prescriptionForm.notes.trim() || undefined,
      });
      setPrescriptionForm(emptyPrescriptionForm);
      setShowPrescriptionDialog(false);
      await loadPharmacy();
    } catch (prescriptionError) {
      setError(
        prescriptionError instanceof Error
          ? prescriptionError.message
          : "Prescription creation failed."
      );
    }
  };

  const dispensePrescription = async (prescription: Prescription) => {
    await apiClient.post<Prescription>(
      `/pharmacy/prescriptions/${prescription.id}/dispense`
    );
    await loadPharmacy();
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
            <h1 className="text-2xl font-extrabold tracking-tight">Pharmacy</h1>
            <p className="text-sm text-muted-foreground">
              Manage medications, stock, prescriptions, and dispensing.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={() => setShowMedicationDialog(true)}>
              <Plus className="mr-2 h-4 w-4" /> Medication
            </Button>
            <Button variant="outline" onClick={() => setShowStockDialog(true)}>
              <PackagePlus className="mr-2 h-4 w-4" /> Stock
            </Button>
            <Button
              onClick={() => setShowPrescriptionDialog(true)}
              className="gradient-cta gap-2 border-0 text-primary-foreground"
            >
              <Plus className="h-4 w-4" /> Prescription
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-6 p-6">
        {hasResourceErrors(dataErrors) && (
          <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
            Some pharmacy data could not be loaded. Available sections are still usable.
          </div>
        )}

        <div className="grid gap-4 md:grid-cols-4">
          <Metric label="Medications" value={String(medications.length)} icon={Pill} />
          <Metric label="Stock Units" value={String(summary.stock)} icon={PackagePlus} />
          <Metric label="Pending" value={String(summary.pending)} icon={ShoppingCart} />
          <Metric label="Dispensed" value={String(summary.dispensed)} icon={CheckCircle2} />
        </div>

        <div className="grid gap-6 xl:grid-cols-[1fr_380px]">
          <Card className="border-border/60">
            <CardHeader>
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <CardTitle className="text-base">Prescriptions</CardTitle>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                    placeholder="Search patient or status"
                    className="w-full pl-9 sm:w-72"
                  />
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {loading ? (
                <p className="py-12 text-center text-sm text-muted-foreground">
                  Loading pharmacy...
                </p>
              ) : visiblePrescriptions.length === 0 ? (
                <EmptyState />
              ) : (
                <div className="space-y-2">
                  {visiblePrescriptions.map((prescription, index) => (
                    <motion.div
                      key={prescription.id}
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.03 }}
                      className="grid gap-3 rounded-xl border border-border/60 p-4 transition-colors hover:border-primary/30 md:grid-cols-[1.2fr_.7fr_1fr_auto]"
                    >
                      <div>
                        <p className="font-semibold text-foreground">
                          {patientNames[prescription.patient_id] || "Unknown patient"}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          RX {prescription.id.slice(0, 8)}
                        </p>
                      </div>
                      <StatusBadge status={prescription.status} />
                      <p className="text-sm text-muted-foreground">
                        {prescription.notes || "No notes"}
                      </p>
                      <Button
                        variant="outline"
                        disabled={prescription.status !== "PENDING"}
                        onClick={() => dispensePrescription(prescription)}
                      >
                        Dispense
                      </Button>
                    </motion.div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="border-border/60">
            <CardHeader>
              <CardTitle className="text-base">Medication Stock</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {medications.length === 0 ? (
                <p className="py-8 text-center text-sm text-muted-foreground">
                  No medications configured.
                </p>
              ) : (
                medications.map((medication) => {
                  const item = inventory[medication.id];
                  return (
                    <div key={medication.id} className="rounded-xl border border-border/60 p-3">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="font-semibold text-foreground">
                            {medicationNames[medication.id]}
                          </p>
                          <p className="text-xs text-muted-foreground">{medication.code}</p>
                        </div>
                        <p className="text-sm font-semibold">{formatCurrency(medication.price)}</p>
                      </div>
                      <div className="mt-3 flex items-center justify-between text-sm">
                        <span className="text-muted-foreground">Stock</span>
                        <span className="font-semibold">{item?.quantity || 0}</span>
                      </div>
                      <p className="mt-1 text-xs text-muted-foreground">
                        Reorder at {medication.reorder_level ?? 10}
                      </p>
                    </div>
                  );
                })
              )}
            </CardContent>
          </Card>
        </div>

        <div className="flex justify-end">
          <Button asChild variant="outline" className="gap-2">
            <Link to={`/dashboard/${facilitySlug}/patients`}>
              <Users className="h-4 w-4" /> Patient Registry
            </Link>
          </Button>
        </div>
      </main>

      <Dialog open={showMedicationDialog} onOpenChange={setShowMedicationDialog}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>Create Medication</DialogTitle>
            <DialogDescription>Add a medication to this facility.</DialogDescription>
          </DialogHeader>
          <form onSubmit={createMedication} className="grid gap-4 pt-2 sm:grid-cols-2">
            <Field label="Name" value={medicationForm.name} onChange={(value) => setMedicationForm((current) => ({ ...current, name: value }))} required />
            <Field label="Code" value={medicationForm.code} onChange={(value) => setMedicationForm((current) => ({ ...current, code: value }))} required />
            <Field label="Generic Name" value={medicationForm.generic_name} onChange={(value) => setMedicationForm((current) => ({ ...current, generic_name: value }))} />
            <Field label="Category" value={medicationForm.category} onChange={(value) => setMedicationForm((current) => ({ ...current, category: value }))} />
            <Field label="Unit" value={medicationForm.unit} onChange={(value) => setMedicationForm((current) => ({ ...current, unit: value }))} />
            <Field label="Strength" value={medicationForm.strength} onChange={(value) => setMedicationForm((current) => ({ ...current, strength: value }))} />
            <Field label="Price" type="number" value={medicationForm.price} onChange={(value) => setMedicationForm((current) => ({ ...current, price: value }))} />
            <Field label="Reorder Level" type="number" value={medicationForm.reorder_level} onChange={(value) => setMedicationForm((current) => ({ ...current, reorder_level: value }))} />
            {error && <FormError message={error} />}
            <DialogActions onCancel={() => setShowMedicationDialog(false)} submitLabel="Create Medication" />
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={showStockDialog} onOpenChange={setShowStockDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Stock</DialogTitle>
            <DialogDescription>Receive pharmacy stock for a medication.</DialogDescription>
          </DialogHeader>
          <form onSubmit={addStock} className="space-y-4 pt-2">
            <SelectField
              label="Medication"
              value={stockForm.medication_id}
              placeholder="Select medication"
              options={medications.map((medication) => ({
                value: medication.id,
                label: medicationNames[medication.id],
              }))}
              onChange={(value) => setStockForm((current) => ({ ...current, medication_id: value }))}
            />
            <Field label="Quantity" type="number" value={stockForm.quantity} onChange={(value) => setStockForm((current) => ({ ...current, quantity: value }))} required />
            <Field label="Expiry Date" type="date" value={stockForm.expiry_date} onChange={(value) => setStockForm((current) => ({ ...current, expiry_date: value }))} />
            <Field label="Batch Number" value={stockForm.batch_number} onChange={(value) => setStockForm((current) => ({ ...current, batch_number: value }))} />
            <Field label="Location" value={stockForm.location} onChange={(value) => setStockForm((current) => ({ ...current, location: value }))} />
            {error && <FormError message={error} />}
            <DialogActions onCancel={() => setShowStockDialog(false)} submitLabel="Add Stock" />
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={showPrescriptionDialog} onOpenChange={setShowPrescriptionDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New Prescription</DialogTitle>
            <DialogDescription>Create a one-medication prescription.</DialogDescription>
          </DialogHeader>
          <form onSubmit={createPrescription} className="space-y-4 pt-2">
            <SelectField
              label="Patient"
              value={prescriptionForm.patient_id}
              placeholder="Select patient"
              options={patients.map((patient) => ({
                value: patient.id,
                label: patientNames[patient.id],
              }))}
              onChange={(value) => setPrescriptionForm((current) => ({ ...current, patient_id: value }))}
            />
            <SelectField
              label="Medication"
              value={prescriptionForm.medication_id}
              placeholder="Select medication"
              options={medications.map((medication) => ({
                value: medication.id,
                label: medicationNames[medication.id],
              }))}
              onChange={(value) => setPrescriptionForm((current) => ({ ...current, medication_id: value }))}
            />
            <Field label="Quantity" type="number" value={prescriptionForm.quantity} onChange={(value) => setPrescriptionForm((current) => ({ ...current, quantity: value }))} required />
            <Field label="Dosage" value={prescriptionForm.dosage} onChange={(value) => setPrescriptionForm((current) => ({ ...current, dosage: value }))} />
            <Field label="Instructions" value={prescriptionForm.instructions} onChange={(value) => setPrescriptionForm((current) => ({ ...current, instructions: value }))} />
            <div>
              <Label>Notes</Label>
              <Textarea
                className="mt-1.5"
                value={prescriptionForm.notes}
                onChange={(event) => setPrescriptionForm((current) => ({ ...current, notes: event.target.value }))}
              />
            </div>
            {error && <FormError message={error} />}
            <DialogActions onCancel={() => setShowPrescriptionDialog(false)} submitLabel="Create Prescription" />
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

const EmptyState = () => (
  <div className="py-16 text-center">
    <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-muted">
      <Pill className="h-6 w-6 text-muted-foreground" />
    </div>
    <p className="font-semibold text-foreground">No prescriptions found</p>
    <p className="mt-1 text-sm text-muted-foreground">
      Add medication stock, then create a patient prescription.
    </p>
  </div>
);

const StatusBadge = ({ status }: { status: string }) => {
  const variant =
    status === "DISPENSED"
      ? "bg-emerald-500/10 text-emerald-700"
      : status === "CANCELLED"
        ? "bg-destructive/10 text-destructive"
        : "bg-primary/10 text-primary";

  return (
    <span className={`inline-flex h-fit rounded-full px-2.5 py-1 text-xs font-semibold ${variant}`}>
      {status}
    </span>
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
      min={type === "number" ? "0" : undefined}
      step={type === "number" ? "0.01" : undefined}
      value={value}
      onChange={(event) => onChange(event.target.value)}
      required={required}
    />
  </div>
);

const SelectField = ({
  label,
  value,
  placeholder,
  options,
  onChange,
}: {
  label: string;
  value: string;
  placeholder?: string;
  options: Array<{ value: string; label: string }>;
  onChange: (value: string) => void;
}) => (
  <div>
    <Label>{label}</Label>
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger className="mt-1.5">
        <SelectValue placeholder={placeholder} />
      </SelectTrigger>
      <SelectContent>
        {options.map((option) => (
          <SelectItem key={option.value} value={option.value}>
            {option.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  </div>
);

const DialogActions = ({
  onCancel,
  submitLabel,
}: {
  onCancel: () => void;
  submitLabel: string;
}) => (
  <div className="flex gap-3 sm:col-span-2">
    <Button type="button" variant="outline" className="flex-1" onClick={onCancel}>
      Cancel
    </Button>
    <Button type="submit" className="gradient-cta flex-1 border-0 text-primary-foreground">
      {submitLabel}
    </Button>
  </div>
);

const FormError = ({ message }: { message: string }) => (
  <p className="rounded-lg border border-destructive/20 bg-destructive/10 px-3 py-2 text-sm text-destructive sm:col-span-2">
    {message}
  </p>
);

export default Pharmacy;
