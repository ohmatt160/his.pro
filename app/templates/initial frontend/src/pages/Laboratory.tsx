import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { motion } from "framer-motion";
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  FlaskConical,
  Plus,
  Search,
  TestTube2,
  Users,
} from "lucide-react";
import { apiClient } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
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

type Patient = {
  id: string;
  first_name: string;
  last_name: string;
  full_name?: string;
};

type PatientListResponse = {
  patients: Patient[];
  total: number;
};

type LabTest = {
  id: string;
  name: string;
  code: string;
  description?: string | null;
  category?: string | null;
  unit?: string | null;
  reference_range?: string | null;
  price?: number | null;
  is_active: boolean;
};

type LabOrder = {
  id: string;
  patient_id: string;
  test_id: string;
  ordered_by: string;
  status: "PENDING" | "COLLECTED" | "IN_PROGRESS" | "COMPLETED" | "CANCELLED" | string;
  priority?: "ROUTINE" | "URGENT" | "STAT" | string | null;
  notes?: string | null;
  completed_at?: string | null;
  created_at: string;
};

type LabResult = {
  id: string;
  order_id: string;
  value?: string | null;
  is_abnormal?: boolean | null;
  notes?: string | null;
};

const emptyTestForm = {
  name: "",
  code: "",
  category: "",
  unit: "",
  reference_range: "",
  price: "",
  description: "",
};

const emptyOrderForm = {
  patient_id: "",
  test_id: "",
  priority: "ROUTINE",
  notes: "",
};

const emptyResultForm = {
  value: "",
  is_abnormal: false,
  notes: "",
};

const formatCurrency = (value?: number | null) =>
  new Intl.NumberFormat("en-NG", {
    style: "currency",
    currency: "NGN",
    maximumFractionDigits: 0,
  }).format(value || 0);

