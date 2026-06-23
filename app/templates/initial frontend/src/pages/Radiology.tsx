import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  CheckCircle2,
  FileText,
  ImagePlus,
  Plus,
  ScanLine,
  Search,
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
import { getWorkspaceDashboardPath, getWorkspaceRoutePath } from "@/lib/facility-workspace";
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

type RadiologyOrder = {
  id: string;
  patient_id: string;
  modality: "X-ray" | "CT" | "MRI" | "Ultrasound" | string;
  body_part: string;
  clinical_notes?: string | null;
  status: "pending" | "ordered" | "completed" | "cancelled" | string;
  report?: string | null;
  report_date?: string | null;
  request_date: string;
  patient_name?: string | null;
  requested_by_name?: string | null;
  radiologist_name?: string | null;
};

type RadiologyResource = "patients" | "orders";

const modalities = ["X-ray", "CT", "MRI", "Ultrasound"];

const emptyOrderForm = {
  patient_id: "",
  modality: "X-ray",
  body_part: "",
  clinical_notes: "",
};

const Radiology = () => {
  const navigate = useNavigate();
  const { facilitySlug = "", branchSlug = "" } = useParams();
  const [patients, setPatients] = useState<Patient[]>([]);
  const [orders, setOrders] = useState<RadiologyOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [showOrderDialog, setShowOrderDialog] = useState(false);
  const [reportOrder, setReportOrder] = useState<RadiologyOrder | null>(null);
  const [orderForm, setOrderForm] = useState(emptyOrderForm);
  const [report, setReport] = useState("");
  const [error, setError] = useState("");
  const [dataErrors, setDataErrors] = useState<ResourceErrors<RadiologyResource>>({});

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

  const visibleOrders = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) {
      return orders;
    }

    return orders.filter((order) => {
      const patientName = order.patient_name || patientNames[order.patient_id] || "";
      return (
        patientName.toLowerCase().includes(query) ||
        order.modality.toLowerCase().includes(query) ||
        order.body_part.toLowerCase().includes(query) ||
        order.status.toLowerCase().includes(query)
      );
    });
  }, [orders, patientNames, search]);

  const summary = useMemo(
    () => ({
      pending: orders.filter((order) => order.status === "pending").length,
      ordered: orders.filter((order) => order.status === "ordered").length,
      completed: orders.filter((order) => order.status === "completed").length,
    }),
    [orders]
  );

  const loadRadiology = async () => {
    setLoading(true);
    try {
      const [patientResponse, orderResponse] = await Promise.allSettled([
        apiClient.get<PatientListResponse>("/patients?page=1&per_page=100"),
        apiClient.get<RadiologyOrder[]>("/radiology?per_page=100"),
      ]);

      const errors: ResourceErrors<RadiologyResource> = {};
      addSettledError(errors, "patients", patientResponse, "Patients could not be loaded.");
      addSettledError(errors, "orders", orderResponse, "Radiology orders could not be loaded.");

      setPatients(settledValue(patientResponse, { patients: [] }).patients);
      setOrders(settledValue(orderResponse, []));
      setDataErrors(errors);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRadiology().catch(() => {
      setLoading(false);
    });
  }, []);

  const createOrder = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");

    if (!orderForm.patient_id || !orderForm.modality || !orderForm.body_part.trim()) {
      setError("Patient, modality, and body part are required.");
      return;
    }

    try {
      await apiClient.post<RadiologyOrder>("/radiology", {
        patient_id: orderForm.patient_id,
        modality: orderForm.modality,
        body_part: orderForm.body_part.trim(),
        clinical_notes: orderForm.clinical_notes.trim() || undefined,
      });
      setOrderForm(emptyOrderForm);
      setShowOrderDialog(false);
      await loadRadiology();
    } catch (orderError) {
      setError(orderError instanceof Error ? orderError.message : "Order creation failed.");
    }
  };

  const updateStatus = async (order: RadiologyOrder, status: string) => {
    await apiClient.put<RadiologyOrder>(`/radiology/${order.id}`, { status });
    await loadRadiology();
  };

  const saveReport = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!reportOrder) {
      return;
    }

    setError("");
    if (!report.trim()) {
      setError("Report text is required.");
      return;
    }

    try {
      await apiClient.put<RadiologyOrder>(`/radiology/${reportOrder.id}/report`, {
        report: report.trim(),
      });
      setReport("");
      setReportOrder(null);
      await loadRadiology();
    } catch (reportError) {
      setError(reportError instanceof Error ? reportError.message : "Report save failed.");
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
            <h1 className="text-2xl font-extrabold tracking-tight">Radiology</h1>
            <p className="text-sm text-muted-foreground">
              Request imaging studies and record radiology reports.
            </p>
          </div>
          <Button
            onClick={() => {
              setError("");
              setShowOrderDialog(true);
            }}
            className="gradient-cta gap-2 border-0 text-primary-foreground"
          >
            <Plus className="h-4 w-4" /> Imaging Order
          </Button>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-6 p-6">
        {hasResourceErrors(dataErrors) && (
          <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
            Some radiology data could not be loaded. Available sections are still usable.
          </div>
        )}

        <div className="grid gap-4 md:grid-cols-4">
          <Metric label="Orders" value={String(orders.length)} icon={ScanLine} />
          <Metric label="Pending" value={String(summary.pending)} icon={ImagePlus} />
          <Metric label="Ordered" value={String(summary.ordered)} icon={FileText} />
          <Metric label="Completed" value={String(summary.completed)} icon={CheckCircle2} />
        </div>

        <Card className="border-border/60">
          <CardHeader>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <CardTitle className="text-base">Imaging Orders</CardTitle>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Search patient, modality, status"
                  className="w-full pl-9 sm:w-72"
                />
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {loading ? (
              <p className="py-12 text-center text-sm text-muted-foreground">
                Loading radiology...
              </p>
            ) : visibleOrders.length === 0 ? (
              <EmptyState />
            ) : (
              <div className="space-y-2">
                {visibleOrders.map((order, index) => (
                  <motion.div
                    key={order.id}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.03 }}
                    className="grid gap-3 rounded-xl border border-border/60 p-4 transition-colors hover:border-primary/30 lg:grid-cols-[1.1fr_.8fr_1fr_auto]"
                  >
                    <div>
                      <p className="font-semibold text-foreground">
                        {order.patient_name || patientNames[order.patient_id] || "Unknown patient"}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {order.modality} · {order.body_part}
                      </p>
                      {order.report && (
                        <p className="mt-2 line-clamp-2 text-xs text-muted-foreground">
                          {order.report}
                        </p>
                      )}
                    </div>
                    <div>
                      <StatusBadge status={order.status} />
                      <p className="mt-1 text-xs text-muted-foreground">
                        {order.requested_by_name || "Requested"}
                      </p>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {order.clinical_notes || "No clinical notes"}
                    </p>
                    <div className="flex flex-wrap gap-2 lg:justify-end">
                      {order.status === "pending" && (
                        <Button variant="outline" onClick={() => updateStatus(order, "ordered")}>
                          Mark Ordered
                        </Button>
                      )}
                      {order.status !== "completed" && order.status !== "cancelled" && (
                        <Button
                          onClick={() => {
                            setError("");
                            setReport(order.report || "");
                            setReportOrder(order);
                          }}
                        >
                          Report
                        </Button>
                      )}
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

      <Dialog open={showOrderDialog} onOpenChange={setShowOrderDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New Imaging Order</DialogTitle>
            <DialogDescription>Request a radiology study for a patient.</DialogDescription>
          </DialogHeader>
          <form onSubmit={createOrder} className="space-y-4 pt-2">
            <SelectField
              label="Patient"
              value={orderForm.patient_id}
              placeholder="Select patient"
              options={patients.map((patient) => ({
                value: patient.id,
                label: patientNames[patient.id],
              }))}
              onChange={(value) => setOrderForm((current) => ({ ...current, patient_id: value }))}
            />
            <SelectField
              label="Modality"
              value={orderForm.modality}
              options={modalities.map((modality) => ({ value: modality, label: modality }))}
              onChange={(value) => setOrderForm((current) => ({ ...current, modality: value }))}
            />
            <Field
              label="Body Part"
              value={orderForm.body_part}
              onChange={(value) => setOrderForm((current) => ({ ...current, body_part: value }))}
              required
            />
            <div>
              <Label>Clinical Notes</Label>
              <Textarea
                className="mt-1.5"
                value={orderForm.clinical_notes}
                onChange={(event) => setOrderForm((current) => ({ ...current, clinical_notes: event.target.value }))}
              />
            </div>
            {error && <FormError message={error} />}
            <DialogActions onCancel={() => setShowOrderDialog(false)} submitLabel="Create Order" />
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={Boolean(reportOrder)} onOpenChange={(open) => !open && setReportOrder(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Radiology Report</DialogTitle>
            <DialogDescription>
              {reportOrder ? `${reportOrder.modality} · ${reportOrder.body_part}` : "Imaging report"}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={saveReport} className="space-y-4 pt-2">
            <div>
              <Label>Report *</Label>
              <Textarea
                className="mt-1.5 min-h-36"
                value={report}
                onChange={(event) => setReport(event.target.value)}
                required
              />
            </div>
            {error && <FormError message={error} />}
            <DialogActions onCancel={() => setReportOrder(null)} submitLabel="Save Report" />
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
      <ScanLine className="h-6 w-6 text-muted-foreground" />
    </div>
    <p className="font-semibold text-foreground">No imaging orders found</p>
    <p className="mt-1 text-sm text-muted-foreground">
      Create an order for X-ray, CT, MRI, or ultrasound.
    </p>
  </div>
);

const StatusBadge = ({ status }: { status: string }) => {
  const variant =
    status === "completed"
      ? "bg-emerald-500/10 text-emerald-700"
      : status === "ordered"
        ? "bg-amber-500/10 text-amber-700"
        : status === "cancelled"
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
  required,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  required?: boolean;
}) => (
  <div>
    <Label>
      {label}
      {required ? " *" : ""}
    </Label>
    <Input
      className="mt-1.5"
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
  <div className="flex gap-3">
    <Button type="button" variant="outline" className="flex-1" onClick={onCancel}>
      Cancel
    </Button>
    <Button type="submit" className="gradient-cta flex-1 border-0 text-primary-foreground">
      {submitLabel}
    </Button>
  </div>
);

const FormError = ({ message }: { message: string }) => (
  <p className="rounded-lg border border-destructive/20 bg-destructive/10 px-3 py-2 text-sm text-destructive">
    {message}
  </p>
);

export default Radiology;