const Laboratory = () => {
  const navigate = useNavigate();
  const { facilitySlug = "" } = useParams();
  const [patients, setPatients] = useState<Patient[]>([]);
  const [tests, setTests] = useState<LabTest[]>([]);
  const [orders, setOrders] = useState<LabOrder[]>([]);
  const [results, setResults] = useState<Record<string, LabResult | null>>({});
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [showTestDialog, setShowTestDialog] = useState(false);
  const [showOrderDialog, setShowOrderDialog] = useState(false);
  const [resultOrder, setResultOrder] = useState<LabOrder | null>(null);
  const [testForm, setTestForm] = useState(emptyTestForm);
  const [orderForm, setOrderForm] = useState(emptyOrderForm);
  const [resultForm, setResultForm] = useState(emptyResultForm);
  const [error, setError] = useState("");

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

  const testNames = useMemo(
    () =>
      tests.reduce<Record<string, string>>((acc, test) => {
        acc[test.id] = `${test.name} (${test.code})`;
        return acc;
      }, {}),
    [tests]
  );

  const visibleOrders = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) {
      return orders;
    }

    return orders.filter((order) => {
      const patientName = patientNames[order.patient_id] || "";
      const testName = testNames[order.test_id] || "";
      return (
        patientName.toLowerCase().includes(query) ||
        testName.toLowerCase().includes(query) ||
        order.status.toLowerCase().includes(query) ||
        (order.priority || "").toLowerCase().includes(query)
      );
    });
  }, [orders, patientNames, search, testNames]);

  const summary = useMemo(
    () => ({
      pending: orders.filter((order) => order.status === "PENDING").length,
      inProgress: orders.filter((order) => order.status === "IN_PROGRESS").length,
      completed: orders.filter((order) => order.status === "COMPLETED").length,
    }),
    [orders]
  );

  const loadLaboratory = async () => {
    setLoading(true);
    try {
      const [patientResponse, testResponse, orderResponse] = await Promise.all([
        apiClient.get<PatientListResponse>("/patients?page=1&per_page=100"),
        apiClient.get<LabTest[]>("/laboratory/tests"),
        apiClient.get<LabOrder[]>("/laboratory/orders"),
      ]);
      setPatients(patientResponse.patients);
      setTests(testResponse);
      setOrders(orderResponse);

      const completedOrders = orderResponse.filter(
        (order) => order.status === "COMPLETED"
      );
      const resultEntries = await Promise.all(
        completedOrders.map(async (order) => {
          try {
            const result = await apiClient.get<LabResult>(
              `/laboratory/results/${order.id}`
            );
            return [order.id, result] as const;
          } catch {
            return [order.id, null] as const;
          }
        })
      );
      setResults(Object.fromEntries(resultEntries));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLaboratory().catch(() => {
      setPatients([]);
      setTests([]);
      setOrders([]);
      setLoading(false);
    });
  }, []);

  const createTest = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");

    if (!testForm.name.trim() || !testForm.code.trim()) {
      setError("Test name and code are required.");
      return;
    }

    try {
      await apiClient.post<LabTest>("/laboratory/tests", {
        name: testForm.name.trim(),
        code: testForm.code.trim().toUpperCase(),
        category: testForm.category.trim() || undefined,
        unit: testForm.unit.trim() || undefined,
        reference_range: testForm.reference_range.trim() || undefined,
        price: testForm.price ? Number(testForm.price) : undefined,
        description: testForm.description.trim() || undefined,
      });
      setTestForm(emptyTestForm);
      setShowTestDialog(false);
      await loadLaboratory();
    } catch (testError) {
      setError(testError instanceof Error ? testError.message : "Test creation failed.");
    }
  };

  const createOrder = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");

    if (!orderForm.patient_id || !orderForm.test_id) {
      setError("Patient and test are required.");
      return;
    }

    try {
      await apiClient.post<LabOrder>("/laboratory/orders", {
        patient_id: orderForm.patient_id,
        test_id: orderForm.test_id,
        priority: orderForm.priority,
        notes: orderForm.notes.trim() || undefined,
      });
      setOrderForm(emptyOrderForm);
      setShowOrderDialog(false);
      await loadLaboratory();
    } catch (orderError) {
      setError(orderError instanceof Error ? orderError.message : "Order creation failed.");
    }
  };

  const updateOrderStatus = async (order: LabOrder, status: string) => {
    await apiClient.put<LabOrder>(`/laboratory/orders/${order.id}`, { status });
    await loadLaboratory();
  };

  const saveResult = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!resultOrder) {
      return;
    }

    setError("");
    if (!resultForm.value.trim() && !resultForm.notes.trim()) {
      setError("Enter a result value or result note.");
      return;
    }

    try {
      await apiClient.post<LabResult>(`/laboratory/results/${resultOrder.id}`, {
        value: resultForm.value.trim() || undefined,
        is_abnormal: resultForm.is_abnormal,
        notes: resultForm.notes.trim() || undefined,
      });
      setResultForm(emptyResultForm);
      setResultOrder(null);
      await loadLaboratory();
    } catch (resultError) {
      setError(resultError instanceof Error ? resultError.message : "Result entry failed.");
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
            <h1 className="text-2xl font-extrabold tracking-tight">Laboratory</h1>
            <p className="text-sm text-muted-foreground">
              Manage lab tests, patient orders, and results.
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => setShowTestDialog(true)}>
              <Plus className="mr-2 h-4 w-4" /> Lab Test
            </Button>
            <Button
              onClick={() => setShowOrderDialog(true)}
              className="gradient-cta gap-2 border-0 text-primary-foreground"
            >
              <Plus className="h-4 w-4" /> New Order
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-6 p-6">
        <div className="grid gap-4 md:grid-cols-4">
          <Metric label="Active Tests" value={String(tests.length)} icon={TestTube2} />
          <Metric label="Pending" value={String(summary.pending)} icon={FlaskConical} />
          <Metric label="In Progress" value={String(summary.inProgress)} icon={AlertTriangle} />
          <Metric label="Completed" value={String(summary.completed)} icon={CheckCircle2} />
        </div>

        <div className="grid gap-6 xl:grid-cols-[1fr_360px]">
          <Card className="border-border/60">
            <CardHeader>
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <CardTitle className="text-base">Lab Orders</CardTitle>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                    placeholder="Search patient, test, status"
                    className="w-full pl-9 sm:w-72"
                  />
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {loading ? (
                <p className="py-12 text-center text-sm text-muted-foreground">
                  Loading lab workspace...
                </p>
              ) : visibleOrders.length === 0 ? (
                <EmptyState />
              ) : (
                <div className="space-y-2">
                  {visibleOrders.map((order, index) => {
                    const result = results[order.id];
                    return (
                      <motion.div
                        key={order.id}
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: index * 0.03 }}
                        className="grid gap-3 rounded-xl border border-border/60 p-4 transition-colors hover:border-primary/30 lg:grid-cols-[1.2fr_1fr_.8fr_auto]"
                      >
                        <div>
                          <p className="font-semibold text-foreground">
                            {patientNames[order.patient_id] || "Unknown patient"}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {testNames[order.test_id] || "Unknown test"}
                          </p>
                          {result?.value && (
                            <p className="mt-2 text-xs text-muted-foreground">
                              Result: <span className="font-medium text-foreground">{result.value}</span>
                              {result.is_abnormal ? " · Abnormal" : ""}
                            </p>
                          )}
                        </div>
                        <div>
                          <StatusBadge status={order.status} />
                          <p className="mt-1 text-xs text-muted-foreground">
                            Priority {order.priority || "ROUTINE"}
                          </p>
                        </div>
                        <div className="text-sm text-muted-foreground">
                          {order.notes || "No notes"}
                        </div>
                        <div className="flex flex-wrap gap-2 lg:justify-end">
                          {order.status === "PENDING" && (
                            <Button variant="outline" onClick={() => updateOrderStatus(order, "COLLECTED")}>
                              Collect
                            </Button>
                          )}
                          {order.status === "COLLECTED" && (
                            <Button variant="outline" onClick={() => updateOrderStatus(order, "IN_PROGRESS")}>
                              Start
                            </Button>
                          )}
                          {order.status !== "COMPLETED" && order.status !== "CANCELLED" && (
                            <Button
                              onClick={() => {
                                setError("");
                                setResultOrder(order);
                              }}
                            >
                              Enter Result
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
              <CardTitle className="text-base">Test Catalogue</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {tests.length === 0 ? (
                <p className="py-8 text-center text-sm text-muted-foreground">
                  No lab tests configured.
                </p>
              ) : (
                tests.map((test) => (
                  <div key={test.id} className="rounded-xl border border-border/60 p-3">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="font-semibold text-foreground">{test.name}</p>
                        <p className="text-xs text-muted-foreground">{test.code}</p>
                      </div>
                      <p className="text-sm font-semibold">{formatCurrency(test.price)}</p>
                    </div>
                    <p className="mt-2 text-xs text-muted-foreground">
                      {test.category || "General"}{test.unit ? ` · ${test.unit}` : ""}
                    </p>
                    {test.reference_range && (
                      <p className="mt-1 text-xs text-muted-foreground">
                        Ref: {test.reference_range}
                      </p>
                    )}
                  </div>
                ))
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

      <Dialog open={showTestDialog} onOpenChange={setShowTestDialog}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>Create Lab Test</DialogTitle>
            <DialogDescription>Add a test to the laboratory catalogue.</DialogDescription>
          </DialogHeader>
          <form onSubmit={createTest} className="grid gap-4 pt-2 sm:grid-cols-2">
            <Field label="Name" value={testForm.name} onChange={(value) => setTestForm((current) => ({ ...current, name: value }))} required />
            <Field label="Code" value={testForm.code} onChange={(value) => setTestForm((current) => ({ ...current, code: value }))} required />
            <Field label="Category" value={testForm.category} onChange={(value) => setTestForm((current) => ({ ...current, category: value }))} />
            <Field label="Unit" value={testForm.unit} onChange={(value) => setTestForm((current) => ({ ...current, unit: value }))} />
            <Field label="Reference Range" value={testForm.reference_range} onChange={(value) => setTestForm((current) => ({ ...current, reference_range: value }))} />
            <Field label="Price" type="number" value={testForm.price} onChange={(value) => setTestForm((current) => ({ ...current, price: value }))} />
            <div className="sm:col-span-2">
              <Label>Description</Label>
              <Textarea
                className="mt-1.5"
                value={testForm.description}
                onChange={(event) => setTestForm((current) => ({ ...current, description: event.target.value }))}
              />
            </div>
            {error && <FormError message={error} />}
            <DialogActions onCancel={() => setShowTestDialog(false)} submitLabel="Create Test" />
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={showOrderDialog} onOpenChange={setShowOrderDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New Lab Order</DialogTitle>
            <DialogDescription>Request a lab test for a patient.</DialogDescription>
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
              label="Test"
              value={orderForm.test_id}
              placeholder="Select test"
              options={tests.map((test) => ({ value: test.id, label: testNames[test.id] }))}
              onChange={(value) => setOrderForm((current) => ({ ...current, test_id: value }))}
            />
            <SelectField
              label="Priority"
              value={orderForm.priority}
              options={[
                { value: "ROUTINE", label: "Routine" },
                { value: "URGENT", label: "Urgent" },
                { value: "STAT", label: "Stat" },
              ]}
              onChange={(value) => setOrderForm((current) => ({ ...current, priority: value }))}
            />
            <div>
              <Label>Notes</Label>
              <Textarea
                className="mt-1.5"
                value={orderForm.notes}
                onChange={(event) => setOrderForm((current) => ({ ...current, notes: event.target.value }))}
              />
            </div>
            {error && <FormError message={error} />}
            <DialogActions onCancel={() => setShowOrderDialog(false)} submitLabel="Create Order" />
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={Boolean(resultOrder)} onOpenChange={(open) => !open && setResultOrder(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Enter Lab Result</DialogTitle>
            <DialogDescription>
              {resultOrder ? testNames[resultOrder.test_id] || "Lab order" : "Lab order"}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={saveResult} className="space-y-4 pt-2">
            <Field label="Result Value" value={resultForm.value} onChange={(value) => setResultForm((current) => ({ ...current, value }))} />
            <div className="flex items-center gap-2 rounded-lg border border-border/60 p-3">
              <Checkbox
                checked={resultForm.is_abnormal}
                onCheckedChange={(checked) =>
                  setResultForm((current) => ({ ...current, is_abnormal: checked === true }))
                }
                id="is_abnormal"
              />
              <Label htmlFor="is_abnormal" className="text-sm font-medium">
                Flag as abnormal
              </Label>
            </div>
            <div>
              <Label>Result Notes</Label>
              <Textarea
                className="mt-1.5"
                value={resultForm.notes}
                onChange={(event) => setResultForm((current) => ({ ...current, notes: event.target.value }))}
              />
            </div>
            {error && <FormError message={error} />}
            <DialogActions onCancel={() => setResultOrder(null)} submitLabel="Save Result" />
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
      <FlaskConical className="h-6 w-6 text-muted-foreground" />
    </div>
    <p className="font-semibold text-foreground">No lab orders found</p>
    <p className="mt-1 text-sm text-muted-foreground">
      Create a test and order it for a patient.
    </p>
  </div>
);

const StatusBadge = ({ status }: { status: string }) => {
  const variant =
    status === "COMPLETED"
      ? "bg-emerald-500/10 text-emerald-700"
      : status === "IN_PROGRESS"
        ? "bg-amber-500/10 text-amber-700"
        : status === "CANCELLED"
          ? "bg-destructive/10 text-destructive"
          : "bg-primary/10 text-primary";

  return (
    <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${variant}`}>
      {status.replace("_", " ")}
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

export default Laboratory;
